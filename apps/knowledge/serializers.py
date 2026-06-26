from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from .models import KnowledgeAttachment, KnowledgeCategory, KnowledgeDocument


def unique_slug(model, label: str, instance=None) -> str:
    base = slugify(label, allow_unicode=True)[:160].strip("-") or "item"
    slug = base
    suffix = 2
    queryset = model.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=slug).exists():
        suffix_text = f"-{suffix}"
        slug = f"{base[: max(1, 160 - len(suffix_text))]}{suffix_text}"
        suffix += 1
    return slug


class KnowledgeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeCategory
        fields = (
            "id",
            "name",
            "slug",
            "legacy_peopleforce_id",
            "description",
            "icon_emoji",
            "visibility_mode",
            "audience_employee_ids",
            "audience_filters",
            "position",
            "parent",
            "is_active",
        )
        read_only_fields = ("slug", "legacy_peopleforce_id")

    def validate_icon_emoji(self, value):
        return (value or "📄")[:16]

    def validate_visibility_mode(self, value):
        allowed = {choice[0] for choice in KnowledgeCategory.VisibilityMode.choices}
        if value not in allowed:
            raise serializers.ValidationError("Unsupported visibility mode.")
        return value

    def validate_audience_employee_ids(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Expected a list of employee IDs.")
        normalized = []
        for item in value:
            try:
                normalized.append(int(item))
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError("Employee IDs must be numbers.") from exc
        return normalized

    def validate(self, attrs):
        parent = attrs.get("parent")
        instance = self.instance
        if instance and parent:
            if parent.pk == instance.pk:
                raise serializers.ValidationError({"parent": "Category cannot be parent of itself."})
            current = parent
            while current:
                if current.pk == instance.pk:
                    raise serializers.ValidationError({"parent": "Category cannot be nested under its descendant."})
                current = current.parent
        return attrs

    def create(self, validated_data):
        validated_data["slug"] = unique_slug(KnowledgeCategory, validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = unique_slug(KnowledgeCategory, validated_data["name"], instance)
        return super().update(instance, validated_data)


class KnowledgeAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeAttachment
        fields = ("id", "legacy_peopleforce_id", "file", "original_name", "content_type", "size_bytes", "source_url", "created_at")


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    owner_name = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    attachments = KnowledgeAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = (
            "id",
            "category",
            "category_name",
            "owner_name",
            "view_count",
            "legacy_peopleforce_id",
            "title",
            "slug",
            "summary",
            "cover_url",
            "body",
            "body_html",
            "status",
            "tags",
            "published_at",
            "attachments",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("slug", "legacy_peopleforce_id", "owner_name", "view_count", "published_at", "created_at", "updated_at")

    def get_owner_name(self, obj):
        if not obj.owner_id:
            return ""
        full_name = obj.owner.get_full_name().strip()
        return full_name or obj.owner.get_username()

    def get_view_count(self, obj):
        payload = obj.legacy_payload or {}
        for key in ("view_count", "views", "visitors_count", "read_count"):
            value = payload.get(key)
            if isinstance(value, int):
                return max(value, 0)
            if isinstance(value, str) and value.isdigit():
                return int(value)
        visitors = payload.get("visitors")
        if isinstance(visitors, list):
            return len(visitors)
        return 0

    def _apply_status_fields(self, validated_data, instance=None):
        status = validated_data.get("status", instance.status if instance else KnowledgeDocument.Status.DRAFT)
        if status == KnowledgeDocument.Status.PUBLISHED:
            published_at = instance.published_at if instance else None
            if not published_at:
                validated_data["published_at"] = timezone.now()
        elif status != KnowledgeDocument.Status.PUBLISHED:
            validated_data["published_at"] = None
        return validated_data

    def create(self, validated_data):
        validated_data["slug"] = unique_slug(KnowledgeDocument, validated_data["title"])
        return super().create(self._apply_status_fields(validated_data))

    def update(self, instance, validated_data):
        if "title" in validated_data and validated_data["title"] != instance.title:
            validated_data["slug"] = unique_slug(KnowledgeDocument, validated_data["title"], instance)
        return super().update(instance, self._apply_status_fields(validated_data, instance))
