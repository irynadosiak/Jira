"""
Main tests for task management functionality.
"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Task


class TaskModelTests(TestCase):
    """Test Task model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assignee = User.objects.create_user(
            username='assignee',
            email='assignee@example.com', 
            password='testpass123'
        )

    def test_task_creation(self):
        """Test basic task creation."""
        task = Task.objects.create(
            title='Test Task',
            description='Test description',
            reporter=self.user,
            status='todo',
            priority='medium'
        )
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.status, 'todo')
        self.assertEqual(task.priority, 'medium')
        self.assertEqual(task.reporter, self.user)
        
        # Check activity was created
        self.assertEqual(task.activities.count(), 1)
        activity = task.activities.first()
        self.assertEqual(activity.activity_type, 'created')

    def test_task_status_change_creates_activity(self):
        """Test that changing status creates activity log."""
        task = Task.objects.create(
            title='Test Task',
            reporter=self.user,
            status='todo'
        )
        initial_activities = task.activities.count()
        
        task.status = 'in_progress'
        task.save()
        
        self.assertEqual(task.activities.count(), initial_activities + 1)
        latest_activity = task.activities.first()  # Latest first due to ordering
        self.assertEqual(latest_activity.activity_type, 'field_change')
        self.assertIn('Status changed', latest_activity.description)

    def test_task_string_representation(self):
        """Test task string representation."""
        task = Task.objects.create(
            title='Test Task',
            reporter=self.user,
            status='todo'
        )
        self.assertEqual(str(task), '[To Do] Test Task')


class TaskWebInterfaceTests(TestCase):
    """Test web interface functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='webuser',
            email='web@example.com',
            password='testpass123'
        )

    def test_home_page(self):
        """Test home page loads correctly."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Simple Task Manager')

    def test_task_list_page(self):
        """Test task list page loads correctly."""
        response = self.client.get(reverse('tasks:task-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tasks')

    def test_dashboard_page(self):
        """Test dashboard page loads correctly."""
        response = self.client.get(reverse('tasks:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_create_task_page(self):
        """Test create task page loads correctly."""
        response = self.client.get(reverse('tasks:task-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Task')

    def test_create_task_submission(self):
        """Test task creation through web form."""
        response = self.client.post(reverse('tasks:task-create'), {
            'title': 'Web Form Task',
            'description': 'Created through web form',
            'priority': 'high'
        })
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check task was created
        self.assertTrue(Task.objects.filter(title='Web Form Task').exists())


# Import tests from separate files
from .test_filters import TaskFilteringTests, APIFilteringTests  # noqa: E402
from .test_api import TaskAPITests  # noqa: E402