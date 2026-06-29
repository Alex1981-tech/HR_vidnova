from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from uuid import uuid4

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from config.permissions import ConfiguredReadOnlyOrAuthenticated

from .audience import resolve_audience
from .models import Announcement, AnnouncementComment, AnnouncementReaction
from .serializers import (
    AnnouncementCommentSerializer,
    AnnouncementSerializer,
    AudiencePreviewSerializer,
)
from .tasks import send_announcement_telegram

logger = logging.getLogger(__name__)

AUDIENCE_SAMPLE_SIZE = 6
ANNOUNCEMENT_MEDIA_MAX_SIZE = 200 * 1024 * 1024
ANNOUNCEMENT_UNSAFE_IMAGE_TYPES = {"image/svg+xml"}


def _sample_payload(qs):
    sample = []
    for emp in qs.order_by("last_name", "first_name")[:AUDIENCE_SAMPLE_SIZE]:
        avatar = ""
        if emp.avatar_file:
            try:
                avatar = emp.avatar_file.url
            except ValueError:
                avatar = ""
        sample.append({"id": emp.id, "full_name": emp.full_name, "avatar_url": avatar or emp.avatar_url or ""})
    return sample


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get_queryset(self):
        qs = Announcement.objects.select_related(
            "author", "author__employee_profile", "author__employee_profile__position",
        ).prefetch_related(
            "comments", "comments__employee", "comments__author",
            "reactions", "reactions__user__employee_profile",
        )
        if self.action == "list":
            qs = qs.filter(status=Announcement.Status.PUBLISHED)
        return qs

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        audience = resolve_audience(
            serializer.validated_data.get("audience_type", "all"),
            serializer.validated_data.get("conditions", []),
        )
        recipients = audience.count()

        scheduled_at = serializer.validated_data.get("scheduled_at")
        now = timezone.now()
        is_future = bool(scheduled_at and scheduled_at > now)
        announcement = serializer.save(
            author=user,
            recipients_count=recipients,
            status=Announcement.Status.SCHEDULED if is_future else Announcement.Status.PUBLISHED,
            published_at=None if is_future else now,
        )
        if not is_future and announcement.notify_telegram:
            self._dispatch_telegram(announcement.id)

    @staticmethod
    def _dispatch_telegram(announcement_id):
        try:
            send_announcement_telegram.delay(announcement_id)
        except Exception:  # noqa: BLE001 — брокер може бути недоступний, не валимо запит
            logger.exception("Failed to enqueue Telegram dispatch for announcement %s", announcement_id)

    @action(detail=False, methods=["post"], url_path="audience-preview")
    def audience_preview(self, request):
        serializer = AudiencePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qs = resolve_audience(
            serializer.validated_data["audience_type"],
            serializer.validated_data.get("conditions", []),
        )
        return Response({"count": qs.count(), "sample": _sample_payload(qs)})

    @action(detail=False, methods=["post"], url_path="media-upload", parser_classes=[MultiPartParser, FormParser])
    def media_upload(self, request):
        upload = request.FILES.get("file") or request.FILES.get("media")
        if not upload:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > ANNOUNCEMENT_MEDIA_MAX_SIZE:
            return Response({"detail": "Файл більший за 200 МБ."}, status=status.HTTP_400_BAD_REQUEST)

        content_type = (getattr(upload, "content_type", "") or "").strip().lower()
        if not content_type:
            content_type = (mimetypes.guess_type(upload.name)[0] or "").lower()
        is_image = content_type.startswith("image/") and content_type not in ANNOUNCEMENT_UNSAFE_IMAGE_TYPES
        is_video = content_type.startswith("video/")
        if not (is_image or is_video):
            return Response(
                {"detail": "Підтримуються тільки фото та відео."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        suffix = Path(upload.name).suffix.lower()
        if not suffix or len(suffix) > 12:
            suffix = mimetypes.guess_extension(content_type) or (".jpg" if is_image else ".mp4")
        now = timezone.now()
        storage_path = f"announcements/media/{now:%Y/%m}/{uuid4().hex}{suffix}"
        saved_path = default_storage.save(storage_path, upload)
        return Response(
            {
                "url": default_storage.url(saved_path),
                "kind": "image" if is_image else "video",
                "content_type": content_type,
                "name": upload.name,
                "size": upload.size,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="react")
    def react(self, request, pk=None):
        announcement = self.get_object()
        emoji = (request.data.get("emoji") or "").strip()
        if not emoji:
            return Response({"detail": "Потрібен emoji."}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user if request.user.is_authenticated else None
        if user is None:
            return Response({"detail": "Потрібна авторизація."}, status=status.HTTP_403_FORBIDDEN)
        existing = AnnouncementReaction.objects.filter(announcement=announcement, user=user, emoji=emoji).first()
        if existing:
            existing.delete()
        else:
            AnnouncementReaction.objects.create(announcement=announcement, user=user, emoji=emoji)
        fresh = self.get_queryset().get(pk=announcement.pk)  # свіжий prefetch реакцій
        data = AnnouncementSerializer(fresh, context=self.get_serializer_context()).data
        return Response({"reactions": data["reactions"]})

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        announcement = self.get_object()
        if request.method == "GET":
            data = AnnouncementCommentSerializer(announcement.comments.all(), many=True).data
            return Response(data)
        if not announcement.allow_comments:
            return Response({"detail": "Коментарі вимкнено."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AnnouncementCommentSerializer(data={**request.data, "announcement": announcement.id})
        serializer.is_valid(raise_exception=True)
        user = request.user if request.user.is_authenticated else None
        employee = getattr(user, "employee_profile", None) if user else None
        serializer.save(author=user, employee=employee)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
