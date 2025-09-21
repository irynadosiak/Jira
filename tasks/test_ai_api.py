from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth.models import User
from django.urls import reverse

from .models import Task, TaskSummary
from .services import AIServiceError


class TaskSummaryAPITests(APITestCase):
    """Test essential AI summary API functionality."""

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

    def test_get_existing_summary(self):
        """Test GET request for existing task summary."""
        url = reverse("tasks:api-task-summary", kwargs={"pk": self.task.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Check that response contains the summary data directly
        self.assertEqual(data["summary_text"], "Test summary text")
        self.assertEqual(data["token_usage"], 100)

    def test_get_nonexistent_summary(self):
        """Test GET request for non-existent task summary."""
        url = reverse("tasks:api-task-summary", kwargs={"pk": self.task.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generate_new_summary(self):
        """Test POST request to generate new task summary."""
        url = reverse("tasks:api-task-generate-summary", kwargs={"pk": self.task.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("generated successfully", data["message"])

        # Verify summary was created
        summary = TaskSummary.objects.get(task=self.task)
        self.assertIn(self.task.title, summary.summary_text)

    def test_delete_existing_summary(self):
        """Test DELETE request for existing task summary."""
        TaskSummary.objects.create(
            task=self.task, summary_text="Test summary text", token_usage=100
        )

        url = reverse("tasks:api-task-summary", kwargs={"pk": self.task.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(TaskSummary.objects.filter(task=self.task).exists())

    @patch("tasks.services.TaskSummaryService.create_or_update_summary")
    def test_generate_summary_handles_ai_error(self, mock_create_summary):
        """Test POST request handles AI service errors."""
        mock_create_summary.side_effect = AIServiceError("AI API error")

        url = reverse("tasks:api-task-generate-summary", kwargs={"pk": self.task.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertIn("AI API error", data["error"])
