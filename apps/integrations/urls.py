from django.urls import path

from .webhook_views import PeopleForceWebhookView

urlpatterns = [
    path("peopleforce/webhook/", PeopleForceWebhookView.as_view(), name="peopleforce-webhook"),
    path("peopleforce/webhook", PeopleForceWebhookView.as_view(), name="peopleforce-webhook-noslash"),
]
