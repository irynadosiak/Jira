# Intelligent Task Manager

A Django-based task management system with AI-powered features, web interface and REST API. Built with Poetry for modern Python dependency management.

## Quick Start

```bash
# Install dependencies with Poetry
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
- 🤖 **AI-Powered Features** - Smart task creation, estimation, and summarization

### AI Functionality

- **Smart Task Creation** - Parse natural language descriptions into structured tasks with automatic priority, type, and estimate extraction
- **Intelligent Estimation** - AI-powered time estimation based on similar tasks and complexity analysis
- **Auto Summaries** - Generate concise task summaries from activities and progress updates
- **Flexible AI Backend** - Supports both OpenAI integration and mock services for development

## API Endpoints

### Core Task Management
- `GET /tasks/api/` - List tasks (with filtering)
- `POST /tasks/api/` - Create task
- `GET /tasks/api/{id}/` - Get task details
- `PUT/PATCH /tasks/api/{id}/` - Update task
- `DELETE /tasks/api/{id}/` - Delete task
- `GET /tasks/api/{id}/activities/` - Get task activities
- `GET /tasks/api/users/` - List users

### AI-Powered Endpoints
- `POST /tasks/api/parse-text/` - Parse natural language into task structure
- `POST /tasks/api/create-from-text/` - Create task directly from text description
- `GET /tasks/api/{id}/estimate/` - Get AI-powered time estimation
- `POST /tasks/api/{id}/generate-summary/` - Generate AI task summary
- `GET /tasks/api/{id}/summary/` - Get existing task summary

### Filtering
Add query parameters: `?status=todo&assignee=1&search=bug`

## AI Configuration

The system supports both OpenAI integration and mock AI services for development.

### Using Real AI (OpenAI)
Set environment variables:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export USE_MOCK_AI=False
export OPENAI_MODEL="gpt-4o-mini"  # or gpt-3.5-turbo
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-openai-api-key
USE_MOCK_AI=False
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7
```

### Using Mock AI (Default)
No configuration needed - the system uses intelligent mock services by default for development without requiring external API keys.

## Development

```bash
make test      # Run tests
make lint      # Code quality checks
make format    # Format code
```

### Using Poetry

```bash
poetry install          # Install dependencies
poetry add package      # Add new dependency
poetry run python manage.py runserver  # Run commands in Poetry env
```

## Project Architecture

The project follows clean architecture principles with a focus on maintainable, testable AI integration.

### Core Structure
- **Django Models** - `Task`, `TaskActivity`, and `TaskSummary` models with proper relationships
- **Web Interface** - Django views and templates for task management UI
- **REST API** - DRF-powered API with both standard CRUD and AI-enhanced endpoints
- 
### AI Services Architecture

The AI functionality is built using several key design patterns:

**Factory Pattern** - `EstimatorFactory`, `TaskParserFactory`, and `SummaryProviderFactory` create appropriate AI service instances based on configuration (OpenAI vs Mock).

**Repository Pattern** - `TaskRepository` and `TaskSummaryRepository` provide clean data access abstraction, separating business logic from Django ORM details.

**Builder Pattern** - `EstimationResultBuilder`, `ReasoningBuilder`, and result builders construct complex response objects with validation and consistent structure.

**Strategy Pattern** - Each AI service (estimation, parsing, summarization) has multiple implementations:
- **OpenAI Implementation** - Full AI integration using OpenAI GPT models
- **Mock Implementation** - Rule-based alternatives for development without API costs

**Interface Segregation** - Clean interfaces (`TaskEstimationServiceInterface`, `TaskSummaryServiceInterface`, etc.) define contracts without implementation details.

### Configuration Management
- **Environment-based Config** - AI services automatically switch between OpenAI and mock implementations based on API key availability and `USE_MOCK_AI` setting
- **Centralized Configuration** - `AIConfig` and service-specific configs manage API keys, models, temperature, and token limits
- **Graceful Degradation** - System works fully without external AI APIs using intelligent mock services

### Service Organization
- **tasks/services/** - Modular AI services organized by domain (estimation, parsing, summary)
- **Layered Architecture** - Clear separation between API endpoints, service layer, and data access
- **Error Handling** - Comprehensive exception hierarchy for different AI operation failures
- **Testing Strategy** - Unit tests for both OpenAI and mock implementations ensure reliability

This architecture provides flexibility to switch between AI providers, maintain functionality during development, and scale AI features independently.