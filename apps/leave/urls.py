from rest_framework.routers import DefaultRouter

from .views import LeaveBalanceViewSet, LeaveRequestViewSet, LeaveTypeViewSet

router = DefaultRouter()
router.register("types", LeaveTypeViewSet, basename="leave-type")
router.register("requests", LeaveRequestViewSet, basename="leave-request")
router.register("balances", LeaveBalanceViewSet, basename="leave-balance")

urlpatterns = router.urls
