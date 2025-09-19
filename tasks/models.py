"""
Task models for basic task management with activity logging.
"""
from django.contrib.auth.models import User
from django.db import models


class Task(models.Model):
    """Task model with essential fields and activity logging."""

    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("in_review", "In Review"),
        ("done", "Done"),
        ("blocked", "Blocked"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    estimate = models.PositiveIntegerField(null=True, blank=True, help_text="Story points")
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reported_tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    def save(self, *args, **kwargs):
        """Save task and create activity log for changes."""
        is_new = not self.pk
        old_task = None
        
        if not is_new:
            old_task = Task.objects.get(pk=self.pk)
        
        super().save(*args, **kwargs)
        
        # Create activity logs
        if is_new:
            TaskActivity.objects.create(
                task=self,
                activity_type="created",
                description=f"Task '{self.title}' was created",
            )
        elif old_task:
            changes = []
            if old_task.status != self.status:
                changes.append(f"Status changed from '{old_task.get_status_display()}' to '{self.get_status_display()}'")
            if old_task.assignee != self.assignee:
                old_assignee = old_task.assignee.username if old_task.assignee else "Unassigned"
                new_assignee = self.assignee.username if self.assignee else "Unassigned"
                changes.append(f"Assignee changed from '{old_assignee}' to '{new_assignee}'")
            if old_task.priority != self.priority:
                changes.append(f"Priority changed from '{old_task.get_priority_display()}' to '{self.get_priority_display()}'")
            if old_task.estimate != self.estimate:
                changes.append(f"Estimate changed from '{old_task.estimate or 'None'}' to '{self.estimate or 'None'}'")
            
            for change in changes:
                TaskActivity.objects.create(
                    task=self,
                    activity_type="field_change",
                    description=change,
                )


class TaskActivity(models.Model):
    """Activity log for tracking task changes."""

    ACTIVITY_TYPES = [
        ("created", "Created"),
        ("field_change", "Field Changed"),
        ("comment", "Comment Added"),
        ("deleted", "Deleted"),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        user_info = f" by {self.user.username}" if self.user else ""
        return f"{self.get_activity_type_display()}: {self.description}{user_info}"