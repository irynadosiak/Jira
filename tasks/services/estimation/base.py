import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings

from ...models import Task

logger = logging.getLogger(__name__)


@dataclass
class EstimationResult:
    """Result from task estimation."""

    estimated_hours: float
    confidence_score: float
    reasoning: str
    similar_tasks: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    def __str__(self) -> str:
        return f"{self.estimated_hours}h (confidence: {self.confidence_score:.2f})"


@dataclass
class EstimationConfig:
    """Configuration for task estimation."""

    api_key: Optional[str]
    model: str
    max_tokens: int
    temperature: float
    use_mock: bool = False

    @classmethod
    def from_settings(cls) -> "EstimationConfig":
        """Create configuration from Django settings."""
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        use_mock = not api_key or getattr(settings, "USE_MOCK_AI", False)

        return cls(
            api_key=api_key,
            model=getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo"),
            max_tokens=getattr(settings, "ESTIMATION_MAX_TOKENS", 400),
            temperature=getattr(settings, "ESTIMATION_TEMPERATURE", 0.3),
            use_mock=use_mock,
        )


class EstimationError(Exception):
    """Base exception for estimation errors."""

    pass


class EstimationConfigurationError(EstimationError):
    """Exception raised for estimation configuration errors."""

    pass


class InsufficientDataError(EstimationError):
    """Exception raised when there's insufficient data for estimation."""

    pass


class TaskEstimator(ABC):
    """Abstract base class for task estimators."""

    def __init__(self, config: EstimationConfig):
        """Initialize estimator with configuration."""
        self.config = config
        self._setup()

    @abstractmethod
    def _setup(self) -> None:
        """Setup the estimator (initialize clients, load models, etc.)."""
        pass

    @abstractmethod
    def estimate_task(self, task: Task) -> EstimationResult:
        """
        Estimate effort required for a task.

        task: Task to estimate
        """
        pass

    def can_estimate(self, task: Task) -> bool:
        """
        Check if task can be estimated.

        task: Task to check
        """
        try:
            self._validate_task(task)
            return True
        except Exception:
            return False

    def _validate_task(self, task: Task) -> None:
        """
        Validate that a task has minimum required information.

        task: Task to validate
        """
        if not task.title or not task.title.strip():
            raise EstimationError("Task must have a title")

        if not task.description or not task.description.strip():
            raise EstimationError(
                "Task must have a description for accurate estimation"
            )

    def _get_similar_tasks_data(
        self, task: Task, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get data from similar completed tasks for context.

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


class EstimatorFactory:
    """Factory for creating task estimators."""

    @staticmethod
    def create_estimator(config: Optional[EstimationConfig] = None) -> TaskEstimator:
        """
        Create an estimator based on configuration.

        config: Estimation configuration. If None, creates from settings.
        """
        if config is None:
            config = EstimationConfig.from_settings()

        try:
            if config.use_mock:
                from .ai_similarity import MockAISimilarityEstimator

                return MockAISimilarityEstimator(config)
            else:
                from .ai_similarity import AISimilarityEstimator

                return AISimilarityEstimator(config)
        except Exception as e:
            logger.error(f"Failed to create estimator: {str(e)}")
            raise EstimationConfigurationError(f"Failed to create estimator: {str(e)}")
