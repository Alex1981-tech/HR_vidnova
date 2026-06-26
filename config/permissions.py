from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission


class ConfiguredReadOnlyOrAuthenticated(BasePermission):
    """Allow configured dev/public API access while keeping production locked down."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS and settings.HR_PUBLIC_READ_API:
            return True
        if request.method not in SAFE_METHODS and getattr(settings, "HR_PUBLIC_WRITE_API", False):
            return True
        return bool(request.user and request.user.is_authenticated)
