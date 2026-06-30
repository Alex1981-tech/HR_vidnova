from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from config.sanitize import sanitize_rich_html

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
    conditions = serializers.JSONField(required=False, write_only=True)

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
            "conditions",
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

    def validate_conditions(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Expected a list of audience conditions.")

        normalized = []
        allowed_operators = {"is", "is_not", "is_empty", "is_not_empty"}
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each condition must be an object.")
            field = str(item.get("field") or "").strip()
            operator = str(item.get("operator") or "").strip()
            raw_values = item.get("value") or []
            if operator not in allowed_operators:
                raise serializers.ValidationError("Unsupported condition operator.")
            if not field:
                raise serializers.ValidationError("Condition field is required.")
            if not isinstance(raw_values, list):
                raw_values = [raw_values]
            values = []
            for raw_value in raw_values:
                try:
                    values.append(int(raw_value))
                except (TypeError, ValueError) as exc:
                    raise serializers.ValidationError("Condition values must be numeric IDs.") from exc
            normalized.append({"field": field, "operator": operator, "value": values})
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

    def _apply_conditions_to_filters(self, validated_data, instance=None):
        if "conditions" not in validated_data:
            return validated_data
        conditions = validated_data.pop("conditions")
        audience_filters = dict(validated_data.get("audience_filters") or (instance.audience_filters if instance else {}) or {})
        audience_filters["employee_status"] = "active"
        audience_filters["conditions"] = conditions
        validated_data["audience_filters"] = audience_filters
        if conditions:
            validated_data["audience_employee_ids"] = []
        return validated_data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        filters = instance.audience_filters if isinstance(instance.audience_filters, dict) else {}
        conditions = filters.get("conditions")
        if isinstance(conditions, list) and conditions:
            data["conditions"] = conditions
        elif instance.visibility_mode == KnowledgeCategory.VisibilityMode.SPECIFIC and instance.audience_employee_ids:
            data["conditions"] = [
                {
                    "field": "employee",
                    "operator": "is",
                    "value": instance.audience_employee_ids,
                }
            ]
        else:
            data["conditions"] = []
        return data

    def create(self, validated_data):
        validated_data = self._apply_conditions_to_filters(validated_data)
        validated_data["slug"] = unique_slug(KnowledgeCategory, validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_conditions_to_filters(validated_data, instance)
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

    def validate_body_html(self, value):
        # P4: HTML-санитайзер на boundary — храним только безопасный HTML.
        return sanitize_rich_html(value)

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
