from django.urls import path

from .views import HeadcountReportView, TenureReportView, TurnoverReportView

urlpatterns = [
    path("headcount/", HeadcountReportView.as_view(), name="report-headcount"),
    path("turnover/", TurnoverReportView.as_view(), name="report-turnover"),
    path("tenure/", TenureReportView.as_view(), name="report-tenure"),
]
