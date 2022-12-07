from re import A
from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.template.response import  TemplateResponse
from django.urls import reverse

# Create your views here.
from django.http import HttpResponse
from django.views import generic
from .models import Procedure, SessionProfile, Attribute

def procedure_detail(request,slug):
    procedure2view= get_object_or_404(Procedure.objects.all(), slug=slug)
    nextproc=Procedure.objects.filter(step__gt=procedure2view.step).order_by('step').first()
    profile2view= get_object_or_404(SessionProfile.objects.all(), pk=1)
    no_action_attr = get_object_or_404(Attribute.objects.all(),pk=3)
    required_attr = get_object_or_404(Attribute.objects.all(),pk=1)
    #
    # If only required is not in the profile we want to show items that have no attributes
    """ if profile2view.attributes.filter(pk=4).count()==0:
        # filter like this gives double results for items if they have multiple attributes. The set operator makes them unique
        check_items=set(procedure2view.checkitem_set.filter(attributes__in=profile2view.attributes.all() ) 
                    | procedure2view.checkitem_set.filter(attributes__isnull=True)
                    | procedure2view.checkitem_set.filter(attributes__in=[required_attr] ))
    else: """
    check_items=set(procedure2view.checkitem_set.filter(attributes__in=profile2view.attributes.all() )  )
    
    # check if no_action_attri is in profile
    if no_action_attr not in profile2view.attributes.all():
        # need a copy of the set to be able to remove from set
        temp=list(check_items)
        for item in temp:
            # We don't want the no action items in the list
            if no_action_attr in item.attributes.all() :
                check_items.remove(item)
    return TemplateResponse(request,'checklist/detail.html', {'procedure':procedure2view, 'check_items':check_items, 'nextproc':nextproc})

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
    attributes=Attribute.objects.all()
    for attr in attributes:
        print(attr.sessionprofile_set.all())
            
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