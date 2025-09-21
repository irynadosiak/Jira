import logging
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async

from django.contrib.auth.models import User

from ..models import Task
from ..services import (
    EstimationError,
    ParserError,
    TaskEstimationService,
    TaskParserService,
    TaskSummaryService,
)
from .base import (
    BaseWebSocketConsumer,
    ProgressTrackingMixin,
    TaskWebSocketMixin,
    WebSocketError,
)

logger = logging.getLogger(__name__)


class TaskEstimationConsumer(
    TaskWebSocketMixin, ProgressTrackingMixin, BaseWebSocketConsumer
):
    """WebSocket consumer for AI-powered task estimation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.estimation_service = TaskEstimationService()

    def requires_authentication(self) -> bool:
        """Estimation allows anonymous access."""
        return False

    async def handle_message(self, data: Dict[str, Any]):
        """Handle estimation request."""
        action = data.get("action")

        if action == "estimate":
            await self.handle_estimation_request()
        else:
            raise WebSocketError(f"Unknown action: {action}")

    async def handle_estimation_request(self):
        """Process task estimation request."""
        # Define operation steps for progress tracking
        self.set_operation_steps(
            [
                {
                    "name": "validate",
                    "progress": 10,
                    "message": "Validating task data...",
                },
                {
                    "name": "analyze",
                    "progress": 30,
                    "message": "Analyzing task complexity...",
                },
                {
                    "name": "similar",
                    "progress": 60,
                    "message": "Finding similar tasks...",
                },
                {
                    "name": "calculate",
                    "progress": 80,
                    "message": "Calculating estimation...",
                },
            ]
        )

        try:
            await self.progress_to_next_step()
            if not await self.can_estimate_task():
                raise WebSocketError(
                    "Task must have both title and description for accurate estimation"
                )
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            result = await self.estimate_task()
            await self.complete_operation(
                {
                    "task_id": self.task_id,
                    "estimation": {
                        "estimated_hours": result.estimated_hours,
                        "confidence_score": result.confidence_score,
                        "reasoning": result.reasoning,
                        "similar_tasks": result.similar_tasks,
                        "metadata": result.metadata,
                    },
                }
            )

        except EstimationError as e:
            await self.send_error(f"Estimation failed: {str(e)}", "estimation_error")
        except Exception as e:
            logger.error(
                f"Failed to estimate task {self.task_id}: {str(e)}", exc_info=True
            )
            await self.send_error("Failed to estimate task", "internal_error")

    @database_sync_to_async
    def can_estimate_task(self) -> bool:
        """Check if task can be estimated."""
        if self.task_id is None:
            return False
        return self.estimation_service.can_estimate(self.task_id)

    @database_sync_to_async
    def estimate_task(self):
        """Perform task estimation."""
        if self.task_id is None:
            raise ValueError("Task ID is required for estimation")
        return self.estimation_service.estimate_task(self.task_id)


class TaskSummaryConsumer(
    TaskWebSocketMixin, ProgressTrackingMixin, BaseWebSocketConsumer
):
    """WebSocket consumer for AI-powered task summary generation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.summary_service = TaskSummaryService()

    def requires_authentication(self) -> bool:
        """Summary generation allows anonymous access."""
        return False

    async def handle_message(self, data: Dict[str, Any]):
        """Handle summary generation request."""
        action = data.get("action")

        if action == "generate_summary":
            await self.handle_summary_request()
        else:
            raise WebSocketError(f"Unknown action: {action}")

    async def handle_summary_request(self):
        """Process summary generation request."""
        # Define operation steps for progress tracking
        self.set_operation_steps(
            [
                {
                    "name": "load_activities",
                    "progress": 20,
                    "message": "Loading task activities...",
                },
                {
                    "name": "analyze_changes",
                    "progress": 40,
                    "message": "Analyzing changes...",
                },
                {
                    "name": "generate_summary",
                    "progress": 70,
                    "message": "Generating summary...",
                },
                {
                    "name": "format_output",
                    "progress": 90,
                    "message": "Formatting output...",
                },
            ]
        )

        try:
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            summary = await self.generate_summary()
            await self.complete_operation(
                {
                    "task_id": self.task_id,
                    "summary": {
                        "summary_text": summary.summary_text,
                        "created_at": summary.created_at.isoformat(),
                        "updated_at": summary.updated_at.isoformat(),
                        "token_usage": summary.token_usage,
                        "last_activity_processed": summary.last_activity_processed.id
                        if summary.last_activity_processed
                        else None,
                    },
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to generate summary for task {self.task_id}: {str(e)}",
                exc_info=True,
            )
            await self.send_error("Failed to generate summary", "summary_error")

    @database_sync_to_async
    def generate_summary(self):
        """Generate task summary."""
        if self.task_id is None:
            raise ValueError("Task ID is required for summary generation")
        return self.summary_service.create_or_update_summary(self.task_id)


class TaskParseConsumer(ProgressTrackingMixin, BaseWebSocketConsumer):
    """WebSocket consumer for parsing text into task data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser_service = TaskParserService()

    def requires_authentication(self) -> bool:
        """Text parsing allows anonymous access for now."""
        return False

    async def handle_message(self, data: Dict[str, Any]):
        """Handle text parsing request."""
        action = data.get("action")

        if action == "parse":
            await self.handle_parse_request(data)
        else:
            raise WebSocketError(f"Unknown action: {action}")

    async def handle_parse_request(self, data: Dict[str, Any]):
        """Process text parsing request."""
        text = data.get("text", "").strip()

        if not text:
            raise WebSocketError("Text is required")

        # Define operation steps for progress tracking
        self.set_operation_steps(
            [
                {
                    "name": "analyze_text",
                    "progress": 30,
                    "message": "Analyzing text...",
                },
                {
                    "name": "extract_data",
                    "progress": 70,
                    "message": "Extracting task information...",
                },
            ]
        )

        try:
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            parse_result = await self.parse_text(text)
            await self.complete_operation(
                {
                    "parsed_data": {
                        "title": parse_result.title,
                        "description": parse_result.description,
                        "priority": parse_result.priority,
                        "estimate": parse_result.estimate,
                        "due_date": parse_result.due_date,
                        "task_type": parse_result.task_type,
                        "tags": parse_result.tags,
                        "confidence_score": parse_result.confidence_score,
                        "raw_text": parse_result.raw_text,
                    }
                }
            )

        except ParserError as e:
            await self.send_error(f"Parsing failed: {str(e)}", "parse_error")
        except Exception as e:
            logger.error(f"Failed to parse text: {str(e)}", exc_info=True)
            await self.send_error("Failed to parse text", "internal_error")

    @database_sync_to_async
    def parse_text(self, text: str):
        """Parse text into task data."""
        return self.parser_service.parse_text_to_task_data(text)


class TaskCreateConsumer(ProgressTrackingMixin, BaseWebSocketConsumer):
    """WebSocket consumer for creating tasks from text."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser_service = TaskParserService()
        self.estimation_service = TaskEstimationService()

    def requires_authentication(self) -> bool:
        """Task creation allows anonymous access."""
        return False

    async def handle_message(self, data: Dict[str, Any]):
        """Handle task creation request."""
        action = data.get("action")

        if action == "create":
            await self.handle_create_request(data)
        else:
            raise WebSocketError(f"Unknown action: {action}")

    async def handle_create_request(self, data: Dict[str, Any]):
        """Process task creation request."""
        text = data.get("text", "").strip()

        if not text:
            raise WebSocketError("Text is required")

        # Define operation steps for progress tracking
        self.set_operation_steps(
            [
                {
                    "name": "parse_text",
                    "progress": 20,
                    "message": "Parsing task description...",
                },
                {"name": "create_task", "progress": 50, "message": "Creating task..."},
                {
                    "name": "estimate_task",
                    "progress": 80,
                    "message": "Estimating task complexity...",
                },
            ]
        )

        try:
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            await self.progress_to_next_step()
            # Use first available user as reporter for anonymous access
            reporter_id = self.user.id if self.user else 1
            task, parse_result = await self.create_task_from_text(text, reporter_id)
            await self.complete_operation(
                {
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "priority": task.priority,
                        "status": task.status,
                        "estimate": task.estimate,
                    },
                    "parse_result": {
                        "confidence_score": parse_result.confidence_score,
                        "task_type": parse_result.task_type,
                        "tags": parse_result.tags,
                    },
                }
            )

        except ParserError as e:
            await self.send_error(f"Failed to parse text: {str(e)}", "parse_error")
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}", exc_info=True)
            await self.send_error("Failed to create task", "internal_error")

    @database_sync_to_async
    def create_task_from_text(self, text: str, reporter_id: Optional[int] = None):
        """Create a task from parsed text with automatic estimation."""
        parse_result = self.parser_service.parse_text_to_task_data(text)

        task_data = {
            "title": parse_result.title,
            "description": parse_result.description,
            "priority": parse_result.priority,
            "status": "todo",
        }
        if reporter_id:
            try:
                reporter = User.objects.get(id=reporter_id)
                task_data["reporter"] = reporter  # type: ignore
            except User.DoesNotExist:
                logger.warning(f"Reporter with ID {reporter_id} not found")
        task = Task.objects.create(**task_data)
        if self.estimation_service.can_estimate(task.id):
            try:
                estimation_result = self.estimation_service.estimate_task(task.id)
                task.estimate = estimation_result.estimated_hours
                task.save()
            except Exception as e:
                logger.warning(f"Failed to auto-estimate task {task.id}: {str(e)}")

        return task, parse_result
