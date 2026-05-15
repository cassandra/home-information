# Profile Management

## Overview

Profiles are predefined configurations that create a fully populated Home Information setup — Locations with background SVGs, LocationViews with zoom/pan settings, Entities with positions, and Collections. They provide the first-time user experience when a user selects a home type (Single Story, Two Story, Apartment) on the welcome page.

## Profile Structure

### JSON Format

Profile data is stored as JSON files in `src/hi/apps/profiles/assets/profiles/`. Each file defines a complete set of Locations, Entities, and Collections.

The field constants for the JSON structure are defined in `src/hi/apps/profiles/constants.py`. The JSON structure follows this hierarchy:

```
profile
  ├── locations[]
  │     ├── svg_template_name  → references a background template
  │     └── views[]            → LocationViews with zoom/pan/rotate settings
  ├── entities[]
  │     ├── positions[]        → placement on specific Locations
  │     ├── paths[]            → SVG paths on specific Locations
  │     └── visible_in_views[] → which LocationViews show this entity
  └── collections[]
        ├── entities[]         → entity names in this collection
        ├── positions[]        → collection positioning
        └── visible_in_views[] → which LocationViews show this collection
```

### SVG Template References

Each Location in the profile JSON has a `svg_template_name` field that references a Django template in the backgrounds directory (see [SVG Background System](svg-background-system.md) for template details). At profile load time, the template is rendered, processed, and written to MEDIA_ROOT. The viewBox is extracted from the rendered SVG — it is not stored in the JSON.

### Profile Types

Profile types are defined in `src/hi/apps/profiles/enums.py` (`ProfileType` enum). Each type maps to a JSON file via the `json_filename()` method.

## Profile Loading

Profile loading is handled by `ProfileManager` in `src/hi/apps/profiles/profile_manager.py`. The load process:

1. Load the JSON file for the selected profile type
2. Render SVG background templates and write to MEDIA_ROOT (`_render_svg_templates`)
3. Create Location and LocationView database objects
4. Create Entity objects with positions and paths
5. Create Collection objects with entity assignments and positioning
6. Set up entity and collection visibility in LocationViews

The `_render_svg_templates` method uses `LocationManager.render_svg_template_to_media()` which renders the Django template, runs it through the SVG processing pipeline, and writes the fragment to MEDIA_ROOT. The rendered filename and extracted viewBox are stored as temporary fields on the location data dict for use during Location creation.

### Error Handling

`ProfileManager` has both strict (`load_profile`) and robust (`load_profile_robust`) loading modes. The robust mode tracks statistics via `ProfileLoadingStats` and continues past individual failures, useful for development and testing.

## Creating a New Profile

### Workflow

The goal is to arrive at a fully configured database state that can be captured as a new profile. How you populate the data is flexible — the snapshot tool captures whatever is in the database.

The typical workflow:

1. **Start with an empty database** — delete existing data or use a fresh database.
2. **Choose "Start with an empty layout"** on the welcome page. This puts you in edit mode with a blank Location.
3. **Create the background SVG** for the first Location using the background editor. Use the palette to draw walls, floors, doors, windows, etc.
4. **Add more Locations** if needed (e.g., second floor, attic, basement). Each gets its own background SVG.
5. **Set up LocationViews** for each Location — configure zoom, pan, and rotation for different viewing perspectives (e.g., "Interior", "Exterior", "Kitchen").
6. **Add Entities** — create all the entities that should be part of this profile. Position them on the appropriate Locations and assign them to LocationViews.
7. **Add Collections** — group entities into collections, position collections, assign visibility.
8. **Generate the snapshot** using the Profile Snapshot Generator (see below). Write to `/tmp` first for review.
9. **Register the profile type** — add a new value to the `ProfileType` enum if this is a completely new profile type.
10. **Commit** — once verified, generate with `output_to_tmp=False` to write the real profile files, then commit.

## Updating an Existing Profile

### Workflow

When updating an existing profile, you want to start from the current profile state, make modifications, and re-capture.

1. **Start with an empty database** — delete existing data or use a fresh database.
2. **Choose the profile to update** on the welcome page (e.g., "Single Story"). This loads the existing profile with all its Locations, Entities, and Collections.
3. **Modify as needed** — edit backgrounds, reposition entities, add/remove items, adjust views. The existing profile gives you the starting point so you only change what needs changing.
4. **Generate the snapshot** — this captures the modified state. The SVG template reconciliation will match unchanged backgrounds to their existing templates and create new template files for any backgrounds you edited.
5. **Review** — check the JSON and any new SVG template files in `/tmp`.
6. **Commit** — generate with `output_to_tmp=False` and commit.

## Profile Snapshot Generator

The snapshot generator captures the current database state into a profile JSON file. It lives at `src/hi/apps/profiles/tests/devtools/profile_snapshot_generator.py`.

### Usage

From the Django shell:
```python
from hi.apps.profiles.tests.devtools.profile_snapshot_generator import ProfileSnapshotGenerator
from hi.apps.profiles.enums import ProfileType

generator = ProfileSnapshotGenerator()

# Write to /tmp for review (safe — doesn't modify real profile files)
output_path = generator.generate_snapshot(ProfileType.SINGLE_STORY, output_to_tmp=True)

# Write directly to the real profile location (overwrites existing)
output_path = generator.generate_snapshot(ProfileType.SINGLE_STORY, output_to_tmp=False)
```

### SVG Template Reconciliation

When generating a snapshot, the generator must determine which background template each Location corresponds to. The Location model only stores a MEDIA_ROOT filename — there's no record of the originating template.

The generator handles this by comparing the Location's SVG fragment content against all rendered background templates:

- **Match found**: The JSON references the matched template name.
- **No match**: The SVG has been customized. The generator creates a new template file by wrapping the fragment in an `<svg>` element with the viewBox and saving it to the backgrounds template directory (or `/tmp` if `output_to_tmp=True`).

This is implemented in `_reconcile_svg_templates()` in the snapshot generator.

### Review Checklist

After generating a snapshot:

1. **Review the JSON** — check the output file for correctness. Verify `svg_template_name` fields reference valid templates.
2. **Review new SVG templates** — if the generator created new template files, open them in a browser to verify they render correctly.
3. **Test the round-trip** — load the generated profile on a fresh database to verify it produces the expected result.

## Key Files

| File | Purpose |
|------|---------|
| `src/hi/apps/profiles/profile_manager.py` | Profile loading logic |
| `src/hi/apps/profiles/constants.py` | JSON field name constants |
| `src/hi/apps/profiles/enums.py` | ProfileType enum |
| `src/hi/apps/profiles/assets/profiles/*.json` | Profile JSON data files |
| `src/hi/apps/profiles/tests/devtools/profile_snapshot_generator.py` | Snapshot generation tool |
| `src/hi/apps/profiles/templates/profiles/svg/backgrounds/` | Background SVG templates |
| `src/hi/apps/location/location_manager.py` | SVG template rendering to MEDIA_ROOT |
| `src/hi/apps/common/svg_utils.py` | SVG processing pipeline |
