# Integration Guidelines

## Architecture Overview

Each integration is a Django app in `hi/services/` directory. The `hi.integration` app provides management interfaces and base classes.

### Key Concepts
- **integration_id**: Unique identifier for each integration type
- **integration_key**: Associates entities/sensors with external systems
- **detail_attrs**: Opaque data blob - only the integration uses this data

### Capability model
Each integration declares its `IntegrationCapability` set on `IntegrationMetaData.capabilities` (`hi/integrations/enums.py`). Three capabilities exist today:

- **`CONNECT`** — live mirror of an upstream system. Realized by an `IntegrationConnector` subclass returned from `IntegrationGateway.get_connector()`. All four "Connectors"-tab integrations (HA, ZM, Frigate, HomeBox) declare CONNECT.
- **`IMPORT`** — one-shot copy of upstream items into HI as locally-owned entities. Realized by an `IntegrationImporter` subclass returned from `IntegrationGateway.get_importer()`. HomeBox is the only integration to declare IMPORT alongside CONNECT today (see [`docs/dev/integrations/data-import.md`](data-import.md) for the developer surface).
- **`ATTRIBUTE_REFERENCE`** — search-and-attach surface that contributes URL attributes to existing Entity / Location records (no entity import, no live mirror). Realized by an `IntegrationAttributeReferencer` subclass returned from `IntegrationGateway.get_attribute_referencer()`. Paperless-ngx is the only integration to declare ATTRIBUTE_REFERENCE today. ATTRIBUTE_REFERENCE-only integrations are configured on a sibling tab labeled "Content Sources" instead of "Connectors" — the page chrome differs because there's no monitor / sync lifecycle.

The three per-capability classes (`IntegrationConnector`, `IntegrationImporter`, `IntegrationAttributeReferencer`) share a common base `CapabilityGateway` (`hi/integrations/capability_gateway.py`). Each declares a `capability` class attribute identifying the `IntegrationCapability` it realizes, and overrides cross-capability concerns: `get_metadata()` (abstract), `get_description()` (operator-facing one-line description), and `get_attribute_actions_template_name()` (optional template fragment for the attribute form's action bar). Capability-specific concerns (sync, import, search) stay on the subclass. Adding a new capability means subclassing `CapabilityGateway`, declaring the `capability` class attribute, and overriding only the methods that apply to the new shape.

The `connector/`, `importer/`, and `referencer/` sub-packages live as peers under `hi/integrations/`.

Per-attribute `IntegrationAttributeType` declarations may carry an optional `capabilities` set to restrict which capability's UI surfaces the attribute. Default is `ALL_CAPABILITIES`.

Per-entity capability state is derived from the integration columns on `Entity`, not stored as a separate field:

- **Live Connect** (`is_external`): `integration_id` is set.
- **Imported or detached** (`is_imported` / `is_detached` — operational synonyms today, with `has_integration_provenance` as the umbrella predicate): `previous_integration_id` is set, `integration_id` is `NULL`.
- **Native**: both columns `NULL`.

Query sites use the matching `EntityModelManager` helpers (`external_for`, `imported_for`, `detached_for`, `with_integration_provenance`) so the call site reads as semantic intent. The IMPORT-initiation block check in `CapabilityBlockViewMixin` uses `Entity.objects.external_for(...)`; `IntegrationImporter.discard_imported_data` uses `Entity.objects.imported_for(...)`.

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

### EntityStateType vs. EntityStateRole
Each `EntityState` carries two independent axes:

- **`EntityStateType`** — local value semantics: value storage, unit handling, value-to-label translation, per-value rendering template. Answers "how do I store / interpret / render this value?"
- **`EntityStateRole`** — the state's contextual identity within its enclosing entity. Answers "what role does this state play in its entity's composite presentation?"

For multi-state entities where multiple `EntityState` instances share the same `EntityStateType` (a thermostat's current vs. target temperatures; a fan's direction vs. preset_mode), the role is what disambiguates them downstream. Every `EntityStateType` has a default `EntityStateRole` with the same name (e.g., `EntityStateType.TEMPERATURE` → `EntityStateRole.TEMPERATURE`), so an `EntityState` saved without an explicit role still has one — automatically.

Two tiers of role member coexist in the same enum:
- **Type-default roles** — one per `EntityStateType`, name-matched. Applied automatically at `EntityState` save time when no explicit role is set. Unchanged integrations get these for free.
- **Domain-prefixed refinements** — `THERMOSTAT_CURRENT_TEMPERATURE`, `FAN_SPEED`, `LIGHT_BRIGHTNESS`, etc. Integrations set these explicitly where the domain calls for it (typically in substate spec lists).

The integration's job is to **declare what each state means** via its role. Presentation order is HI's responsibility, applied via per-EntityType `EntityStateRoleOrdering` instances in `hi.apps.entity.entity_state_role_order`. New EntityTypes or new roles get added to those tables as needed.

See `hi/services/hass/hass_converter.py` (climate / fan / light state-spec lists) for the pattern: each `_StateSpec` may carry an explicit `role` field; the spec → `EntityState` creation passes it through.

## Code Conventions

### File layout and naming
Each integration is a self-contained Django app under `hi/services/<integration_id>/`. Across the existing integrations (`hass/`, `zoneminder/`, `homebox/`) the same role-files appear with parallel naming — use this layout for new integrations so a contributor coming from one integration can find their way around another:

- `integration.py` — `IntegrationGateway` subclass, the registration entry point
- `<prefix>_metadata.py` — module-level `IntegrationMetaData` instance
- `<prefix>_client.py` (and/or `<prefix>_client_factory.py`) — outbound API client + credential validation
- `<prefix>_manager.py` — singleton coordinator (attribute cache, change listeners, health status)
- `<prefix>_converter.py` — wire-format ↔ HI model translation (the bulk of integration logic)
- `<prefix>_sync.py` — `IntegrationConnector` subclass driving entity sync
- `<prefix>_controller.py` — HI control commands → integration service calls
- `<prefix>_mixins.py` — manager-accessor mixin for views/handlers
- `monitors.py` — `PeriodicMonitor` subclass(es) for polling and health probes
- `apps.py`, `urls.py`, `views.py` — standard Django wiring

`<prefix>` is a short integration mnemonic (`hass_`, `zm_`, `hb_`, `pl_`). Keep it consistent across all files within the integration.

ATTRIBUTE_REFERENCE-only integrations (paperless-ngx today) don't need all the role-files above — they have no monitors, no sync, no converter, and no manager singleton (the capability has no live state to own). They still ship `integration.py`, `<prefix>_metadata.py`, `<prefix>_client.py`, plus a `<prefix>_referencer.py` for the `IntegrationAttributeReferencer` subclass and `<prefix>_models.py` (or `_constants.py`) for the wire-format strings.

### Centralize wire-format strings
Every integration centralizes its wire-format strings — domain/endpoint names, attribute keys, device-class names, service names, special-state sentinels — in a single class per integration. The exemplar is `HassApi` in `hi/services/hass/hass_models.py`; ZoneMinder's equivalent is `hi/services/zoneminder/constants.py`. The converter, sync, controller, and service composer all import their wire strings from this single source.

Rationale:
- **Typo prevention** — string literals scattered across files don't cross-check; named constants do
- **Discoverability** — the integration's wire vocabulary lives in one file you can read top-to-bottom
- **Refactor safety** — renaming a wire-side string becomes a mechanical edit, not a grep-and-pray
- **Boundary clarity** — when reading the converter, every string that crosses the wire boundary is obviously a wire string

Do not inline raw wire strings outside this centralization module. If you find yourself writing `'climate'` or `'unavailable'` in a converter, hoist it to the constants class first.

### Default alarm wiring
The model-level factories in `hi.apps.model_helper.HiModelHelper` (`create_movement_sensor`, `create_smoke_sensor`, `create_moisture_sensor`, `create_open_close_sensor`, `create_connectivity_sensor`) accept an `add_default_alarm : bool = False` parameter. When True, the factory also creates the canonical default alarm event definition for that sensor type (using `f'{sensor.name} Alarm'` and the same `integration_key` as the sensor).

Use this for the common case of sharing the sensor's integration_key with its alarm event. If an integration needs a *different* integration_key for the alarm event (e.g., ZoneMinder's separate `MOVEMENT_EVENT_PREFIX`), leave the flag False and call the matching `create_*_event_definition` explicitly with the alternate key.

The default alarm definitions are a starting point — the user can customize entity_state, value, operator, windows, dedupe, and alarm levels through the event-definition edit UI. The integration's role is to provide a reasonable default, not a final policy.

For continuous-value EntityStateTypes (`BATTERY_LEVEL` percentage, future temperature / humidity out-of-range, etc.), `EventClause` carries an `EventClauseOperator` (`EQ` / `LT` / `LTE` / `GT` / `GTE`) so alarms can fire on threshold crossings instead of exact-value matches. The integration uses a dedicated factory like `create_battery_level_event_definition`; the operator and threshold are otherwise transparent.

## Integration Setup Process

### 1. Create Django App
```bash
cd src/hi/services
../../manage.py startapp myintegration
```

### 2. Configure App
- Set fully qualified name in `apps.py`: `name = 'hi.services.myintegration'`
- Add to `INSTALLED_APPS` in `hi/settings/base.py`

### 3. Declare Metadata and Capabilities
Create a module-level `IntegrationMetaData` instance (in `<prefix>_metadata.py`) declaring the integration's `integration_id`, label, logo path, attribute-type enum, and `capabilities` set. The `capabilities` set is what binds the integration to its UI surfaces — CONNECT puts it on the Connectors tab; IMPORT adds it to the Data Import tab; ATTRIBUTE_REFERENCE puts it on the Content Sources tab.

### 4. Create Gateway Class
Implement `IntegrationGateway` (in `integration.py`) with the methods that apply to the declared capabilities:

- `get_metadata()` — return the `IntegrationMetaData` instance. Required.
- `get_connector()` — return an `IntegrationConnector` subclass instance when CONNECT is advertised; default `None`.
- `get_importer()` — return an `IntegrationImporter` subclass instance when IMPORT is advertised; default `None`.
- `get_attribute_referencer()` — return an `IntegrationAttributeReferencer` subclass instance when ATTRIBUTE_REFERENCE is advertised; default `None`.
- `validate_configuration(integration_attributes)` — schema-only validation of the attribute set. Required (no network operations).
- `validate_access(integration_attributes, timeout_secs)` — bounded live probe against the configured credentials. Required (used by the configure flow and by health-check helpers).
- `notify_settings_changed()` — invoked by the framework after the operator saves attributes. Reload your manager / re-init clients here. Default no-op.

The per-capability work (sync, candidate-listing, search) lives on the capability subclass returned from the matching `get_*` method.

### 5. Auto-Discovery
No factory registration is needed. `IntegrationManager.discover_defined_integrations()` walks `INSTALLED_APPS` for `hi.services.*` apps, imports each app's `integration.py`, and registers any `IntegrationGateway` subclass it finds. As long as the app is in `INSTALLED_APPS` and `integration.py` exposes a gateway subclass, it shows up automatically.

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
See "4. Create Gateway Class" above for the full method list. Highlights:

- **`validate_configuration(attrs)`** — schema check only. Returns `IntegrationValidationResult`. Must not perform network operations.
- **`validate_access(attrs, timeout_secs)`** — live probe against the proposed credentials. Returns `ConnectionTestResult`. Must respect the timeout. Used at attribute-save time and before relaunching monitors on Resume.
- **`get_<capability>()`** — return the capability instance the framework consults for capability-specific work. Returning `None` opts the integration out of that capability's UI surfaces even if the capability is in `IntegrationMetaData.capabilities` (defensive disable).

The framework owns the surrounding workflow (configure modal, save lifecycle, sync UI, picker UI). The gateway and its capability instances supply the integration-specific bits.

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
Custom exception hierarchy (`hi/integrations/exceptions.py`):
- `IntegrationError` — base class.
- `IntegrationDisabledError` — operation attempted against a disabled integration.
- `IntegrationAttributeError` — required attribute missing or invalid.
- `IntegrationConnectionError` — upstream unreachable / auth rejected during a live operation.

## Key Base Classes & Modules

### Core Classes
- `hi.integrations.integration_gateway.IntegrationGateway` — per-integration entry point; auto-discovered from each `hi.services.*` app's `integration.py`.
- `hi.integrations.capability_gateway.CapabilityGateway` — shared base of the three per-capability classes; carries `capability`, `get_metadata`, `get_description`, `get_attribute_actions_template_name`.
- `hi.integrations.connector.integration_connector.IntegrationConnector` — CONNECT capability surface (sync, monitor, controller, health).
- `hi.integrations.importer.integration_importer.IntegrationImporter` — IMPORT capability surface (candidate list, run, discard).
- `hi.integrations.referencer.integration_referencer.IntegrationAttributeReferencer` — ATTRIBUTE_REFERENCE capability surface (search).
- `hi.integrations.integration_manager.IntegrationManager` — discovery and lifecycle singleton.
- `hi.apps.common.singleton.Singleton` — singleton base used by `IntegrationManager` and many per-integration managers.

### Example Integrations
- `hi.services.hass/` — Home Assistant (CONNECT).
- `hi.services.zoneminder/` — ZoneMinder (CONNECT).
- `hi.services.frigate/` — Frigate (CONNECT).
- `hi.services.homebox/` — HomeBox (CONNECT + IMPORT).
- `hi.services.paperless/` — paperless-ngx (ATTRIBUTE_REFERENCE-only). Slimmer file layout — no manager singleton, no monitors, no converter — because the capability has no live state to own.

## Related Documentation
- [Service Patterns](service-patterns.md)
- [Gateway Implementation](gateway-implementation.md)
- [Weather Integration](weather-integration.md)
- [Backend Guidelines](../backend/backend-guidelines.md)
