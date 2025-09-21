import logging
from typing import Any, Dict, Optional

from ...models import Task
from ..interfaces import TaskParserServiceInterface
from ..repositories import RepositoryFactory, TaskRepositoryInterface
from .base import ParseResult, TaskParser, TaskParserFactory

logger = logging.getLogger(__name__)


class TaskParserService(TaskParserServiceInterface):
    """Service for parsing natural language text into structured task data."""

    def __init__(
        self,
        parser: Optional[TaskParser] = None,
        task_repository: Optional[TaskRepositoryInterface] = None,
    ):
        """
        Initialize the parser service with dependencies.

        parser: TaskParser instance. If None, creates one using factory.
        task_repository: Task repository for data access
        """
        self.parser = parser or TaskParserFactory.create_parser()
        self.task_repository = (
            task_repository or RepositoryFactory.create_task_repository()
        )
        logger.info(
            f"TaskParserService initialized with parser: {type(self.parser).__name__}"
        )

    def parse_text_to_task_data(self, text: str) -> ParseResult:
        """
        Parse natural language text into structured task data.

        text: Natural language text describing a task
        """
        try:
            logger.info(f"Parsing text to task data: {text[:100]}...")

            # Pre-parsing validation
            validation_result = self._validate_parsing_request(text)
            if not validation_result["is_valid"]:
                from .base import ParserError

                raise ParserError(
                    f"Validation failed: {'; '.join(validation_result['errors'])}"
                )

            # Perform parsing
            result = self.parser.parse_text(text)

            # Post-parsing validation and enhancement
            enhanced_result = self._enhance_parse_result(result)

            logger.info(
                f"Successfully parsed text to task: '{enhanced_result.title}' "
                f"(confidence: {enhanced_result.confidence_score:.2f})"
            )
            return enhanced_result

        except Exception as e:
            logger.error(f"Error parsing text to task data: {str(e)}")
            raise

    def create_task_from_text(self, text: str, reporter_id: int) -> Task:
        """
        Parse text and create a task directly.

        text: Natural language text describing a task
        reporter_id: ID of the user creating the task
        """
        try:
            # Parse the text
            parse_result = self.parse_text_to_task_data(text)

            # Create task from parsed data
            task_data = self._convert_parse_result_to_task_data(
                parse_result, reporter_id
            )
            task = Task.objects.create(**task_data)

            logger.info(f"Created task from text: '{task.title}' (ID: {task.id})")
            return task

        except Exception as e:
            logger.error(f"Error creating task from text: {str(e)}")
            raise

    def get_parsing_suggestions(self, text: str) -> Dict[str, Any]:
        """
        Get suggestions for improving text parsing.

        text: Text to analyze
        """
        suggestions: Dict[str, Any] = {
            "text_length": len(text),
            "suggestions": [],
            "tips": [],
            "estimated_confidence": 0.0,
        }

        # Analyze text characteristics
        if len(text) < 10:
            suggestions["suggestions"].append("Add more details for better parsing")
            suggestions["tips"].append("Include what needs to be done and why")

        if len(text) > 1000:
            suggestions["suggestions"].append("Consider breaking into multiple tasks")
            suggestions["tips"].append(
                "Shorter descriptions are easier to parse accurately"
            )

        # Check for missing information
        text_lower = text.lower()

        if not any(
            word in text_lower
            for word in [
                "fix",
                "add",
                "create",
                "implement",
                "update",
                "remove",
                "build",
            ]
        ):
            suggestions["suggestions"].append(
                "Include action words (fix, add, create, etc.)"
            )

        if not any(
            word in text_lower
            for word in ["priority", "urgent", "high", "low", "important"]
        ):
            suggestions["tips"].append("Mention priority level if important")

        if not any(word in text_lower for word in ["hour", "day", "week", "point"]):
            suggestions["tips"].append("Include time estimates for better planning")

        # Estimate confidence
        if len(text) >= 20 and any(
            word in text_lower for word in ["fix", "add", "create"]
        ):
            suggestions["estimated_confidence"] = 0.8
        elif len(text) >= 10:
            suggestions["estimated_confidence"] = 0.6
        else:
            suggestions["estimated_confidence"] = 0.3

        return suggestions

    def _validate_parsing_request(self, text: str) -> Dict[str, Any]:
        """Validate if text is suitable for parsing."""
        errors = []
        warnings = []

        # Basic validation
        if not text or not text.strip():
            errors.append("Text cannot be empty")

        if text and len(text.strip()) < 5:
            errors.append("Text too short - please provide more details")

        if text and len(text) > 2000:
            errors.append("Text too long - please keep under 2000 characters")

        # Quality checks
        if text and len(text.split()) < 3:
            warnings.append("Very brief text - parsing may be less accurate")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _enhance_parse_result(self, result: ParseResult) -> ParseResult:
        """Enhance parse result with additional processing."""
        # Ensure title is not empty
        if not result.title or not result.title.strip():
            result.title = "New Task"

        # Ensure description is not empty
        if not result.description or not result.description.strip():
            result.description = result.raw_text or "No description provided"

        # Validate priority
        valid_priorities = ["low", "medium", "high", "urgent"]
        if result.priority not in valid_priorities:
            result.priority = "medium"

        # Validate task type
        valid_types = ["task", "bug", "feature", "story", "epic"]
        if result.task_type not in valid_types:
            result.task_type = "task"

        return result

    def _convert_parse_result_to_task_data(
        self, result: ParseResult, reporter_id: int
    ) -> Dict[str, Any]:
        """Convert ParseResult to Task model data."""

        task_data = {
            "title": result.title,
            "description": result.description,
            "priority": result.priority,
            "status": "todo",  # Default status for new tasks
            "reporter_id": reporter_id,
        }

        # Add optional fields if present
        if result.estimate:
            task_data["estimate"] = result.estimate

        if result.due_date:
            try:
                from datetime import datetime

                due_date = datetime.strptime(result.due_date, "%Y-%m-%d").date()
                task_data["due_date"] = due_date
            except ValueError:
                logger.warning(f"Invalid due date format: {result.due_date}")

        return task_data
