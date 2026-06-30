from rest_framework.routers import DefaultRouter

from .views import (
    EmployeeLeavePolicyAssignmentViewSet,
    LeaveBalanceViewSet,
    LeaveLedgerEntryViewSet,
    LeavePolicyViewSet,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
)

router = DefaultRouter()
router.register("types", LeaveTypeViewSet, basename="leave-type")
router.register("policies", LeavePolicyViewSet, basename="leave-policy")
router.register("policy-assignments", EmployeeLeavePolicyAssignmentViewSet, basename="leave-policy-assignment")
router.register("ledger", LeaveLedgerEntryViewSet, basename="leave-ledger")
router.register("requests", LeaveRequestViewSet, basename="leave-request")
router.register("balances", LeaveBalanceViewSet, basename="leave-balance")

urlpatterns = router.urls
