# Integration Guidelines

## Integration Architecture

Each integration is a Django app in the `hi/services` directory. The `hi.integration` app handles integration management and required interfaces.

## Nomenclature

- **integration_id** - Unique identifier for each integration type
- **integration_key** - Used to associate with external integration for entities, sensors, controllers, etc.
- **integration_attr_key** - Unique identifier for user-defined attributes needed by implementation

## How to Add an Integration

### 1. Create Django App

```bash
cd src/hi/services
../../manage.py startapp myintegration
```

### 2. Configure App

Ensure `name` is fully qualified in `hi/services/myintegration/apps.py`:

```python
class MyIntegrationConfig(AppConfig):
    name = 'hi.services.myintegration'
```

Add to `INSTALLED_APPS` in `hi/settings/base.py`:

```python
INSTALLED_APPS = [
    # ...
    'hi.services.myintegration',
]
```

### 3. Define Integration Type

Add to the IntegrationType enum:

```python
class IntegrationType(Enum):
    MYINTEGRATION = ('My Integration', 'For my stuff.')
```

### 4. Create Integration Gateway

Create `hi/services/myintegration/myintegration_gateway.py`:

```python
from hi.integration.integration_gateway import IntegrationGateway
from hi.utils.singleton import Singleton

class MyIntegrationGateway(Singleton, IntegrationGateway):
    
    def activate(self, integration_instance):
        """Handle integration activation"""
        # Validation and setup logic
        integration_instance.status = IntegrationStatus.ACTIVE
        integration_instance.save()
        return {'status': 'success', 'message': 'Integration activated'}
    
    def deactivate(self, integration_instance):
        """Handle integration deactivation"""
        # Cleanup logic
        integration_instance.status = IntegrationStatus.INACTIVE
        integration_instance.save()
        return {'status': 'success', 'message': 'Integration deactivated'}
    
    def manage(self, request, integration_instance):
        """Handle management interface"""
        if request.method == 'POST':
            return self.handle_management_post(request, integration_instance)
        return self.render_management_page(request, integration_instance)
```

### 5. Register with Factory

Add to `hi/integrations/integration_factory.py`:

```python
from hi.services.myintegration.myintegration_gateway import MyIntegrationGateway

def get_integration_gateway(integration_type):
    if integration_type == IntegrationType.MYINTEGRATION:
        return MyIntegrationGateway()
    # ... other integrations
```

## Integration Gateway Methods

### Activate Method

Handle integration activation flow:

```python
def activate(self, integration_instance):
    try:
        # Validate configuration
        self.validate_configuration(integration_instance)
        
        # Test connection
        self.test_connection(integration_instance)
        
        # Initialize resources
        self.initialize_integration(integration_instance)
        
        integration_instance.status = IntegrationStatus.ACTIVE
        integration_instance.save()
        
        return {
            'status': 'success',
            'message': 'Integration activated successfully',
            'redirect': None
        }
    except ValidationError as e:
        return {
            'status': 'error',
            'message': str(e),
            'redirect': None
        }
```

### Deactivate Method

Handle cleanup and deactivation:

```python
def deactivate(self, integration_instance):
    try:
        # Clean up entities
        entities_removed = self.cleanup_entities(integration_instance)
        
        # Close connections
        self.close_connections(integration_instance)
        
        integration_instance.status = IntegrationStatus.INACTIVE
        integration_instance.save()
        
        return {
            'status': 'success',
            'message': f'Integration deactivated. Removed {entities_removed} entities.',
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error during deactivation: {str(e)}'
        }
```

### Manage Method

Provide management interface:

```python
def manage(self, request, integration_instance):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'sync_entities':
            return self.sync_entities(integration_instance)
        elif action == 'test_connection':
            return self.test_connection_endpoint(integration_instance)
        elif action == 'update_config':
            return self.update_configuration(request, integration_instance)
    
    # Render management page
    context = {
        'integration': integration_instance,
        'entity_count': self.get_entity_count(integration_instance),
        'last_sync': self.get_last_sync_time(integration_instance),
        'connection_status': self.get_connection_status(integration_instance),
    }
    return render(request, 'myintegration/manage.html', context)
```

## API Integration Patterns

### HTTP Client Pattern

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class MyIntegrationClient:
    def __init__(self, base_url, api_key, timeout=30):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.session = self._create_session()
    
    def _create_session(self):
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Default headers
        session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'HomeInformation/1.0'
        })
        
        return session
    
    def get_entities(self):
        response = self.session.get(
            f'{self.base_url}/entities',
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
```

### WebSocket Integration Pattern

```python
import asyncio
import websockets
import json

class MyIntegrationWebSocket:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        self.websocket = None
        self.running = False
    
    async def connect(self):
        """Establish WebSocket connection"""
        headers = {'Authorization': f'Bearer {self.api_key}'}
        self.websocket = await websockets.connect(self.url, extra_headers=headers)
        self.running = True
    
    async def listen(self):
        """Listen for messages"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            self.running = False
    
    async def handle_message(self, data):
        """Process received message"""
        message_type = data.get('type')
        
        if message_type == 'entity_update':
            await self.handle_entity_update(data)
        elif message_type == 'status_change':
            await self.handle_status_change(data)
```

## Data Synchronization Patterns

### Entity Synchronization

```python
class EntitySynchronizer:
    def __init__(self, integration_instance):
        self.integration = integration_instance
        self.client = MyIntegrationClient(
            integration_instance.base_url,
            integration_instance.api_key
        )
    
    def sync_entities(self):
        """Synchronize entities from external system"""
        try:
            external_entities = self.client.get_entities()
            
            synced_count = 0
            for ext_entity in external_entities:
                entity, created = self.sync_single_entity(ext_entity)
                if entity:
                    synced_count += 1
            
            # Remove entities no longer in external system
            removed_count = self.cleanup_removed_entities(external_entities)
            
            return {
                'synced': synced_count,
                'removed': removed_count,
                'total': len(external_entities)
            }
            
        except Exception as e:
            raise IntegrationError(f"Entity sync failed: {str(e)}")
    
    def sync_single_entity(self, external_entity):
        """Sync individual entity"""
        integration_id = external_entity['id']
        
        entity, created = Entity.objects.get_or_create(
            integration_name=self.integration.integration_type.name,
            integration_id=integration_id,
            defaults={
                'name': external_entity['name'],
                'entity_type': self.get_or_create_entity_type(external_entity),
                'location': self.get_default_location(),
            }
        )
        
        # Update entity properties
        if not created:
            entity.name = external_entity['name']
            entity.save()
        
        # Sync entity states
        self.sync_entity_states(entity, external_entity)
        
        return entity, created
```

## Error Handling Patterns

### Custom Exception Classes

```python
class IntegrationError(Exception):
    """Base class for integration errors"""
    pass

class ConnectionError(IntegrationError):
    """Connection-related errors"""
    pass

class AuthenticationError(IntegrationError):
    """Authentication/authorization errors"""
    pass

class DataValidationError(IntegrationError):
    """Data validation errors"""
    pass
```

### Error Recovery Patterns

```python
class ResilientIntegrationClient:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
    
    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with circuit breaker pattern"""
        @self.circuit_breaker
        def _request():
            response = self.session.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response
        
        try:
            return _request()
        except CircuitBreakerOpenException:
            raise ConnectionError("Service temporarily unavailable")
        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Request failed: {str(e)}")
```

## Related Documentation
- Service patterns: [Service Patterns](service-patterns.md)
- Gateway implementation: [Gateway Implementation](gateway-implementation.md)
- External API standards: [External API Standards](external-api-standards.md)
- Weather integration: [Weather Integration](weather-integration.md)
- Backend integration: [Backend Guidelines](../backend/backend-guidelines.md)