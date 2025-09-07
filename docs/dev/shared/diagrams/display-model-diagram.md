# Display Model Relationships Diagram

This diagram shows how items are positioned and displayed in the visual interface.

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

## Key Relationships

- **Location → LocationView**: One-to-many. Multiple views/perspectives of the same space
- **Location → Position/Path**: One-to-many. Items positioned within the location
- **Entity → Position/Path**: One-to-many. Same item can appear in multiple locations
- **Entity ↔ Collection**: Many-to-many through CollectionEntity join table
- **LocationView → EntityView/CollectionView**: Controls what appears in each view

## Visual Organization Concepts

This model enables:
- Same entity appearing in multiple locations or views
- Different visual representations (icon vs. path)
- Collections independent of physical positioning
- View-specific filtering and organization

## Alternative Formats

- [PlantUML Version](display-model.plantuml) - For use with PlantUML renderers
- [Back to Data Model Overview](../data-model.md)