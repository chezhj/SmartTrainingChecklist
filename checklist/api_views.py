"""JSON API endpoints for checklist item state management."""

import json
from datetime import datetime, timezone

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Attribute, CheckItem, FlightItemState, FlightSession, FlightSessionAttribute, Procedure
from .rules import collect_leaf_evaluations, evaluate_rule


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


@require_GET
def poll_view(request):
    """
    GET /api/poll/?procedure=<slug>&since=<unix_timestamp>
    Returns checked items newer than `since` and the current sim connection state.
    No session → returns an empty-but-valid response (not 403).
    """
    session = _get_flight_session(request)
    if session is None:
        return JsonResponse({"checked_items": [], "sim_connected": False, "last_seen": 0})

    try:
        since_ts = int(request.GET.get("since", 0) or 0)
    except (ValueError, TypeError):
        since_ts = 0
    since_dt = datetime.fromtimestamp(since_ts, tz=timezone.utc)

    states = FlightItemState.objects.filter(
        flight_session=session,
        status__in=("checked", "skipped"),
        checked_at__gt=since_dt,
    ).select_related("checklist_item")

    checked_items = [
        {
            "id": s.checklist_item.pk,
            "source": "SKIPPED" if s.status == "skipped" else s.source.upper(),
        }
        for s in states
    ]

    last_seen = 0
    sim_connected = False
    sim_initializing = False
    if session.last_plugin_contact:
        last_seen = int(session.last_plugin_contact.timestamp())
        age = (datetime.now(tz=timezone.utc) - session.last_plugin_contact).total_seconds()
        sim_connected = age < 5
        sim_initializing = not sim_connected and age < 15

    response = {
        "checked_items": checked_items,
        "sim_connected": sim_connected,
        "sim_initializing": sim_initializing,
        "last_seen": last_seen,
    }

    if settings.DEBUG and session is not None:
        from .plugin_views import _last_datarefs
        procedure_slug = request.GET.get("procedure", "")
        last_state = _last_datarefs.get(session.pk, {})
        debug_rules = []
        if procedure_slug:
            try:
                procedure = Procedure.objects.get(slug=procedure_slug)
                active_attr_ids = list(
                    FlightSessionAttribute.objects.filter(
                        flight_session=session, is_active=True
                    ).values_list("attribute_id", flat=True)
                )
                done_ids = set(
                    FlightItemState.objects.filter(
                        flight_session=session, status__in=("checked", "skipped")
                    ).values_list("checklist_item_id", flat=True)
                )
                all_items = list(
                    CheckItem.objects.filter(procedure=procedure)
                    .prefetch_related("attributes")
                    .order_by("step")
                )
                visible_items = [i for i in all_items if i.shouldshow(active_attr_ids)]

                _OPTIONAL_ATTR = 4

                def _is_optional(item):
                    return any(a.pk == _OPTIONAL_ATTR for a in item.attributes.all())

                gate_step = None
                for item in visible_items:
                    if item.pk not in done_ids and not _is_optional(item):
                        gate_step = item.step
                        break

                active_items = [
                    i for i in visible_items
                    if i.pk not in done_ids and (gate_step is None or i.step <= gate_step)
                ]

                for item in active_items:
                    if item.auto_check_rule is None:
                        continue
                    debug_rules.append({
                        "item_id": item.pk,
                        "item": item.item,
                        "step": item.step,
                        "is_gate": item.step == gate_step and not _is_optional(item),
                        "rule_pass": evaluate_rule(item.auto_check_rule, last_state),
                        "conditions": collect_leaf_evaluations(item.auto_check_rule, last_state),
                    })
            except Exception:
                pass
        response["debug_rules"] = debug_rules

        # Attribute live_rule evaluations
        debug_attributes = []
        try:
            active_attr_ids_set = set(
                FlightSessionAttribute.objects.filter(
                    flight_session=session, is_active=True
                ).values_list("attribute_id", flat=True)
            )
            for attr in Attribute.objects.exclude(live_rule=None).order_by("order"):
                if not attr.live_rule:
                    continue
                debug_attributes.append({
                    "attr_id": attr.pk,
                    "title": attr.title,
                    "label": attr.label,
                    "is_active": attr.pk in active_attr_ids_set,
                    "rule_pass": evaluate_rule(attr.live_rule, last_state),
                    "conditions": collect_leaf_evaluations(attr.live_rule, last_state),
                })
        except Exception:
            pass
        response["debug_attributes"] = debug_attributes

    return JsonResponse(response)


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


@require_GET
def attribute_transition_view(request):
    """
    GET /api/attribute-transition/

    Evaluates Attribute.live_rule for every attribute that has one, using the
    latest cached dataref snapshot from the plugin. Called by the browser
    before navigating to a new procedure.

    Responses:
        200  {
               "applied":  [<attr_id>, ...],   # silently activated (activate_only)
               "prompts":  [                   # returned to browser for pilot to confirm
                 {
                   "attr_id": <int>,
                   "attr_title": "<str>",
                   "prompt_message": "<str>",
                   "currently_active": <bool>,
                   "suggested_active": <bool>
                 }, ...
               ]
             }

    Attributes already in session.pilot_overrides are skipped (pilot decided
    this session). Attributes without live_rule or live_rule_mode are ignored.
    """
    from .plugin_views import _last_datarefs  # in-process cache, no DB round-trip

    session = _get_flight_session(request)
    if session is None:
        return JsonResponse({"applied": [], "prompts": []})

    datarefs = _last_datarefs.get(session.pk, {})
    overrides = session.pilot_overrides  # {str(attr_id): bool}

    applied = []
    prompts = []

    attrs = Attribute.objects.exclude(live_rule=None).exclude(live_rule_mode="")
    for attr in attrs:
        if not attr.live_rule_mode:
            continue

        attr_id_str = str(attr.pk)
        if attr_id_str in overrides:
            continue  # pilot has already decided for this session

        rule_fires = evaluate_rule(attr.live_rule, datarefs)

        fsa = FlightSessionAttribute.objects.filter(
            flight_session=session, attribute=attr
        ).first()
        currently_active = fsa.is_active if fsa else False

        if attr.live_rule_mode == "activate_only":
            if rule_fires and not currently_active:
                FlightSessionAttribute.objects.update_or_create(
                    flight_session=session,
                    attribute=attr,
                    defaults={"is_active": True, "source": "live_rule"},
                )
                applied.append(attr.pk)

        elif attr.live_rule_mode == "prompt_on_change":
            if rule_fires != currently_active:
                prompts.append({
                    "attr_id": attr.pk,
                    "attr_title": attr.label or attr.title,
                    "prompt_message": attr.prompt_message,
                    "currently_active": currently_active,
                    "suggested_active": rule_fires,
                })

    return JsonResponse({"applied": applied, "prompts": prompts})
