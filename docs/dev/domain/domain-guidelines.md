# Domain Guidelines

## Entity-Centric Architecture

All controllable/observable items modeled as entities with states for unified management.

### Core Models
- **Entity**: Central model for all objects (devices, features, software)
- **EntityState**: State variables that are sensed/controlled
- **EntityType**: Categorization and behavior definition
- **Location**: Physical spaces with SVG-based floor plans
- **Sensor/Controller**: Observation and control of entity states

Also see [Data Model](../shared/data-model.md)

## Business Logic Patterns

### Status Display System
Entity status driven by `StatusDisplayManager` which:
- Calculates display states from sensor data
- Implements time-based value decay (Active → Recent → Past → Idle)
- Resolves priority when entities have multiple sensors
- Coordinates with frontend for visual representation

**Key Classes**: `StatusDisplayManager`, `StatusDisplayData`, `SensorResponseManager`

### Multi-Sensor Priority Resolution
Each `LocationView` can set `location_view_type` to determine which `EntityStateType` takes precedence for visual display. See `hi.apps.location.enums.LocationViewType`.

### Weather Integration
Multi-source weather system with:
- **WeatherManager**: Singleton coordinating multiple data sources
- **Priority-based data merging**: Higher priority sources provide primary data
- **Alert integration**: External weather alerts converted to system alarms
- **Source attribution**: Every data point tracked with source and timestamp

See [Weather Integration](../integrations/weather-integration.md) for technical details.

## Event & Alert Architecture

### Event System
- **EventDefinition**: Multi-clause triggers with time windows
- **EventClause**: Individual trigger conditions
- **EventAction**: Automated responses

### Alert System
- **Alert**: System-wide notifications
- **AlertManager**: Singleton queue-based processing
- **AlarmLevel**: Priority classification

## Advanced Patterns

### Entity Delegation
Delegate entities reflect principal entity states using `EntityStateDelegation` model with automatic state synchronization.

### Collection Management
Logical entity groupings with aggregate status calculation from member entities.

### Spatial Calculations
Location-based geometric operations for entity positioning and spatial relationships.

### Security State Logic
Enums with embedded business rules for state transitions and behavior validation.

## Key Modules & Classes

### Managers
- `hi.apps.sensor.sensor_response_manager.SensorResponseManager`
- `hi.apps.alert.alert_manager.AlertManager`
- `hi.apps.weather.weather_manager.WeatherManager`

### Enums
- `hi.apps.location.enums.LocationViewType`
- `hi.apps.common.enums.LabeledEnum` (base class)

### Models
- `hi.apps.entity.models.Entity`
- `hi.apps.entity.models.EntityState`
- `hi.apps.location.models.Location`

## Related Documentation
- [Entity Patterns](entity-patterns.md)
- [Event Alert Systems](event-alert-systems.md)
- [Business Logic](business-logic.md)
- [Data Model](../shared/data-model.md)
