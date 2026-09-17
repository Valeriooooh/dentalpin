"""TreasuryService — accounts, transfers, corrections, balances.

The ledger is append-only: money moves via paired transfer legs sharing
a ``group_id``, or single manual corrections (memo required — silent
money edits are an audit hole). Balances are always derived
(opening + signed entries), never stored. Payment/expense auto-posting
is explicitly Later.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import EventType, event_bus

from .models import TreasuryAccount, TreasuryEntry

_SIGN = {
    "transfer_out": Decimal("-1"),
    "transfer_in": Decimal("1"),
    "correction_in": Decimal("1"),
    "correction_out": Decimal("-1"),
    "opening": Decimal("1"),
}


class TreasuryService:
    @staticmethod
    async def list_accounts(db: AsyncSession, clinic_id: UUID) -> list[TreasuryAccount]:
        stmt = (
            select(TreasuryAccount)
            .where(TreasuryAccount.clinic_id == clinic_id)
            .order_by(TreasuryAccount.name)
        )
        return (await db.execute(stmt)).scalars().all()

    @staticmethod
    async def get_account(
        db: AsyncSession, clinic_id: UUID, account_id: UUID
    ) -> TreasuryAccount | None:
        stmt = select(TreasuryAccount).where(
            TreasuryAccount.id == account_id, TreasuryAccount.clinic_id == clinic_id
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def balance(db: AsyncSession, account: TreasuryAccount) -> Decimal:
        rows = (
            await db.execute(
                select(TreasuryEntry.kind, TreasuryEntry.amount).where(
                    TreasuryEntry.account_id == account.id,
                    TreasuryEntry.clinic_id == account.clinic_id,
                )
            )
        ).all()
        signed = sum(
            (TreasuryService._signed(kind, amount) for kind, amount in rows),
            Decimal("0"),
        )
        return (account.opening_balance or Decimal("0")) + signed

    @staticmethod
    def _signed(kind: str, amount: Decimal) -> Decimal:
        """Sign an entry amount — unknown kinds raise instead of vanishing."""
        try:
            return _SIGN[kind] * amount
        except KeyError:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown entry kind: {kind}",
            ) from None

    @staticmethod
    async def create_account(db: AsyncSession, clinic_id: UUID, data: dict) -> TreasuryAccount:
        row = TreasuryAccount(clinic_id=clinic_id, **data)
        if row.opening_balance is not None:
            row.opening_balance = row.opening_balance.quantize(Decimal("0.01"))
        db.add(row)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="An account with this name already exists",
            ) from exc
        except DataError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Opening balance is out of range",
            ) from exc
        return row

    @staticmethod
    async def update_account(db: AsyncSession, row: TreasuryAccount, data: dict) -> TreasuryAccount:
        for key, value in data.items():
            setattr(row, key, value)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="An account with this name already exists",
            ) from exc
        return row

    @staticmethod
    async def delete_account(db: AsyncSession, row: TreasuryAccount) -> None:
        # Refuse when ledger history exists — deleting an account with
        # entries would drop its audit trail (entries cascade). Deactivate
        # via PATCH instead (AccountUpdate.is_active).
        entries = (
            await db.execute(
                select(func.count())
                .select_from(TreasuryEntry)
                .where(TreasuryEntry.account_id == row.id)
            )
        ).scalar_one()
        if entries:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Account has ledger entries — deactivate it instead of deleting",
            )
        await db.delete(row)
        await db.flush()

    @staticmethod
    async def transfer(
        db: AsyncSession,
        clinic_id: UUID,
        from_account: TreasuryAccount,
        to_account: TreasuryAccount,
        amount: Decimal,
        memo: str | None,
        at: datetime | None,
        created_by: UUID | None = None,
    ) -> list[TreasuryEntry]:
        if from_account.id == to_account.id:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Source and destination must differ",
            )
        stamp = at or datetime.now(UTC)
        amount = amount.quantize(Decimal("0.01"))
        group_id = uuid4()
        legs = [
            TreasuryEntry(
                clinic_id=clinic_id,
                account_id=from_account.id,
                group_id=group_id,
                kind="transfer_out",
                amount=amount,
                at=stamp,
                memo=memo,
                created_by=created_by,
            ),
            TreasuryEntry(
                clinic_id=clinic_id,
                account_id=to_account.id,
                group_id=group_id,
                kind="transfer_in",
                amount=amount,
                at=stamp,
                memo=memo,
                created_by=created_by,
            ),
        ]
        db.add_all(legs)
        await db.flush()
        await event_bus.publish(
            EventType.TREASURY_TRANSFERRED,
            {
                "clinic_id": str(clinic_id),
                "group_id": str(group_id),
                "from_account_id": str(from_account.id),
                "to_account_id": str(to_account.id),
                "amount": str(amount),
                "created_by": str(created_by) if created_by else None,
            },
            db=db,
        )
        return legs

    @staticmethod
    async def correct(
        db: AsyncSession,
        clinic_id: UUID,
        account: TreasuryAccount,
        amount: Decimal,
        direction: str,
        memo: str,
        at: datetime | None,
        created_by: UUID | None = None,
    ) -> TreasuryEntry:
        row = TreasuryEntry(
            clinic_id=clinic_id,
            account_id=account.id,
            group_id=uuid4(),
            kind=f"correction_{direction}",
            amount=amount.quantize(Decimal("0.01")),
            at=at or datetime.now(UTC),
            memo=memo,
            created_by=created_by,
        )
        db.add(row)
        await db.flush()
        await event_bus.publish(
            EventType.TREASURY_CORRECTED,
            {
                "clinic_id": str(clinic_id),
                "account_id": str(account.id),
                "entry_id": str(row.id),
                "amount": str(row.amount),
                "direction": direction,
                "memo": memo,
                "created_by": str(created_by) if created_by else None,
            },
            db=db,
        )
        return row

    @staticmethod
    async def statement(
        db: AsyncSession, clinic_id: UUID, account_id: UUID, limit: int = 100
    ) -> list[TreasuryEntry]:
        stmt = (
            select(TreasuryEntry)
            .where(
                TreasuryEntry.account_id == account_id,
                TreasuryEntry.clinic_id == clinic_id,
            )
            .order_by(TreasuryEntry.at.desc(), TreasuryEntry.created_at.desc())
            .limit(min(limit, 500))
        )
        return (await db.execute(stmt)).scalars().all()
