from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "is_archived", "order")
    list_filter = ("is_archived",)
    search_fields = ("name",)
    filter_horizontal = ("members",)
    ordering = ("order", "name")
