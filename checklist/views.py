"""
Base views for checklist
"""

import csv
from time import time
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from datetime import timedelta
from django.utils.timezone import now

# Create your views here.
from django.views import generic

from checklist.simbrief import SimBrief
from .models import Procedure, Attribute


def procedure_detail(request, slug):
    """ "
    view/function to show all checkitems and attribs for the given slug
    based on the flight profile in the session
    """
    time_start = time()
    ## get the procedure to view based on slug
    procedure2view = get_object_or_404(Procedure.objects.all(), slug=slug)

    # get next and previous procedure to fill next and back button
    # As step does not need to have increments of 1, get the first or last
    # ordered by step, filtered by current step number
    nextproc = (
        Procedure.objects.filter(step__gt=procedure2view.step).order_by("step").first()
    )
    prevproc = (
        Procedure.objects.filter(step__lt=procedure2view.step).order_by("step").last()
    )
    # print(request.)
    # Check if profile exits
    if "attrib" not in request.session:
        return HttpResponseRedirect(reverse("checklist:start"))

    allitems = procedure2view.checkitem_set.all()
    query_ids = [
        item.id for item in allitems if item.shouldshow(request.session["attrib"])
    ]
    check_items = procedure2view.checkitem_set.filter(id__in=query_ids)

    time_finished = time()
    query_time = round(time_finished - time_start, 3)

    # If len(check_items) is zero and there's a next procedure, redirect to it
    if len(check_items) == 0:
        # Check if referrer is same as next
        if nextproc and (nextproc.slug in request.META["HTTP_REFERER"]):
            if prevproc:
                return HttpResponseRedirect(
                    reverse("checklist:detail", args=[prevproc.slug])
                )
        ##and nextproc is not None:
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
    }
    return TemplateResponse(
        request,
        "checklist/detail.html",
        context,
    )


class IndexView(generic.ListView):
    """basic class view to show all procedures"""

    template_name = "checklist/index.html"
    context_object_name = "procedure_list"

    def get_queryset(self):
        return Procedure.objects.order_by("step")


def update_profile_with_simbrief(request, simbrief):
    """
    Update the session['attrib'] list based on SimBrief data.
    """
    # Retrieve the current attribute list from the session
    attlist = request.session.get("attrib", [])

    # Extract cleaned temperature once
    if simbrief.temperature:
        cleaned_temperature = float(simbrief.temperature.replace("°C", ""))

        # Example condition: Add attribute ID 7 if temperature is below 0°C
        if cleaned_temperature < 0:
            if 7 not in attlist:
                attlist.append(7)

        # Example condition: Add attribute ID 10 if temperature is between 0°C and 10°C
        if 0 < cleaned_temperature < 11:
            if 9 not in attlist:
                attlist.append(9)
            if 7 in attlist:
                attlist.remove(7)

        # if temperature is above 10°C, remove attribute ID 9 and 7
        if cleaned_temperature > 10:
            if 9 in attlist:
                attlist.remove(9)
            if 7 in attlist:
                attlist.remove(7)

    # if bleeds are off, add attribute ID 8
    if simbrief.bleed_setting == "OFF":
        if 8 not in attlist:
            attlist.append(8)
    else:
        if 8 in attlist:
            attlist.remove(8)

    # Update the session with the modified attribute list
    request.session["attrib"] = attlist


def profile_view(request):

    if request.method == "POST":
        # Handle the "Clean" action
        if "Clean" in request.POST:
            print("Cleaning session")
            request.session.flush()

    # Retrieve simbrief_pilot_id from the cookie or request.POST
    simbrief_pilot_id = request.COOKIES.get("simbrief_pilot_id")
    if not simbrief_pilot_id and "simbrief_id" in request.POST:
        simbrief_pilot_id = request.POST["simbrief_id"]

    # Create SimBrief object and fetch data
    simbrief = SimBrief(simbrief_pilot_id)
    simbrief.fetch_data()

    # Update the session['attrib'] list based on SimBrief data
    update_profile_with_simbrief(request, simbrief)

    # Add a cookie for simbrief_pilot_id if "remember_me" is in the GET request
    response = TemplateResponse(
        request,
        "checklist/profile.html",
        {
            "attributes": Attribute.objects.order_by("order"),
            "origin": simbrief.origin or "Unknown",
            "elevation": simbrief.elevation or "Unknown",
            "temperature": simbrief.temperature or "Unknown",
            "runway": simbrief.runway or "Unknown",
            "rwy_length": simbrief.rwy_length or "Unknown",
            "altimeter": simbrief.altimeter or "Unknown",
            "flap_setting": simbrief.flap_setting or "Unknown",
            "bleed_setting": simbrief.bleed_setting or "Unknown",
            "simbrief_id": simbrief.pilot_id or "",
            "error_message": simbrief.error_message or "",
        },
    )

    # set cookie if remember me is checked or if cookie already exists
    if (request.COOKIES.get("simbrief_pilot_id")) or (
        "remember_me" in request.POST and simbrief_pilot_id
    ):
        expiration_date = now() + timedelta(days=31)
        response.set_cookie(
            "simbrief_pilot_id",
            simbrief_pilot_id,
            expires=expiration_date,
            secure=True,  # Ensures the cookie is sent over HTTPS only
            httponly=True,  # Prevents JavaScript access to the cookie
            samesite="Lax",  # Restricts cross-site cookie sharing
        )

    return response


def update_profile(request):
    """
    function that is called when profile is submitted
    Stores profile in session
    add default attributes, that is non visible
    and removes default if related attrib is selected
    """

    attlist = []

    over_rules = {}
    non_visual_attributes = list(Attribute.objects.filter(show=False))

    for default_attrib in non_visual_attributes:
        attlist.append(default_attrib.id)
        if default_attrib.over_ruled_by:
            over_rules[default_attrib.over_ruled_by.id] = default_attrib.id

    attrset = request.POST.getlist("attributes")

    for att in attrset:
        attlist.append(int(att))
        if over_rules.get(int(att), None):
            attlist.remove(over_rules[int(att)])

    request.session["attrib"] = attlist

    return HttpResponseRedirect(reverse("checklist:index"))
