from django.urls import path

from .views import SelfAttendanceView, SelfKnowledgeView, SelfLeaveView, SelfProfileView, SelfTimeCorrectionRequestView

urlpatterns = [
    path("profile/", SelfProfileView.as_view(), name="self-profile"),
    path("attendance/", SelfAttendanceView.as_view(), name="self-attendance"),
    path("time-corrections/", SelfTimeCorrectionRequestView.as_view(), name="self-time-corrections"),
    path("leave/", SelfLeaveView.as_view(), name="self-leave"),
    path("knowledge/", SelfKnowledgeView.as_view(), name="self-knowledge"),
]
