<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

_WORK IN PROGRESS_

# Data Model and Concepts

## Location

- Has an SVG image that defines the visual and coordinate space
- Has zero or more entities
- Entities indirectly associated through a position
- Has zero or more collections
- Collections indirectly associated through a position
- Can have one or more locations, though 1 is most typical

## LocationView

- Defines a bounding box area of the location 
- Defines what is and is not visible
- Defines the view context for sensors and controllers (info, control)
- ViewContext = { information, control }

## LocationItem

- Used as an abstraction/interface for items that can be associated with a Location.
- Helps define a consistent visual represenation for LocationView.
- Initially, Entity and Collection are the two concrete examples fof an LocationItem

## Entity

- A physical or logical object
- Has attributes
- May or may not have a position in the location
- May or may not have sensors and controller
- May or may not have (hidden) state variables.
- May or may not define a coverage Area for its sensors/controllers

## EntityState

- The hidden state of the entity/device that is sensed and/or controlled
- A single entity may have many states

## EntityStateDelegation

- An EntityState of an entity may just be a proxy for another entity's state
- e.g., A thermometer entity with a temperature state is a proxy for an area
- We use the terms 'delegate' and 'principal' for the entities involved in the relation.
- May be one-to-one, one-to-many or many-to-one relationship

## Device (runtime concept, not a DB model)

- An entity with at least one sensor or controller

## Area (runtime concept, not a DB model)

- An wrapper around Entity[type=area]
- Usually defining a physical area that is being sensed and/or controlled
- Defines special visual handling
- Usually defined by SVG path
- If has location/path, should be a (closed, convex) SVG path
- Usually created to be proxied by entities/devices
- Has implicit states that can be related to sensors and controller states
- Clicking will invoke sensors/controllers defined for the area
- Only shows for views it is associated with
- Can be associated with mutliple views

## Sensor

- Provides an observation value of a single entity state variable
- Sensors and their states can only be created through integrations (not user editable)

## Controller

- Provides an action to affect a single entity state variable
- Controllers and their states can only be created through integrations (not user editable)

## Collection

- Defines a logical connection for a group of one or more entities
- Collection of Entity for showing button and accessing list view
- Often used to group non-positional items
- Some entities in a collection may be unpositioned
- Tools, appliances and devices are examples of unpositioned collections
- Collections are tied to a view
- Collection access buttons show at bottom
- If has SVG position, can be overlayed on view
- Inherits from view the view type (control, info)
- Can be associated with mutliple views

## Collection[type=zone]

- Can provide way to group to get single button control of multiple controllers
