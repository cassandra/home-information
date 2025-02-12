<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

_WORK IN PROGRESS_

# Events, Alarms and Alerts

`SensorResponses` can create events for a user-defined set of rules.

`EventDefinitions` define rules and get triggered off changes in one or more `EntityStates`.

Events may result in zero or more `Alarms` (can also trigger a control action).

An `Alarm` defines which `SecurityLevel` it is applicable to and the importance via the `AlarmLevel`.

If the `Alarm` matches the current system security level, it becomes an `Alert` with the defined `AlarmLevel` and an unique `Alarm` signature.

Alerts are those `Alarms` that we want to get the user's attention for.

An `Alert` may contain one or more `Alarm` instances since there is only ever one `Alert` active for a given alarm signature.
