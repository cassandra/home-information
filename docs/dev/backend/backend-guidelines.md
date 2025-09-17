# Backend Guidelines

## Core Concepts & Modules

### App Module Structure
See [Project Structure](../shared/project-structure.md)

### Key Base Classes
- `hi.utils.singleton.Singleton` - All manager classes
- `hi.apps.common.enums.LabeledEnum` - All enums
- `hi.apps.common.model_fields.LabeledEnumField` - Enum storage in models

## Design Patterns

### Entity-Centric Architecture
All controllable/observable items modeled as entities with states:
- `Entity` model with `IntegrationKeyMixin` for external system mapping
- `EntityState` for current state tracking
- Integration key format: `"integration_name:integration_id"`

### Singleton Manager Pattern
Core functionality uses singleton pattern with thread-safe initialization:
- Implement `__init_singleton__()` not `__init__()`
- Use `cls.instance()` for access
- Include `ensure_initialized()` and `ensure_initialized_async()` methods

### Dual Sync/Async Support
Manager classes provide both sync (Django views) and async (integrations) methods:
- Sync: `get_data()`, `do_control()`
- Async: `get_data_async()`, `do_control_async()`

### Database Patterns
- Strategic indexing: Use `db_index=True` and composite indexes
- Entity queries: Always use `select_related()` for foreign keys
- Enum storage: CharField with `LabeledEnumField`, not Django choices

## Django View Philosophy

### Simple Views
Keep view classes lightweight - delegate complex logic to helper classes:
- Business logic → Helper classes
- Database queries → Manager classes
- Data structure construction → Dedicated builder classes

### View Patterns
- Use mixins for common functionality (`EntityMixin`, `LocationViewMixin`)
- Custom base classes for specialized behaviors (`HiModalView`)
- Always use Django URL names, never hardcoded URLs

## Settings & Configuration

### App Settings Auto-Discovery
Create `settings.py` in any app with `SettingEnum` subclass:
- Automatically appears on config page
- Requires `./manage.py migrate` after adding new settings
- Debug internal settings at `/config/internal`

### Adding Config UI Sections
1. Add entry to `ConfigPageType` enum
2. Create view extending `ConfigPageView`
3. Override required methods
4. Create template extending `config/pages/config_base.html`

## Performance Patterns

### Caching
- TTL caching: `cachetools.TTLCache` with thread locks
- Memory efficiency: `collections.deque` for circular buffers

### Threading & AsyncIO
- Background threads: Daemon threads with graceful shutdown
- Django+AsyncIO: Use `asgiref.sync.sync_to_async` for ORM access

## Development Tools

### Debug Settings
Modify `src/hi/settings/development.py`:
- `SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING` - Hide polling requests
- `SUPPRESS_MONITORS` - Disable background tasks
- `BASE_URL_FOR_EMAIL_LINKS` - Email link testing

## Related Documentation
- [Coding Patterns](../shared/coding-patterns.md)
- [Database Conventions](database-conventions.md)
- [Integration Guidelines](../integrations/integration-guidelines.md)
- [Testing Guidelines](../testing/testing-guidelines.md)
