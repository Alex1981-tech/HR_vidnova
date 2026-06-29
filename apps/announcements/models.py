from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.employees.models import Employee, TimestampedModel


class Announcement(TimestampedModel):
    """Оголошення на головній сторінці з опційною розсилкою в Telegram."""

    class Kind(models.TextChoices):
        ANNOUNCEMENT = "announcement", "Оголошення"
        POLL = "poll", "Опитування"

    class Audience(models.TextChoices):
        ALL = "all", "Усі"
        CONDITIONS = "conditions", "Конкретні люди"

    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        SCHEDULED = "scheduled", "Заплановано"
        PUBLISHED = "published", "Опубліковано"

    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.ANNOUNCEMENT, db_index=True)
    body_html = models.TextField(blank=True)
    poll_options = models.JSONField(default=list, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="authored_announcements",
    )
    audience_type = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    # [{field, operator, value:[ids]}] — резолвиться у apps.announcements.audience
    conditions = models.JSONField(default=list, blank=True)

    notify_telegram = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=False)
    notify_web = models.BooleanField(default=True)
    allow_comments = models.BooleanField(default=False)

    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Підсумок розсилки в Telegram
    recipients_count = models.PositiveIntegerField(default=0)
    tg_sent_count = models.PositiveIntegerField(default=0)
    tg_failed_count = models.PositiveIntegerField(default=0)
    tg_dispatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="ann_status_pub_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class AnnouncementComment(TimestampedModel):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="announcement_comments",
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcement_comments",
    )
    body = models.TextField()

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"Comment on {self.announcement_id}"


class AnnouncementReaction(TimestampedModel):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="announcement_reactions",
    )
    emoji = models.CharField(max_length=16)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["announcement", "user", "emoji"], name="uniq_ann_user_emoji"),
        ]

    def __str__(self) -> str:
        return f"{self.emoji} on {self.announcement_id}"


class AnnouncementPollVote(TimestampedModel):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="poll_votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="announcement_poll_votes",
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcement_poll_votes",
    )
    option_index = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["announcement", "option_index"], name="ann_poll_option_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["announcement", "user"], name="uniq_ann_poll_user"),
        ]

    def __str__(self) -> str:
        return f"Vote {self.option_index} on {self.announcement_id}"
