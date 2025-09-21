import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from django.conf import settings

from ..models import Task, TaskActivity

logger = logging.getLogger(__name__)


@dataclass
class AIConfig:
    """Configuration class for AI services."""

    api_key: Optional[str]
    model: str
    max_tokens: int
    temperature: float
    use_mock: bool = False

    @classmethod
    def from_settings(cls) -> "AIConfig":
        """Create configuration from Django settings."""
        api_key = settings.OPENAI_API_KEY
        use_mock = not api_key or getattr(settings, "USE_MOCK_AI", False)

        return cls(
            api_key=api_key,
            model=settings.OPENAI_MODEL,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
            use_mock=use_mock,
        )


class AIProviderError(Exception):
    """Base exception for AI provider errors."""

    pass


class AIConfigurationError(AIProviderError):
    """Exception raised for AI configuration errors."""

    pass


class AIServiceError(AIProviderError):
    """Exception raised for AI service errors."""

    pass


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: AIConfig):
        """Initialize AI provider with configuration."""
        self.config = config
        self._setup()

    @abstractmethod
    def _setup(self) -> None:
        """Setup the AI provider."""
        pass

    @abstractmethod
    def generate_task_summary(
        self,
        task: Task,
        new_activities: List[TaskActivity],
        previous_summary: Optional[str] = None,
    ):
        """Generate or update task summary using AI."""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI provider."""
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
                    "Previous Summary:",
                    previous_summary,
                    "",
                    "New Activities to incorporate:",
                ]
            )
        else:
            context_parts.append("All Task Activities:")

        # Add activities
        if not activities:
            context_parts.append("- No activities recorded")
        else:
            for activity in activities:
                user_info = f" by {activity.user.username}" if activity.user else ""
                timestamp = activity.timestamp.strftime("%Y-%m-%d %H:%M")
                context_parts.append(
                    f"- {timestamp}: {activity.description}{user_info}"
                )

        context_parts.append("")

        # Add instruction
        if previous_summary:
            context_parts.append(
                "Please update the previous summary to incorporate the new activities. "
                "Focus on the most significant changes."
            )
        else:
            context_parts.append(
                "Please create a comprehensive summary of this task and its activities. "
                "Focus on the task's progress, key changes, and current state."
            )

        return "\n".join(context_parts)
