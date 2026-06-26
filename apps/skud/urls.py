from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AccessDeviceViewSet,
    AccessEventViewSet,
    AccessIdentityViewSet,
    AccessSystemViewSet,
    CompanyAttendanceSummaryView,
    EmployeeAttendanceDetailView,
    EmployeeAttendancePeriodView,
    IntegrationRunViewSet,
    TimeCorrectionRequestViewSet,
    WorkDaySummaryViewSet,
)

router = DefaultRouter()
router.register("systems", AccessSystemViewSet, basename="access-system")
router.register("devices", AccessDeviceViewSet, basename="access-device")
router.register("identities", AccessIdentityViewSet, basename="access-identity")
router.register("events", AccessEventViewSet, basename="access-event")
router.register("workdays", WorkDaySummaryViewSet, basename="workday-summary")
router.register("time-correction-requests", TimeCorrectionRequestViewSet, basename="time-correction-request")
router.register("runs", IntegrationRunViewSet, basename="integration-run")

urlpatterns = [
    path("company-attendance/", CompanyAttendanceSummaryView.as_view(), name="company-attendance-summary"),
    path("employee-attendance/<int:employee_id>/", EmployeeAttendanceDetailView.as_view(), name="employee-attendance-detail"),
    path("employee-attendance/<int:employee_id>/periods/", EmployeeAttendancePeriodView.as_view(), name="employee-attendance-period-create"),
    path("employee-attendance/<int:employee_id>/periods/<int:period_id>/", EmployeeAttendancePeriodView.as_view(), name="employee-attendance-period-detail"),
] + router.urls
