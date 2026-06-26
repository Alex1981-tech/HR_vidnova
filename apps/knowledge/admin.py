from django.contrib import admin

from .models import KnowledgeAttachment, KnowledgeCategory, KnowledgeDocument, KnowledgeDocumentVersion


class KnowledgeAttachmentInline(admin.TabularInline):
    model = KnowledgeAttachment
    extra = 0


class KnowledgeDocumentVersionInline(admin.TabularInline):
    model = KnowledgeDocumentVersion
    extra = 0


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "legacy_peopleforce_id", "parent", "position", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug", "legacy_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "legacy_peopleforce_id", "published_at", "updated_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary", "body", "body_html", "legacy_peopleforce_id")
    list_filter = ("status", "category")
    inlines = [KnowledgeDocumentVersionInline, KnowledgeAttachmentInline]
