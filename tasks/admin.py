from django.contrib import admin

from .models import Task, TaskActivity, TaskSummary


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


@admin.register(TaskSummary)
class TaskSummaryAdmin(admin.ModelAdmin):
    """Admin interface for TaskSummary model."""

    list_display = [
        "task",
        "summary_preview",
        "token_usage",
        "created_at",
        "updated_at",
    ]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["task__title", "summary_text"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Task Information",
            {"fields": ("task", "last_activity_processed")},
        ),
        (
            "Summary Content",
            {"fields": ("summary_text",)},
        ),
        (
            "Metadata",
            {
                "fields": ("token_usage", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Summary Preview")
    def summary_preview(self, obj):
        """Show a preview of the summary text."""
        if len(obj.summary_text) > 100:
            return obj.summary_text[:100] + "..."
        return obj.summary_text

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("task", "last_activity_processed")
        )
