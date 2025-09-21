import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result from text-to-task parsing."""

    title: str
    description: str
    priority: str = "medium"
    estimate: Optional[int] = None
    due_date: Optional[str] = None
    task_type: str = "task"
    tags: Optional[list] = None
    confidence_score: float = 0.0
    raw_text: str = ""

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.tags is None:
            self.tags = []

    def __str__(self) -> str:
        return f"ParseResult: '{self.title}' ({self.priority}, {self.confidence_score:.2f})"


class ParserError(Exception):
    """Base exception for parser errors."""

    pass


class ParserConfigurationError(ParserError):
    """Exception raised for parser configuration errors."""

    pass


class ParserProviderError(ParserError):
    """Exception raised for parser provider errors."""

    pass


class TaskParser(ABC):
    """Abstract base class for task text parsers."""

    def __init__(self, config):
        """Initialize task parser with configuration."""
        self.config = config
        self._setup()

    @abstractmethod
    def _setup(self) -> None:
        """Setup the task parser."""
        pass

    @abstractmethod
    def parse_text(self, text: str) -> ParseResult:
        """Parse natural language text into structured task data."""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the parser."""
        pass

    def _validate_text(self, text: str) -> None:
        """Validate input text."""
        if not text or not text.strip():
            raise ParserError("Text cannot be empty")

        if len(text.strip()) < 5:
            raise ParserError("Text too short - please provide more details")

        if len(text) > 2000:
            raise ParserError("Text too long - please keep under 2000 characters")

    def _normalize_priority(self, priority: str) -> str:
        """Normalize priority to valid choices."""
        priority_lower = priority.lower().strip()

        priority_mapping = {
            "low": "low",
            "minor": "low",
            "trivial": "low",
            "medium": "medium",
            "normal": "medium",
            "moderate": "medium",
            "high": "high",
            "important": "high",
            "major": "high",
            "urgent": "urgent",
            "critical": "urgent",
            "blocker": "urgent",
            "emergency": "urgent",
        }

        return priority_mapping.get(priority_lower, "medium")

    def _normalize_task_type(self, task_type: str) -> str:
        """Normalize task type to valid choices."""
        type_lower = task_type.lower().strip()

        type_mapping = {
            "bug": "bug",
            "issue": "bug",
            "defect": "bug",
            "error": "bug",
            "problem": "bug",
            "feature": "feature",
            "enhancement": "feature",
            "improvement": "feature",
            "new": "feature",
            "task": "task",
            "todo": "task",
            "work": "task",
            "chore": "task",
            "story": "story",
            "user story": "story",
            "epic": "epic",
        }

        return type_mapping.get(type_lower, "task")


class TaskParserFactory:
    """Factory for creating task parsers."""

    @staticmethod
    def create_parser(config=None):
        """Create a task parser based on configuration."""
        from ..base import AIConfig

        if config is None:
            config = AIConfig.from_settings()

        try:
            if config.use_mock:
                from .mock_parser import MockTaskParser

                return MockTaskParser(config)
            else:
                from .openai_parser import OpenAITaskParser

                return OpenAITaskParser(config)
        except Exception as e:
            logger.error(f"Failed to create task parser: {str(e)}")
            raise ParserConfigurationError(f"Failed to create task parser: {str(e)}")
