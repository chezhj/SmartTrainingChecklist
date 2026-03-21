"""JSON API endpoints for checklist item state management."""

import json
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import CheckItem, FlightItemState, FlightSession


def _get_flight_session(request):
    """
    Return the active FlightSession for this request, or None.
    Looks up session_key stored in the Django session.
    """
    key = request.session.get("flight_session_key")
    if not key:
        return None
    try:
        return FlightSession.objects.get(session_key=key, is_active=True)
    except FlightSession.DoesNotExist:
        return None


def _parse_body(request):
    """
    Parse JSON request body. Returns (data, error_response).
    On success: (dict, None). On failure: (None, JsonResponse 400).
    """
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JsonResponse({"status": "error", "detail": "Invalid JSON."}, status=400)


@require_POST
def check_view(request):
    """
    POST /api/check/
    Body: { "check_item_id": <int> }
    Marks a checklist item as manually checked for the current flight session.
    """
    session = _get_flight_session(request)
    if session is None:
        return JsonResponse(
            {"status": "error", "detail": "No active flight session."}, status=403
        )

    data, err = _parse_body(request)
    if err:
        return err

    item_id = data.get("check_item_id")
    if not isinstance(item_id, int):
        return JsonResponse(
            {"status": "error", "detail": "check_item_id must be an integer."}, status=400
        )

    try:
        item = CheckItem.objects.get(pk=item_id)
    except CheckItem.DoesNotExist:
        return JsonResponse(
            {"status": "error", "detail": "Check item not found."}, status=400
        )

    FlightItemState.objects.update_or_create(
        flight_session=session,
        checklist_item=item,
        defaults={
            "status": "checked",
            "source": "manual",
            "checked_at": datetime.now(tz=timezone.utc),
        },
    )

    return JsonResponse({"status": "ok", "id": item_id, "source": "MANUAL"})


@require_POST
def uncheck_view(request):
    """
    POST /api/uncheck/
    Body: { "check_item_id": <int> }
    Removes the checked state for a checklist item (absence of row = unchecked).
    Idempotent — returns ok even if the item was not checked.
    """
    session = _get_flight_session(request)
    if session is None:
        return JsonResponse(
            {"status": "error", "detail": "No active flight session."}, status=403
        )

    data, err = _parse_body(request)
    if err:
        return err

    item_id = data.get("check_item_id")
    if not isinstance(item_id, int):
        return JsonResponse(
            {"status": "error", "detail": "check_item_id must be an integer."}, status=400
        )

    try:
        item = CheckItem.objects.get(pk=item_id)
    except CheckItem.DoesNotExist:
        return JsonResponse(
            {"status": "error", "detail": "Check item not found."}, status=400
        )

    FlightItemState.objects.filter(
        flight_session=session, checklist_item=item
    ).delete()

    return JsonResponse({"status": "ok", "id": item_id})
