from django.urls import path

from checklist.export_view import ExportChecklistView

from . import views
from .api_views import attribute_transition_view, check_view, poll_view, uncheck_view
from .auth_views import account_profile_view, delete_account_view
from .plugin_views import plugin_check_next, plugin_session, plugin_state

app_name = "checklist"
urlpatterns = [
    path("", views.profile_view, name="start"),
    path("procedures/", views.IndexView.as_view(), name="index"),
    path("<int:pk>/", views.procedure_detail, name="detailpk"),
    path("<slug:slug>", views.procedure_detail, name="detail"),
    path("profile/", views.profile_view, name="profile"),
    path("export/", ExportChecklistView.as_view(), name="export"),
    path("update-session-role/", views.update_session_role, name="update_session_role"),
    path("account/", account_profile_view, name="account"),
    path("account/delete/", delete_account_view, name="delete_account"),
    path("api/poll/", poll_view, name="api_poll"),
    path("api/check/", check_view, name="api_check"),
    path("api/uncheck/", uncheck_view, name="api_uncheck"),
    path("api/attribute-transition/", attribute_transition_view, name="api_attribute_transition"),
    path("api/plugin/check-next/", plugin_check_next, name="api_plugin_check_next"),
    path("api/plugin/session/", plugin_session, name="api_plugin_session"),
    path("api/plugin/state/", plugin_state, name="api_plugin_state"),
]
