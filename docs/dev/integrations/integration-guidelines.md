# Integration Guidelines

## Architecture Overview

Each integration is a Django app in `hi/services/` directory. The `hi.integration` app provides management interfaces and base classes.

### Key Concepts
- **integration_id**: Unique identifier for each integration type
- **integration_key**: Associates entities/sensors with external systems
- **detail_attrs**: Opaque data blob - only the integration uses this data

### Responsibility Boundaries
Integrations create `SensorResponse` objects which become `Event` objects with duration. The Event duration is the only accessible duration data - Event objects don't know about underlying integration specifics.

## Integration Setup Process

### 1. Create Django App
```bash
cd src/hi/services
../../manage.py startapp myintegration
```

### 2. Configure App
- Set fully qualified name in `apps.py`: `name = 'hi.services.myintegration'`
- Add to `INSTALLED_APPS` in `hi/settings/base.py`

### 3. Define Integration Type
Add to `IntegrationType` enum in appropriate enums file

### 4. Create Gateway Class
Implement `IntegrationGateway` with required methods:
- `activate(integration_instance)` - Setup and validation
- `deactivate(integration_instance)` - Cleanup and shutdown
- `manage(request, integration_instance)` - Management interface

### 5. Register with Factory
Add gateway mapping in `hi/integrations/integration_factory.py`

## Gateway Implementation Patterns

### Gateway Methods
**activate()**: Validate config, test connection, initialize resources
**deactivate()**: Clean up entities, close connections, update status
**manage()**: Handle POST actions (sync, test, config), render management UI

### Return Format
All gateway methods return dict with:
- `status`: 'success' or 'error'
- `message`: User-friendly status message
- `redirect`: Optional redirect URL

## Integration Patterns

### API Integration
- **HTTP Client**: Use `requests.Session` with retry strategies and circuit breakers
- **WebSocket**: Async connection handling with reconnection logic
- **Authentication**: Bearer tokens, API keys, custom headers

### Data Synchronization
- **Entity Sync**: Map external entities to internal Entity models
- **State Sync**: Update EntityState objects from external data
- **Cleanup**: Remove entities no longer in external system

### Error Handling
Custom exception hierarchy:
- `IntegrationError` - Base class
- `ConnectionError` - Network/connectivity issues
- `AuthenticationError` - Auth/authorization failures
- `DataValidationError` - Invalid data from external source

## Key Base Classes & Modules

### Core Classes
- `hi.integration.integration_gateway.IntegrationGateway` - Base gateway class
- `hi.utils.singleton.Singleton` - Singleton pattern for gateways
- `hi.integrations.enums.IntegrationStatus` - Status enumeration

### Factory Pattern
- `hi.integrations.integration_factory.py` - Gateway registration
- `hi.integrations.exceptions.py` - Custom exception classes

### Example Integrations
- `hi.services.hass/` - Home Assistant integration
- `hi.services.zoneminder/` - ZoneMinder integration
- `hi.services.weather/` - Weather service integration

## Related Documentation
- [Service Patterns](service-patterns.md)
- [Gateway Implementation](gateway-implementation.md)
- [Weather Integration](weather-integration.md)
- [Backend Guidelines](../backend/backend-guidelines.md)
