import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import Task, TaskSummary

logger = logging.getLogger(__name__)


class TaskRepositoryInterface(ABC):
    """Abstract interface for task data access."""

    @abstractmethod
    def get_by_id(self, task_id: int) -> Task:
        """Get task by ID."""
        pass

    @abstractmethod
    def get_similar_tasks(self, task: Task, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get similar completed tasks for analysis.

        task: Current task to find similarities for
        limit: Maximum number of similar tasks to return
        """
        pass

    @abstractmethod
    def exists(self, task_id: int) -> bool:
        """Check if task exists."""
        pass


class TaskRepository(TaskRepositoryInterface):
    """Django ORM implementation of task repository."""

    def get_by_id(self, task_id: int) -> Task:
        """Get task by ID."""
        try:
            return Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            logger.error(f"Task with ID {task_id} not found")
            raise

    def get_similar_tasks(self, task: Task, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get similar completed tasks for analysis.

        task: Current task to find similarities for
        limit: Maximum number of similar tasks to return
        """
        # Get recent completed tasks with estimates
        similar_tasks = (
            Task.objects.filter(
                estimate__isnull=False, estimate__gt=0, status__in=["done", "closed"]
            )
            .exclude(id=task.id)
            .order_by("-updated_at")[:limit]
        )

        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description or "",
                "priority": t.priority,
                "estimate": t.estimate,
                "status": t.status,
            }
            for t in similar_tasks
        ]

    def exists(self, task_id: int) -> bool:
        """Check if task exists."""
        return Task.objects.filter(id=task_id).exists()


class TaskSummaryRepositoryInterface(ABC):
    """Abstract interface for task summary data access."""

    @abstractmethod
    def get_by_task_id(self, task_id: int) -> Optional[TaskSummary]:
        """Get summary by task ID."""
        pass

    @abstractmethod
    def create(
        self,
        task: Task,
        summary_text: str,
        last_activity_processed=None,
        token_usage: int = 0,
    ) -> TaskSummary:
        """Create new task summary."""
        pass

    @abstractmethod
    def update(
        self,
        summary: TaskSummary,
        summary_text: str,
        last_activity_processed=None,
        additional_tokens: int = 0,
    ) -> TaskSummary:
        """Update existing task summary."""
        pass

    @abstractmethod
    def delete_by_task_id(self, task_id: int) -> bool:
        """Delete summary by task ID."""
        pass


class TaskSummaryRepository(TaskSummaryRepositoryInterface):
    """Django ORM implementation of task summary repository."""

    def get_by_task_id(self, task_id: int) -> Optional[TaskSummary]:
        """Get summary by task ID."""
        try:
            task = Task.objects.get(id=task_id)
            return getattr(task, "ai_summary", None)
        except Task.DoesNotExist:
            logger.error(f"Task with ID {task_id} not found")
            return None

    def create(
        self,
        task: Task,
        summary_text: str,
        last_activity_processed=None,
        token_usage: int = 0,
    ) -> TaskSummary:
        """Create new task summary."""
        summary = TaskSummary.objects.create(
            task=task,
            summary_text=summary_text,
            last_activity_processed=last_activity_processed,
            token_usage=token_usage,
        )
        logger.info(f"Created new summary for task {task.id}")
        return summary

    def update(
        self,
        summary: TaskSummary,
        summary_text: str,
        last_activity_processed=None,
        additional_tokens: int = 0,
    ) -> TaskSummary:
        """Update existing task summary."""
        summary.summary_text = summary_text
        if last_activity_processed:
            summary.last_activity_processed = last_activity_processed
        summary.token_usage += additional_tokens
        summary.save()

        logger.info(f"Updated summary for task {summary.task.id}")
        return summary

    def delete_by_task_id(self, task_id: int) -> bool:
        """Delete summary by task ID."""
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


class RepositoryFactory:
    """Factory for creating repository instances."""

    @staticmethod
    def create_task_repository() -> TaskRepositoryInterface:
        """Create task repository instance."""
        return TaskRepository()

    @staticmethod
    def create_task_summary_repository() -> TaskSummaryRepositoryInterface:
        """Create task summary repository instance."""
        return TaskSummaryRepository()
