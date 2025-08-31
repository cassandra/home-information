# Backend Guidelines

## App Module Structure

Each Django app follows this standard structure:

```
hi/apps/${APPNAME}/
├── enums.py              # Enums related to the module
├── models.py             # Django ORM models
├── transient_models.py   # Non-ORM models (not persisted)
├── urls.py               # URL patterns when module provides views
├── views.py              # Main views for module
├── views_mixin.py        # Common view functionality
├── forms.py              # Django forms for views
├── ${NAME}_manager.py    # Singleton manager classes
├── settings.py           # User-controllable settings
├── monitors.py           # Periodic background processes
├── templates/${APPNAME}/ # App templates
├── apps.py               # Django-required module definition
├── tests/                # Unit tests
└── admin.py              # Django admin console integration

# Edit mode structure (when applicable)
edit/
├── urls.py               # Edit-only URLs
├── views.py              # Edit-only views
└── ...                   # Same structure for edit functionality
```

## Django Model Patterns

### Integration Key Pattern

All external systems use integration keys for entity mapping:

```python
class IntegrationKeyMixin(models.Model):
    integration_id = models.CharField(max_length=255, null=True, blank=True)
    integration_name = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        abstract = True
    
    @property
    def integration_key(self):
        return f"{self.integration_name}:{self.integration_id}"
```

### Entity-Centric Design

All controllable/observable items modeled as entities with states:

```python
class Entity(IntegrationKeyMixin):
    name = models.CharField(max_length=100)
    location = models.ForeignKey('location.Location', on_delete=models.CASCADE)
    entity_type = models.ForeignKey('EntityType', on_delete=models.CASCADE)
    
    class Meta:
        indexes = [
            models.Index(fields=['integration_name', 'integration_id']),
        ]

class EntityState(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='states')
    entity_state_type = models.ForeignKey('EntityStateType', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['entity', 'entity_state_type']
```


### Database Indexing Strategy

Strategic use of `db_index=True` for query performance:

```python
class SensorResponse(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    value = models.TextField()
    
    class Meta:
        indexes = [
            models.Index(fields=['sensor', '-timestamp']),  # Composite index for queries
            models.Index(fields=['timestamp']),  # For time-range queries
        ]
```

## Singleton Manager Pattern

Core functionality uses singleton pattern for system-wide coordination:

```python
from hi.utils.singleton import Singleton

class AlertManager(Singleton):
    def __init_singleton__(self):
        self._alert_queue = AlertQueue()
        self._lock = threading.Lock()
    
    def add_alert(self, alert_data):
        with self._lock:
            # Thread-safe alert processing
            self._alert_queue.add(alert_data)
    
    @classmethod
    def instance(cls):
        """Get singleton instance"""
        return cls()
```

### Manager Initialization Patterns

```python
def ensure_initialized(self):
    """Ensure manager is properly initialized (sync version)"""
    if not hasattr(self, '_initialized'):
        self._initialize_data_structures()
        self._initialized = True

async def ensure_initialized_async(self):
    """Ensure manager is properly initialized (async version)"""
    if not hasattr(self, '_initialized'):
        await self._initialize_data_structures_async()
        self._initialized = True
```

## Dual Sync/Async Patterns

Many manager classes support both Django views and async integration services:

```python
class WeatherManager(Singleton):
    def get_current_conditions(self):
        """Synchronous version for Django views"""
        return self._fetch_conditions_sync()
    
    async def get_current_conditions_async(self):
        """Asynchronous version for integrations"""
        return await self._fetch_conditions_async()
    
    def do_control(self, device_id, action):
        """Sync control for web requests"""
        return self._execute_control(device_id, action)
    
    async def do_control_async(self, device_id, action):
        """Async control for background processes"""
        return await self._execute_control_async(device_id, action)
```

## Background Process Integration

### Thread Management

```python
class AppMonitorManager(Singleton):
    def __init_singleton__(self):
        self._event_loop = None
        self._background_threads = []
        self._shutdown_event = threading.Event()
    
    def start_background_monitoring(self):
        """Start background monitoring threads"""
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        self._background_threads.append(thread)
    
    def shutdown(self):
        """Graceful shutdown of background processes"""
        self._shutdown_event.set()
        for thread in self._background_threads:
            thread.join(timeout=5.0)
```

### Django + AsyncIO Integration

```python
import asyncio
from asgiref.sync import sync_to_async

class IntegrationManager(Singleton):
    def __init_singleton__(self):
        self._event_loop = asyncio.new_event_loop()
    
    async def process_entities_async(self):
        """Process entities with proper ORM access"""
        # Use select_related to prevent lazy loading issues
        entities = await sync_to_async(list)(
            Entity.objects.select_related('location', 'entity_type').all()
        )
        
        for entity in entities:
            await self._process_entity_async(entity)
```

## Django Views

**Simple Views**: Our design philophy is to keep the Django view classes in views.py somewhat simple. When where the views need non-trivial computations, database queries or construction of intricate data structure, we use some helper class to encapsulate the business logic. For example, the method _group_history_by_time() should be moved to a helper class.  In this case, given the scope of video browsing, it makes sense for there to be a dedicated class for all the various helpers needed related to this feature.

**URL Names**: Always leverage Django url names and never depend on details and strings of user-facing urls.

## Performance Optimization Patterns

### TTL Caching

```python
from cachetools import TTLCache
import threading

class StatusDisplayManager(Singleton):
    def __init_singleton__(self):
        self._cache = TTLCache(maxsize=1000, ttl=60)  # 1 minute TTL
        self._cache_lock = threading.Lock()
    
    def get_status_display(self, entity_id):
        with self._cache_lock:
            if entity_id in self._cache:
                return self._cache[entity_id]
            
            status = self._compute_status_display(entity_id)
            self._cache[entity_id] = status
            return status
```

### Deque-based Aggregation

```python
from collections import deque

class AlertManager(Singleton):
    def __init_singleton__(self):
        # Memory-efficient circular buffer
        self._recent_alerts = deque(maxlen=100)
    
    def add_alert(self, alert):
        self._recent_alerts.append(alert)
        # Automatically removes oldest when maxlen exceeded
```

## Django View Patterns

### View Mixins for Common Functionality

```python
class EntityMixin:
    def get_entity(self):
        """Get entity from URL parameters"""
        entity_id = self.kwargs.get('entity_id')
        return get_object_or_404(Entity, id=entity_id)

class LocationViewMixin:
    def get_location_view(self):
        """Get current location view from session"""
        location_view_id = self.request.session.get('location_view_id')
        if location_view_id:
            return LocationView.objects.get(id=location_view_id)
        return None
```

### Custom View Base Classes

```python
class HiModalView(View):
    """Base for views that handle both sync and async requests"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.async_dispatch(request, *args, **kwargs)
        return self.sync_dispatch(request, *args, **kwargs)
    
    def sync_dispatch(self, request, *args, **kwargs):
        """Handle synchronous requests - render full page"""
        response = super().dispatch(request, *args, **kwargs)
        return response
    
    def async_dispatch(self, request, *args, **kwargs):
        """Handle AJAX requests - return JSON with HTML fragments"""
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(response, 'content'):
            return JsonResponse({
                'modal': response.content.decode('utf-8'),
                'status': 'success'
            })
        return response
```

## Enums

We leverage enums extensively and do not allow "magic" strings to represent core concepts that the application Logic depends on.  We have defined a base class `hi.apps.common.enums.LabeledEnums` for al enums used in the application that slightly extends their capabilities and provides some convenience methods.

A key convenience method is the `from_name` and `from_name_safe` methods. These provide more robust case-insensitve and whitespace-insensitive matching.  The latter does not raise an exception for bad values, but returns the default value for uses where the default bhavior is better than interrupting the flow.

### Enums in Django Models

We have a pattern for storing enums in the database that is used throughout the code.  It is described like this:

The design pattern for storing enumerated values in the Database is *NOT* to use the Django/databases enumeration/choices type, but use a string via Django CharField (VARCHAR) instead.  The rationale is that we prefer the flexibility to add new enums without requiring a database migration for such a trivial change.  

We use a special base level enum hi.apps.common.LabeledEnum for most enums, but especially those stored in the database.  The key features of this class is to ensure consistency as we put values into and out of the database, and to gracefully handle the case of improper values.  Specifically, the `__str__` method returns the enum name in *LOWER* case, though the Django name field matches the casing of the defined enum.

Further, we adopt a naming convention to make the difference between the enum class and the Django model field distinct by having the Django field always have `str` as the fielkd name suffix. For example, if the enum class is named `EntityType`, the Django field name would be `entity_type_str`. Further, we also add a setter/getter pair on the model that matches the enum name and that accepts/returns an enum instance. e.g.,
```
    @property
    def entity_type(self) -> EntityType:
        return EntityType.from_name_safe( self.entity_type_str )

    @entity_type.setter
    def entity_type( self, entity_type : EntityType ):
        self.entity_type_str = str(entity_type)
        return
```

We are aware that there is a risk in this pattern, and we have done work to correct it by creating the custom Django model field `hi.apps.common.model_fields.LabeledEnumField`. All going forward new enums must use this new custom field when storing in a model.  Retrofitting existing models is on a best effort, time availability basis.

## Settings and Configuration

### App Settings Pattern

Each internal Django app module can provide user-controllable settings that appear on the main config page. These settings are auto-discovered by the `config` app module. The presence of a file named `settings.py` in an app module will automatically get picked up and create a new config area on the user-facing config page.

In the `settings.py` file, define a subclass of the enum `SettingEnum` to define the label and data types:

```python
# In app/settings.py
from hi.config.enums import SettingEnum

class WeatherSettings(SettingEnum):
    REFRESH_INTERVAL = ("refresh_interval", int, 300, "Weather refresh interval (seconds)")
    DEFAULT_LOCATION = ("default_location", str, "", "Default weather location")
    ENABLE_ALERTS = ("enable_alerts", bool, True, "Enable weather alerts")
    
    def __init__(self, key, data_type, default_value, description):
        self.key = key
        self.data_type = data_type
        self.default_value = default_value
        self.description = description
```

### Adding to Existing Settings

After adding a new value to an app's `SettingEnum`, you will need to run `./manage.py migrate` to populate the database with the new setting and its default value. New settings are written to the DB using a post-migrate signal.

### Internal Settings Debugging

For debugging help, there is a URL to inspect the Django internal `settings.py` content:
```
http://localhost:8411/config/internal
```

### Adding New Config UI Tab Section

To add a new tab section to the Configuration UI:

1. **Add entry to `ConfigPageType`**
2. **Add a View** - view class should extend `ConfigPageView`
3. **Override methods**:
   - `config_page_type()`
   - `get_main_template_name()`
   - `get_template_context()`
4. **Create template** (matching name)
5. **Template should extend** `config/pages/config_base.html`
6. **Add to `urls.py`** (ensure this is included in top-level `urls.py`)

## Related Documentation
- Django patterns: [Django Patterns](django-patterns.md)
- Database conventions: [Database Conventions](database-conventions.md)
- Async/sync patterns: [Async Sync Patterns](async-sync-patterns.md)
- Integration patterns: [Integration Guidelines](../integrations/integration-guidelines.md)
- Testing: [Testing Guidelines](../testing/testing-guidelines.md)

## Debugging

## Custom Debug Settings

You can modify these variables in `src/hi/settings/development.py` to enable/disable some custom development features:

- `SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING` - Suppress showing the request line log message. The polling front-end will generate a long stream of these and it make it hard to see other requests.
- `SUPPRESS_MONITORS` - Turns off running any of the background monitor tasks.  Useful when working on something not related ot them to prevent unnecessary logging and resource usage.
- `BASE_URL_FOR_EMAIL_LINKS` - If needing to test the links in delivered emails. We usually need this to point back to the local development server that send the email.
