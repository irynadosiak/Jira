import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from django.contrib.auth.models import AnonymousUser

from ..models import Task

logger = logging.getLogger(__name__)


class WebSocketError(Exception):
    """Custom exception for WebSocket errors."""

    pass


class WebSocketPermissionError(WebSocketError):
    """Exception for permission-related WebSocket errors."""

    pass


class BaseWebSocketConsumer(AsyncWebsocketConsumer, ABC):
    """Base WebSocket consumer with common functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.authenticated = False

    async def connect(self):
        """Accept WebSocket connection and authenticate user."""
        # Get user from scope (set by AuthMiddleware)
        self.user = self.scope.get("user")
        self.authenticated = self.user and not isinstance(self.user, AnonymousUser)

        # Check if authentication is required
        if self.requires_authentication() and not self.authenticated:
            logger.warning(
                f"Unauthenticated WebSocket connection attempt to {self.__class__.__name__}"
            )
            await self.close(code=4001)  # Custom close code for authentication required
            return

        await self.accept()
        await self.send_message(
            {
                "type": "connection",
                "status": "connected",
                "message": "WebSocket connected successfully",
            }
        )

        logger.info(
            f"WebSocket connected: {self.__class__.__name__} for user {self.user}"
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(
            f"WebSocket disconnected: {self.__class__.__name__} with code {close_code}"
        )

    async def receive(self, text_data):
        """Receive and process message from WebSocket."""
        try:
            data = json.loads(text_data)

            # Validate message structure
            if not isinstance(data, dict):
                raise WebSocketError("Message must be a JSON object")

            action = data.get("action")
            if not action:
                raise WebSocketError("Message must include 'action' field")

            # Check permissions before processing
            await self.check_permissions(data)

            # Handle the message
            await self.handle_message(data)

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except WebSocketPermissionError as e:
            await self.send_error(f"Permission denied: {str(e)}")
        except WebSocketError as e:
            await self.send_error(str(e))
        except Exception as e:
            logger.error(
                f"Unexpected error in {self.__class__.__name__}: {str(e)}",
                exc_info=True,
            )
            await self.send_error("Internal server error")

    @abstractmethod
    async def handle_message(self, data: Dict[str, Any]):
        """Override in subclasses to handle specific message types."""
        pass

    async def check_permissions(self, data: Dict[str, Any]):
        """Override in subclasses to implement permission checks."""
        pass

    def requires_authentication(self) -> bool:
        """Override in subclasses to require authentication."""
        return True

    # Messaging methods
    async def send_message(self, data: Dict[str, Any]):
        """Send a structured message to the client."""
        await self.send(text_data=json.dumps(data))

    async def send_error(self, message: str, code: Optional[str] = None):
        """Send error message to client."""
        error_data = {"type": "error", "message": message}
        if code:
            error_data["code"] = code
        await self.send_message(error_data)

    async def send_success(self, data: Dict[str, Any]):
        """Send success response to client."""
        await self.send_message({"type": "success", **data})

    async def send_progress(
        self, message: str, progress: Optional[int] = None, step: Optional[str] = None
    ):
        """Send progress update to client."""
        progress_data: Dict[str, Any] = {"type": "progress", "message": message}
        if progress is not None:
            progress_data["progress"] = progress
        if step:
            progress_data["step"] = step
        await self.send_message(progress_data)


class TaskWebSocketMixin:
    """Mixin for WebSocket consumers that work with tasks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = None
        self.task = None

    async def connect(self):
        """Extract task ID from URL and validate task access."""
        # Extract task_id from URL if present
        url_kwargs = self.scope.get("url_route", {}).get("kwargs", {})  # type: ignore
        self.task_id = url_kwargs.get("task_id")

        if self.task_id:
            self.task_id = int(self.task_id)

        await super().connect()  # type: ignore

    async def check_permissions(self, data: Dict[str, Any]):
        """Check if user has permission to access the task."""
        await super().check_permissions(data)  # type: ignore

        if self.task_id:
            # Load task if not already loaded
            if not self.task:
                self.task = await self.get_task(self.task_id)

            if not self.task:
                raise WebSocketPermissionError(f"Task {self.task_id} not found")

            # Check if user can view this task
            if not await self.can_access_task(self.task):
                raise WebSocketPermissionError(
                    "You don't have permission to access this task"
                )

    @database_sync_to_async
    def get_task(self, task_id: int) -> Optional[Task]:
        """Get task from database."""
        try:
            return Task.objects.select_related("assignee", "reporter").get(id=task_id)
        except Task.DoesNotExist:
            return None

    async def can_access_task(self, task: Task) -> bool:
        """Check if user can access the given task."""
        # Allow anonymous access to all tasks
        return True

    @database_sync_to_async
    def refresh_task(self):
        """Refresh task from database."""
        if self.task:
            self.task.refresh_from_db()
        return self.task


class ProgressTrackingMixin:
    """
    Mixin for tracking multi-step operations with progress updates.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.operation_steps = []
        self.current_step = 0

    def set_operation_steps(self, steps: list):
        """Set the steps for the current operation."""
        self.operation_steps = steps
        self.current_step = 0

    async def progress_to_next_step(self, message: Optional[str] = None):
        """Advance to the next step and send progress update."""
        if self.current_step < len(self.operation_steps):
            step_info = self.operation_steps[self.current_step]
            step_name = step_info["name"]
            step_progress = step_info["progress"]

            display_message = message or step_info.get("message", step_name)

            await self.send_progress(  # type: ignore
                message=display_message, progress=step_progress, step=step_name
            )

            self.current_step += 1

    async def complete_operation(self, success_data: Dict[str, Any]):
        """Mark operation as complete and send final response."""
        await self.send_progress("Operation completed!", 100, "complete")  # type: ignore
        await self.send_success(success_data)  # type: ignore
