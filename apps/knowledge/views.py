import subprocess
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db.models import Q
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import viewsets

from config.permissions import ConfiguredReadOnlyOrAuthenticated

from .models import KnowledgeCategory, KnowledgeDocument
from .serializers import KnowledgeCategorySerializer, KnowledgeDocumentSerializer


class KnowledgeModelViewSet(viewsets.ModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]


class KnowledgeCategoryViewSet(KnowledgeModelViewSet):
    queryset = KnowledgeCategory.objects.all()
    serializer_class = KnowledgeCategorySerializer


class KnowledgeDocumentViewSet(KnowledgeModelViewSet):
    serializer_class = KnowledgeDocumentSerializer
    max_video_upload_bytes = 150 * 1024 * 1024

    def get_queryset(self):
        qs = KnowledgeDocument.objects.select_related("category", "owner").prefetch_related("attachments").all()
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(summary__icontains=search) | Q(body__icontains=search))
        return qs

    def perform_create(self, serializer):
        owner = self.request.user if self.request.user and self.request.user.is_authenticated else None
        serializer.save(owner=owner)

    def perform_update(self, serializer):
        owner = self.request.user if self.request.user and self.request.user.is_authenticated else serializer.instance.owner
        legacy_payload = dict(serializer.instance.legacy_payload or {})
        legacy_payload["hr_local_edit"] = {
            "updated_at": timezone.now().isoformat(),
            "user_id": owner.pk if owner else None,
        }
        serializer.save(owner=owner, legacy_payload=legacy_payload)

    @action(detail=False, methods=["post"], url_path="cover-upload", parser_classes=[MultiPartParser])
    def cover_upload(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > 5 * 1024 * 1024:
            return Response({"detail": "Cover file is too large. Maximum size is 5 MB."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.content_type != "image/webp":
            return Response({"detail": "Unsupported cover format. Upload cropped webp covers only."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        path = f"knowledge/covers/{now:%Y/%m}/{uuid4().hex}.webp"
        saved_path = default_storage.save(path, ContentFile(upload.read()))
        return Response({"url": default_storage.url(saved_path)}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="media-upload", parser_classes=[MultiPartParser])
    def media_upload(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not upload.content_type.startswith("video/"):
            return Response({"detail": "Only video uploads are supported here."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > self.max_video_upload_bytes:
            return Response({"detail": "Video file is too large. Maximum size is 150 MB."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            url = self._transcode_video(upload)
        except FileNotFoundError:
            return Response({"detail": "ffmpeg is not installed on the backend container."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except subprocess.TimeoutExpired:
            return Response({"detail": "Video transcoding timed out."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or b"").decode("utf-8", errors="ignore").strip().splitlines()[-1:] or ["Video transcoding failed."]
            return Response({"detail": detail[0][:300]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"url": url, "kind": "video", "content_type": "video/mp4"}, status=status.HTTP_201_CREATED)

    def _transcode_video(self, upload) -> str:
        token = uuid4().hex
        suffix = Path(upload.name).suffix.lower()
        if not suffix or len(suffix) > 10:
            suffix = ".video"

        temp_dir = Path(settings.MEDIA_ROOT) / "knowledge" / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        input_path = temp_dir / f"{token}-input{suffix}"
        output_path = temp_dir / f"{token}-converted.mp4"

        try:
            with input_path.open("wb") as destination:
                for chunk in upload.chunks():
                    destination.write(chunk)

            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                r"scale=trunc(min(1280\,iw)/2)*2:-2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "30",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)

            now = timezone.now()
            storage_path = f"knowledge/media/videos/{now:%Y/%m}/{token}.mp4"
            with output_path.open("rb") as converted:
                saved_path = default_storage.save(storage_path, File(converted))
            return default_storage.url(saved_path)
        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
