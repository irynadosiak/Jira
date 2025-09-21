from typing import cast
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .models import Task, TaskActivity, TaskSummary
from .services import AIConfig, AIServiceError, TaskSummaryService
from .services.summary import (
    MockSummaryProvider,
    OpenAISummaryProvider,
    SummaryConfigurationError,
    SummaryError,
    SummaryProviderFactory,
    SummaryResult,
)


class AIConfigTests(TestCase):
    """Test AIConfig functionality."""

    @override_settings(OPENAI_API_KEY="test-key", USE_MOCK_AI=False)
    def test_ai_config_from_settings(self):
        """Test creating AIConfig from Django settings."""
        config = AIConfig.from_settings()
        self.assertEqual(config.api_key, "test-key")
        self.assertFalse(config.use_mock)

    @override_settings(OPENAI_API_KEY=None, USE_MOCK_AI=True)
    def test_ai_config_mock_mode(self):
        """Test AIConfig defaults to mock mode when no API key."""
        config = AIConfig.from_settings()
        self.assertIsNone(config.api_key)
        self.assertTrue(config.use_mock)


class MockAIProviderTests(TestCase):
    """Test MockAIProvider implementation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.task = Task.objects.create(
            title="Test Task",
            description="Test description",
            reporter=self.user,
            status="todo",
            priority="medium",
        )
        self.config = AIConfig(
            api_key=None,
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7,
            use_mock=True,
        )

    def test_mock_provider_generate_summary(self):
        """Test generating summary with MockSummaryProvider."""
        provider = MockSummaryProvider(self.config)
        activities = list(self.task.activities.all())

        result = provider.generate_task_summary(self.task, activities)

        self.assertIsInstance(result, SummaryResult)
        self.assertIn(self.task.title, result.summary)
        self.assertGreater(result.tokens_used, 0)


class OpenAIProviderTests(TestCase):
    """Test OpenAIProvider implementation."""

    def setUp(self):
        self.config = AIConfig(
            api_key="test-api-key",
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7,
            use_mock=False,
        )

    def test_openai_provider_setup_no_api_key(self):
        """Test OpenAIProvider setup fails without API key."""
        config = AIConfig(
            api_key=None,
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7,
            use_mock=False,
        )

        with self.assertRaises(SummaryError):
            OpenAISummaryProvider(config)

    @patch("tasks.services.summary.openai_provider.OpenAI")
    def test_openai_provider_generate_summary_success(self, mock_openai):
        """Test successful summary generation with OpenAISummaryProvider."""
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated summary text"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 75

        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAISummaryProvider(self.config)

        # Create minimal test data
        user = User.objects.create_user(username="testuser")
        task = Task.objects.create(title="Test Task", reporter=user, status="todo")
        activities = list(task.activities.all())

        result = provider.generate_task_summary(task, activities)

        self.assertIsInstance(result, SummaryResult)
        self.assertEqual(result.summary, "Generated summary text")
        self.assertEqual(result.tokens_used, 75)


class SummaryProviderFactoryTests(TestCase):
    """Test SummaryProviderFactory functionality."""

    @override_settings(OPENAI_API_KEY=None, USE_MOCK_AI=True)
    def test_factory_create_mock_provider(self):
        """Test factory creates MockSummaryProvider from settings."""
        provider = SummaryProviderFactory.create_provider()
        self.assertIsInstance(provider, MockSummaryProvider)

    def test_factory_handles_configuration_error(self):
        """Test factory handles configuration errors."""
        config = AIConfig(
            api_key=None,
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7,
            use_mock=False,  # This should cause an error
        )

        with self.assertRaises(SummaryConfigurationError):
            SummaryProviderFactory.create_provider(config)


class TaskSummaryServiceTests(TestCase):
    """Test TaskSummaryService core functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.task = Task.objects.create(
            title="Test Task",
            description="Test description",
            reporter=self.user,
            status="todo",
            priority="medium",
        )

    def test_create_new_summary(self):
        """Test creating new task summary."""
        service = TaskSummaryService()

        summary = service.create_or_update_summary(self.task.id)

        self.assertIsInstance(summary, TaskSummary)
        self.assertEqual(summary.task, self.task)
        self.assertIsNotNone(summary.summary_text)
        self.assertIn(self.task.title, summary.summary_text)

    def test_update_existing_summary(self):
        """Test updating existing task summary."""
        service = TaskSummaryService()

        # Create initial summary
        initial_summary = service.create_or_update_summary(self.task.id)

        # Add new activity
        TaskActivity.objects.create(
            task=self.task,
            activity_type="comment",
            description="Added a comment",
            user=self.user,
        )

        # Update summary
        updated_summary = service.create_or_update_summary(self.task.id)

        self.assertEqual(updated_summary.id, initial_summary.id)
        self.assertNotEqual(updated_summary.summary_text, initial_summary.summary_text)

    def test_get_and_delete_summary(self):
        """Test getting and deleting summary."""
        service = TaskSummaryService()

        # Initially no summary
        self.assertIsNone(service.get_summary(self.task.id))

        # Create summary
        created_summary = service.create_or_update_summary(self.task.id)

        # Get summary
        retrieved_summary = service.get_summary(self.task.id)
        self.assertIsNotNone(retrieved_summary)
        retrieved_summary = cast(
            TaskSummary, retrieved_summary
        )  # Type narrowing for mypy
        self.assertEqual(retrieved_summary.id, created_summary.id)

        # Delete summary
        result = service.delete_summary(self.task.id)
        self.assertTrue(result)
        self.assertIsNone(service.get_summary(self.task.id))

    def test_service_handles_errors(self):
        """Test service error handling."""
        service = TaskSummaryService()

        # Test non-existent task
        with self.assertRaises(Task.DoesNotExist):
            service.create_or_update_summary(99999)

        # Test AI provider error
        mock_provider = Mock()
        mock_provider.generate_task_summary.side_effect = AIServiceError("Test error")
        service_with_error = TaskSummaryService(summary_provider=mock_provider)

        with self.assertRaises(AIServiceError):
            service_with_error.create_or_update_summary(self.task.id)
