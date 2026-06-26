from django.urls import path

from .views import BotLinkByPhoneView

urlpatterns = [
    path("link-by-phone/", BotLinkByPhoneView.as_view(), name="bot-link-by-phone"),
]
