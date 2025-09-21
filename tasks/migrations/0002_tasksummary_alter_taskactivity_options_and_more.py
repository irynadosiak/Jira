import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskSummary",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "summary_text",
                    models.TextField(
                        help_text="AI-generated summary of task activities"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the summary was first created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="When the summary was last updated"
                    ),
                ),
                (
                    "token_usage",
                    models.PositiveIntegerField(
                        default=0, help_text="Total OpenAI tokens used for this summary"
                    ),
                ),
            ],
            options={
                "verbose_name": "Task Summary",
                "verbose_name_plural": "Task Summaries",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AlterModelOptions(
            name="taskactivity",
            options={"ordering": ["-timestamp"]},
        ),
        migrations.RemoveIndex(
            model_name="task",
            name="tasks_task_status_4a0a95_idx",
        ),
        migrations.RemoveIndex(
            model_name="task",
            name="tasks_task_assigne_a1ddb3_idx",
        ),
        migrations.RemoveIndex(
            model_name="task",
            name="tasks_task_priorit_a900d4_idx",
        ),
        migrations.RemoveIndex(
            model_name="task",
            name="tasks_task_created_be1ba2_idx",
        ),
        migrations.AlterField(
            model_name="task",
            name="assignee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_tasks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="estimate",
            field=models.PositiveIntegerField(
                blank=True, help_text="Story points", null=True
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="priority",
            field=models.CharField(
                choices=[
                    ("low", "Low"),
                    ("medium", "Medium"),
                    ("high", "High"),
                    ("critical", "Critical"),
                ],
                default="medium",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="reporter",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reported_tasks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="status",
            field=models.CharField(
                choices=[
                    ("todo", "To Do"),
                    ("in_progress", "In Progress"),
                    ("in_review", "In Review"),
                    ("done", "Done"),
                    ("blocked", "Blocked"),
                ],
                default="todo",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="title",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="taskactivity",
            name="activity_type",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("field_change", "Field Changed"),
                    ("comment", "Comment Added"),
                    ("deleted", "Deleted"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="taskactivity",
            name="description",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="taskactivity",
            name="task",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activities",
                to="tasks.task",
            ),
        ),
        migrations.AlterField(
            model_name="taskactivity",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="tasksummary",
            name="last_activity_processed",
            field=models.ForeignKey(
                blank=True,
                help_text="Last activity included in this summary",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="tasks.taskactivity",
            ),
        ),
        migrations.AddField(
            model_name="tasksummary",
            name="task",
            field=models.OneToOneField(
                help_text="Task this summary belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ai_summary",
                to="tasks.task",
            ),
        ),
    ]
