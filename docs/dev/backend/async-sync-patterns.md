# Async/Sync Patterns

## Dual Interface Pattern

Many manager classes provide both sync and async methods:

```python
class WeatherManager(Singleton):
    def get_current_conditions(self):
        """Synchronous version for Django views"""
        return self._fetch_conditions_sync()
    
    async def get_current_conditions_async(self):
        """Asynchronous version for integrations"""
        return await self._fetch_conditions_async()
```

## Background Process Coordination

### Thread Safety
```python
class AlertManager(Singleton):
    def __init_singleton__(self):
        self._lock = threading.Lock()
        self._alert_queue = deque()
    
    def add_alert(self, alert):
        with self._lock:
            self._alert_queue.append(alert)
```

### Django + AsyncIO Integration
```python
import asyncio
from asgiref.sync import sync_to_async

class IntegrationManager(Singleton):
    async def process_entities_async(self):
        entities = await sync_to_async(list)(
            Entity.objects.select_related('location').all()
        )
        for entity in entities:
            await self._process_entity_async(entity)
```

## Event Loop Management

### Proper Initialization
```python
class BackgroundService(Singleton):
    def __init_singleton__(self):
        self._event_loop = None
        self._background_task = None
    
    def start_service(self):
        if not self._event_loop:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            self._background_task = self._event_loop.create_task(self._run_background())
```

## Related Documentation
- Backend guidelines: [Backend Guidelines](backend-guidelines.md)
- Testing async patterns: [Testing Patterns](../testing/testing-patterns.md#manager-class-asyncsync-testing)