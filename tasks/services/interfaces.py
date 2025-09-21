from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import TaskSummary
from .estimation.base import EstimationResult


class TaskEstimationServiceInterface(ABC):
    """Interface for task estimation services."""

    @abstractmethod
    def estimate_task(self, task_id: int) -> EstimationResult:
        """
        Estimate effort for a task.

        task_id: ID of the task to estimate
        """
        pass

    @abstractmethod
    def can_estimate(self, task_id: int) -> bool:
        """
        Check if a task can be estimated.

        task_id: ID of the task to check
        """
        pass

    @abstractmethod
    def get_estimation_metadata(self, task_id: int) -> Dict[str, Any]:
        """
        Get metadata about estimation capability for a task.

        task_id: ID of the task to check
        """
        pass


class TaskSummaryServiceInterface(ABC):
    """Interface for task summary services."""

    @abstractmethod
    def create_or_update_summary(self, task_id: int) -> TaskSummary:
        """
        Create new summary or update existing one.

        task_id: ID of the task to summarize
        """
        pass

    @abstractmethod
    def get_summary(self, task_id: int) -> Optional[TaskSummary]:
        """
        Get existing summary for a task.

        task_id: ID of the task
        """
        pass

    @abstractmethod
    def delete_summary(self, task_id: int) -> bool:
        """
        Delete summary for a task.

        task_id: ID of the task
        """
        pass

    @abstractmethod
    def analyze_summary_quality(self, task_id: int) -> Dict[str, Any]:
        """
        Analyze the quality of a task summary.

        task_id: ID of the task
        """
        pass


class AIProviderServiceInterface(ABC):
    """Interface for AI provider services."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if AI provider is available."""
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the AI provider."""
        pass

    @abstractmethod
    def estimate_cost(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Estimate cost for an operation.

        operation: Type of operation ('summary', 'estimation', etc.)
        """
        pass


class TaskAnalyticsServiceInterface(ABC):
    """Interface for task analytics services."""

    @abstractmethod
    def get_task_metrics(self, task_id: int) -> Dict[str, Any]:
        """
        Get metrics for a specific task.

        task_id: ID of the task
        """
        pass

    @abstractmethod
    def get_estimation_accuracy(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get estimation accuracy for a completed task.

        task_id: ID of the task
        """
        pass

    @abstractmethod
    def get_similar_tasks_analysis(self, task_id: int) -> Dict[str, Any]:
        """
        Analyze similar tasks for a given task.

        task_id: ID of the task
        """
        pass


class TaskValidationServiceInterface(ABC):
    """Interface for task validation services."""

    @abstractmethod
    def validate_for_estimation(self, task_id: int) -> Dict[str, Any]:
        """
        Validate if task is ready for estimation.

        task_id: ID of the task
        """
        pass

    @abstractmethod
    def validate_for_summary(self, task_id: int) -> Dict[str, Any]:
        """
        Validate if task is ready for summary generation.

        task_id: ID of the task
        """
        pass

    @abstractmethod
    def suggest_improvements(self, task_id: int) -> List[str]:
        """
        Suggest improvements for a task.

        task_id: ID of the task
        """
        pass


class CacheServiceInterface(ABC):
    """Interface for caching services."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value.

        key: Cache key
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set cached value.

        key: Cache key
        value: Value to cache
        timeout: Timeout in seconds
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete cached value.

        key: Cache key
        """
        pass

    @abstractmethod
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear cached values matching pattern.

        pattern: Pattern to match
        """
        pass


class NotificationServiceInterface(ABC):
    """Interface for notification services."""

    @abstractmethod
    def notify_estimation_complete(
        self, task_id: int, result: EstimationResult
    ) -> bool:
        """
        Notify when estimation is complete.

        task_id: ID of the task
        result: Estimation result
        """
        pass

    @abstractmethod
    def notify_summary_updated(self, task_id: int, summary: TaskSummary) -> bool:
        """
        Notify when summary is updated.

        task_id: ID of the task
        summary: Updated summary
        """
        pass

    @abstractmethod
    def notify_error(
        self, service: str, error: str, task_id: Optional[int] = None
    ) -> bool:
        """
        Notify about service errors.

        service: Service name
        error: Error message
        task_id: Optional task ID
        """
        pass
