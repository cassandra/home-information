# Home Assistant (HA) Integration

Ths app uses the `module hi.services.hass` to integrate with the Home Assistant API. It uses the app's general integration framework defined in the module `hi.integrations`.

## Initial Synchronization

When first enabled, it pulls in the state values via the API and does the following:
- Attempts to combined states that are part of the same device.
- Maps each HA state to our model's EntityState.
- Maps each aggregated "device" into our model's EntityState.
- For each state, create our models Sensor and/or Controller depending on the type of state.

After the initial synchronization, our database is populated with an IntegratiohnKey reference back to the HA state. This is done by `hi.services/hass.hass_sync.HassSynchronizer`.

The capabilities of the states/devices from HA are hard-coded in the `hi.services/hass.hass_converter.HassConverter` module.  This mapping is based solely on guessing based on the available information in the API response.  This is imperfect information and a lot of heuristics are used.

## Polling

After the initial synchronization and database population, a background monitor periodically polls that same HA API "states" endpoint. The API response also contains the current status for each state and the app uses that to update the screen and to detect changes in state values for triggering events.

