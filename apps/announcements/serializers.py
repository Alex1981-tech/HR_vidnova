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
    poll_results = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            "id", "title", "kind", "body_html", "poll_options",
            "author", "author_name", "author_avatar", "author_role",
            "audience_type", "conditions",
            "notify_telegram", "notify_email", "notify_web", "allow_comments",
            "scheduled_at", "status", "published_at",
            "recipients_count", "tg_sent_count", "tg_failed_count", "tg_dispatched_at",
            "comments_count", "comments", "reactions", "poll_results", "user_vote", "created_at", "updated_at",
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

    def _poll_vote_counts(self, obj):
        counts = {index: 0 for index, _ in enumerate(obj.poll_options or [])}
        total = 0
        for vote in obj.poll_votes.all():
            if vote.option_index in counts:
                counts[vote.option_index] += 1
                total += 1
        return counts, total

    def get_poll_results(self, obj):
        if obj.kind != Announcement.Kind.POLL:
            return []
        counts, total = self._poll_vote_counts(obj)
        results = []
        for index, text in enumerate(obj.poll_options or []):
            count = counts.get(index, 0)
            percentage = round((count / total) * 100) if total else 0
            results.append({
                "index": index,
                "text": text,
                "votes": count,
                "percentage": percentage,
                "total_votes": total,
            })
        return results

    def get_user_vote(self, obj):
        if obj.kind != Announcement.Kind.POLL:
            return None
        request = self.context.get("request")
        user = getattr(request, "user", None)
        user_id = user.id if (user and user.is_authenticated) else None
        if not user_id:
            return None
        for vote in obj.poll_votes.all():
            if vote.user_id == user_id:
                return vote.option_index
        return None

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Назва обов'язкова.")
        return value

    def validate_poll_options(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Варіанти мають бути списком.")
        options = []
        for option in value:
            text = str(option or "").strip()
            if not text:
                continue
            options.append(text[:255])
        if len(options) > 20:
            raise serializers.ValidationError("Максимум 20 варіантів.")
        return options

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", Announcement.Kind.ANNOUNCEMENT))
        poll_options = attrs.get(
            "poll_options",
            getattr(self.instance, "poll_options", []) if self.instance else [],
        )
        if kind == Announcement.Kind.POLL and len(poll_options or []) < 2:
            raise serializers.ValidationError({"poll_options": "Додайте щонайменше два варіанти."})
        if kind != Announcement.Kind.POLL:
            attrs["poll_options"] = []
        return attrs

    def update(self, instance, validated_data):
        old_kind = instance.kind
        old_options = list(instance.poll_options or [])
        updated = super().update(instance, validated_data)
        new_options = list(updated.poll_options or [])
        options_changed = "poll_options" in validated_data and old_options != new_options
        kind_changed_from_poll = old_kind == Announcement.Kind.POLL and updated.kind != Announcement.Kind.POLL
        if options_changed or kind_changed_from_poll:
            updated.poll_votes.all().delete()
        return updated


class AudiencePreviewSerializer(serializers.Serializer):
    audience_type = serializers.ChoiceField(choices=Announcement.Audience.choices, default="all")
    conditions = serializers.ListField(child=serializers.DictField(), required=False, default=list)
