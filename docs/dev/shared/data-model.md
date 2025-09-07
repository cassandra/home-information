# Data Model

## Overview

Home Information uses a carefully designed data model that separates concerns between:
- **Core Models**: What things are and how they behave (entities, states, sensors, controllers)
- **Display Models**: Where and how things appear visually (locations, views, positioning)

This separation allows the same physical item to appear in multiple views with different representations while maintaining a single source of truth for its data and behavior.

## Core Concepts

### Entity

The fundamental building block representing a physical or logical object in your home.

**Key Characteristics:**
- Represents items like appliances, fixtures, devices, areas, or systems
- Has a name and entity type (determines visual appearance)
- May have associated attributes (user-defined information)
- May have states that can be sensed or controlled
- Can be created by users or through integrations

**Examples:** Refrigerator, light switch, HVAC system, pool area, security zone

### EntityState

The hidden internal state of an entity that can be monitored or controlled.

**Key Characteristics:**
- Not directly visible to users (hence "hidden")
- Represents changeable properties of an entity
- Can have zero or more sensors observing it
- Can have zero or more controllers affecting it
- Defined by integrations, not user-editable

**Examples:** 
- Temperature state of a thermostat
- On/off state of a light switch
- Open/closed state of a door sensor

### Sensor

Observes and reports the current value of an EntityState.

**Key Characteristics:**
- Provides observation values for exactly one EntityState
- Created only through integrations (not user-editable)
- Has integration details for communication
- Maintains last seen timestamp for freshness

**Examples:**
- Motion sensor reporting movement
- Temperature sensor reporting degrees
- Door sensor reporting open/closed status

### Controller

Provides actions to change an EntityState.

**Key Characteristics:**
- Controls exactly one EntityState
- Created only through integrations (not user-editable)
- Defines the type of control available
- Has integration details for communication

**Examples:**
- Light switch controller (on/off)
- Thermostat controller (set temperature)
- Lock controller (lock/unlock)

### EntityAttribute

User-defined information associated with an entity.

**Key Characteristics:**
- Custom information added by users
- Can be text, files, numbers, or other value types
- Includes documents like manuals, warranties, notes
- Fully editable by users
- Supports file uploads

**Examples:**
- Product manual PDF
- Warranty expiration date
- Service history notes
- Model and serial numbers

## Visual Organization Concepts

### Location

Represents a physical space with a visual background.

**Key Characteristics:**
- Has an SVG image defining the visual space
- Serves as container for positioned entities
- Can represent floors, rooms, property, or areas
- Defines the coordinate system for positioning
- Can have multiple views into the same space

**Examples:** Main floor, basement, backyard, entire property

### LocationView

A specific perspective or zoom into a Location.

**Key Characteristics:**
- Always associated with exactly one Location
- Defines visible area through SVG transforms
- Controls which entities are visible
- Can focus on specific areas or concerns
- Supports different view contexts (information vs. control)

**Examples:**
- "Kitchen View" - zoomed to kitchen area
- "Security View" - showing all security devices
- "HVAC View" - displaying heating/cooling systems

### Collection

A logical grouping of entities independent of physical location.

**Key Characteristics:**
- Groups related entities regardless of position
- Can display as list or grid view
- Some entities may not have physical positions
- Collections themselves can optionally appear on location views

**Examples:**
- "Power Tools" - various tools stored in garage
- "Small Appliances" - kitchen gadgets
- "Maintenance Items" - filters, batteries, supplies

## Positioning and Display Models

### EntityPosition / CollectionPosition

Defines icon-based positioning for items in a Location.

**Key Characteristics:**
- Specifies x,y coordinates in SVG space
- Includes scale and rotation parameters
- Most common display method
- One entity can have multiple positions (different locations)

### EntityPath / CollectionPath

Defines path-based display for items in a Location.

**Key Characteristics:**
- Uses SVG path notation
- Suitable for linear features or areas
- Can represent open or closed paths
- Useful for pipes, wires, zones, property boundaries

**Examples:**
- Underground utility lines
- Fence boundaries
- Security zones
- Irrigation paths

### EntityView / CollectionView

Links items to specific LocationViews where they should appear.

**Key Characteristics:**
- Many-to-many relationship
- Controls visibility per view
- Allows same entity in multiple views
- Enables view-specific organization

## Advanced Concepts

### EntityStateDelegation

Defines proxy relationships between entity states.

**Key Characteristics:**
- One entity's state can represent another's
- Supports one-to-one, one-to-many, many-to-one relationships
- Enables visual state changes on delegate entities
- Uses principal/delegate terminology

**Examples:**
- Temperature sensor in room acts as proxy for room's temperature
- Motion sensor state affects visual display of an area
- Multiple sensors aggregate to represent overall zone status

### LocationItem (Interface)

Abstract concept for items that can be associated with a Location.

**Key Characteristics:**
- Provides consistent interface for visual representation
- Currently implemented by Entity and Collection
- Enables uniform handling in views
- Defines common display behaviors

### Device (Runtime Concept)

Not a database model but a useful conceptual grouping.

**Definition:** An entity that has at least one sensor or controller
**Purpose:** Distinguishes active (integrated) items from passive (information-only) items

## Model Relationships

The complete relationship structure is visualized in two diagrams:

### Core Model Relationships
Shows Entity, EntityState, Sensor, Controller, and EntityAttribute relationships.
- [View Mermaid Diagram](diagrams/core-model-diagram.md) (renders in GitHub)
- [PlantUML Source](diagrams/core-model.plantuml)

### Display Model Relationships
Shows Location, LocationView, positioning, and collection relationships.
- [View Mermaid Diagram](diagrams/display-model-diagram.md) (renders in GitHub)
- [PlantUML Source](diagrams/display-model.plantuml)

## Data Portability

All relationships are stored in standard SQLite foreign key relationships, making the data:
- Queryable with standard SQL
- Exportable to other formats
- Understandable without the application
- Migratable to other systems if needed

## Related Documentation

- **Implementation Details**: [Domain Guidelines](../domain/domain-guidelines.md)
- **Entity Patterns**: [Entity Patterns](../domain/entity-patterns.md)
- **Backend Models**: [Backend Guidelines](../backend/backend-guidelines.md)
- **Visual Representation**: [Frontend Guidelines](../frontend/frontend-guidelines.md)
- **Architecture Overview**: [Architecture Overview](architecture-overview.md)