"""
Base views for checklist
"""

from time import time

from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect, get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import generic

from checklist.simbrief import SimBrief

from .models import (
    Attribute,
    FlightInfo,
    FlightItemState,
    FlightSession,
    FlightSessionAttribute,
    Procedure,
    UserAttributeDefault,
    UserProfile,
)


# ── SimBrief helpers ──────────────────────────────────────────────────────────

# Maps SimBrief-derived conditions to Attribute titles.
# Order matters: more specific conditions first.
_OFP_TEMP_RULES = [
    (lambda t: t < 0, "Anti-Ice Normal"),
    (lambda t: 0 < t < 11, "ZeroToTen"),
]
_OFP_BLEED_OFF_TITLE = "Short Runway"


def _derive_ofp_attrib_ids(sb_temp: str, sb_bleed: str) -> set[int]:
    """
    Return the set of Attribute IDs that the SimBrief OFP implies should be active.
    Looks up by title so PKs can vary across deployments.
    """
    derived: set[int] = set()
    attr_by_title = {a.title: a.id for a in Attribute.objects.all()}

    if sb_temp:
        try:
            temp = float(sb_temp.replace("°C", "").strip())
            for condition, title in _OFP_TEMP_RULES:
                if condition(temp):
                    if title in attr_by_title:
                        derived.add(attr_by_title[title])
                    break  # only one temperature band can apply
        except ValueError:
            pass

    if sb_bleed == "OFF":
        title = _OFP_BLEED_OFF_TITLE
        if title in attr_by_title:
            derived.add(attr_by_title[title])

    return derived


# ── Flight session creation ───────────────────────────────────────────────────


def _get_user_default_ids(user_profile) -> set[int]:
    """Return the set of Attribute IDs saved as defaults for the given user profile."""
    if user_profile is None:
        return set()
    return set(
        UserAttributeDefault.objects.filter(user_profile=user_profile)
        .values_list("attribute_id", flat=True)
    )


def _update_session_attributes(
    flight_session,
    selected_attr_ids: list[int],
    ofp_attr_ids: set[int],
    user_default_ids: set[int],
) -> None:
    """Apply attribute form choices to an existing FlightSession in-place."""
    selected_set = set(selected_attr_ids)
    for attr in Attribute.objects.all():
        is_active = (
            attr.id in selected_set
            or attr.id in ofp_attr_ids
            or attr.id in user_default_ids
        )
        if attr.id in ofp_attr_ids:
            source = "ofp_derived"
        elif attr.id in selected_set and attr.id not in user_default_ids:
            source = "pilot_override"
        else:
            source = "user_default"
        FlightSessionAttribute.objects.update_or_create(
            flight_session=flight_session,
            attribute=attr,
            defaults={"is_active": is_active, "source": source},
        )


def _create_flight_session(
    user_profile,
    selected_attr_ids: list[int],
    ofp_attr_ids: set[int],
    user_default_ids: set[int],
    simbrief_data: dict | None,
    pilot_role: str,
    pilot_function: str,
    active_phase: str = "",
) -> FlightSession:
    """
    Create a FlightSession with FlightSessionAttribute rows (one per Attribute)
    and optionally a FlightInfo record.

    Seeding priority (highest wins for is_active):
      OFP-derived  >  pilot selected on form  >  user saved default
    Source field reflects the origin of the value.
    """
    # Determine initial active_phase from first procedure if not supplied
    if not active_phase:
        first_proc = Procedure.objects.order_by("step").first()
        active_phase = first_proc.slug if first_proc else ""

    session = FlightSession.objects.create(
        user_profile=user_profile,
        pilot_role=pilot_role,
        pilot_function=pilot_function,
        active_phase=active_phase,
    )

    # Create one row per Attribute (eager seeding)
    all_attributes = Attribute.objects.all()
    session_attrs = []
    for attr in all_attributes:
        is_active = (
            attr.id in selected_attr_ids
            or attr.id in ofp_attr_ids
            or attr.id in user_default_ids
        )
        if attr.id in ofp_attr_ids:
            source = "ofp_derived"
        elif attr.id in selected_attr_ids and attr.id not in user_default_ids:
            source = "pilot_override"
        else:
            source = "user_default"
        session_attrs.append(
            FlightSessionAttribute(
                flight_session=session,
                attribute=attr,
                is_active=is_active,
                source=source,
            )
        )
    FlightSessionAttribute.objects.bulk_create(session_attrs)

    # Create FlightInfo if SimBrief data is available
    if simbrief_data and simbrief_data.get("origin"):
        try:
            oat = int(
                float(simbrief_data.get("temp", "").replace("°C", "").strip() or 0)
            )
        except ValueError:
            oat = None
        FlightInfo.objects.create(
            flight_session=session,
            origin_icao=simbrief_data.get("origin", ""),
            destination_icao=simbrief_data.get("destination", ""),
            departure_runway=simbrief_data.get("runway", ""),
            flaps_setting=simbrief_data.get("flaps", ""),
            callsign=simbrief_data.get("callsign", ""),
            block_fuel_kg=simbrief_data.get("block_fuel"),
            finres_altn_kg=simbrief_data.get("finres_altn"),
            oat=oat,
            ofp_loaded=True,
        )

    return session


# ── Profile / flight setup view ───────────────────────────────────────────────


def _fetch_and_cache_simbrief(request, simbrief_id: str) -> None:
    """Fetch a SimBrief plan and write all OFP session keys including derived conditions."""
    sb = SimBrief(simbrief_id)
    sb.fetch_data()
    request.session["sb_origin"] = getattr(sb, "origin", "") or ""
    request.session["sb_destination"] = getattr(sb, "destination", "") or ""
    request.session["sb_runway"] = getattr(sb, "runway", "") or ""
    request.session["sb_temp"] = getattr(sb, "temperature", "") or ""
    request.session["sb_flaps"] = getattr(sb, "flap_setting", "") or ""
    request.session["sb_bleed"] = getattr(sb, "bleed_setting", "") or ""
    request.session["sb_callsign"] = getattr(sb, "callsign", "") or ""
    request.session["sb_block_fuel"] = getattr(sb, "block_fuel", None)
    request.session["sb_finres_altn"] = getattr(sb, "finres_altn", None)
    request.session["sb_simbrief_id"] = simbrief_id
    derived = _derive_ofp_attrib_ids(
        request.session["sb_temp"], request.session["sb_bleed"]
    )
    request.session["sb_derived_attribs"] = list(derived)
    request.session["sb_error"] = getattr(sb, "error_message", "") or ""


def profile_view(request):
    """
    Flight setup page. Handles POST actions:
      get_plan        — fetch SimBrief OFP, cache in session, re-render
      start_checklist — create FlightSession + redirect to checklist
      clear           — deactivate session, re-fetch SimBrief from profile, return to setup
      new_flight      — deactivate session, return to setup for reconfiguration
    """
    # ── POST: clear ──────────────────────────────────────────────────────────
    if request.method == "POST" and request.POST.get("action") == "clear":
        _deactivate_current_session(request)
        _clear_flight_session_keys(request)
        simbrief_id = ""
        if request.user.is_authenticated:
            try:
                simbrief_id = request.user.profile.simbrief_id or ""
            except UserProfile.DoesNotExist:
                pass
        if simbrief_id:
            _fetch_and_cache_simbrief(request, simbrief_id)
        return redirect("checklist:start")

    # ── POST: get_plan ───────────────────────────────────────────────────────
    if request.method == "POST" and request.POST.get("action") == "get_plan":
        simbrief_id = request.POST.get("simbrief_id", "").strip()
        if simbrief_id:
            _fetch_and_cache_simbrief(request, simbrief_id)
        return redirect("checklist:start")

    # ── POST: new_flight — deactivate current session, return to setup ───────
    if request.method == "POST" and request.POST.get("action") == "new_flight":
        _deactivate_current_session(request)
        _clear_flight_session_keys(request)
        return redirect("checklist:start")

    # ── POST: start_checklist ─────────────────────────────────────────────────
    if request.method == "POST" and request.POST.get("action") == "start_checklist":
        selected_ids = [int(x) for x in request.POST.getlist("attributes")]
        ofp_ids = set(request.session.get("sb_derived_attribs", []))

        dual_mode = "dual_mode" in request.POST
        if dual_mode:
            pilot_role = "PF"
            pilot_function = "C"
        else:
            pilot_role = "SOLO"
            pilot_function = "BOTH"

        user_profile = None
        if request.user.is_authenticated:
            try:
                user_profile = request.user.profile
            except UserProfile.DoesNotExist:
                pass

        user_default_ids = _get_user_default_ids(user_profile)

        # Continue existing session in-place when one is already active
        existing_key = request.session.get("flight_session_key")
        if existing_key:
                try:
                    existing_session = FlightSession.objects.get(
                        session_key=existing_key, is_active=True
                    )
                    _update_session_attributes(
                        existing_session, selected_ids, ofp_ids, user_default_ids
                    )
                    if (
                        existing_session.pilot_role != pilot_role
                        or existing_session.pilot_function != pilot_function
                    ):
                        existing_session.pilot_role = pilot_role
                        existing_session.pilot_function = pilot_function
                        existing_session.save(update_fields=["pilot_role", "pilot_function"])
                    request.session["dual_mode"] = dual_mode
                    if dual_mode:
                        request.session["pilot_role"] = pilot_role
                        request.session["captain_role"] = "C"
                    active_slug = existing_session.active_phase
                    if active_slug:
                        return redirect("checklist:detail", slug=active_slug)
                    first_proc = Procedure.objects.order_by("step").first()
                    if first_proc:
                        return redirect("checklist:detail", slug=first_proc.slug)
                    return redirect("checklist:index")
                except FlightSession.DoesNotExist:
                    pass  # fall through to create new

        # Create a new session (no active session found)
        simbrief_data = _get_simbrief_session_data(request)
        _deactivate_current_session(request)

        session = _create_flight_session(
            user_profile=user_profile,
            selected_attr_ids=selected_ids,
            ofp_attr_ids=ofp_ids,
            user_default_ids=user_default_ids,
            simbrief_data=simbrief_data,
            pilot_role=pilot_role,
            pilot_function=pilot_function,
        )

        # Store session key — this is now the only flight-state key in Django session
        request.session["flight_session_key"] = session.session_key

        # Write role state so the existing toggle_switches.js / update_session_role
        # endpoint continue to work until they are migrated in a later step.
        request.session["dual_mode"] = dual_mode
        if dual_mode:
            request.session["pilot_role"] = "PF"
            request.session["captain_role"] = "C"

        first_proc = Procedure.objects.order_by("step").first()
        if first_proc:
            return redirect("checklist:detail", slug=first_proc.slug)
        return redirect("checklist:index")

    # ── GET (and unrecognised POSTs) ─────────────────────────────────────────
    simbrief_id = ""
    if request.user.is_authenticated:
        try:
            simbrief_id = request.user.profile.simbrief_id or ""
        except UserProfile.DoesNotExist:
            pass
    # Session-cached SimBrief ID overrides profile (user typed a different one)
    simbrief_id = request.session.get("sb_simbrief_id", simbrief_id)

    ofp_derived_ids = set(request.session.get("sb_derived_attribs", []))
    # Conditions: flight-specific (not user preference); General: user preference defaults
    conditions_attrs = Attribute.objects.filter(show=True, is_user_preference=False).order_by("order")
    general_attrs = Attribute.objects.filter(show=True, is_user_preference=True).order_by("order")

    user_profile = None
    if request.user.is_authenticated:
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            pass
    user_default_ids = _get_user_default_ids(user_profile)

    # Check for an active flight session
    active_flight_session = None
    existing_key = request.session.get("flight_session_key")
    if existing_key:
        try:
            active_flight_session = FlightSession.objects.get(
                session_key=existing_key, is_active=True
            )
        except FlightSession.DoesNotExist:
            pass

    # Pre-checked attribute IDs.
    # OFP-derived IDs are always included so loading a new plan updates the toggles.
    if active_flight_session:
        session_active_ids = set(
            FlightSessionAttribute.objects.filter(
                flight_session=active_flight_session, is_active=True
            ).values_list("attribute_id", flat=True)
        )
        prechecked_ids = session_active_ids | ofp_derived_ids
        dual_mode_active = active_flight_session.pilot_role != "SOLO"
    else:
        prechecked_ids = ofp_derived_ids | user_default_ids
        dual_mode_active = request.session.get("dual_mode", False)

    context = {
        "conditions_attrs": conditions_attrs,
        "general_attrs": general_attrs,
        "simbrief_id": simbrief_id,
        "sb_origin": request.session.get("sb_origin", ""),
        "sb_destination": request.session.get("sb_destination", ""),
        "sb_runway": request.session.get("sb_runway", ""),
        "sb_temp": request.session.get("sb_temp", ""),
        "sb_flaps": request.session.get("sb_flaps", ""),
        "sb_callsign": request.session.get("sb_callsign", ""),
        "sb_block_fuel": request.session.get("sb_block_fuel"),
        "sb_finres_altn": request.session.get("sb_finres_altn"),
        "sb_error": request.session.get("sb_error", ""),
        "ofp_derived_ids": ofp_derived_ids,
        "user_default_ids": user_default_ids,
        "active_flight_session": active_flight_session,
        "prechecked_ids": prechecked_ids,
        "dual_mode_active": dual_mode_active,
    }
    return TemplateResponse(request, "checklist/profile.html", context)


def _get_simbrief_session_data(request) -> dict | None:
    if request.session.get("sb_origin"):
        return {
            "origin": request.session.get("sb_origin", ""),
            "destination": request.session.get("sb_destination", ""),
            "runway": request.session.get("sb_runway", ""),
            "temp": request.session.get("sb_temp", ""),
            "flaps": request.session.get("sb_flaps", ""),
            "callsign": request.session.get("sb_callsign", ""),
            "block_fuel": request.session.get("sb_block_fuel"),
            "finres_altn": request.session.get("sb_finres_altn"),
        }
    return None


# All session keys that belong to a flight — cleared on reset, never on logout.
_FLIGHT_SESSION_KEYS = [
    "flight_session_key",
    "dual_mode",
    "pilot_role",
    "captain_role",
    "sb_origin",
    "sb_destination",
    "sb_runway",
    "sb_temp",
    "sb_flaps",
    "sb_bleed",
    "sb_callsign",
    "sb_block_fuel",
    "sb_finres_altn",
    "sb_derived_attribs",
    "sb_simbrief_id",
    "sb_error",
]


def _deactivate_current_session(request):
    key = request.session.get("flight_session_key")
    if key:
        FlightSession.objects.filter(session_key=key).update(is_active=False)


def _clear_flight_session_keys(request):
    """Remove all flight-state keys from the Django session, preserving auth state."""
    for k in _FLIGHT_SESSION_KEYS:
        request.session.pop(k, None)


# ── Checklist views ───────────────────────────────────────────────────────────


def procedure_detail(request, slug=None, pk=None):
    """Show all check items for the given procedure slug."""
    time_start = time()

    if slug:
        procedure2view = get_object_or_404(Procedure, slug=slug)
    else:
        procedure2view = get_object_or_404(Procedure, pk=pk)

    nextproc = (
        Procedure.objects.filter(step__gt=procedure2view.step).order_by("step").first()
    )
    prevproc = (
        Procedure.objects.filter(step__lt=procedure2view.step).order_by("step").last()
    )

    # Require an active flight session
    session_key = request.session.get("flight_session_key")
    if not session_key:
        return HttpResponseRedirect(reverse("checklist:start"))
    try:
        flight_session = FlightSession.objects.get(
            session_key=session_key, is_active=True
        )
    except FlightSession.DoesNotExist:
        return HttpResponseRedirect(reverse("checklist:start"))

    # Advance the active_phase frontier (forward-only)
    current_frontier = Procedure.objects.filter(slug=flight_session.active_phase).first()
    current_frontier_step = current_frontier.step if current_frontier else 0
    if procedure2view.step > current_frontier_step:
        flight_session.active_phase = procedure2view.slug
        flight_session.save(update_fields=["active_phase"])
    active_phase_step = max(procedure2view.step, current_frontier_step)

    active_attr_ids = list(
        FlightSessionAttribute.objects.filter(
            flight_session=flight_session, is_active=True
        ).values_list("attribute_id", flat=True)
    )

    allitems = procedure2view.checkitem_set.all()
    query_ids = [item.id for item in allitems if item.shouldshow(active_attr_ids)]
    filtered_check_items = procedure2view.checkitem_set.filter(id__in=query_ids)

    # Roles still come from session (migrated to FlightSession in a later step)
    pilot_role = request.session.get("pilot_role", None)
    captain_role = request.session.get("captain_role", None)
    dual_mode = request.session.get("dual_mode", False)

    check_items = []
    for item in filtered_check_items:
        item.lowlight = (
            dual_mode
            and item.role != "BOTH"
            and item.role not in [pilot_role, captain_role]
        )
        check_items.append(item)

    # Annotate items with server-side checked state (one query)
    state_map = {
        s.checklist_item_id: s
        for s in FlightItemState.objects.filter(
            flight_session=flight_session,
            checklist_item_id__in=[item.id for item in check_items],
        )
    }
    for item in check_items:
        state = state_map.get(item.id)
        if state and state.status == "checked":
            item.checked_css = f"ci-{state.source}"  # "ci-manual" or "ci-auto"
        else:
            item.checked_css = ""  # skipped/pending/absent → unchecked

    time_finished = time()
    query_time = round(time_finished - time_start, 3)

    if len(check_items) == 0:
        if nextproc and (nextproc.slug in request.META.get("HTTP_REFERER", "")):
            if prevproc:
                return HttpResponseRedirect(
                    reverse("checklist:detail", args=[prevproc.slug])
                )
        else:
            if nextproc:
                return HttpResponseRedirect(
                    reverse("checklist:detail", args=[nextproc.slug])
                )

    context = {
        "procedure": procedure2view,
        "check_items": check_items,
        "nextproc": nextproc,
        "prevproc": prevproc,
        "proctime": query_time,
        "all_procedures": Procedure.objects.order_by("step"),
        "flight_session": flight_session,
        "active_phase_step": active_phase_step,
    }
    return TemplateResponse(request, "checklist/detail.html", context)


class IndexView(generic.ListView):
    """List all procedures."""

    template_name = "checklist/index.html"
    context_object_name = "procedure_list"

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("flight_session_key"):
            return HttpResponseRedirect(reverse("checklist:start"))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Procedure.objects.order_by("step")


def update_session_role(request):
    """Updates the session with the selected roles (Pilot Role and Captain Role)."""
    if request.method == "POST":
        pilot_role = request.POST.get("pilot_role", "PM")
        captain_role = request.POST.get("captain_role", "FO")
        request.session["pilot_role"] = pilot_role
        request.session["captain_role"] = captain_role
        return JsonResponse(
            {"success": True, "pilot_role": pilot_role, "captain_role": captain_role}
        )
    return JsonResponse({"success": False}, status=400)
