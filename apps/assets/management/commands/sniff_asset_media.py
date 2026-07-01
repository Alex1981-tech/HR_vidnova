"""Визначає реальний тип медіа активів (magic-байти) і виправляє відео, збережені як .jpg."""

import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.assets.models import AssetPhoto


def _sniff(head: bytes) -> str:
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"mif1", b"heim"):
            return "image/heic"
        return "video/mp4"
    return "application/octet-stream"


class Command(BaseCommand):
    help = "Проставляє content_type кожному AssetPhoto; відео (.jpg) перейменовує у .mp4."

    def handle(self, *args, **options):
        fixed_type = renamed = 0
        for ph in AssetPhoto.objects.all():
            if not ph.image:
                continue
            path = os.path.join(settings.MEDIA_ROOT, ph.image.name)
            if not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                head = f.read(16)
            ctype = _sniff(head)
            update = []
            if ph.content_type != ctype:
                ph.content_type = ctype
                update.append("content_type")
                fixed_type += 1
            # Відео з розширенням-зображенням → перейменувати у .mp4, щоб браузер грав.
            if ctype == "video/mp4" and not ph.image.name.lower().endswith(".mp4"):
                new_name = os.path.splitext(ph.image.name)[0] + ".mp4"
                new_path = os.path.join(settings.MEDIA_ROOT, new_name)
                os.rename(path, new_path)
                ph.image.name = new_name
                update.append("image")
                renamed += 1
            if update:
                ph.save(update_fields=update)
        self.stdout.write(self.style.SUCCESS(f"Готово: content_type у {fixed_type}, перейменовано відео {renamed}."))
