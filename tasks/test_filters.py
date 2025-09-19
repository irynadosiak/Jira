"""
Tests for filtering functionality.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Task


class TaskFilteringTests(TestCase):
    """Test task filtering functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2', 
            email='user2@example.com',
            password='testpass123'
        )
        
        # Create test tasks with various attributes
        self.task1 = Task.objects.create(
            title='Todo Task',
            description='This is a todo task with bug keyword',
            reporter=self.user1,
            assignee=self.user1,
            status='todo',
            priority='high',
            estimate=5
        )
        self.task2 = Task.objects.create(
            title='In Progress Task',
            description='This is in progress',
            reporter=self.user1,
            assignee=self.user2,
            status='in_progress',
            priority='medium',
            estimate=3
        )
        self.task3 = Task.objects.create(
            title='Done Task',
            description='This is completed',
            reporter=self.user2,
            assignee=self.user1,
            status='done',
            priority='low',
            estimate=8
        )
        self.task4 = Task.objects.create(
            title='Blocked Task',
            description='This task is blocked',
            reporter=self.user2,
            assignee=None,  # Unassigned
            status='blocked',
            priority='critical'
        )

    def test_filter_by_status(self):
        """Test filtering tasks by status."""
        response = self.client.get(reverse('tasks:task-list'), {'status': 'todo'})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].status, 'todo')

    def test_filter_by_priority(self):
        """Test filtering tasks by priority."""
        response = self.client.get(reverse('tasks:task-list'), {'priority': 'high'})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].priority, 'high')

    def test_filter_by_assignee(self):
        """Test filtering tasks by assignee."""
        response = self.client.get(reverse('tasks:task-list'), {'assignee': self.user1.id})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 2)  # task1 and task3
        for task in tasks:
            self.assertEqual(task.assignee, self.user1)

    def test_filter_by_reporter(self):
        """Test filtering tasks by reporter."""
        response = self.client.get(reverse('tasks:task-list'), {'reporter': self.user2.id})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 2)  # task3 and task4
        for task in tasks:
            self.assertEqual(task.reporter, self.user2)

    def test_filter_unassigned_tasks(self):
        """Test filtering unassigned tasks."""
        response = self.client.get(reverse('tasks:task-list'), {'assignee': 'unassigned'})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertIsNone(tasks[0].assignee)

    def test_search_in_title(self):
        """Test search functionality in title."""
        response = self.client.get(reverse('tasks:task-list'), {'search': 'Progress'})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, 'In Progress Task')

    def test_search_in_description(self):
        """Test search functionality in description."""
        response = self.client.get(reverse('tasks:task-list'), {'search': 'bug'})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertIn('bug', tasks[0].description.lower())

    def test_combined_filters(self):
        """Test combining multiple filters."""
        response = self.client.get(reverse('tasks:task-list'), {
            'status': 'done',
            'assignee': self.user1.id,
            'priority': 'low'
        })
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].status, 'done')
        self.assertEqual(tasks[0].assignee, self.user1)
        self.assertEqual(tasks[0].priority, 'low')

    def test_filter_with_search(self):
        """Test combining filters with search."""
        response = self.client.get(reverse('tasks:task-list'), {
            'status': 'todo',
            'search': 'todo'
        })
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].status, 'todo')

    def test_no_results_filter(self):
        """Test filter that returns no results."""
        response = self.client.get(reverse('tasks:task-list'), {
            'status': 'done',
            'assignee': self.user2.id  # user2 is not assigned to any done tasks
        })
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 0)

    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        response = self.client.get(reverse('tasks:task-list'), {'search': 'PROGRESS'})
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertIn('progress', tasks[0].title.lower())

    def test_pagination_with_filters(self):
        """Test that pagination works with filters."""
        # Create more tasks to test pagination
        for i in range(15):
            Task.objects.create(
                title=f'Extra Task {i}',
                reporter=self.user1,
                status='todo',
                priority='low'
            )
        
        response = self.client.get(reverse('tasks:task-list'), {'status': 'todo'})
        self.assertEqual(response.status_code, 200)
        
        # Check pagination
        page_obj = response.context['page_obj']
        self.assertTrue(page_obj.has_next())
        self.assertEqual(len(page_obj), 12)  # 12 items per page

    def test_empty_filter_values(self):
        """Test that empty filter values are ignored."""
        response = self.client.get(reverse('tasks:task-list'), {
            'status': '',
            'priority': '',
            'assignee': '',
            'search': ''
        })
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 4)  # All tasks should be returned

    def test_invalid_filter_values(self):
        """Test handling of invalid filter values."""
        response = self.client.get(reverse('tasks:task-list'), {
            'assignee': '99999',  # Non-existent user ID
            'status': 'invalid_status'
        })
        self.assertEqual(response.status_code, 200)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 0)  # No tasks should match invalid filters


class APIFilteringTests(TestCase):
    """Test API filtering functionality."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='apiuser1',
            email='api1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='apiuser2',
            email='api2@example.com',
            password='testpass123'
        )
        
        self.task1 = Task.objects.create(
            title='API Task 1',
            reporter=self.user1,
            assignee=self.user1,
            status='todo',
            priority='high',
            estimate=5
        )
        self.task2 = Task.objects.create(
            title='API Task 2',
            reporter=self.user2,
            assignee=self.user2,
            status='in_progress',
            priority='medium',
            estimate=3
        )

    def test_api_filter_by_status(self):
        """Test API filtering by status."""
        response = self.client.get(reverse('tasks:api-task-list-create'), {'status': 'todo'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['status'], 'todo')

    def test_api_filter_by_assignee(self):
        """Test API filtering by assignee."""
        response = self.client.get(reverse('tasks:api-task-list-create'), {'assignee': self.user1.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['assignee']['id'], self.user1.id)

    def test_api_search(self):
        """Test API search functionality."""
        response = self.client.get(reverse('tasks:api-task-list-create'), {'search': 'API Task 1'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['title'], 'API Task 1')

    def test_api_ordering(self):
        """Test API ordering functionality."""
        # Test that ordering parameter is accepted
        response = self.client.get(reverse('tasks:api-task-list-create'), {'ordering': 'title'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)

    def test_api_multiple_filters(self):
        """Test API with multiple filters."""
        response = self.client.get(reverse('tasks:api-task-list-create'), {
            'status': 'todo',
            'priority': 'high',
            'assignee': self.user1.id
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        result = data['results'][0]
        self.assertEqual(result['status'], 'todo')
        self.assertEqual(result['priority'], 'high')
        self.assertEqual(result['assignee']['id'], self.user1.id)