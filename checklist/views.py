from re import A
from select import select
from time  import time
from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.template.response import  TemplateResponse
from django.urls import reverse
from django.db.models import Subquery

# Create your views here.
from django.http import HttpResponse
from django.views import generic
from .models import Procedure, SessionProfile, Attribute

QUERYMETHOD = False

def procedure_detail(request,slug):
    tStart = time()
    procedure2view= get_object_or_404(Procedure.objects.all(), slug=slug)
    nextproc=Procedure.objects.filter(step__gt=procedure2view.step).order_by('step').first()
    prevproc=Procedure.objects.filter(step__lt=procedure2view.step).order_by('step').last()
    
    profile2view= get_object_or_404(SessionProfile.objects.all(), pk=1)
    if QUERYMETHOD:    
        if profile2view.attributes.filter(pk=3).count()==0 :
            selected_item_id=procedure2view.checkitem_set.filter(attributes__in=profile2view.attributes.all()
                ).exclude(attributes__pk=3).values('pk').distinct()
        elif profile2view.attributes.filter(pk=4).count()==0 :
            selected_item_id=procedure2view.checkitem_set.filter(attributes__in=profile2view.attributes.all()
                ).exclude(attributes__pk=4).values('pk').distinct() 
        else:
            selected_item_id=procedure2view.checkitem_set.filter(attributes__in=profile2view.attributes.all()).values('pk').distinct()    
        #selected_item_id=procedure2view.checkitem_set.filter(attributes__in=profile2view.attributes.all()).values('pk').distinct()
        zero_items=procedure2view.checkitem_set.filter(attributes__isnull=True).values('pk').distinct()
   
        
        #check_items=procedure2view.checkitem_set.filter(attributes__in=profile2view.attributes.all())| procedure2view.checkitem_set.filter(attributes__isnull=True)
        check_items=procedure2view.checkitem_set.filter(pk__in=selected_item_id|zero_items)
    else:
        allitems=procedure2view.checkitem_set.all()
        query_ids = [item.id for item in allitems if item.shouldshow(profile2view)]
        check_items=procedure2view.checkitem_set.filter(id__in=query_ids)

        """ q = Model.objects.filter(...)...
        # here is the trick
        q_ids = [o.id for o in q if o.method()]
        q = q.filter(id__in=q_ids) """
        pass
 
   
    
    tFinish=time()
    query_time=round(tFinish - tStart,3)

    return TemplateResponse(request,'checklist/detail.html', {'procedure':procedure2view, 'check_items':check_items, 'nextproc':nextproc,'prevproc':prevproc,'proctime': query_time })


""" q = Model.objects.filter(...)...
# here is the trick
q_ids = [o.id for o in q if o.method()]
q = q.filter(id__in=q_ids) """

class IndexView(generic.ListView):
    template_name = 'checklist/index.html'
    context_object_name = 'procedure_list'

    def get_queryset(self):
        return Procedure.objects.order_by('step')


""" class DetailView(generic.DetailView):
    model = Procedure
    template_name = 'checklist/detail.html'
    
    def get_queryset(self, **kwargs):
        req_attr= Attribute.objects.get(id=1)
        return Procedure.objects.filter(checkitem__in=items) """

def profile_view(request):
    profile2view= get_object_or_404(SessionProfile.objects.all(), pk=1)
    attributes=Attribute.objects.order_by('order')
            
    return TemplateResponse(request,'checklist/profile.html', {'profile':profile2view, 'attributes':attributes})

def update_profile(request):
    profile= get_object_or_404(SessionProfile.objects.all(), pk=1)
    profile.attributes.clear()
    attrset=request.POST.getlist('attributes')
    for id in attrset:
        attribute2Add = get_object_or_404(Attribute.objects.all(), id=id)
        profile.attributes.add(attribute2Add)
    profile.save()    
    return HttpResponseRedirect(reverse('checklist:index') )


  


class ProfileView(generic.DetailView):
    model = SessionProfile
    template_name = 'checklist/profile.html'