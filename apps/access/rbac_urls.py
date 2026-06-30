"""URL-маршруты RBAC management API (Этап 6), монтируются под /api/access/."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.access.rbac_views import (
    AccessRoleAssignmentViewSet,
    AccessRoleAuditViewSet,
    AccessRoleViewSet,
    EffectiveAccessPreviewView,
    PermissionCatalogView,
)

router = DefaultRouter()
router.register("roles", AccessRoleViewSet, basename="access-role")
router.register("assignments", AccessRoleAssignmentViewSet, basename="access-role-assignment")
router.register("audit", AccessRoleAuditViewSet, basename="access-role-audit")

urlpatterns = [
    path("permissions/", PermissionCatalogView.as_view(), name="access-permission-catalog"),
    path("effective-preview/", EffectiveAccessPreviewView.as_view(), name="access-effective-preview"),
    path("", include(router.urls)),
]
