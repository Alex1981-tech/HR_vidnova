from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class KnowledgeCategory(TimestampedModel):
    class VisibilityMode(models.TextChoices):
        ALL = "all", "All"
        SPECIFIC = "specific", "Specific people"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    description = models.TextField(blank=True)
    icon_emoji = models.CharField(max_length=16, default="📄", blank=True)
    visibility_mode = models.CharField(max_length=20, choices=VisibilityMode.choices, default=VisibilityMode.ALL)
    audience_employee_ids = models.JSONField(default=list, blank=True)
    audience_filters = models.JSONField(default=dict, blank=True)
    position = models.PositiveIntegerField(default=0)
    legacy_payload = models.JSONField(default=dict, blank=True)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class KnowledgeDocument(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    category = models.ForeignKey(KnowledgeCategory, on_delete=models.PROTECT, related_name="documents")
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=260, unique=True)
    summary = models.TextField(blank=True)
    cover_url = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    tags = models.JSONField(default=list, blank=True)
    legacy_payload = models.JSONField(default=dict, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="knowledge_documents")
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["category__name", "title"]
        indexes = [
            models.Index(fields=["category", "status"], name="knowledge_category_status_idx"),
            models.Index(fields=["status", "-updated_at"], name="knowledge_status_updated_idx"),
            models.Index(fields=["legacy_peopleforce_id"], name="knowledge_doc_pf_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class KnowledgeDocumentVersion(TimestampedModel):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=240)
    body = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="knowledge_versions")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["document", "version"], name="uniq_knowledge_doc_version"),
        ]
        ordering = ["document", "-version"]

    def __str__(self) -> str:
        return f"{self.document} v{self.version}"


class KnowledgeAttachment(TimestampedModel):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="attachments")
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    file = models.FileField(upload_to="knowledge/")
    original_name = models.CharField(max_length=260)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    source_url = models.URLField(max_length=1000, blank=True)
    legacy_payload = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="knowledge_attachments")

    class Meta:
        ordering = ["document", "original_name"]

    def __str__(self) -> str:
        return self.original_name
