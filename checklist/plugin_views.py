"""
Plugin-facing API endpoints (API-key auth).

All endpoints in this file are called by the xFlow X-Plane plugin,
not by the browser. Auth is via Bearer token, not Django session.
"""

import logging
from datetime import datetime, timezone

from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    CheckItem,
    FlightItemState,
    FlightSession,
    FlightSessionAttribute,
    Procedure,
    UserProfile,
)

logger = logging.getLogger(__name__)


def _get_profile_from_api_key(request):
    """
    Resolve a UserProfile from an Authorization: Bearer <raw_key> header.
    Returns the profile on success, None on any failure.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    raw_key = auth[7:]
    for profile in UserProfile.objects.exclude(api_key_hash=None):
        if check_password(raw_key, profile.api_key_hash):
            return profile
    return None


@csrf_exempt
@require_POST
def plugin_check_next(request):
    """
    POST /api/plugin/check-next/

    Marks the next unchecked visible item in the session's active phase as
    manually checked. Called by the xFlow plugin on joystick/keyboard press.

    Responses:
        200  item was checked  {"checked": "<action_label>"}
        204  phase complete — nothing left to check
        401  bad or missing API key
        404  no active session, or no active phase, or procedure not found
    """
    profile = _get_profile_from_api_key(request)
    if profile is None:
        return JsonResponse({}, status=401)

    session = FlightSession.objects.filter(
        user_profile=profile, is_active=True
    ).first()
    if session is None:
        logger.info("check_next: no active session for user %s", profile.user.username)
        return JsonResponse({}, status=404)

    if not session.active_phase:
        logger.info("check_next: no active phase for user %s", profile.user.username)
        return JsonResponse({}, status=404)

    # Update last_plugin_contact — proof-of-life for the connection badge
    now = datetime.now(tz=timezone.utc)
    FlightSession.objects.filter(pk=session.pk).update(last_plugin_contact=now)

    try:
        procedure = Procedure.objects.get(slug=session.active_phase)
    except Procedure.DoesNotExist:
        logger.warning(
            "check_next: active_phase slug %r not found (user %s)",
            session.active_phase,
            profile.user.username,
        )
        return JsonResponse({}, status=404)

    active_attr_ids = list(
        FlightSessionAttribute.objects.filter(
            flight_session=session, is_active=True
        ).values_list("attribute_id", flat=True)
    )

    checked_ids = set(
        FlightItemState.objects.filter(
            flight_session=session, status="checked"
        ).values_list("checklist_item_id", flat=True)
    )

    next_item = None
    for item in CheckItem.objects.filter(procedure=procedure).order_by("step"):
        if item.pk in checked_ids:
            continue
        if item.shouldshow(active_attr_ids):
            next_item = item
            break

    if next_item is None:
        return JsonResponse({}, status=204)

    FlightItemState.objects.update_or_create(
        flight_session=session,
        checklist_item=next_item,
        defaults={
            "status": "checked",
            "source": "manual",
            "checked_at": now,
        },
    )

    return JsonResponse({"checked": next_item.action_label}, status=200)
