import logging
from typing import Any, Dict, List, Optional

from ..repositories import RepositoryFactory, TaskSummaryRepositoryInterface

logger = logging.getLogger(__name__)


class TaskSummaryAnalyzer:
    """Analyzer for task summary patterns and insights."""

    def __init__(
        self, summary_repository: Optional[TaskSummaryRepositoryInterface] = None
    ):
        """Initialize analyzer."""
        self.summary_repository = (
            summary_repository or RepositoryFactory.create_task_summary_repository()
        )

    def analyze_summary_quality(self, task_id: int) -> Dict[str, Any]:
        """Analyze the quality of a task summary."""
        summary = self.summary_repository.get_by_task_id(task_id)
        if not summary:
            return {"quality_score": 0, "issues": ["No summary exists"]}

        issues = []
        quality_score = 100

        # Check summary length
        if len(summary.summary_text) < 50:
            issues.append("Summary too short")
            quality_score -= 20
        elif len(summary.summary_text) > 1000:
            issues.append("Summary too long")
            quality_score -= 10

        # Check for key information
        text_lower = summary.summary_text.lower()
        if "status" not in text_lower:
            issues.append("Missing status information")
            quality_score -= 15

        if "priority" not in text_lower:
            issues.append("Missing priority information")
            quality_score -= 10

        # Check recency
        if summary.last_activity_processed:
            from django.utils import timezone

            days_since_update = (
                timezone.now() - summary.last_activity_processed.timestamp
            ).days
            if days_since_update > 7:
                issues.append("Summary may be outdated")
                quality_score -= 15

        return {
            "quality_score": max(0, quality_score),
            "issues": issues,
            "summary_length": len(summary.summary_text),
            "token_usage": summary.token_usage,
        }

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get overall summary statistics."""
        # This would require additional repository methods
        # For now, return placeholder
        return {
            "total_summaries": 0,
            "average_length": 0,
            "total_tokens_used": 0,
        }

    def suggest_improvements(self, task_id: int) -> List[str]:
        """Suggest improvements for a task summary."""
        summary = self.summary_repository.get_by_task_id(task_id)
        if not summary:
            return ["Create a summary first"]

        suggestions = []
        text = summary.summary_text.lower()

        if len(summary.summary_text) < 100:
            suggestions.append("Consider adding more detail about task progress")

        if "next steps" not in text and "next" not in text:
            suggestions.append("Include information about next steps")

        if "blocker" not in text and "blocked" not in text:
            suggestions.append("Mention any blockers or dependencies")

        if summary.token_usage > 500:
            suggestions.append(
                "Consider using a more concise summary style to reduce token usage"
            )

        return suggestions
