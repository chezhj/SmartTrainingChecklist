from django.urls import path

from . import views

app_name = 'checklist'
urlpatterns = [
    path('', views.profile_view, name='start'),
    path('procedures/', views.IndexView.as_view(), name='index'),
    path('<int:pk>/', views.procedure_detail, name='detailpk'),
    path("<slug:slug>", views.procedure_detail, name="detail"),
    path('profile/', views.profile_view, name='profile'),
    path('update_profile/', views.update_profile, name='update_profile')
    ]