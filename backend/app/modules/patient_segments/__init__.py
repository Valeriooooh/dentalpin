"""patient_segments — clinic-local patient tags for grouping and campaigns."""

from fastapi import APIRouter

from app.core.plugins import BaseModule

from .models import PatientSegment, PatientSegmentLink
from .router import router


class PatientSegmentsModule(BaseModule):
    """Patient segments, surfaced on the patient page."""

    manifest = {
        "name": "patient_segments",
        "version": "0.1.0",
        "summary": "Clinic-local patient tags for grouping and campaigns.",
        "author": "DentalPin Core Team",
        "license": "BSL-1.1",
        "category": "community",
        "depends": ["patients"],
        "installable": True,
        # Optional module: ships inactive, the admin activates it from the
        # module admin UI (repo policy for new non-core modules).
        "auto_install": False,
        "removable": True,
        "role_permissions": {
            "admin": ["*"],
            "dentist": ["read", "write"],
            "hygienist": ["read"],
            "assistant": ["read", "write"],
            "receptionist": ["read", "write"],
        },
        "frontend": {
            "layer_path": "frontend",
            # No standalone nav entry — surfaces inline on the patient page
            # via the `patient.summary.cards` slot (slots.client.ts), same
            # extension point patient_relationships uses.
        },
    }

    def get_models(self) -> list:
        return [PatientSegment, PatientSegmentLink]

    def get_router(self) -> APIRouter:
        return router

    def get_permissions(self) -> list[str]:
        # Registry namespaces with the module name -> final perms are
        # ``patient_segments.read`` / ``patient_segments.write``.
        return ["read", "write"]
