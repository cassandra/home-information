# Core Model Relationships Diagram

This diagram shows how the system models physical devices, their states, and the sensors/controllers that interact with those states.

```mermaid
erDiagram
    Entity ||--o{ EntityState : "has"
    EntityState ||--o{ Sensor : "observed by"
    EntityState ||--o{ Controller : "controlled by"
    Entity ||--o{ EntityAttribute : "has custom"
    
    Entity {
        bigint id PK
        string name
        string entity_type_str
        string integration_id
        string integration_name
        boolean can_user_delete
        datetime created_datetime
    }
    
    EntityState {
        bigint id PK
        bigint entity_id FK
        string entity_state_type_str
        string name
        text value_range_str
    }
    
    Sensor {
        bigint id PK
        bigint entity_state_id FK
        string name
        string integration_id
        string integration_name
        text value
        datetime last_seen_datetime
    }
    
    Controller {
        bigint id PK
        bigint entity_state_id FK
        string name
        string integration_id
        string integration_name
        string controller_type_str
    }
    
    EntityAttribute {
        bigint id PK
        bigint entity_id FK
        string name
        text value
        string file_value
        string attribute_type_str
        string value_type_str
        datetime created_datetime
    }
```

## Key Relationships

- **Entity → EntityState**: One-to-many. An entity can have multiple internal states (temperature, on/off, etc.)
- **EntityState → Sensor**: One-to-many. Multiple sensors can observe the same state
- **EntityState → Controller**: One-to-many. Multiple controllers can affect the same state
- **Entity → EntityAttribute**: One-to-many. Users can add unlimited custom attributes

## Alternative Formats

- [PlantUML Version](core-model.plantuml) - For use with PlantUML renderers
- [Back to Data Model Overview](../data-model.md)