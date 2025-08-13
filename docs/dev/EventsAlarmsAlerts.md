<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Events, Alarms and Alerts

`SensorResponses` can create events for a user-defined set of rules.

`EventDefinitions` define rules and get triggered off changes in one or more `EntityStates`.

Events may result in zero or more `Alarms` (can also trigger a control action).

An `Alarm` defines which `SecurityLevel` it is applicable to and the importance via the `AlarmLevel`.

If the `Alarm` matches the current system security level, it becomes an `Alert` with the defined `AlarmLevel` and an unique `Alarm` signature.

Alerts are those `Alarms` that we want to get the user's attention for.

An `Alert` may contain one or more `Alarm` instances since there is only ever one `Alert` active for a given alarm signature.

A WeatherAlert can also create an alarm and (system) alert.

## Alarm Signature System

Each alarm has a unique signature format: `{alarm_source}.{alarm_type}.{alarm_level}`

- `alarm_source`: The source of the alarm (e.g., EVENT, WEATHER)
- `alarm_type`: The specific type of alarm within that source
- `alarm_level`: The severity level (INFO, WARNING, CRITICAL)

Multiple alarms with the same signature are grouped into a single Alert, preventing duplicate notifications for the same condition.

## Alert Lifecycle Management

### Creation
- Alarms are added to the system and become Alerts if they match the current SecurityLevel
- Each Alert starts with a `start_datetime` and calculates an `end_datetime` based on `alarm_lifetime_secs`

### Grouping
- When a new alarm arrives with the same signature as an existing Alert, it gets added to that Alert
- The Alert's `end_datetime` is extended based on the new alarm's lifetime
- Alert titles show the count when multiple alarms are grouped: "Critical: Motion Detected (3)"

### Acknowledgment
- Users can acknowledge Alerts to stop active notifications
- Acknowledged Alerts remain visible but don't trigger new notifications

### Expiration and Removal
- Alerts are automatically removed when they expire (`end_datetime` passes)
- Acknowledged Alerts are also automatically removed during periodic maintenance
- Maximum of 50 Alerts are kept in memory at any time

## Audio Signal Integration

Each `AlarmLevel` maps to specific audio files for user notification:

- `INFO`: Configurable info audio file (e.g., chime)
- `WARNING`: Configurable warning audio file (e.g., buzzer)
- `CRITICAL`: Configurable critical audio file (e.g., alarm siren)

Audio signals can be customized per installation and may eventually support alarm-specific sounds (e.g., tornado siren for weather alerts).

## Notification Integration

- When an Alert is first created (single alarm), it automatically generates a notification item
- Notifications can be sent via email or other configured channels
- Notifications are only sent for the first alarm in an Alert to prevent spam
- Notifications respect the system's SecurityLevel settings

## Security Level Filtering

- Each Alarm specifies which `SecurityLevel` it applies to
- Only Alarms matching the current system SecurityLevel become active Alerts
- This allows different alarm behaviors for different security contexts (e.g., home vs. away)

## Priority System

Alerts are prioritized based on `AlarmLevel` priority values:

- `CRITICAL`: 1000 (highest priority)
- `WARNING`: 100
- `INFO`: 10
- `NONE`: 0 (not alert-worthy, rejected)

Priority determines:
- Order of display in alert lists
- Which audio signal plays when multiple alerts are active
- Auto-switching behavior for console displays

## Weather Alert Integration

Weather alerts from external sources (e.g., NWS) can be converted to system Alarms based on:

- **Alert Type Filtering**: Not all weather alerts should create alarms (e.g., informational vs. actionable)
- **Severity Mapping**: Weather alert severity levels map to system `AlarmLevel`
- **Appropriate Lifetimes**: Weather alerts have different duration characteristics than sensor-based events
- **Security Level Application**: Weather alarms typically apply to all security levels
