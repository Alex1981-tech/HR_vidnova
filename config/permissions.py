from django.conf import settings
from django.db.models import Q
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSystemAdmin(BasePermission):
    """Доступ лише адмінам: superuser/staff або активне призначення адмін-ролі RBAC."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.is_staff:
            return True
        try:
            from apps.access.models import AccessRoleAssignment
            from apps.access.role_seeds import ADMIN_ROLE_SLUG
        except Exception:
            return False
        emp = getattr(user, "employee_profile", None)
        cond = Q(user=user)
        if emp:
            cond |= Q(employee=emp)
        return AccessRoleAssignment.objects.filter(
            cond, role__slug=ADMIN_ROLE_SLUG, role__is_active=True, is_active=True
        ).exists()


class ConfiguredReadOnlyOrAuthenticated(BasePermission):
    """Allow configured dev/public API access while keeping production locked down."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS and settings.HR_PUBLIC_READ_API:
            return True
        if request.method not in SAFE_METHODS and getattr(settings, "HR_PUBLIC_WRITE_API", False):
            return True
        return bool(request.user and request.user.is_authenticated)
