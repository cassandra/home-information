# Data Model Concepts

## Entity

- A physical or logical object with associated information
- Has zero or more attributes
- May or may not have sensors and controllers (from device integrations)
- May or may not have (hidden) EntityState variables
- May or may not define other entities as delegates of its state

## EntityState

- The hidden state of the entity/device that is sensed and/or controlled
- A single entity may have zero or more states

## EntityStateDelegation

- An EntityState of an entity may just be a proxy for another entity's state
- Example: A thermometer entity with a temperature state is a proxy for an area that is a room
- We use the terms 'delegate' and 'principal' for the entities involved in the relation
- Main use is to have the delegate's visual representation reflect the status of the principal's state
- May be one-to-one, one-to-many or many-to-one relationship

## Location

- Has an SVG image that defines the visual and coordinate space
- Has zero or more entities
- Entities optionally associated with a position
- Has zero or more collections
- Collections optionally associated with a position
- Can define one or more sub-locations

## LocationView

- Associated with a Location
- Can define one or more Location Views for a Location
- Defines the view bounding box area and rotation of the location SVG
- Defines what entities are and are not visible in this view
- Defines the view context for sensors and controllers (info, control)
- ViewContext = { information, control }

## LocationItem

- Used as an abstraction/interface for items that can be associated with a Location
- Helps define a consistent visual representation for LocationView
- Initially, Entity and Collection are the two concrete examples of a LocationItem

## EntityPosition / CollectionPosition

- For entities/collections positioned in a Location and visually appearing as an icon
- Defines the position, scale and rotation of the icon

## EntityPath / CollectionPath

- For entities/collections positioned in a Location and visually appearing as an open or closed path

## Device (runtime concept, not a DB model)

- An entity with at least one sensor or controller

## Sensor

- Provides an observation value of a single entity's state variable
- Sensors and their states can only be created through integrations (not user editable)

## Controller

- Provides an action to affect a single entity state variable
- Controllers and their states can only be created through integrations (not user editable)

## Collection

- Defines a logical connection for a group of one or more entities
- Some entities in a collection may be unpositioned
- Example: tools, appliances and devices are potential examples of unpositioned collections
- Collections may or may not be shown in a Location View (as a path)

## Related Documentation

- Implementation details: [Domain Guidelines](../domain/domain-guidelines.md)
- Entity patterns: [Entity Patterns](../domain/entity-patterns.md)
- Backend models: [Backend Guidelines](../backend/backend-guidelines.md)
- Visual representation: [Frontend Guidelines](../frontend/frontend-guidelines.md)