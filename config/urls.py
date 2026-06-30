"""Root URL routing for HR Vidnova."""

from django.conf import settings
from django.contrib import admin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import include, path
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from config.media import protected_media
from apps.employees.models import Employee
from apps.selfservice.models import UserPreference
from apps.selfservice.serializers import UserPreferenceSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AuthStatusView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []

    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        employee = None
        if user:
            try:
                profile = user.employee_profile
                employee = {
                    "id": profile.id,
                    "full_name": profile.full_name,
                    "status": profile.status,
                }
            except Employee.DoesNotExist:
                employee = None
            preferences = UserPreferenceSerializer(UserPreference.objects.get_or_create(user=user)[0]).data
        else:
            preferences = None
        return Response(
            {
                "authenticated": bool(user),
                "user": {
                    "id": user.id,
                    "username": user.get_username(),
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                }
                if user
                else None,
                "employee": employee,
                "preferences": preferences,
                "access": self._access_payload(user),
            }
        )

    @staticmethod
    def _access_payload(user):
        # RBAC (Этап 5): эффективные роли/права для frontend-gating.
        # НЕ источник enforcement — backend permissions остаются обязательными.
        from django.conf import settings

        from apps.access import rbac

        if user is None:
            return {"is_admin": False, "roles": [], "permissions": {}, "enforced": bool(settings.RBAC_ENFORCE)}
        return {
            "is_admin": rbac.is_admin(user),
            "roles": sorted(rbac.get_effective_roles(user)),
            "permissions": {
                code: sorted(levels) for code, levels in rbac.get_effective_permissions(user).items()
            },
            "enforced": bool(settings.RBAC_ENFORCE),
        }


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/status/", AuthStatusView.as_view(), name="auth-status"),
    path("api/auth/", include("apps.access.auth_urls")),
    path("api/bot/", include("apps.access.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/reports/", include("apps.dashboard.reports_urls")),
    path("api/me/", include("apps.selfservice.urls")),
    path("api/employees/", include("apps.employees.urls")),
    path("api/assets/", include("apps.assets.urls")),
    path("api/skud/", include("apps.skud.urls")),
    path("api/leave/", include("apps.leave.urls")),
    path("api/knowledge/", include("apps.knowledge.urls")),
    path("api/announcements/", include("apps.announcements.urls")),
    path("api/projects/", include("apps.projects.urls")),
    path("api/integrations/", include("apps.integrations.urls")),
    path("api/access/", include("apps.access.rbac_urls")),
    path("api/public/v3/", include("apps.integrations.peopleforce_compat_urls")),
    path("api/peopleforce-compatible/v3/", include("apps.integrations.peopleforce_compat_urls")),
]

# P2: media всегда через защищённый view (анонимный доступ запрещён в production).
urlpatterns += [
    path("media/<path:path>", protected_media, name="protected-media"),
]
