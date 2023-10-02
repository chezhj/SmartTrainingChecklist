"""
Base views for checklist
"""
from time import time
from django.shortcuts import get_object_or_404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse

# Create your views here.
from django.views import generic
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

    if len(check_items) == 0 and nextproc is not None:
        # If len(check_items) is zero and there's a next procedure, redirect to it
        return HttpResponseRedirect(reverse("checklist:detail", args=[nextproc.slug]))

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


def profile_view(request):
    """basic function view for the profile"""
    if "Clean" in request.GET:
        request.session.flush()

    # request.session["profile"] = 0

    attributes = Attribute.objects.order_by("order")

    return TemplateResponse(
        request,
        "checklist/profile.html",
        {
            "attributes": attributes,
        },
    )


def update_profile(request):
    """
    function that is called when profile is submitted
    Stores profile in session
    add default attributes
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
