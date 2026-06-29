from __future__ import annotations

from rest_framework import serializers

from .models import Announcement, AnnouncementComment


def _user_avatar(user) -> str:
    """URL аватара співробітника, прив'язаного до User (через employee_profile)."""
    employee = getattr(user, "employee_profile", None)
    if not employee:
        return ""
    if employee.avatar_file:
        try:
            return employee.avatar_file.url
        except ValueError:
            pass
    return employee.avatar_url or ""


def _user_display_name(user) -> str:
    employee = getattr(user, "employee_profile", None)
    if employee and employee.full_name:
        return employee.full_name
    return user.get_full_name() or user.get_username()


class AnnouncementCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementComment
        fields = ("id", "announcement", "author", "author_name", "author_avatar", "employee", "body", "created_at")
        read_only_fields = ("author", "created_at")

    def get_author_name(self, obj):
        if obj.employee:
            return obj.employee.full_name
        if obj.author:
            return _user_display_name(obj.author)
        return ""

    def get_author_avatar(self, obj):
        if obj.employee and obj.employee.avatar_file:
            try:
                return obj.employee.avatar_file.url
            except ValueError:
                pass
        if obj.employee and obj.employee.avatar_url:
            return obj.employee.avatar_url
        return _user_avatar(obj.author) if obj.author else ""


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            "id", "title", "body_html", "author", "author_name", "author_avatar", "author_role",
            "audience_type", "conditions",
            "notify_telegram", "notify_web", "allow_comments",
            "scheduled_at", "status", "published_at",
            "recipients_count", "tg_sent_count", "tg_failed_count", "tg_dispatched_at",
            "comments_count", "comments", "reactions", "created_at", "updated_at",
        )
        read_only_fields = (
            "author", "status", "published_at",
            "recipients_count", "tg_sent_count", "tg_failed_count", "tg_dispatched_at",
        )

    def get_author_name(self, obj):
        if obj.author:
            return _user_display_name(obj.author)
        return ""

    def get_author_avatar(self, obj):
        return _user_avatar(obj.author) if obj.author else ""

    def get_author_role(self, obj):
        employee = getattr(obj.author, "employee_profile", None) if obj.author else None
        if employee and employee.position_id:
            return employee.position.name
        return ""

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_comments(self, obj):
        return AnnouncementCommentSerializer(obj.comments.all(), many=True).data

    def get_reactions(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        user_id = user.id if (user and user.is_authenticated) else None
        summary = {}
        for r in obj.reactions.all():
            entry = summary.setdefault(r.emoji, {"emoji": r.emoji, "count": 0, "reacted": False, "users": []})
            entry["count"] += 1
            entry["users"].append(_user_display_name(r.user) if r.user else "Користувач")
            if user_id and r.user_id == user_id:
                entry["reacted"] = True
        return list(summary.values())

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Назва обов'язкова.")
        return value


class AudiencePreviewSerializer(serializers.Serializer):
    audience_type = serializers.ChoiceField(choices=Announcement.Audience.choices, default="all")
    conditions = serializers.ListField(child=serializers.DictField(), required=False, default=list)
