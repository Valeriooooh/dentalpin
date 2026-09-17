# Changelog — treasury

## Unreleased

- `created_by` on every entry (new nullable column, `tre_0002`) +
  `treasury.transferred` / `treasury.corrected` events; accounts with
  ledger entries refuse DELETE with 409 (deactivate instead);
  table-level kind/amount guards (`tre_0003`); decimal edges are 422.

- Initial module: cash/bank accounts, paired transfers, manual
  corrections with required memos, derived balances, treasury page.
  Later (own design): payment/expense auto-posting, overdraft guards.
- Fix composable import depth in `pages/treasury/index.vue` (`../` →
  `../../`, TS2307 in CI frontend-typecheck) and stamp real
  `last_verified_commit` in the en/es screen docs.
