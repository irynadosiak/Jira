# Simple Task Manager

A clean Django-based task management system with web interface and REST API.

## Quick Start

```bash
# Install and setup
make install
make migrate

# Run server
make runserver
```

Visit http://127.0.0.1:8000/tasks/

## Features

- ✅ **Web Interface** - Create, edit, view, and manage tasks
- 📊 **Dashboard** - Task statistics and overview  
- 🔍 **Search & Filter** - Filter by status, assignee, search text
- 📝 **Activity Log** - Automatic tracking of task changes
- 🚀 **REST API** - Full CRUD operations via API

## API Endpoints

- `GET /tasks/api/` - List tasks (with filtering)
- `POST /tasks/api/` - Create task
- `GET /tasks/api/{id}/` - Get task details
- `PUT/PATCH /tasks/api/{id}/` - Update task
- `DELETE /tasks/api/{id}/` - Delete task
- `GET /tasks/api/{id}/activities/` - Get task activities
- `GET /tasks/api/users/` - List users

### Filtering
Add query parameters: `?status=todo&assignee=1&search=bug`

## Development

```bash
make test      # Run tests
```

## Project Structure

```
tasks/
├── models.py      # Task and TaskActivity models
├── views.py       # Web interface views  
├── api.py         # REST API views and serializers
├── urls.py        # URL routing
├── admin.py       # Django admin
└── tests.py       # Simple tests
```