from django.contrib import admin

from .models import Task, TaskActivity


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin interface for Task model."""

    list_display = [
        "title",
        "status",
        "priority",
        "assignee",
        "reporter",
        "estimate",
        "created_at",
        "updated_at",
    ]
    list_filter = ["status", "priority", "assignee", "reporter", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "status", "priority")},
        ),
        (
            "Assignment & Estimation",
            {"fields": ("assignee", "reporter", "estimate", "due_date")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("assignee", "reporter")


@admin.register(TaskActivity)
class TaskActivityAdmin(admin.ModelAdmin):
    """Admin interface for TaskActivity model."""

    list_display = ["task", "activity_type", "user", "timestamp"]
    list_filter = ["activity_type", "timestamp", "user"]
    search_fields = ["task__title", "description"]
    readonly_fields = ["timestamp"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("task", "user")
