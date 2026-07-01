from django.urls import path

from .views import (
    SelfAttendanceView,
    SelfKnowledgeView,
    SelfLeaveView,
    SelfPreferenceView,
    SelfProfileView,
    SelfSecurityLogView,
    SelfTimeCorrectionRequestView,
)

urlpatterns = [
    path("profile/", SelfProfileView.as_view(), name="self-profile"),
    path("security-log/", SelfSecurityLogView.as_view(), name="self-security-log"),
    path("preferences/", SelfPreferenceView.as_view(), name="self-preferences"),
    path("attendance/", SelfAttendanceView.as_view(), name="self-attendance"),
    path("time-corrections/", SelfTimeCorrectionRequestView.as_view(), name="self-time-corrections"),
    path("leave/", SelfLeaveView.as_view(), name="self-leave"),
    path("knowledge/", SelfKnowledgeView.as_view(), name="self-knowledge"),
]
