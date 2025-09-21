import json
import logging
from typing import Any, Dict, List

from openai import OpenAI

from ...models import Task
from ..builders import (
    EstimationResultBuilder,
    MockEstimationBuilder,
    SimilarTaskAnalysisBuilder,
)
from ..prompts import PromptBuilderFactory
from ..repositories import RepositoryFactory
from .base import (
    EstimationConfigurationError,
    EstimationError,
    EstimationResult,
    TaskEstimator,
)

logger = logging.getLogger(__name__)


class AISimilarityEstimator(TaskEstimator):
    """AI-powered estimator using similarity analysis with improved architecture."""

    def _setup(self) -> None:
        """Setup the AI similarity estimator."""
        if not self.config.api_key:
            raise EstimationConfigurationError("OpenAI API key is required")

        try:
            self.client = OpenAI(api_key=self.config.api_key)
            self.task_repository = RepositoryFactory.create_task_repository()
            logger.info(
                f"AI similarity estimator initialized with model: {self.config.model}"
            )
        except Exception as e:
            raise EstimationConfigurationError(
                f"Failed to initialize OpenAI client: {str(e)}"
            )

    def estimate_task(self, task: Task) -> EstimationResult:
        """Estimate task using AI similarity analysis."""
        self._validate_task(task)

        # Get similar tasks for context
        similar_tasks = self.task_repository.get_similar_tasks(task, limit=15)

        try:
            # Get AI response
            ai_result = self._get_ai_estimation(task, similar_tasks)

            # Build result using builder pattern
            return self._build_estimation_result(task, similar_tasks, ai_result)

        except EstimationError:
            raise
        except Exception as e:
            logger.error(
                f"AI similarity estimation failed for task {task.id}: {str(e)}"
            )
            raise EstimationError(f"AI similarity estimation failed: {str(e)}")

    def can_estimate(self, task: Task) -> bool:
        """Check if task can be estimated."""
        try:
            self._validate_task(task)
            return True
        except Exception:
            return False

    def _get_ai_estimation(
        self, task: Task, similar_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get AI estimation from OpenAI."""
        prompt = self._build_estimation_prompt(task, similar_tasks)

        logger.info(f"Requesting AI similarity estimation for task {task.id}")

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt(),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        response_text = response.choices[0].message.content
        if not response_text:
            raise EstimationError("AI returned empty response")

        return self._parse_ai_response(response_text, response.usage)

    def _get_system_prompt(self) -> str:
        """Get system prompt for AI estimation."""
        from ..prompts import SystemPromptBuilder

        return (
            SystemPromptBuilder(
                "an expert project manager specializing in software task estimation"
            )
            .add_capability(
                "analyzing task similarity and providing accurate effort estimates"
            )
            .set_response_format("Always respond with valid JSON format as requested.")
            .build()
        )

    def _build_estimation_prompt(
        self, task: Task, similar_tasks: List[Dict[str, Any]]
    ) -> str:
        """Build the prompt for AI similarity estimation."""
        return (
            PromptBuilderFactory.create_estimation_prompt_builder(task)
            .add_similar_tasks(similar_tasks)
            .build()
        )

    def _parse_ai_response(self, response_text: str, usage) -> Dict[str, Any]:
        """Parse and validate AI response."""
        try:
            ai_result = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {response_text}")
            raise EstimationError(f"Invalid JSON response from AI: {str(e)}")

        # Validate required fields
        required_fields = ["estimated_hours", "confidence_score", "reasoning"]
        for field in required_fields:
            if field not in ai_result:
                raise EstimationError(f"AI response missing required field: {field}")

        # Add usage information
        ai_result["_usage"] = usage
        return ai_result

    def _build_estimation_result(
        self, task: Task, similar_tasks: List[Dict[str, Any]], ai_result: Dict[str, Any]
    ) -> EstimationResult:
        """Build EstimationResult using builder pattern."""
        # Extract and validate values
        estimated_hours = float(ai_result["estimated_hours"])
        confidence_score = float(ai_result["confidence_score"])

        # Build similar task analysis
        analysis_builder = SimilarTaskAnalysisBuilder()
        for task_data in similar_tasks[:5]:  # Top 5 for result
            matching_analysis = self._find_matching_analysis(task_data, ai_result)
            analysis_builder.add_task_analysis(
                task_data["id"], task_data, matching_analysis
            )

        # Build result using builder
        usage = ai_result.get("_usage")
        tokens_used = usage.total_tokens if usage else 0

        result_builder = (
            EstimationResultBuilder()
            .set_hours(estimated_hours)
            .set_confidence(confidence_score)
            .add_reasoning_section(
                "AI Similarity-Based Estimation", ai_result["reasoning"]
            )
        )

        # Add similar task analysis
        if similar_tasks:
            result_builder.add_reasoning_section("Similar Task Analysis", "")
            result_builder.add_reasoning_list(analysis_builder.build_for_reasoning())

        # Add risk factors if present
        if ai_result.get("risk_factors"):
            result_builder.add_reasoning_section("Risk Factors", "")
            result_builder.add_reasoning_list(ai_result["risk_factors"])

        # Add assumptions if present
        if ai_result.get("assumptions"):
            result_builder.add_reasoning_section("Assumptions", "")
            result_builder.add_reasoning_list(ai_result["assumptions"])

        # Add technical details
        result_builder.add_reasoning_text(f"\nModel: {self.config.model}")
        result_builder.add_reasoning_text(f"Temperature: {self.config.temperature}")
        result_builder.add_reasoning_text(
            f"Historical tasks analyzed: {len(similar_tasks)}"
        )

        # Set similar tasks and metadata
        result_builder.set_similar_tasks(analysis_builder.build_for_result())
        result_builder.set_metadata(
            {
                "model": self.config.model,
                "tokens_used": tokens_used,
                "temperature": self.config.temperature,
                "historical_tasks_count": len(similar_tasks),
                "risk_factors": ai_result.get("risk_factors", []),
                "assumptions": ai_result.get("assumptions", []),
                "similar_task_analysis": ai_result.get("similar_task_analysis", []),
            }
        )

        estimation_result = result_builder.build()

        logger.info(
            f"AI similarity estimation completed for task {task.id}: "
            f"{estimation_result.estimated_hours}h (confidence: {estimation_result.confidence_score:.2f}, tokens: {tokens_used})"
        )

        return estimation_result

    def _find_matching_analysis(
        self, task_data: Dict[str, Any], ai_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find matching analysis for a task in AI result."""
        return next(
            (
                a
                for a in ai_result.get("similar_task_analysis", [])
                if isinstance(a, dict) and a.get("task_id") == task_data["id"]
            ),
            {},
        )


class MockAISimilarityEstimator(TaskEstimator):
    """Mock AI similarity estimator with improved architecture."""

    def _setup(self) -> None:
        """Setup mock estimator."""
        self.task_repository = RepositoryFactory.create_task_repository()
        logger.info("Mock AI similarity estimator initialized - no external API calls")

    def estimate_task(self, task: Task) -> EstimationResult:
        """Generate mock AI similarity estimation."""
        self._validate_task(task)

        # Get similar tasks for realistic mock
        similar_tasks = self.task_repository.get_similar_tasks(task, limit=5)

        # Use builder pattern for mock estimation
        mock_builder = (
            MockEstimationBuilder(task)
            .analyze_title_complexity()
            .analyze_description_complexity()
            .analyze_priority_impact()
            .apply_similar_tasks_influence(similar_tasks)
            .apply_deterministic_variance()
        )

        estimated_hours = mock_builder.get_estimated_hours()

        # Calculate mock confidence
        confidence = self._calculate_mock_confidence(task, similar_tasks)

        # Build similar tasks result with mock similarity scores
        similar_tasks_result = self._build_mock_similar_tasks(similar_tasks, task.id)

        # Build result using builder pattern
        result_builder = (
            EstimationResultBuilder()
            .set_hours(estimated_hours)
            .set_confidence(confidence)
            .add_reasoning_section("Mock AI Similarity-Based Estimation")
            .add_reasoning_section("Task Analysis")
            .add_reasoning_list(self._build_task_analysis_list(task, mock_builder))
            .add_reasoning_section("Complexity Factors")
            .add_reasoning_list(
                mock_builder.complexity_factors or ["Standard complexity"]
            )
            .add_reasoning_section("Similar Tasks Analysis")
            .add_reasoning_list(
                self._build_similar_tasks_reasoning(similar_tasks_result)
            )
            .add_reasoning_section("Estimation Calculation")
            .add_reasoning_list(
                self._build_calculation_list(estimated_hours, mock_builder, confidence)
            )
            .add_reasoning_text(
                "\nNote: This is a mock estimation for development purposes."
            )
            .set_similar_tasks(similar_tasks_result)
            .set_metadata(
                {
                    **mock_builder.get_metadata(),
                    "historical_tasks_count": len(similar_tasks),
                }
            )
        )

        return result_builder.build()

    def can_estimate(self, task: Task) -> bool:
        """Check if task can be estimated."""
        try:
            self._validate_task(task)
            return True
        except Exception:
            return False

    def _calculate_mock_confidence(
        self, task: Task, similar_tasks: List[Dict[str, Any]]
    ) -> float:
        """Calculate mock confidence score."""
        confidence = 0.75
        if similar_tasks:
            confidence += min(len(similar_tasks) * 0.03, 0.15)
        if task.description and len(task.description) > 50:
            confidence += 0.05

        return min(confidence, 0.9)

    def _build_mock_similar_tasks(
        self, similar_tasks: List[Dict[str, Any]], seed: int
    ) -> List[Dict[str, Any]]:
        """Build mock similar tasks with similarity scores."""
        import random

        random.seed(seed)

        similar_tasks_result = []
        for i, task_data in enumerate(similar_tasks[:3]):
            similarity_score = 0.9 - (i * 0.1) + random.uniform(-0.1, 0.1)
            similarity_score = max(0.3, min(similarity_score, 0.95))

            similar_tasks_result.append(
                {
                    "id": task_data["id"],
                    "title": task_data["title"],
                    "estimate": task_data["estimate"],
                    "priority": task_data["priority"],
                    "similarity_score": round(similarity_score, 2),
                }
            )

        return similar_tasks_result

    def _build_task_analysis_list(
        self, task: Task, mock_builder: MockEstimationBuilder
    ) -> List[str]:
        """Build task analysis list."""
        title_words = len(task.title.split())
        desc_words = len(task.description.split()) if task.description else 0

        return [
            f"Title complexity: {title_words} words",
            f"Description length: {desc_words} words",
            f"Priority: {task.priority} (×{mock_builder.priority_multiplier})",
        ]

    def _build_similar_tasks_reasoning(
        self, similar_tasks_result: List[Dict[str, Any]]
    ) -> List[str]:
        """Build reasoning for similar tasks."""
        if not similar_tasks_result:
            return ["No similar tasks found"]

        return [
            f"Task #{st['id']}: {st['estimate']}h (similarity: {st['similarity_score']:.2f})"
            for st in similar_tasks_result
        ]

    def _build_calculation_list(
        self,
        estimated_hours: float,
        mock_builder: MockEstimationBuilder,
        confidence: float,
    ) -> List[str]:
        """Build calculation reasoning list."""
        return [
            f"Base estimate: {estimated_hours / mock_builder.variance_factor:.1f}h",
            f"Adjusted for complexity: {estimated_hours:.1f}h",
            f"Confidence: {confidence:.2f}",
        ]
