"""
Simple web interface views for task management.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from .models import Task, TaskActivity


def task_list(request):
    """List all tasks with comprehensive filtering and search."""
    tasks = Task.objects.select_related('assignee', 'reporter').all()
    
    # Comprehensive filtering
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    priority_filter = request.GET.get('priority')
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    
    assignee_filter = request.GET.get('assignee')
    if assignee_filter:
        if assignee_filter == 'unassigned':
            tasks = tasks.filter(assignee__isnull=True)
        else:
            tasks = tasks.filter(assignee_id=assignee_filter)
    
    reporter_filter = request.GET.get('reporter')
    if reporter_filter:
        tasks = tasks.filter(reporter_id=reporter_filter)
    
    search = request.GET.get('search')
    if search:
        tasks = tasks.filter(
            models.Q(title__icontains=search) | 
            models.Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(tasks, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    users = User.objects.all().order_by('first_name', 'last_name', 'username')
    
    context = {
        'page_obj': page_obj,
        'tasks': page_obj,
        'users': users,
        'status_choices': Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES,
        'current_status': status_filter,
        'current_priority': priority_filter,
        'current_assignee': assignee_filter,
        'current_reporter': reporter_filter,
        'current_search': search,
    }
    return render(request, 'tasks/task_list.html', context)


def task_detail(request, pk):
    """Show task details with activities."""
    task = get_object_or_404(Task.objects.prefetch_related('activities'), pk=pk)
    return render(request, 'tasks/task_detail.html', {'task': task})


def task_create(request):
    """Create a new task."""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        priority = request.POST.get('priority', 'medium')
        estimate = request.POST.get('estimate')
        assignee_id = request.POST.get('assignee')
        due_date = request.POST.get('due_date')
        
        if not title:
            messages.error(request, 'Title is required.')
            return redirect('tasks:task-create')
        
        # Get or create default user
        reporter = User.objects.first()
        if not reporter:
            reporter = User.objects.create_user(username='system')
        
        assignee = None
        if assignee_id:
            assignee = User.objects.filter(id=assignee_id).first()
        
        # Handle estimate
        estimate_value = None
        if estimate:
            try:
                estimate_value = int(estimate)
            except ValueError:
                pass
        
        Task.objects.create(
            title=title,
            description=description,
            priority=priority,
            estimate=estimate_value,
            assignee=assignee,
            reporter=reporter,
            due_date=due_date if due_date else None
        )
        messages.success(request, f"Task '{title}' was created successfully!")
        return redirect('tasks:task-list')
    
    users = User.objects.all()
    context = {
        'users': users,
        'priority_choices': Task.PRIORITY_CHOICES,
    }
    return render(request, 'tasks/task_form.html', context)


def task_update(request, pk):
    """Update an existing task."""
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.status = request.POST.get('status', task.status)
        task.priority = request.POST.get('priority', task.priority)
        
        estimate = request.POST.get('estimate')
        if estimate:
            try:
                task.estimate = int(estimate)
            except ValueError:
                pass
        
        assignee_id = request.POST.get('assignee')
        if assignee_id:
            task.assignee = User.objects.filter(id=assignee_id).first()
        else:
            task.assignee = None
        
        due_date = request.POST.get('due_date')
        task.due_date = due_date if due_date else None
        
        task.save()
        messages.success(request, f"Task '{task.title}' was updated successfully!")
        return redirect('tasks:task-detail', pk=task.pk)
    
    users = User.objects.all()
    context = {
        'task': task,
        'users': users,
        'status_choices': Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES,
    }
    return render(request, 'tasks/task_form.html', context)


def task_delete(request, pk):
    """Delete a task."""
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        title = task.title
        task.delete()
        messages.success(request, f"Task '{title}' was deleted.")
        return redirect('tasks:task-list')
    
    return render(request, 'tasks/task_confirm_delete.html', {'task': task})


def task_quick_update(request, pk):
    """Quick status update for tasks."""
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=pk)
        new_status = request.POST.get('status')
        if new_status in [choice[0] for choice in Task.STATUS_CHOICES]:
            task.status = new_status
            task.save()
            messages.success(request, f"Task status updated to {task.get_status_display()}!")
    return redirect('tasks:task-detail', pk=pk)


def dashboard(request):
    """Simple dashboard with essential statistics and 2 key charts."""
    from datetime import datetime, timedelta
    import json
    
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='done').count()
    unassigned_count = Task.objects.filter(assignee__isnull=True).count()
    completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
    
    # Status distribution for chart
    status_data = []
    for status_key, status_display in Task.STATUS_CHOICES:
        count = Task.objects.filter(status=status_key).count()
        if count > 0:  # Only include statuses that have tasks
            status_data.append({
                'label': status_display,
                'value': count,
                'color': {
                    'todo': '#9aa0a6',
                    'in_progress': '#fbbc04',
                    'in_review': '#4285f4',
                    'done': '#34a853',
                    'blocked': '#ea4335'
                }.get(status_key, '#9aa0a6')
            })
    
    # Task completion trend (last 7 days)
    completion_trend = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).date()
        completed_count = Task.objects.filter(
            status='done',
            updated_at__date=date
        ).count()
        completion_trend.append({
            'date': date.strftime('%m/%d'),
            'completed': completed_count
        })
    
    # Simple completion time calculation
    completed_tasks_with_due_date = Task.objects.filter(status='done', due_date__isnull=False)
    completion_times = []
    for task in completed_tasks_with_due_date:
        days_to_complete = (task.updated_at.date() - task.created_at.date()).days
        completion_times.append(days_to_complete)
    
    avg_completion_time = round(sum(completion_times) / len(completion_times)) if completion_times else 0
    
    # Recent tasks
    recent_tasks = Task.objects.select_related('assignee', 'reporter').order_by('-updated_at')[:6]
    
    context = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'unassigned_count': unassigned_count,
        'completion_rate': completion_rate,
        'avg_completion_time': avg_completion_time,
        'recent_tasks': recent_tasks,
        # Chart data as JSON
        'status_data_json': json.dumps(status_data),
        'completion_trend_json': json.dumps(completion_trend),
    }
    return render(request, 'tasks/dashboard.html', context)