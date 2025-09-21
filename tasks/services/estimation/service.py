import logging
from typing import Any, Dict, List, Optional

from ...models import Task
from ..interfaces import TaskEstimationServiceInterface
from ..repositories import RepositoryFactory, TaskRepositoryInterface
from .base import EstimationError, EstimationResult, EstimatorFactory, TaskEstimator

logger = logging.getLogger(__name__)


class TaskEstimationService(TaskEstimationServiceInterface):
    """Enhanced task estimation service with better architecture."""

    def __init__(
        self,
        estimator: Optional[TaskEstimator] = None,
        task_repository: Optional[TaskRepositoryInterface] = None,
    ):
        """
        Initialize estimation service.

        estimator: TaskEstimator instance. If None, creates one using factory.
        task_repository: Task repository for data access
        """
        self.estimator = estimator or EstimatorFactory.create_estimator()
        self.task_repository = (
            task_repository or RepositoryFactory.create_task_repository()
        )
        logger.info(
            f"TaskEstimationService initialized with estimator: {type(self.estimator).__name__}"
        )

    def estimate_task(self, task_id: int) -> EstimationResult:
        """
        Estimate effort for a task.

        task_id: ID of the task to estimate
        """
        try:
            task = self.task_repository.get_by_id(task_id)

            # Pre-estimation validation
            validation_result = self._validate_estimation_request(task)
            if not validation_result["is_valid"]:
                raise EstimationError(
                    f"Task validation failed: {'; '.join(validation_result['errors'])}"
                )

            # Perform estimation
            result = self.estimator.estimate_task(task)

            # Post-estimation validation
            self._validate_estimation_result(result)

            logger.info(
                f"Successfully estimated task {task_id}: {result.estimated_hours}h"
            )
            return result

        except Task.DoesNotExist:
            logger.error(f"Task with ID {task_id} not found")
            raise
        except EstimationError as e:
            logger.error(f"Estimation error for task {task_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during estimation for task {task_id}: {str(e)}"
            )
            raise EstimationError(f"Estimation failed: {str(e)}")

    def can_estimate(self, task_id: int) -> bool:
        """
        Check if a task can be estimated.

        task_id: ID of the task to check
        """
        try:
            if not self.task_repository.exists(task_id):
                return False

            task = self.task_repository.get_by_id(task_id)
            return self.estimator.can_estimate(task)
        except Exception as e:
            logger.error(f"Error checking if task {task_id} can be estimated: {str(e)}")
            return False

    def get_estimation_metadata(self, task_id: int) -> Dict[str, Any]:
        """
        Get metadata about estimation capability for a task.

        task_id: ID of the task to check
        """
        metadata: Dict[str, Any] = {
            "task_exists": False,
            "can_estimate": False,
            "estimator_type": type(self.estimator).__name__,
            "validation_errors": [],
            "similar_tasks_count": 0,
        }

        try:
            if not self.task_repository.exists(task_id):
                metadata["validation_errors"].append("Task does not exist")
                return metadata

            metadata["task_exists"] = True
            task = self.task_repository.get_by_id(task_id)

            # Check estimation capability
            metadata["can_estimate"] = self.estimator.can_estimate(task)

            # Validation check
            validation_result = self._validate_estimation_request(task)
            metadata["validation_errors"] = validation_result.get("errors", [])

            # Similar tasks count
            metadata["similar_tasks_count"] = len(
                self.task_repository.get_similar_tasks(task, limit=100)
            )

            # Task complexity indicators
            metadata["complexity_indicators"] = self._analyze_task_complexity(task)

        except Exception as e:
            logger.error(
                f"Error getting estimation metadata for task {task_id}: {str(e)}"
            )
            metadata["validation_errors"].append(f"Error analyzing task: {str(e)}")

        return metadata

    def compare_estimations(self, task_ids: List[int]) -> Dict[str, Any]:
        """Compare estimations across multiple tasks."""
        comparisons: Dict[str, Any] = {
            "tasks": [],
            "average_hours": 0.0,
            "confidence_range": {"min": 1.0, "max": 0.0},
            "common_factors": [],
        }

        total_hours = 0.0
        valid_estimations = 0

        for task_id in task_ids:
            try:
                if self.can_estimate(task_id):
                    result = self.estimate_task(task_id)
                    comparisons["tasks"].append(
                        {
                            "task_id": task_id,
                            "estimated_hours": result.estimated_hours,
                            "confidence_score": result.confidence_score,
                        }
                    )

                    total_hours += result.estimated_hours
                    valid_estimations += 1

                    # Update confidence range
                    comparisons["confidence_range"]["min"] = min(
                        comparisons["confidence_range"]["min"], result.confidence_score
                    )
                    comparisons["confidence_range"]["max"] = max(
                        comparisons["confidence_range"]["max"], result.confidence_score
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to estimate task {task_id} for comparison: {str(e)}"
                )

        if valid_estimations > 0:
            comparisons["average_hours"] = total_hours / valid_estimations

        return comparisons

    def _validate_estimation_request(self, task: Task) -> Dict[str, Any]:
        """Validate if task is ready for estimation."""
        errors = []
        warnings = []

        # Basic validation
        if not task.title or not task.title.strip():
            errors.append("Task must have a title")

        if not task.description or not task.description.strip():
            errors.append("Task must have a description")

        # Quality checks
        if task.description and len(task.description) < 20:
            warnings.append(
                "Description is very brief - estimation may be less accurate"
            )

        if task.title and len(task.title.split()) < 3:
            warnings.append("Title is very brief - consider adding more detail")

        # Status checks
        if task.status in ["done", "closed"]:
            warnings.append("Task is already completed")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _validate_estimation_result(self, result: EstimationResult) -> None:
        """Validate estimation result."""
        if result.estimated_hours <= 0:
            raise EstimationError("Estimated hours must be positive")

        if result.estimated_hours > 1000:
            logger.warning(f"Very high estimation: {result.estimated_hours}h")

        if not (0 <= result.confidence_score <= 1):
            raise EstimationError("Confidence score must be between 0 and 1")

        if not result.reasoning or len(result.reasoning.strip()) < 10:
            raise EstimationError("Estimation must include reasoning")

    def _analyze_task_complexity(self, task: Task) -> Dict[str, Any]:
        """Analyze task complexity indicators."""
        indicators: Dict[str, Any] = {
            "title_word_count": len(task.title.split()) if task.title else 0,
            "description_word_count": len(task.description.split())
            if task.description
            else 0,
            "has_assignee": task.assignee is not None,
            "has_due_date": task.due_date is not None,
            "priority_level": task.priority,
            "estimated_complexity": "unknown",
        }

        # Simple complexity estimation
        complexity_score = 0

        if indicators["title_word_count"] > 8:
            complexity_score += 1
        if indicators["description_word_count"] > 100:
            complexity_score += 2
        if task.priority in ["high", "urgent"]:
            complexity_score += 1

        if complexity_score >= 3:
            indicators["estimated_complexity"] = "high"
        elif complexity_score >= 1:
            indicators["estimated_complexity"] = "medium"
        else:
            indicators["estimated_complexity"] = "low"

        return indicators
