# Integration Guidelines

## Architecture Overview

Each integration is a Django app in `hi/services/` directory. The `hi.integration` app provides management interfaces and base classes.

### Key Concepts
- **integration_id**: Unique identifier for each integration type
- **integration_key**: Associates entities/sensors with external systems
- **detail_attrs**: Opaque data blob - only the integration uses this data

### One-to-many state composition
A single upstream state may decompose into multiple HI EntityStates when the upstream protocol packs several independently-controllable values into one entity (e.g., a color light's brightness + hue + saturation + color temperature). The framework supports this via:

- **integration_key suffix convention**: each derived EntityState gets its own integration_key (e.g., `light.x` for the parent, `light.x~hue` / `light.x~saturation` for the substates). The integration controls the suffix scheme.
- **`IntegrationConverterHelper`** (`hi/integrations/integration_converter_helper.py`): a classmethod helper used by converters that need to compose outbound calls from multiple HI EntityState values. Exposes `get_latest_state_values(integration_keys)` for the runtime cache lookup. Inbound decomposition writes each substate value through `SensorResponse`; outbound recomposition reads it back via this helper.
- The integration's converter decides which upstream attributes become substates and how they map back to outbound calls. See the HA integration's substate handling for a worked example.

### Unit conversion at the integration boundary
Integrations whose external system reports values with a unit (HA's `temperature_unit`, sensor `unit_of_measurement`, etc.) MUST normalize at the boundary: convert inbound values to a canonical unit before storing, and convert outbound values from canonical to the external system's required unit. The canonical unit is declared once where the EntityState is created (e.g., HA's climate substate specs declare °C as canonical for temperatures). Downstream code reads `EntityState.units` rather than re-asserting the canonical, so changing the choice propagates through the spec → EntityState chain without code edits at every conversion site.

- **`IntegrationMetadataCache`** (`hi/integrations/integration_metadata_cache.py`) caches `EntityState.units` per `IntegrationKey` so polling-loop unit lookups don't multiply DB queries. Process-wide, lazy-warmed; provides parallel sync and async APIs (use the async variant from monitor coroutines so DB access goes through `sync_to_async`).
- **`IntegrationConverterHelper.to_entity_state_value` / `from_entity_state_value`** (both with `_async` variants) are the boundary helpers backed by the cache. Inbound (`to_`) takes an external value + external unit and returns the value in the EntityState's stored unit. Outbound (`from_`) takes an EntityState-unit value + target external unit. Both pass through unchanged when units are absent or already match — safe to call uniformly without per-state-type branching.

See `hi/services/hass/hass_converter.py` (climate substate inbound + setpoint outbound dispatch) for a worked example.

The symmetric server ↔ UI boundary uses `ConsoleConverterHelper`; see [Frontend Guidelines](../frontend/frontend-guidelines.md#unit-bearing-values-server--ui-translation).

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

### 6. Write Per-Integration Documentation
Every user-configured integration MUST ship with two short docs based
on the templates:

- **User-facing**: copy [`docs/integrations/_template.md`](../../integrations/_template.md)
  to `docs/integrations/<integration-name>.md` and fill in all seven
  sections (Overview, Prerequisites, Obtaining credentials,
  Configuration values, Setup walkthrough, Troubleshooting, Known
  limitations).
- **Developer-facing**: copy [`_template.md`](_template.md) to
  `docs/dev/integrations/<integration-name>.md` and fill in all six
  sections (Overview, Key modules, API patterns, Implementation
  notes, Testing approach, References). Keep it high-level and refer
  to the code for details — the code is the authoritative source.

After creating both docs, add a one-paragraph entry plus a link in
the user-facing landing page at [`docs/Integrations.md`](../../Integrations.md).

> **Internal data sources** like the Weather subsystem
> (`docs/dev/integrations/weather-integration.md`) do not require
> per-integration user-facing docs — they are not user-configured in
> the integration sense. The template structure above applies only to
> integrations that appear on the Settings → Integrations page.

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
- `hi.services.homebox/` - HomeBox integration

## Related Documentation
- [Service Patterns](service-patterns.md)
- [Gateway Implementation](gateway-implementation.md)
- [Weather Integration](weather-integration.md)
- [Backend Guidelines](../backend/backend-guidelines.md)
