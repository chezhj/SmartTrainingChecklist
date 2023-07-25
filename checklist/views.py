from re import A
from select import select
from time import time
from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.db.models import Subquery

# Create your views here.
from django.http import HttpResponse
from django.views import generic
from .models import Procedure, Attribute

QUERYMETHOD = False


def procedure_detail(request, slug):
    tStart = time()
    procedure2view = get_object_or_404(Procedure.objects.all(), slug=slug)
    nextproc = (
        Procedure.objects.filter(step__gt=procedure2view.step).order_by("step").first()
    )
    prevproc = (
        Procedure.objects.filter(step__lt=procedure2view.step).order_by("step").last()
    )

    # profile2view = get_object_or_404(sessionKey=request.session.session_key)

    allitems = procedure2view.checkitem_set.all()
    query_ids = [
        item.id for item in allitems if item.shouldshow(request.session["attrib"])
    ]
    check_items = procedure2view.checkitem_set.filter(id__in=query_ids)

    tFinish = time()
    query_time = round(tFinish - tStart, 3)

    return TemplateResponse(
        request,
        "checklist/detail.html",
        {
            "procedure": procedure2view,
            "check_items": check_items,
            "nextproc": nextproc,
            "prevproc": prevproc,
            "proctime": query_time,
        },
    )


""" q = Model.objects.filter(...)...
# here is the trick
q_ids = [o.id for o in q if o.method()]
q = q.filter(id__in=q_ids) """


class IndexView(generic.ListView):
    template_name = "checklist/index.html"
    context_object_name = "procedure_list"

    def get_queryset(self):
        return Procedure.objects.order_by("step")


""" class DetailView(generic.DetailView):
    model = Procedure
    template_name = 'checklist/detail.html'
    
    def get_queryset(self, **kwargs):
        req_attr= Attribute.objects.get(id=1)
        return Procedure.objects.filter(checkitem__in=items) """


def profile_view(request):
    if "Clean" in request.GET:
        request.session.flush()

    request.session["profile"] = 0

    # if request.session.session_key:
    #     profile2view = SessionProfile.objects.filter(
    #         sessionKey=request.session.session_key
    #     ).first()
    #     # hier nog iets met fout aghandeling
    #     if profile2view:
    #         request.session["profile"] = profile2view.pk
    # else:
    #     profile2view = None

    attributes = Attribute.objects.order_by("order")

    return TemplateResponse(
        request,
        "checklist/profile.html",
        {
            "attributes": attributes,
        },
    )


def update_profile(request):
    # profile = None
    # if request.session.session_key:
    #     profile = SessionProfile.objects.filter(
    #         sessionKey=request.session.session_key
    #     ).first()
    # if not profile:
    #     profile = SessionProfile.objects.create()
    # profile.sessionKey = request.session.session_key
    # profile.attributes.clear()
    attrset = request.POST.getlist("attributes")
    attlist = []
    for att in attrset:
        attlist.append(int(att))
    request.session["attrib"] = attlist

    # for id in attrset:
    #    attribute2Add = get_object_or_404(Attribute.objects.all(), id=id)
    # profile.attributes.add(attribute2Add)
    # profile.save()
    return HttpResponseRedirect(reverse("checklist:index"))


class ProfileView(generic.DetailView):
    # model = SessionProfile
    template_name = "checklist/profile.html"
