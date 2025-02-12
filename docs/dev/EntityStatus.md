<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

_WORK IN PROGRESS_

# Entity Status Display

All entity state variables are indirectly observed through a sensor, and all sensor values come from an integration, usually by polling an external service, device, file, etc.  Integrations are responsible for normalizing sensor values and encapsulating them in a SensorResponse instance.  The SensorResponseManager is the module that will receive these responses from integrations and will provide the latest status values and value histories to the various views.  The SensorResponseManager also detects changes of status values and feed those into the alerting subsystem.

## Status (Visual) Display [Location View]

A given Entity (SVG icon or SVG path) can alter its screen appearance based on the value of sensor readings for its underlying state variables.  Mapping sensor responses to SVG appearance is the responsibility of the Status Display Helpers using StatusDisplayData. There are a few ways this can be done, depending on the underlying entity state type that the sensor is observing.

1. It can take the (normalized) sensor value directly and add it as a CSS class name to the displayed SVG file.  This allows CSS rules to adjust the visual display for any well-known sensor values (hardcoded in CSS rules).
2. For well known sensor values, there can also be predefined/hard-coded alternative SVG icons.
3. It can map a sensor value into a color scheme that is used for the SVG fill, stroke and opacity attributes.  This is predominantly used for area entitiess (closed SVG paths) to visually show activity in an area.  This can be from a continuous variable sensor value (e.g., temperature) or a function of the sensor value history (see Value Decaying section below).

## Value Decaying

For some entity state types (and sensors), we not only want to display the current sensor value, but also represent the recent past values.  For example, when motion is detected in an area, we want to highlight that, but after the motion event is over, we will want to visually show that it was "active" in the recent past.  e.g., Active motion is shown as red, but over time decays to oranges then yellows when the motion is over.

## Multiple Sensors

The visual representation provided is always for an Entity, but an entity can have multiple states and multiple sensors.  Trying to reason about and support visual distinctions across the cross-product of values for multiple sensors would be more complicated than anyone could understand as well and complicated to implement.  Thus, the design decision is that at most one entity state will determine the visual view of the SVG.

To achieve this, we define a default priority of the entity states and the highest priority state will be used.  However, a single static priority order is too limiting for many use cases.  Thus, we need to be able to support different priorties for different purposes.  For example, we may want a climate control view and a security view of a defined area.  In the former, we want the temperature sensor value to dictate the visual display, while in the latter, the motion sensor should have its value impacting the area's visual display.

To allow some user control over the visuals from sensor values, each LocationView instance can have its location_view_type set to one of the enum values whicih will determine which EntityStateType value will take precedence for status displays. See hi.apps.location.enums.LocationViewType.

## Client-Server Interactions to Refresh State Display

The Javascript polling.js module polls the server for the latest sensor values for all entity states.  The server fetches the latest sensor values via StatusDataHelper, computes their visual display using StatusDisplayData and then returns a generalized JSON dicttionary that maps css class names to a set of attribute name-value pairs to update.   The original rendered HTML from the Django templates will make sure the proper entities have the proper class names and attribute values for this to work.

The polling.js module tries to be general and only deal with finding class names and updating attribute name-value pairs. This works for the SVG <g> aND <path> tags. However, there a few special case patterns needs for SELECT tags for controllers and <div> elements for the non-SVG display cases (e.g., viewing entity status in a Collection View or in a sttaus modal).

