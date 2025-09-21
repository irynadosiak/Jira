import logging
from typing import Optional

from ..models import Task, TaskSummary
from .base import AIProvider, AIProviderError, AIProviderFactory

logger = logging.getLogger(__name__)


class TaskSummaryService:
    """Service for managing task summaries."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        """Initialize the service with AI provider."""
        self.ai_provider = ai_provider or AIProviderFactory.create_provider()

    def create_or_update_summary(self, task_id: int) -> TaskSummary:
        """Create new summary or update existing one with new activities."""
        try:
            task = Task.objects.get(id=task_id)
            existing_summary = getattr(task, "ai_summary", None)

            if existing_summary:
                logger.info(f"Updating existing summary for task {task_id}")
                return self._update_existing_summary(task, existing_summary)
            else:
                logger.info(f"Creating new summary for task {task_id}")
                return self._create_new_summary(task)

        except Task.DoesNotExist:
            logger.error(f"Task with ID {task_id} not found")
            raise
        except AIProviderError as e:
            logger.error(f"AI provider error while processing task {task_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error while creating/updating summary for task {task_id}: {str(e)}"
            )
            raise

    def _create_new_summary(self, task: Task) -> TaskSummary:
        """Create a new summary for all task activities."""
        activities = list(task.activities.all().order_by("timestamp"))

        if not activities:
            summary_text = (
                f"Task '{task.title}' was created with {task.get_status_display()} status "
                f"and {task.get_priority_display()} priority."
            )
            if task.assignee:
                summary_text += f" Assigned to {task.assignee.username}."
            token_usage = 0
        else:
            ai_result = self.ai_provider.generate_task_summary(task, activities)
            summary_text = ai_result.summary
            token_usage = ai_result.tokens_used

        summary = TaskSummary.objects.create(
            task=task,
            summary_text=summary_text,
            last_activity_processed=activities[-1] if activities else None,
            token_usage=token_usage,
        )

        logger.info(f"Created new summary for task {task.id}")
        return summary

    def _update_existing_summary(
        self, task: Task, existing_summary: TaskSummary
    ) -> TaskSummary:
        """Update existing summary with new activities."""
        # Get activities newer than the last processed one
        if existing_summary.last_activity_processed:
            new_activities = list(
                task.activities.filter(
                    timestamp__gt=existing_summary.last_activity_processed.timestamp
                ).order_by("timestamp")
            )
        else:
            # If no last processed activity, get all activities
            new_activities = list(task.activities.all().order_by("timestamp"))

        if not new_activities:
            logger.info(
                f"No new activities found for task {task.id}, returning existing summary"
            )
            return existing_summary

        # Generate updated summary
        ai_result = self.ai_provider.generate_task_summary(
            task, new_activities, existing_summary.summary_text
        )

        # Update the summary
        existing_summary.summary_text = ai_result.summary
        existing_summary.last_activity_processed = new_activities[-1]
        existing_summary.token_usage += ai_result.tokens_used
        existing_summary.save()

        logger.info(
            f"Updated summary for task {task.id} with {len(new_activities)} new activities"
        )
        return existing_summary

    def get_summary(self, task_id: int) -> Optional[TaskSummary]:
        """Get existing summary for a task."""
        try:
            task = Task.objects.get(id=task_id)
            return getattr(task, "ai_summary", None)
        except Task.DoesNotExist:
            logger.error(f"Task with ID {task_id} not found")
            return None

    def delete_summary(self, task_id: int) -> bool:
        """Delete summary for a task."""
        try:
            task = Task.objects.get(id=task_id)
            summary = getattr(task, "ai_summary", None)
            if summary:
                summary.delete()
                logger.info(f"Deleted summary for task {task_id}")
                return True
            return False
        except Task.DoesNotExist:
            logger.error(f"Task with ID {task_id} not found")
            return False
