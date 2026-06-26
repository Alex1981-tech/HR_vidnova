from rest_framework.routers import DefaultRouter

from .views import KnowledgeCategoryViewSet, KnowledgeDocumentViewSet

router = DefaultRouter()
router.register("categories", KnowledgeCategoryViewSet, basename="knowledge-category")
router.register("documents", KnowledgeDocumentViewSet, basename="knowledge-document")

urlpatterns = router.urls
