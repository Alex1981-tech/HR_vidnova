from django.urls import path

from .views import HeadcountReportView, SystemSecurityLogView, TenureReportView, TurnoverReportView

urlpatterns = [
    path("system-log/", SystemSecurityLogView.as_view(), name="report-system-log"),
    path("headcount/", HeadcountReportView.as_view(), name="report-headcount"),
    path("turnover/", TurnoverReportView.as_view(), name="report-turnover"),
    path("tenure/", TenureReportView.as_view(), name="report-tenure"),
]
