import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .estimation.base import EstimationResult

logger = logging.getLogger(__name__)


class EstimationResultBuilder:
    """Builder for constructing EstimationResult objects."""

    def __init__(self):
        """Initialize builder with default values."""
        self.reset()

    def reset(self) -> "EstimationResultBuilder":
        """Reset builder to initial state."""
        self._estimated_hours: float = 0.0
        self._confidence_score: float = 0.0
        self._reasoning_parts: List[str] = []
        self._similar_tasks: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}
        return self

    def set_hours(self, hours: float) -> "EstimationResultBuilder":
        """Set estimated hours."""
        self._estimated_hours = max(0.1, min(hours, 500))  # Reasonable bounds
        return self

    def set_confidence(self, confidence: float) -> "EstimationResultBuilder":
        """Set confidence score."""
        self._confidence_score = max(0.0, min(confidence, 1.0))  # 0-1 range
        return self

    def add_reasoning_section(
        self, title: str, content: str = ""
    ) -> "EstimationResultBuilder":
        """Add a reasoning section."""
        if title:
            self._reasoning_parts.append(title)
            if "=" in title or "-" in title:
                # Title is already formatted
                pass
            else:
                # Add underline for section titles
                self._reasoning_parts.append("=" * len(title))

        if content:
            self._reasoning_parts.extend(["", content])

        return self

    def add_reasoning_list(
        self, items: List[str], prefix: str = "•"
    ) -> "EstimationResultBuilder":
        """Add a list of reasoning items."""
        for item in items:
            self._reasoning_parts.append(f"{prefix} {item}")
        return self

    def add_reasoning_text(self, text: str) -> "EstimationResultBuilder":
        """Add plain reasoning text."""
        if text:
            self._reasoning_parts.extend(["", text])
        return self

    def set_similar_tasks(
        self, similar_tasks: List[Dict[str, Any]]
    ) -> "EstimationResultBuilder":
        """Set similar tasks."""
        self._similar_tasks = similar_tasks[:5]  # Limit to top 5
        return self

    def add_metadata(self, key: str, value: Any) -> "EstimationResultBuilder":
        """Add metadata item."""
        self._metadata[key] = value
        return self

    def set_metadata(self, metadata: Dict[str, Any]) -> "EstimationResultBuilder":
        """Set entire metadata dictionary."""
        self._metadata = metadata.copy()
        return self

    def build(self) -> "EstimationResult":
        """Build the EstimationResult."""
        from .estimation.base import EstimationResult

        reasoning = (
            "\n".join(self._reasoning_parts)
            if self._reasoning_parts
            else "No reasoning provided"
        )

        return EstimationResult(
            estimated_hours=round(self._estimated_hours, 1),
            confidence_score=self._confidence_score,
            reasoning=reasoning,
            similar_tasks=self._similar_tasks,
            metadata=self._metadata,
        )


class ReasoningBuilder:
    """Helper builder specifically for reasoning text construction."""

    def __init__(self):
        """Initialize reasoning builder."""
        self._parts: List[str] = []

    def add_header(self, title: str, underline_char: str = "=") -> "ReasoningBuilder":
        """Add a header section."""
        self._parts.extend([title, underline_char * len(title), ""])
        return self

    def add_section(self, title: str, underline_char: str = "-") -> "ReasoningBuilder":
        """Add a section title."""
        self._parts.extend(["", title, underline_char * len(title)])
        return self

    def add_text(self, text: str) -> "ReasoningBuilder":
        """Add plain text."""
        self._parts.append(text)
        return self

    def add_list(self, items: List[str], prefix: str = "•") -> "ReasoningBuilder":
        """Add a bulleted list."""
        for item in items:
            self._parts.append(f"{prefix} {item}")
        return self

    def add_key_value(self, key: str, value: str) -> "ReasoningBuilder":
        """Add key-value pair."""
        self._parts.append(f"{key}: {value}")
        return self

    def add_blank_line(self) -> "ReasoningBuilder":
        """Add a blank line."""
        self._parts.append("")
        return self

    def build(self) -> str:
        """Build the reasoning text."""
        return "\n".join(self._parts)


class SimilarTaskAnalysisBuilder:
    """Builder for constructing similar task analysis."""

    def __init__(self):
        """Initialize builder."""
        self._analyses: List[Dict[str, Any]] = []

    def add_task_analysis(
        self,
        task_id: int,
        task_data: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None,
    ) -> "SimilarTaskAnalysisBuilder":
        """Add analysis for a similar task."""
        similarity_score = 0.0
        factors = []

        if ai_analysis and isinstance(ai_analysis, dict):
            similarity_score = ai_analysis.get("similarity_score", 0.0)
            factors = ai_analysis.get("similarity_factors", [])

        analysis = {
            "id": task_id,
            "title": task_data.get("title", ""),
            "estimate": task_data.get("estimate", 0),
            "priority": task_data.get("priority", ""),
            "similarity_score": round(similarity_score, 2),
            "factors": factors,
        }

        self._analyses.append(analysis)
        return self

    def build_for_reasoning(self) -> List[str]:
        """Build reasoning text lines for similar tasks."""
        if not self._analyses:
            return ["• No similar tasks found"]

        lines = []
        for analysis in self._analyses:
            line = f"• Task #{analysis['id']}: {analysis['estimate']}h"
            if analysis["similarity_score"] > 0:
                line += f" (similarity: {analysis['similarity_score']:.2f})"
            lines.append(line)

            if analysis["factors"]:
                lines.append(f"  Factors: {', '.join(analysis['factors'])}")

        return lines

    def build_for_result(self) -> List[Dict[str, Any]]:
        """Build similar tasks for EstimationResult."""
        return [
            {
                "id": analysis["id"],
                "title": analysis["title"],
                "estimate": analysis["estimate"],
                "priority": analysis["priority"],
                "similarity_score": analysis["similarity_score"],
            }
            for analysis in self._analyses
        ]


class MockEstimationBuilder:
    """Builder for mock estimation results."""

    def __init__(self, task):
        """Initialize with task."""
        self.task = task
        self.complexity_factors: List[str] = []
        self.base_hours: float = 3.0
        self.priority_multiplier: float = 1.0
        self.variance_factor: float = 1.0

    def analyze_title_complexity(self) -> "MockEstimationBuilder":
        """Analyze title complexity."""
        title_words = len(self.task.title.split())
        if title_words > 8:
            self.base_hours *= 1.3
            self.complexity_factors.append("Complex title")
        elif title_words < 3:
            self.base_hours *= 0.8
            self.complexity_factors.append("Simple title")
        return self

    def analyze_description_complexity(self) -> "MockEstimationBuilder":
        """Analyze description complexity."""
        if self.task.description:
            desc_words = len(self.task.description.split())
            if desc_words > 100:
                self.base_hours *= 1.5
                self.complexity_factors.append("Detailed description")
            elif desc_words < 20:
                self.base_hours *= 0.9
                self.complexity_factors.append("Brief description")
        return self

    def analyze_priority_impact(self) -> "MockEstimationBuilder":
        """Analyze priority impact."""
        priority_multipliers = {"low": 0.8, "medium": 1.0, "high": 1.2, "urgent": 1.4}
        self.priority_multiplier = priority_multipliers.get(self.task.priority, 1.0)
        self.base_hours *= self.priority_multiplier

        if self.priority_multiplier != 1.0:
            self.complexity_factors.append(f"{self.task.priority} priority")
        return self

    def apply_similar_tasks_influence(
        self, similar_tasks: List[Dict[str, Any]]
    ) -> "MockEstimationBuilder":
        """Apply influence from similar tasks."""
        if similar_tasks:
            avg_similar_estimate = sum(t["estimate"] for t in similar_tasks) / len(
                similar_tasks
            )
            # Blend with similar tasks average (70% similar, 30% calculated)
            self.base_hours = (avg_similar_estimate * 0.7) + (self.base_hours * 0.3)
            self.complexity_factors.append(
                f"Based on {len(similar_tasks)} similar tasks"
            )
        return self

    def apply_deterministic_variance(self) -> "MockEstimationBuilder":
        """Apply deterministic variance based on task ID."""
        import random

        random.seed(self.task.id)
        self.variance_factor = random.uniform(0.85, 1.15)
        return self

    def get_estimated_hours(self) -> float:
        """Get final estimated hours."""
        return self.base_hours * self.variance_factor

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for mock estimation."""
        return {
            "model": "mock-ai-similarity",
            "tokens_used": 0,
            "is_mock": True,
            "complexity_factors": self.complexity_factors,
            "priority_multiplier": self.priority_multiplier,
            "variance_factor": round(self.variance_factor, 2),
        }
