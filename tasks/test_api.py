"""
Tests for API functionality.
"""
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Task, TaskActivity


class TaskAPITests(APITestCase):
    """Test Task API endpoints."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        self.task = Task.objects.create(
            title='API Test Task',
            description='Test task for API',
            reporter=self.user1,
            assignee=self.user2,
            status='todo',
            priority='high',
            estimate=5
        )

    def test_get_task_list(self):
        """Test retrieving task list via API."""
        url = reverse('tasks:api-task-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 1)
        
        task_data = response.data['results'][0]
        self.assertEqual(task_data['title'], 'API Test Task')
        self.assertEqual(task_data['status'], 'todo')

    def test_get_task_detail(self):
        """Test retrieving single task via API."""
        url = reverse('tasks:api-task-detail', kwargs={'pk': self.task.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'API Test Task')
        self.assertEqual(response.data['reporter']['username'], 'testuser1')
        self.assertEqual(response.data['assignee']['username'], 'testuser2')
        self.assertIn('activities', response.data)

    def test_create_task_via_api(self):
        """Test creating task via API."""
        url = reverse('tasks:api-task-list-create')
        data = {
            'title': 'New API Task',
            'description': 'Created via API',
            'status': 'todo',
            'priority': 'medium',
            'estimate': 3,
            'assignee_id': self.user1.id
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New API Task')
        self.assertEqual(response.data['priority'], 'medium')
        
        # Check task was created in database
        self.assertTrue(Task.objects.filter(title='New API Task').exists())

    def test_create_task_minimal_data(self):
        """Test creating task with minimal required data."""
        url = reverse('tasks:api-task-list-create')
        data = {
            'title': 'Minimal Task'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Minimal Task')
        self.assertEqual(response.data['status'], 'todo')  # Default status
        self.assertEqual(response.data['priority'], 'medium')  # Default priority

    def test_update_task_via_api(self):
        """Test updating task via API."""
        url = reverse('tasks:api-task-detail', kwargs={'pk': self.task.pk})
        data = {
            'title': 'Updated API Task',
            'status': 'in_progress',
            'priority': 'critical'
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated API Task')
        self.assertEqual(response.data['status'], 'in_progress')
        
        # Check database was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated API Task')
        self.assertEqual(self.task.status, 'in_progress')
        
        # Check activity was created
        activities = self.task.activities.filter(activity_type='field_change')
        self.assertTrue(activities.exists())

    def test_full_update_task_via_api(self):
        """Test full update (PUT) of task via API."""
        url = reverse('tasks:api-task-detail', kwargs={'pk': self.task.pk})
        data = {
            'title': 'Fully Updated Task',
            'description': 'Completely new description',
            'status': 'done',
            'priority': 'low',
            'estimate': 10,
            'assignee_id': self.user1.id,
            'reporter_id': self.user2.id
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Fully Updated Task')
        self.assertEqual(response.data['status'], 'done')
        self.assertEqual(response.data['assignee']['id'], self.user1.id)

    def test_delete_task_via_api(self):
        """Test deleting task via API."""
        task_id = self.task.pk
        url = reverse('tasks:api-task-detail', kwargs={'pk': task_id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check task was deleted
        self.assertFalse(Task.objects.filter(pk=task_id).exists())

    def test_get_task_activities(self):
        """Test retrieving task activities via API."""
        # Update task to create more activities
        self.task.status = 'in_progress'
        self.task.save()
        
        url = reverse('tasks:api-task-activities', kwargs={'task_id': self.task.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)  # created + status change
        
        # Check activity data
        activity = response.data['results'][0]  # Latest first
        self.assertIn('activity_type', activity)
        self.assertIn('description', activity)
        self.assertIn('timestamp', activity)

    def test_get_users_list(self):
        """Test retrieving users list via API."""
        url = reverse('tasks:api-users')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Note: There might be more users from other tests
        self.assertGreaterEqual(len(response.data['results']), 2)
        
        user_data = response.data['results'][0]
        self.assertIn('username', user_data)
        self.assertIn('email', user_data)

    def test_invalid_task_id(self):
        """Test handling of invalid task ID."""
        url = reverse('tasks:api-task-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_task_without_required_fields(self):
        """Test creating task without required fields."""
        url = reverse('tasks:api-task-list-create')
        data = {
            'description': 'Missing title'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_create_task_with_invalid_assignee(self):
        """Test creating task with invalid assignee ID."""
        url = reverse('tasks:api-task-list-create')
        data = {
            'title': 'Task with invalid assignee',
            'assignee_id': 99999
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('assignee_id', response.data)

    def test_create_task_with_invalid_status(self):
        """Test creating task with invalid status."""
        url = reverse('tasks:api-task-list-create')
        data = {
            'title': 'Task with invalid status',
            'status': 'invalid_status'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_api_pagination(self):
        """Test API pagination."""
        # Create multiple tasks
        for i in range(25):
            Task.objects.create(
                title=f'Pagination Test Task {i}',
                reporter=self.user1,
                status='todo',
                priority='low'
            )
        
        url = reverse('tasks:api-task-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('count', response.data)
        
        # Check that we get paginated results
        self.assertLessEqual(len(response.data['results']), 20)  # Default page size

    def test_api_ordering(self):
        """Test API ordering functionality."""
        # Test that ordering parameter is accepted and returns 200
        url = reverse('tasks:api-task-list-create')
        response = self.client.get(url, {'ordering': 'title'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        
        # Test descending order
        response = self.client.get(url, {'ordering': '-title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_task_serialization_completeness(self):
        """Test that task serialization includes all expected fields."""
        url = reverse('tasks:api-task-detail', kwargs={'pk': self.task.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_fields = [
            'id', 'title', 'description', 'status', 'priority', 'estimate',
            'assignee', 'reporter', 'created_at', 'updated_at', 'due_date', 'activities'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data, f"Field '{field}' missing from serialization")

    def test_activity_creation_on_task_changes(self):
        """Test that activities are created when tasks change via API."""
        url = reverse('tasks:api-task-detail', kwargs={'pk': self.task.pk})
        
        # Record initial activity count
        initial_count = self.task.activities.count()
        
        # Update task via API
        data = {
            'status': 'in_progress',
            'assignee_id': self.user1.id,
            'priority': 'critical'
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that activities were created
        self.task.refresh_from_db()
        new_count = self.task.activities.count()
        self.assertGreater(new_count, initial_count)
        
        # Check that activities contain expected changes
        recent_activities = self.task.activities.filter(activity_type='field_change')
        activity_descriptions = [activity.description for activity in recent_activities]
        
        self.assertTrue(any('Status changed' in desc for desc in activity_descriptions))
        self.assertTrue(any('Assignee changed' in desc for desc in activity_descriptions))
        self.assertTrue(any('Priority changed' in desc for desc in activity_descriptions))

    def test_concurrent_task_updates(self):
        """Test handling of concurrent task updates."""
        url = reverse('tasks:api-task-detail', kwargs={'pk': self.task.pk})
        
        # Simulate concurrent updates
        data1 = {'title': 'Updated by User 1'}
        data2 = {'description': 'Updated by User 2'}
        
        response1 = self.client.patch(url, data1)
        response2 = self.client.patch(url, data2)
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verify final state
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated by User 1')
        self.assertEqual(self.task.description, 'Updated by User 2')

    def test_api_error_handling(self):
        """Test API error handling for various scenarios."""
        # Test 404 for non-existent task
        url = reverse('tasks:api-task-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test 400 for invalid data
        url = reverse('tasks:api-task-list-create')
        response = self.client.post(url, {'invalid_field': 'value'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test 405 for wrong method
        url = reverse('tasks:api-task-detail', kwargs={'pk': self.task.pk})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)