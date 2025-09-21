import logging
from typing import List, Optional

from ...models import Task, TaskActivity
from .base import SummaryProvider, SummaryResult

logger = logging.getLogger(__name__)


class MockSummaryProvider(SummaryProvider):
    """Mock implementation of summary provider for testing."""

    def _setup(self) -> None:
        """Setup mock provider."""
        logger.info("Mock summary provider initialized - no external API calls")

    def generate_task_summary(
        self,
        task: Task,
        new_activities: List[TaskActivity],
        previous_summary: Optional[str] = None,
    ) -> SummaryResult:
        """Generate mock task summary."""
        logger.info(f"Generating mock summary for task {task.id}")

        # Build mock summary based on task data
        summary_parts = [
            f"Task '{task.title}' summary: current status: {task.get_status_display().lower()}, "
            f"priority: {task.get_priority_display().lower()}."
        ]

        # Add activity count
        if new_activities:
            summary_parts.append(f"{len(new_activities)} recent activities tracked.")
        else:
            summary_parts.append("No recent activities.")

        # Add assignee info
        if task.assignee:
            summary_parts.append(f"Assigned to {task.assignee.username}.")
        else:
            summary_parts.append("No assignee.")

        # Add previous summary context if exists
        if previous_summary:
            summary_parts.append("Summary updated with new activities.")
        else:
            summary_parts.append("Task created and being tracked in the system.")

        # Simulate some token usage
        mock_summary = " ".join(summary_parts)
        mock_tokens = len(mock_summary.split()) * 2  # Rough token estimation

        return SummaryResult(summary=mock_summary, tokens_used=mock_tokens)

    def _get_system_prompt(self) -> str:
        """Get mock system prompt."""
        return "Mock system prompt for development and testing purposes."
