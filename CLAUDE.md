# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

```bash
# Install dependencies
make install

# Set up/update database
make migrate

# Run development server
make runserver

# Run all tests
make test

# Run specific test file
python3 manage.py test tasks.test_api
python3 manage.py test tasks.test_filters
python3 manage.py test tasks.tests

# Django shell for debugging
python3 manage.py shell

# Create Django superuser
python3 manage.py createsuperuser

# Database migrations
python3 manage.py makemigrations tasks
python3 manage.py migrate

# Run specific test class or method
python3 manage.py test tasks.tests.TaskModelTest
python3 manage.py test tasks.test_api.TaskAPITest.test_create_task
```

## High-Level Architecture

### Core Components

1. **Django Project Structure**
   - Main project configuration in `Jira/` directory (settings.py, urls.py)
   - Single app `tasks/` contains all business logic
   - Database: SQLite3 (db.sqlite3)
   - Django 5.2.6 with Django REST Framework 3.14.0

2. **Data Layer (tasks/models.py)**
   - `Task` model: Core entity with fields for title, description, status (todo/in-progress/in-review/done/blocked), priority (low/medium/high/critical), assignee/reporter (ForeignKey to User)
   - `TaskActivity` model: Automatically logs all changes to tasks via overridden save() method
   - Activity logging tracks field changes by comparing old and new values

3. **API Layer (tasks/api.py)**
   - All API components consolidated in single file (ViewSets, Serializers, Filters)
   - `TaskFilter`: Comprehensive filtering using django-filter
   - REST endpoints under `/tasks/api/` with full CRUD operations
   - Open permissions (AllowAny) - no authentication required
   - Pagination enabled (20 items per page)

4. **Web Interface (tasks/views.py)**
   - Class-based views using Django generics
   - Dashboard view aggregates task statistics
   - Template inheritance structure with base.html
   - Forms handled via Django's built-in CreateView/UpdateView

### Request Flow
- Web: URL → tasks/urls.py → views.py → templates → Response
- API: URL → tasks/urls.py → api.py (ViewSet) → Serializer → JSON Response
- Both interfaces share the same models and business logic

### Testing Strategy
- Model tests in tasks/tests.py (basic CRUD operations)
- API tests in tasks/test_api.py (endpoints, filtering, pagination)
- Filter tests in tasks/test_filters.py (query parameter handling)
- Tests use Django TestCase with isolated test database

### Key Patterns
- Activity logging: Override save() method and compare field changes
- Single file modules: All API logic in api.py, all views in views.py
- No custom middleware or authentication system
- Static files directory exists but currently unused

### API Endpoints
- `GET /tasks/api/` - List tasks (supports filtering)
- `POST /tasks/api/` - Create task
- `GET /tasks/api/{id}/` - Get task details
- `PUT/PATCH /tasks/api/{id}/` - Update task
- `DELETE /tasks/api/{id}/` - Delete task
- `GET /tasks/api/{id}/activities/` - Get task activities
- `GET /tasks/api/users/` - List users

### Development Notes
- Currently configured for development (DEBUG=True)
- No environment-specific configuration files
- Migrations are tracked in version control
- SQLite database file (db.sqlite3) present in repository