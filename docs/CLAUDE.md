# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow for GitHub Issues

When working on GitHub issues, follow this development workflow:

1. **Read the GitHub issue and all its comments** - Understand the requirements, context, and any discussion
2. **Ensure staging branch is in sync with GitHub** - Make sure you have the latest changes
3. **Create a dev branch off the staging branch** - Follow naming conventions from `docs/dev/Workflow.md`
4. **Do development changes** - Commit to git at logical checkpoints during development
5. **After first commit, push the branch to GitHub** - Use the same branch name as the local one
6. **Once issue is complete and all changes pushed** - Create a pull request using the template
7. **Before creating the pull request** - Ensure all unit tests pass and linting is clean

For detailed branching conventions and additional workflow information, see `docs/dev/Workflow.md`.

## Common Development Commands

### Environment Setup
```bash
# Initialize development environment (one-time setup)
make env-build-dev
python3.11 -m venv venv
. ./init-env-dev.sh
pip install -r src/hi/requirements/development.txt

# Daily development setup
. ./init-env-dev.sh  # Sources virtual env and environment variables
```

### Django Management
```bash
cd src

# Database operations
./manage.py migrate
./manage.py makemigrations
./manage.py check

# Testing
./manage.py test                    # Run all unit tests
./manage.py test weather.tests     # Run specific app tests

# User management
./manage.py hi_createsuperuser
./manage.py hi_creategroups

# Development server
./manage.py runserver              # Runs on http://127.0.0.1:8411
```

### Code Quality
```bash
# Linting and formatting (from development.txt requirements)
black src/                         # Format code
flake8 src/                       # Lint code
autopep8 --in-place --recursive src/  # Auto-format
```

### Docker Operations
```bash
# Build and run in containers
make docker-build
make docker-run-fg                 # Foreground
make docker-run                    # Background
make docker-stop
```

## Architecture Overview

### Core Django Applications

**Entity App**: Central model for all physical/logical objects (devices, features, software). Uses integration keys for external system connectivity and supports SVG-based positioning.

**Location App**: Physical space management with SVG-based floor plans. Manages hierarchical locations and spatial positioning of entities and collections.

**Sense App**: Sensor data collection and monitoring. Links to EntityState with history persistence for various sensor types.

**Control App**: Device control and automation. Manages controllable devices with action history tracking.

**Event App**: Event-driven automation system with multi-clause triggers, time windows, and automated responses.

**Alert App**: Alert and alarm management using singleton pattern with queue-based processing.

**Collection App**: Logical grouping and organization of entities for management and display.

**Weather App**: Weather data integration with pluggable sources (NWS) and data aggregation.

### Integration Layer

**Home Assistant Integration** (`src/hi/services/hass/`): Full two-way sync with Home Assistant including entity mapping, state synchronization, and controller integration.

**ZoneMinder Integration** (`src/hi/services/zoneminder/`): Camera and video surveillance system integration for security monitoring.

**Integration Pattern**: All external systems use integration keys for mapping entities between systems.

### Key Architectural Patterns

- **Entity-Centric Design**: All controllable/observable items modeled as entities with states
- **Singleton Managers**: Core functionality uses singleton pattern (AlertManager, WeatherManager)
- **SVG-Based Visualization**: Locations and entities support SVG graphics for spatial representation
- **Mixin Pattern**: Common functionality shared through mixins (SecurityMixins, NotifyMixins)
- **Event-Driven Architecture**: Automated responses based on state changes and sensor readings

### File Structure Conventions

- `apps/*/models.py`: Django models for each application
- `apps/*/managers.py`: Business logic managers (often singletons)
- `apps/*/transient_models.py`: Non-database models for data transfer
- `apps/*/templates/*/panes/`: UI component templates
- `apps/*/templates/*/modals/`: Modal dialog templates
- `apps/*/tests/`: Unit tests and test data
- `integrations/`: Cross-system integration framework
- `services/*/`: External service integrations (HASS, ZoneMinder)

### Database and Dependencies

- **Database**: SQLite for development, supports PostgreSQL for production
- **Cache**: Redis required for development and production
- **Frontend**: jQuery 3.7, Bootstrap 4, custom SVG manipulation
- **Python**: 3.11+, Django 4.2

### Testing Infrastructure

- Unit tests: `./manage.py test`
- Visual testing pages: Available at `/tests/ui` when `DEBUG=True`
- Integration tests: Custom management commands (`hass_test`, `zm_test`)

#### High-Value vs Low-Value Testing Criteria

**HIGH-VALUE Tests (Focus Here)**
- **Database constraints and cascade deletion behavior** - Critical for data integrity
- **Complex business logic and algorithms** - Custom calculations, aggregation, processing
- **Singleton pattern behavior** - Manager classes, initialization, thread safety
- **Enum property conversions with custom logic** - from_name_safe(), business rules
- **File handling and storage operations** - Upload, deletion, cleanup, error handling
- **Integration key parsing and external system interfaces** - API boundaries
- **Complex calculations** - Geometric (SVG positioning), ordering, aggregation logic
- **Caching and performance optimizations** - TTL caches, database indexing
- **Auto-discovery and Django startup integration** - Module loading, initialization sequences
- **Thread safety and concurrent operations** - Locks, shared state, race conditions
- **Background process coordination** - Async/sync dual access, event loop management

**LOW-VALUE Tests (Avoid These)**
- Simple property getters/setters that just return field values
- Django ORM internals verification (Django already tests this)
- Trivial enum label checking without business logic
- Basic field access and obvious default values
- Simple string formatting without complex logic

#### Critical Testing Anti-Patterns (Never Do These)

**NEVER Test Behavior Based on Log Messages**
- **Problem**: Log message assertions (`self.assertLogs()`, checking log output) are fragile and break easily when logging changes
- **Issue**: Many existing tests deliberately disable logging for performance and clarity
- **Solution**: Test actual behavior changes - state modifications, return values, method calls, side effects
- **Example**: Instead of `assertLogs('module', level='WARNING')`, verify the actual error handling behavior occurred

```python
# BAD - Testing based on log messages
with self.assertLogs('weather.manager', level='WARNING') as log_context:
    manager.process_data(invalid_data)
    self.assertTrue(any("Error processing" in msg for msg in log_context.output))

# GOOD - Testing actual behavior
mock_fallback = Mock()
with patch.object(manager, 'fallback_handler', mock_fallback):
    result = manager.process_data(invalid_data)
    mock_fallback.assert_called_once()
    self.assertIsNone(result)  # Verify expected failure behavior
```

#### Django-Specific Testing Patterns

```python
# Abstract Model Testing - Create concrete test class
class ConcreteTestModel(AbstractModel):
    def required_abstract_method(self):
        return "test_implementation"

# Mock Django operations for database-less testing
with patch('django.db.models.Model.save') as mock_save:
    instance.save()
    mock_save.assert_called_once()

# Integration Key Pattern Testing
def test_integration_key_inheritance(self):
    model = TestModel.objects.create(
        integration_id='test_id',
        integration_name='test_integration'
    )
    self.assertEqual(model.integration_id, 'test_id')

# Singleton Manager Testing
def test_manager_singleton_behavior(self):
    manager1 = ManagerClass()
    manager2 = ManagerClass()
    self.assertIs(manager1, manager2)

# Background Process and Threading Testing
async def test_async_manager_method(self):
    with patch('asyncio.run') as mock_run:
        result = await manager.async_method()
        mock_run.assert_called()

def test_manager_thread_safety(self):
    results = []
    def worker():
        results.append(manager.thread_safe_operation())
    
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
```

#### System Architecture Patterns Discovered

**Module Dependency Hierarchy**
- **Entity/EntityState**: Central hub used by control, event, sense, collection modules
- **Location/LocationView**: Complex SVG positioning system used by entity, collection
- **Integration Key Pattern**: Shared across control, event, sense for external system integration
- **Cascade Deletion Chains**: Critical data integrity enforcement across related models

**Auto-Discovery and Django Integration**
- **Settings Manager**: Tightly integrated with Django initialization, requires special handling in tests
- **Module Loading**: Some managers use Django apps registry for auto-discovery of monitors/handlers
- **Startup Dependencies**: Initialization order matters for singleton managers
- **Cache Integration**: Some managers integrate with Redis/cache systems requiring mocking in tests
- **Background Process Integration**: Manager classes designed for both Django web context and background processes
- **Thread Management**: Some managers spawn background threads that must coordinate with Django lifecycle
- **Async/Sync Dual Access**: Manager classes provide both synchronous and asynchronous interfaces for different contexts

**Background Process and Threading Patterns**
- **AppMonitorManager**: Manages async event loops and background monitoring threads
- **Dual Interface Pattern**: Manager classes expose both sync and async methods (e.g., `do_control()` and `do_control_async()`)
- **Django + AsyncIO Integration**: Background processes must coordinate Django ORM with asyncio event loops
- **Startup Coordination**: Background threads initialized during Django startup sequence
- **Graceful Shutdown**: Background processes must handle Django shutdown signals properly
- **Thread Safety**: Manager singletons use threading.Lock() for safe access from multiple threads
- **Event Loop Management**: Some managers maintain their own asyncio event loops separate from Django
- **Process Separation**: Some functionality runs in separate processes from Django web server
- **Shared State Management**: Managers handle state synchronization between web and background processes
- **Database Connection Handling**: Background processes manage their own DB connections separate from request cycle

**Performance and Concurrency Patterns**
- **TTL Caching**: StatusDisplayManager uses cachetools for performance optimization
- **Thread Safety**: Manager classes use threading.Lock() for concurrent access
- **Deque-based Aggregation**: Alert system uses collections.deque with maxlen for memory efficiency
- **Database Indexing**: Strategic use of db_index=True for query performance

**Complex Business Logic Patterns**
- **SVG Geometric Calculations**: Location positioning, viewbox conversions, bounds calculation
- **Enum Business Rules**: Security states with auto_change_allowed and notification logic
- **File Lifecycle Management**: Automatic cleanup on deletion, unique filename generation
- **Event Window Logic**: Time-based event aggregation with deduplication windows

### Security and Configuration

- Environment variables managed via `.private/env/` (not committed)
- Settings split by environment: `development.py`, `production.py`, `staging.py`
- Config app provides centralized system configuration storage

## Coding Style Guidelines

### Control Flow Statements
- Always include explicit `continue` statements in loops, even when not syntactically required
- Always include explicit `return` statements in functions, even when not syntactically required
- This improves code readability and makes control flow intentions explicit

### Operator Spacing
- Use spaces around assignment operators and most other operators in expressions
- Examples: `x = y + z`, `result += value`, `if count == 0`, `total -= amount`
- Exception: Don't add spaces in function keyword arguments (`func(x=y)`) or type annotations (`x: int = 5`)

Example:
```python
def process_items(items):
    results = []
    for item in items:
        if not item.valid:
            continue  # Explicit continue for invalid items
        
        if item.needs_processing:
            result = process(item)
            results.append(result)
            continue  # Explicit continue after processing
        
        # Handle non-processing case
        results.append(item.default_value)
        continue  # Explicit continue at end of loop
    
    return results  # Explicit return at end of function

def simple_function():
    print("Hello world")
    return  # Explicit return even for void functions
```

### General Guidelines
- Follow existing code patterns and conventions in the codebase
- Use descriptive variable and function names
- Maintain consistency with Django and Python best practices

## Git Commit Guidelines

### Remote Repository
- The remote repository name is `github` (not `origin`)
- Use `git push github` or `git push -u github branch-name` for pushing branches

### Pull Request Template
- GitHub pull request template is located at `.github/PULL_REQUEST_TEMPLATE.md`
- Template includes standard sections: Category, Changes Summary, How to Test, Checklist, etc.
- When creating PRs with `gh pr create`, the template will auto-populate

### Commit Message Style
- Use concise, descriptive commit messages without attribution text
- Focus on **what** was changed and **why**, not implementation details
- Keep messages professional and project-focused
- **Do NOT include** Claude Code attribution, co-author tags, or generated-by comments

**Good examples:**
```
Fix weather module unit test failures and improve WMO units handling
Add support for temperature offset unit arithmetic in Pint
Remove invalid AlertUrgency.PAST enum value for weather alerts
```

**Avoid:**
```
🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```
