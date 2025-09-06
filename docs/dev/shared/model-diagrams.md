# Home Information Model Relationships

This document provides visual diagrams of the core data model relationships in Home Information.

## 1. Core Model Relationships (Device & State Architecture)

This diagram shows how the system models physical devices, their states, and the sensors/controllers that interact with those states.

### Mermaid Diagram

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

### PlantUML Alternative

```plantuml
@startuml Core Model Relationships

entity Entity {
    * id : bigint <<PK>>
    --
    * name : string
    * entity_type_str : string
    integration_id : string
    integration_name : string
    can_user_delete : boolean
    created_datetime : datetime
}

entity EntityState {
    * id : bigint <<PK>>
    * entity_id : bigint <<FK>>
    --
    * entity_state_type_str : string
    name : string
    value_range_str : text
}

entity Sensor {
    * id : bigint <<PK>>
    * entity_state_id : bigint <<FK>>
    --
    * name : string
    integration_id : string
    integration_name : string
    value : text
    last_seen_datetime : datetime
}

entity Controller {
    * id : bigint <<PK>>
    * entity_state_id : bigint <<FK>>
    --
    * name : string
    integration_id : string
    integration_name : string
    controller_type_str : string
}

entity EntityAttribute {
    * id : bigint <<PK>>
    * entity_id : bigint <<FK>>
    --
    * name : string
    value : text
    file_value : string
    attribute_type_str : string
    value_type_str : string
}

Entity ||--o{ EntityState : has
EntityState ||--o{ Sensor : "observed by"
EntityState ||--o{ Controller : "controlled by"
Entity ||--o{ EntityAttribute : "has attributes"

@enduml
```

### Key Concepts

- **Entity**: Represents physical items in your home (refrigerator, light switch, thermostat, etc.)
- **EntityState**: The hidden internal state of an entity that can be sensed or controlled (e.g., on/off, temperature, open/closed)
- **Sensor**: Observes and reports the value of an EntityState (e.g., motion sensor, temperature sensor)
- **Controller**: Can change the value of an EntityState (e.g., switch controller, thermostat controller)
- **EntityAttribute**: User-defined custom information about an entity (manuals, notes, warranties, etc.)

## 2. Display Model Relationships (Visual Organization)

This diagram shows how items are positioned and displayed in the visual interface.

### Mermaid Diagram

```mermaid
erDiagram
    Location ||--o{ LocationView : "has views"
    Location ||--o{ EntityPosition : "positions entities"
    Location ||--o{ EntityPath : "paths entities"
    Location ||--o{ CollectionPosition : "positions collections"
    Location ||--o{ CollectionPath : "paths collections"
    Location ||--o{ LocationAttribute : "has custom"
    
    Entity ||--o{ EntityPosition : "positioned by"
    Entity ||--o{ EntityPath : "pathed by"
    Entity ||--o{ EntityView : "appears in"
    Entity }o--o{ Collection : "CollectionEntity"
    
    Collection ||--o{ CollectionPosition : "positioned by"
    Collection ||--o{ CollectionPath : "pathed by"
    Collection ||--o{ CollectionView : "appears in"
    Collection ||--o{ CollectionEntity : "contains"
    
    LocationView ||--o{ EntityView : "shows entities"
    LocationView ||--o{ CollectionView : "shows collections"
    
    Location {
        bigint id PK
        string name
        string svg_fragment_filename
        string svg_view_box_str
        integer order_id
    }
    
    LocationView {
        bigint id PK
        bigint location_id FK
        string name
        string location_view_type_str
        string svg_transform_str
        integer order_id
    }
    
    Entity {
        bigint id PK
        string name
        string entity_type_str
    }
    
    EntityPosition {
        bigint id PK
        bigint entity_id FK
        bigint location_id FK
        decimal svg_x
        decimal svg_y
        decimal svg_scale
        decimal svg_rotate
    }
    
    EntityPath {
        bigint id PK
        bigint entity_id FK
        bigint location_id FK
        text svg_path
    }
    
    EntityView {
        bigint id PK
        bigint entity_id FK
        bigint location_view_id FK
    }
    
    Collection {
        bigint id PK
        string name
        string collection_type_str
        string collection_display_str
    }
    
    CollectionEntity {
        bigint id PK
        bigint collection_id FK
        bigint entity_id FK
    }
```

### PlantUML Alternative

```plantuml
@startuml Display Model Relationships

entity Location {
    * id : bigint <<PK>>
    --
    * name : string
    * svg_fragment_filename : string
    svg_view_box_str : string
    order_id : integer
}

entity LocationView {
    * id : bigint <<PK>>
    * location_id : bigint <<FK>>
    --
    * name : string
    location_view_type_str : string
    svg_transform_str : string
    order_id : integer
}

entity Entity {
    * id : bigint <<PK>>
    --
    * name : string
    * entity_type_str : string
}

entity Collection {
    * id : bigint <<PK>>
    --
    * name : string
    collection_type_str : string
    collection_display_str : string
    order_id : integer
}

entity EntityPosition {
    * id : bigint <<PK>>
    * entity_id : bigint <<FK>>
    * location_id : bigint <<FK>>
    --
    svg_x : decimal
    svg_y : decimal
    svg_scale : decimal
    svg_rotate : decimal
}

entity EntityPath {
    * id : bigint <<PK>>
    * entity_id : bigint <<FK>>
    * location_id : bigint <<FK>>
    --
    svg_path : text
}

entity EntityView {
    * id : bigint <<PK>>
    * entity_id : bigint <<FK>>
    * location_view_id : bigint <<FK>>
}

entity CollectionEntity {
    * id : bigint <<PK>>
    * collection_id : bigint <<FK>>
    * entity_id : bigint <<FK>>
}

entity CollectionView {
    * id : bigint <<PK>>
    * collection_id : bigint <<FK>>
    * location_view_id : bigint <<FK>>
}

Location ||--o{ LocationView : "has views"
Location ||--o{ EntityPosition : "positions"
Location ||--o{ EntityPath : "paths"

Entity ||--o{ EntityPosition : "positioned at"
Entity ||--o{ EntityPath : "drawn as path"
Entity ||--o{ EntityView : "visible in"
Entity }o--o{ Collection : "grouped in"

Collection ||--o{ CollectionEntity : contains
Collection ||--o{ CollectionView : "visible in"

LocationView ||--o{ EntityView : "displays"
LocationView ||--o{ CollectionView : "displays"

@enduml
```

### Key Concepts

- **Location**: A physical space (house, floor, property) with an SVG background
- **LocationView**: A specific view/zoom into a Location (e.g., "Kitchen View", "Security View")
- **Entity**: Items that can be displayed (same as in Core Model)
- **Collection**: Named groups of entities (e.g., "Power Tools", "Small Appliances")
- **EntityPosition**: Defines where an entity appears as an icon (x, y, scale, rotation)
- **EntityPath**: Defines an entity as an SVG path (for linear items like pipes, wires)
- **EntityView**: Links an entity to specific LocationViews where it should appear
- **CollectionEntity**: Many-to-many relationship between Collections and Entities
- **CollectionView**: Links a collection to specific LocationViews where it should appear

## Understanding the Architecture

### Separation of Concerns

The architecture clearly separates:
1. **Physical/Logical Model** (Core): What things are and how they behave
2. **Visual/Display Model**: Where and how things appear visually

This separation allows:
- The same entity to appear in multiple views
- Different visual representations (icon vs. path) for the same entity
- Collections to organize entities independently of their physical location
- Views to show subsets of items relevant to specific concerns (security, HVAC, etc.)

### Data Portability

All relationships are stored in standard SQLite foreign key relationships, making the data:
- Queryable with standard SQL
- Exportable to other formats
- Understandable without the application
- Migratable to other systems if needed