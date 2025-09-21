import logging
from typing import Any, Dict, List, Optional

from ...models import Task, TaskActivity, TaskSummary
from ..interfaces import TaskSummaryServiceInterface
from ..repositories import (
    RepositoryFactory,
    TaskRepositoryInterface,
    TaskSummaryRepositoryInterface,
)
from .base import SummaryProvider, SummaryProviderFactory

logger = logging.getLogger(__name__)


class TaskSummaryService(TaskSummaryServiceInterface):
    """Service for managing task summaries with improved architecture."""

    def __init__(
        self,
        summary_provider: Optional[SummaryProvider] = None,
        task_repository: Optional[TaskRepositoryInterface] = None,
        summary_repository: Optional[TaskSummaryRepositoryInterface] = None,
    ):
        """Initialize the service with dependencies."""
        self.summary_provider = (
            summary_provider or SummaryProviderFactory.create_provider()
        )
        self.task_repository = (
            task_repository or RepositoryFactory.create_task_repository()
        )
        self.summary_repository = (
            summary_repository or RepositoryFactory.create_task_summary_repository()
        )

    def create_or_update_summary(self, task_id: int) -> TaskSummary:
        """Create new summary or update existing one with new activities."""
        try:
            task = self.task_repository.get_by_id(task_id)
            existing_summary = self.summary_repository.get_by_task_id(task_id)

            if existing_summary:
                logger.info(f"Updating existing summary for task {task_id}")
                return self._update_existing_summary(task, existing_summary)
            else:
                logger.info(f"Creating new summary for task {task_id}")
                return self._create_new_summary(task)

        except Exception as e:
            logger.error(
                f"Error while creating/updating summary for task {task_id}: {str(e)}"
            )
            raise

    def get_summary(self, task_id: int) -> Optional[TaskSummary]:
        """Get existing summary for a task."""
        return self.summary_repository.get_by_task_id(task_id)

    def delete_summary(self, task_id: int) -> bool:
        """Delete summary for a task."""
        return self.summary_repository.delete_by_task_id(task_id)

    def analyze_summary_quality(self, task_id: int) -> Dict[str, Any]:
        """
        Analyze the quality of a task summary.

        task_id: ID of the task

        Returns:
            Dictionary with quality analysis
        """
        from .analyzer import TaskSummaryAnalyzer

        analyzer = TaskSummaryAnalyzer(self.summary_repository)
        return analyzer.analyze_summary_quality(task_id)

    def _create_new_summary(self, task: Task) -> TaskSummary:
        """Create a new summary for all task activities."""
        activities = self._get_all_activities(task)

        if not activities:
            summary_text, token_usage = self._create_basic_summary(task)
        else:
            summary_text, token_usage = self._generate_ai_summary(task, activities)

        return self.summary_repository.create(
            task=task,
            summary_text=summary_text,
            last_activity_processed=activities[-1] if activities else None,
            token_usage=token_usage,
        )

    def _update_existing_summary(
        self, task: Task, existing_summary: TaskSummary
    ) -> TaskSummary:
        """Update existing summary with new activities."""
        new_activities = self._get_new_activities(task, existing_summary)

        if not new_activities:
            logger.info(
                f"No new activities found for task {task.id}, returning existing summary"
            )
            return existing_summary

        # Generate updated summary
        summary_text, token_usage = self._generate_ai_summary(
            task, new_activities, existing_summary.summary_text
        )

        return self.summary_repository.update(
            summary=existing_summary,
            summary_text=summary_text,
            last_activity_processed=new_activities[-1],
            additional_tokens=token_usage,
        )

    def _get_all_activities(self, task: Task) -> List[TaskActivity]:
        """Get all activities for a task."""
        return list(task.activities.all().order_by("timestamp"))

    def _get_new_activities(
        self, task: Task, existing_summary: TaskSummary
    ) -> List[TaskActivity]:
        """Get activities newer than the last processed one."""
        if existing_summary.last_activity_processed:
            return list(
                task.activities.filter(
                    timestamp__gt=existing_summary.last_activity_processed.timestamp
                ).order_by("timestamp")
            )
        else:
            # If no last processed activity, get all activities
            return self._get_all_activities(task)

    def _create_basic_summary(self, task: Task) -> tuple[str, int]:
        """Create basic summary when no activities exist."""
        summary_parts = [
            f"Task '{task.title}' was created with {task.get_status_display()} status",
            f"and {task.get_priority_display()} priority.",
        ]

        if task.assignee:
            summary_parts.append(f"Assigned to {task.assignee.username}.")

        if task.estimate:
            summary_parts.append(f"Estimated effort: {task.estimate} story points.")

        if task.due_date:
            summary_parts.append(f"Due date: {task.due_date.strftime('%Y-%m-%d')}.")

        return " ".join(summary_parts), 0

    def _generate_ai_summary(
        self,
        task: Task,
        activities: List[TaskActivity],
        previous_summary: Optional[str] = None,
    ) -> tuple[str, int]:
        """Generate AI summary for activities."""
        try:
            result = self.summary_provider.generate_task_summary(
                task, activities, previous_summary
            )
            return result.summary, result.tokens_used
        except Exception as e:
            logger.error(f"Unexpected error during AI summary generation: {str(e)}")
            raise
