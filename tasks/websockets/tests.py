from unittest.mock import patch

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from django.contrib.auth.models import User
from django.test import TestCase

from ..models import Task
from .ai_consumers import (
    TaskCreateConsumer,
    TaskEstimationConsumer,
    TaskParseConsumer,
    TaskSummaryConsumer,
)


class WebSocketTestCase(TestCase):
    """Base test case for WebSocket consumers."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.task = Task.objects.create(
            title="Test Task",
            description="Test task description",
            priority="medium",
            status="todo",
            reporter=self.user,
        )

    async def connect_websocket(self, consumer_class, path_kwargs=None):
        """Helper to connect to a WebSocket consumer."""
        communicator = WebsocketCommunicator(consumer_class.as_asgi(), "/ws/test/")

        # Add user to scope for authentication
        communicator.scope["user"] = self.user
        if path_kwargs:
            communicator.scope["url_route"] = {"kwargs": path_kwargs}

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Read connection message
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "connection")
        self.assertEqual(response["status"], "connected")

        return communicator


class TaskEstimationConsumerTest(WebSocketTestCase):
    """Tests for TaskEstimationConsumer."""

    async def test_estimation_success(self):
        """Test successful task estimation."""
        communicator = await self.connect_websocket(
            TaskEstimationConsumer, {"task_id": str(self.task.id)}
        )

        # Mock the estimation service
        with patch(
            "tasks.websockets.ai_consumers.TaskEstimationService"
        ) as mock_service:
            mock_service.return_value.can_estimate.return_value = True

            # Mock estimation result
            class MockResult:
                estimated_hours = 8.0
                confidence_score = 0.85
                reasoning = "Test reasoning"
                similar_tasks = []
                metadata = {}

            mock_service.return_value.estimate_task.return_value = MockResult()

            # Send estimation request
            await communicator.send_json_to({"action": "estimate"})

            # Read progress messages
            messages = []
            for _ in range(6):  # 4 progress + 1 complete + 1 success
                message = await communicator.receive_json_from()
                messages.append(message)

            # Check final success message
            success_message = messages[-1]
            self.assertEqual(success_message["type"], "success")
            self.assertEqual(success_message["task_id"], self.task.id)
            self.assertEqual(success_message["estimation"]["estimated_hours"], 8.0)

        await communicator.disconnect()

    async def test_estimation_task_not_found(self):
        """Test estimation with non-existent task."""
        communicator = await self.connect_websocket(
            TaskEstimationConsumer, {"task_id": "99999"}
        )

        await communicator.send_json_to({"action": "estimate"})

        # Should receive error about task not found
        progress_message = await communicator.receive_json_from()
        self.assertEqual(progress_message["type"], "progress")

        error_message = await communicator.receive_json_from()
        self.assertEqual(error_message["type"], "error")
        self.assertIn("not found", error_message["message"])

        await communicator.disconnect()


class TaskSummaryConsumerTest(WebSocketTestCase):
    """Tests for TaskSummaryConsumer."""

    async def test_summary_generation_success(self):
        """Test successful summary generation."""
        communicator = await self.connect_websocket(
            TaskSummaryConsumer, {"task_id": str(self.task.id)}
        )

        # Mock the summary service
        with patch("tasks.websockets.ai_consumers.TaskSummaryService") as mock_service:
            # Mock summary result
            class MockSummary:
                summary_text = "Test summary"
                created_at = "2023-01-01T00:00:00Z"
                updated_at = "2023-01-01T00:00:00Z"
                token_usage = 100
                last_activity_processed = None

            mock_service.return_value.create_or_update_summary.return_value = (
                MockSummary()
            )

            # Send summary request
            await communicator.send_json_to({"action": "generate_summary"})

            # Read all messages until success
            messages = []
            for _ in range(6):  # 4 progress + 1 complete + 1 success
                message = await communicator.receive_json_from()
                messages.append(message)

            # Check final success message
            success_message = messages[-1]
            self.assertEqual(success_message["type"], "success")
            self.assertEqual(success_message["task_id"], self.task.id)
            self.assertEqual(success_message["summary"]["summary_text"], "Test summary")

        await communicator.disconnect()


class TaskParseConsumerTest(WebSocketTestCase):
    """Tests for TaskParseConsumer."""

    async def test_text_parsing_success(self):
        """Test successful text parsing."""
        communicator = await self.connect_websocket(TaskParseConsumer)

        # Mock the parser service
        with patch("tasks.websockets.ai_consumers.TaskParserService") as mock_service:
            # Mock parse result
            class MockParseResult:
                title = "Parsed Title"
                description = "Parsed description"
                priority = "high"
                estimate = 5.0
                due_date = None
                task_type = "feature"
                tags = ["urgent"]
                confidence_score = 0.9
                raw_text = "Create urgent feature for user login"

            mock_service.return_value.parse_text_to_task_data.return_value = (
                MockParseResult()
            )

            # Send parse request
            await communicator.send_json_to(
                {"action": "parse", "text": "Create urgent feature for user login"}
            )

            # Read all messages until success
            messages = []
            for _ in range(4):  # 2 progress + 1 complete + 1 success
                message = await communicator.receive_json_from()
                messages.append(message)

            # Check final success message
            success_message = messages[-1]
            self.assertEqual(success_message["type"], "success")
            self.assertEqual(success_message["parsed_data"]["title"], "Parsed Title")
            self.assertEqual(success_message["parsed_data"]["priority"], "high")

        await communicator.disconnect()

    async def test_parsing_empty_text(self):
        """Test parsing with empty text."""
        communicator = await self.connect_websocket(TaskParseConsumer)

        await communicator.send_json_to({"action": "parse", "text": ""})

        # Should receive error about empty text
        error_message = await communicator.receive_json_from()
        self.assertEqual(error_message["type"], "error")
        self.assertIn("required", error_message["message"])

        await communicator.disconnect()


class TaskCreateConsumerTest(WebSocketTestCase):
    """Tests for TaskCreateConsumer."""

    async def test_task_creation_success(self):
        """Test successful task creation."""
        communicator = await self.connect_websocket(TaskCreateConsumer)

        # Mock the services
        with patch(
            "tasks.websockets.ai_consumers.TaskParserService"
        ) as mock_parser, patch(
            "tasks.websockets.ai_consumers.TaskEstimationService"
        ) as mock_estimator:
            # Mock parse result
            class MockParseResult:
                title = "New Task"
                description = "New task description"
                priority = "medium"
                estimate = None
                due_date = None
                task_type = "task"
                tags = []
                confidence_score = 0.8
                raw_text = "Create new task for testing"

            mock_parser.return_value.parse_text_to_task_data.return_value = (
                MockParseResult()
            )
            mock_estimator.return_value.can_estimate.return_value = False

            # Send create request
            await communicator.send_json_to(
                {
                    "action": "create",
                    "text": "Create new task for testing",
                    "reporter_id": self.user.id,
                }
            )

            # Read all messages until success
            messages = []
            for _ in range(5):  # 3 progress + 1 complete + 1 success
                message = await communicator.receive_json_from()
                messages.append(message)

            # Check final success message
            success_message = messages[-1]
            self.assertEqual(success_message["type"], "success")
            self.assertEqual(success_message["task"]["title"], "New Task")

            # Verify task was created in database
            task_exists = await database_sync_to_async(
                Task.objects.filter(title="New Task").exists
            )()
            self.assertTrue(task_exists)

        await communicator.disconnect()


class WebSocketErrorHandlingTest(WebSocketTestCase):
    """Tests for WebSocket error handling."""

    async def test_invalid_json(self):
        """Test handling of invalid JSON."""
        communicator = await self.connect_websocket(TaskParseConsumer)

        # Send invalid JSON
        await communicator.send_to(text_data="invalid json")

        # Should receive error message
        error_message = await communicator.receive_json_from()
        self.assertEqual(error_message["type"], "error")
        self.assertIn("Invalid JSON", error_message["message"])

        await communicator.disconnect()

    async def test_missing_action(self):
        """Test handling of message without action."""
        communicator = await self.connect_websocket(TaskParseConsumer)

        await communicator.send_json_to({"text": "some text"})

        # Should receive error about missing action
        error_message = await communicator.receive_json_from()
        self.assertEqual(error_message["type"], "error")
        self.assertIn("action", error_message["message"])

        await communicator.disconnect()

    async def test_unknown_action(self):
        """Test handling of unknown action."""
        communicator = await self.connect_websocket(TaskParseConsumer)

        await communicator.send_json_to({"action": "unknown_action"})

        # Should receive error about unknown action
        error_message = await communicator.receive_json_from()
        self.assertEqual(error_message["type"], "error")
        self.assertIn("Unknown action", error_message["message"])

        await communicator.disconnect()
