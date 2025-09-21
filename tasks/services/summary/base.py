import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ...models import Task, TaskActivity

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result from task summary generation."""

    summary: str
    tokens_used: int

    def __str__(self) -> str:
        return f"Summary ({self.tokens_used} tokens): {self.summary[:50]}..."


class SummaryError(Exception):
    """Base exception for summary errors."""

    pass


class SummaryConfigurationError(SummaryError):
    """Exception raised for summary configuration errors."""

    pass


class SummaryProviderError(SummaryError):
    """Exception raised for summary provider errors."""

    pass


class SummaryProvider(ABC):
    """Abstract base class for summary providers."""

    def __init__(self, config):
        """Initialize summary provider with configuration."""
        self.config = config
        self._setup()

    @abstractmethod
    def _setup(self) -> None:
        """Setup the summary provider."""
        pass

    @abstractmethod
    def generate_task_summary(
        self,
        task: Task,
        new_activities: List[TaskActivity],
        previous_summary: Optional[str] = None,
    ) -> SummaryResult:
        """Generate or update task summary."""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the provider."""
        pass

    def _build_context(
        self,
        task: Task,
        activities: List[TaskActivity],
        previous_summary: Optional[str],
    ) -> str:
        """Build context for AI prompt."""
        context_parts = [
            f"Task: {task.title}",
            f"Description: {task.description or 'No description provided'}",
            f"Current Status: {task.get_status_display()}",
            f"Priority: {task.get_priority_display()}",
        ]

        # Add assignee and reporter info
        if task.assignee:
            context_parts.append(f"Assignee: {task.assignee.username}")
        if task.reporter:
            context_parts.append(f"Reporter: {task.reporter.username}")

        # Add estimate if available
        if task.estimate:
            context_parts.append(f"Estimate: {task.estimate} story points")

        # Add due date if available
        if task.due_date:
            context_parts.append(f"Due Date: {task.due_date.strftime('%Y-%m-%d')}")

        context_parts.append("")

        # Handle previous summary
        if previous_summary:
            context_parts.extend(
                [
                    "PREVIOUS SUMMARY:",
                    previous_summary,
                    "",
                    "NEW ACTIVITIES TO INCORPORATE:",
                ]
            )
        else:
            context_parts.append("RECENT ACTIVITIES:")

        # Add activities
        for activity in activities:
            timestamp = activity.timestamp.strftime("%Y-%m-%d %H:%M")
            context_parts.append(f"- {timestamp}: {activity.description}")

        return "\n".join(context_parts)


class SummaryProviderFactory:
    """Factory for creating summary providers."""

    @staticmethod
    def create_provider(config=None):
        """Create a summary provider based on configuration."""
        from ..base import AIConfig

        if config is None:
            config = AIConfig.from_settings()

        try:
            if config.use_mock:
                from .mock_provider import MockSummaryProvider

                return MockSummaryProvider(config)
            else:
                from .openai_provider import OpenAISummaryProvider

                return OpenAISummaryProvider(config)
        except Exception as e:
            logger.error(f"Failed to create summary provider: {str(e)}")
            raise SummaryConfigurationError(
                f"Failed to create summary provider: {str(e)}"
            )
