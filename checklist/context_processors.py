"""
Custom context processors for the checklist app.
"""

from .models import SOP


def sop_context(request):
    """
    Injects the active SOP (first/only record) into every template context.

    Provides:
        sop          — SOP instance or None
        sop_icao     — icao_code string or ""
        sop_version  — content_version string or ""
        sop_notes    — release_notes string or ""
    """
    sop = SOP.objects.first()
    return {
        "sop": sop,
        "sop_icao": sop.icao_code if sop else "",
        "sop_version": sop.content_version if sop else "",
        "sop_notes": sop.release_notes if sop else "",
    }
