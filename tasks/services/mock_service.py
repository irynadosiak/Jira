import logging
from typing import List, Optional

from ..models import Task, TaskActivity
from .base import AIProvider, AISummaryResult

logger = logging.getLogger(__name__)


class MockAIProvider(AIProvider):
    """Mock AI provider for development and testing."""

    def _setup(self) -> None:
        """Setup mock provider (no external dependencies)."""
        logger.info("Using mock AI provider - no external API calls will be made")

    def generate_task_summary(
        self,
        task: Task,
        new_activities: List[TaskActivity],
        previous_summary: Optional[str] = None,
    ) -> AISummaryResult:
        """Generate a mock summary for development/testing purposes."""
        logger.info(f"Generating mock summary for task {task.id}")

        status_info = f"Current status: {task.get_status_display()}"
        priority_info = f"Priority: {task.get_priority_display()}"

        if task.assignee:
            assignee_info = f"Assigned to: {task.assignee.username}"
        else:
            assignee_info = "No assignee"

        activity_count = len(new_activities)
        if activity_count == 0:
            activity_info = "No recent activities"
        elif activity_count == 1:
            activity_info = "1 recent activity"
        else:
            activity_info = f"{activity_count} recent activities"

        if previous_summary:
            mock_summary = (
                f"Updated summary for '{task.title}': {status_info.lower()}, {priority_info.lower()}. "
                f"{activity_info} recorded. {assignee_info}. "
                f"Task progress continues with recent updates."
            )
        else:
            mock_summary = (
                f"Task '{task.title}' summary: {status_info.lower()}, {priority_info.lower()}. "
                f"{activity_info} tracked. {assignee_info}. "
                f"Task created and being tracked in the system."
            )

        mock_tokens = min(len(mock_summary.split()) * 2 + 50, 150)

        return AISummaryResult(summary=mock_summary, tokens_used=mock_tokens)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for mock AI (not used but required by interface)."""
        return (
            "You are a project management assistant that creates concise, professional "
            "summaries of task activities."
        )
