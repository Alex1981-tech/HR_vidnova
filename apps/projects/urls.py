from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet, TimeEntryViewSet

router = DefaultRouter()
router.register("time-entries", TimeEntryViewSet, basename="time-entry")
router.register("", ProjectViewSet, basename="project")

urlpatterns = router.urls
