"""
Simple but complete API for task management.
"""
from rest_framework import generics, serializers, filters
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from django.contrib.auth.models import User
from .models import Task, TaskActivity


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class TaskActivitySerializer(serializers.ModelSerializer):
    """Simple activity serializer."""
    class Meta:
        model = TaskActivity
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    """Task serializer with related data."""
    assignee = UserSerializer(read_only=True)
    reporter = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assignee', write_only=True, required=False, allow_null=True
    )
    reporter_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='reporter', write_only=True, required=False
    )
    activities = TaskActivitySerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        """Create task with default reporter if needed."""
        if 'reporter' not in validated_data:
            default_user = User.objects.first()
            if not default_user:
                default_user = User.objects.create_user(
                    username='system',
                    first_name='System',
                    last_name='User',
                    email='system@example.com'
                )
            validated_data['reporter'] = default_user
        return super().create(validated_data)


class TaskFilter(django_filters.FilterSet):
    """Comprehensive filtering for tasks."""
    assignee = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        empty_label="All Assignees"
    )
    reporter = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        empty_label="All Reporters"
    )
    unassigned = django_filters.BooleanFilter(
        field_name='assignee',
        lookup_expr='isnull',
        label='Unassigned tasks'
    )
    
    class Meta:
        model = Task
        fields = {
            'status': ['exact'],
            'priority': ['exact'],
            'assignee': ['exact'],
            'reporter': ['exact'],
            'estimate': ['exact', 'gte', 'lte'],
            'created_at': ['date', 'date__gte', 'date__lte'],
            'due_date': ['date', 'date__gte', 'date__lte', 'isnull'],
        }


class TaskListCreateView(generics.ListCreateAPIView):
    """List and create tasks with filtering and search."""
    queryset = Task.objects.select_related('reporter', 'assignee').all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status', 'due_date']
    ordering = ['-created_at']


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, delete tasks."""
    queryset = Task.objects.select_related('reporter', 'assignee').prefetch_related('activities')
    serializer_class = TaskSerializer


class TaskActivityListView(generics.ListAPIView):
    """List activities for a specific task."""
    serializer_class = TaskActivitySerializer

    def get_queryset(self):
        task_id = self.kwargs['task_id']
        return TaskActivity.objects.filter(task_id=task_id)


class UserListView(generics.ListAPIView):
    """List users for assignment."""
    queryset = User.objects.all()
    serializer_class = UserSerializer