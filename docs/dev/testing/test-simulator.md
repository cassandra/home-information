# Simulator Testing

There is a simulator app that lives inside the same Django code structure, but represents a completely different running application, albeit, sharing some code with the main app.  The simulator is used to simulate integrations for testing the Home Informaton app. It's a separate Django application with its own database, located in the `hi/simulator` directory. There's a special `simulator.py` command alongside the main `manage.py` script.

## Simulator Setup (Testing Integration)

### Initialize Simulator Database

```bash
cd $PROJ_DIR/src

# Simulator uses same commands as main manage.py
./simulator.py migrate
./simulator.py hi_createsuperuser
./simulator.py hi_creategroups

# Run simulator server
./simulator.py runserver
```

**Access simulator**: Visit [http://127.0.0.1:7411](http://127.0.0.1:7411)

The `simulator.py` script acts just like the main `manage.py` script with all the same commands (runserver, migrate, etc.), but manages the simulator application instead.

## Purpose and architecture

The simulator stands in for the upstream services that real
integrations talk to. It mounts service-shaped HTTP endpoints under
`http://127.0.0.1:7411/services/<service>/...` that respond with the
same shapes the real services would, sourced from a curated
**SimProfile**. Switching profiles changes what the integrations see
on their next Import or Refresh, which is the lever for exercising
sync behavior end-to-end.

The simulator is a separate Django app with its own database (see the
top of this file). It does not talk to HI directly — HI's
integration configurations point at the simulator's URLs and treat
it as the upstream service.

Per-integration simulator code lives at
`src/hi/simulator/services/<service>/`:

- `src/hi/simulator/services/hass/` — HA `/api/states` and related
  endpoints.
- `src/hi/simulator/services/zoneminder/` — ZM monitor and event
  endpoints, plus an MJPEG-shaped stream endpoint.
- `src/hi/simulator/services/homebox/` — HomeBox `/api/v1/...`
  inventory endpoints.

Each service folder typically contains `simulator.py` (the
service-specific subclass of the `Simulator` base), `sim_models.py`
(the field shapes the seed command writes), and `api/` (the HTTP
views that produce the upstream-shaped responses).

## Configuring HI integrations to point at the simulator

Run the simulator on `127.0.0.1:7411` (the default) and configure HI
on its own port (typically `8411`). In HI's integration Configure
forms, paste the corresponding URL:

| Integration  | HI Configure field | URL to enter                                              |
|--------------|--------------------|-----------------------------------------------------------|
| Home Assistant | Server URL       | `http://127.0.0.1:7411/services/hass`                     |
| HomeBox      | API URL            | `http://127.0.0.1:7411/services/homebox/api`              |
| ZoneMinder   | API URL            | `http://127.0.0.1:7411/services/zoneminder/api`           |
| ZoneMinder   | Portal URL         | `http://127.0.0.1:7411/services/zoneminder/`              |

For the credentials fields, any non-empty values work — the
simulator does not validate passwords or tokens. Anything sensible
(e.g., `simuser` / `simpass`) is fine.

For the Home Assistant integration, set the **Allowed Item Types**
to a narrow list that matches what your active SimProfile produces;
otherwise the import will pull only the items your profile actually
has.

## Profile seeding (`seed_sim_profiles`)

The `seed_sim_profiles` management command populates the simulator
database with a curated suite of SimProfiles for manual testing. It
is the source of every realistic upstream payload the simulator
serves; without it the simulator is empty.

```bash
cd $PROJ_DIR/src
./simulator.py seed_sim_profiles
```

Re-running the command is a no-op when a profile already exists.
Pass `--reset` to delete and recreate the matching profile (and
its entities) before recreating.

After seeding, switch the simulator's active profile from the web UI
at [http://127.0.0.1:7411](http://127.0.0.1:7411).

### Profiles

Five profiles are seeded, each designed to exercise a specific
scenario. The authoritative list and per-profile contents live in
the command's own docstring at
`src/hi/simulator/management/commands/seed_sim_profiles.py`; the
table below is a short orientation.

| Profile            | What it exercises |
|--------------------|-------------------|
| `empty`            | Zero items in every integration. Tests the initial-import-with-nothing path and the refresh-against-emptied-upstream path. |
| `baseline`         | Realistic small-install set: mixed HA device types, a handful of HomeBox items, a few ZM monitors. The "before" state for delta tests. |
| `baseline-changed` | Same shape as `baseline` with deltas in every integration. Pairing it with `baseline` exercises the five sync-result categories — created, updated, reconnected, detached, removed — in a single flip. |
| `hass-zoo`         | One HA entity of every supported type. Visual / grouping coverage for the HASS converter; HomeBox and ZM stay empty. |
| `volume`           | Large counts (30 HA, 25 HomeBox, 10 ZM monitors). Stresses modal list overflow scrolling and dispatcher group sizing. |

### Operator workflow for full-category sync-result coverage

The `baseline ↔ baseline-changed` pair is the canonical workflow for
exercising every sync-result category. The command's docstring
spells out the exact step-by-step (which entities to add custom
attributes to, what each Refresh shows in the result modal); read
it directly when running the workflow rather than trying to keep a
copy of the steps here in sync.

## Dependencies

### Python 3.11
- **macOS**: Download from python.org
- **Ubuntu**: Use deadsnakes PPA

### Redis
- **macOS**: `brew install redis`
- **Ubuntu**: Manual installation from source

### Docker (Optional)
- **macOS**: Docker Desktop
- **Ubuntu**: docker.io package

## Related Documentation
- Workflow guidelines: [Workflow Guidelines](../workflow/workflow-guidelines.md)
- Release process: [Release Process](../workflow/release-process.md)
- Dependencies: [Dependencies](../../dev/Dependencies.md)
