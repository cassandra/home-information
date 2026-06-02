# Environment Variables

Adding (or removing, or renaming) an environment variable that the app reads touches **four** files. The cross-source drift check covers three of them automatically; the fourth — the app-side dataclass — relies on code review.

## When to read this

Any time you add a new env-var dependency in app code: new integration credentials, a new feature flag, a new config knob. If the app reads it from `os.environ` (directly or via `EnvironmentSettings`), the ritual below applies.

## Files to update

In recommended order:

1. **`src/hi/environment/server.py`** — `EnvironmentSettings` dataclass. Add a field with type and default. Use `= None` for required vars (absence raises `ImproperlyConfigured`); use an empty/zero/false default for optional.

   Field names are intentionally **not** required to match env-var names — `EnvironmentSettings.SECRET_KEY` reads `DJANGO_SECRET_KEY`, `EnvironmentSettings.REDIS_HOST` reads `HI_REDIS_HOST`, etc. The mapping (prefix-stripping and any explicit rename) is handled inside `EnvironmentSettings`. Pick a field name that reads naturally in app code; the env-var name follows the project's `HI_` / `DJANGO_` convention.

2. **`deploy/env-generate.py`** — two edits in the same file:
   - Add an entry to `SETTING_SECTIONS` under the appropriate section (or add a new section). Include a placeholder value and inline guidance on required vs. optional.
   - Assign a real value for the var, either in the `__init__` overlay (`self._settings_map.update(...)`) for vars with a fixed default, or in `generate_env_file()` for vars filled in by interactive prompts.

   `validate_settings()` fails the run if a var is declared in `SETTING_SECTIONS` but never assigned (or vice versa), so this step is self-checking the moment you run `make env-build`.

3. **`install.sh`** — the heredoc between `<< INSTALL_ENV_FILE_EOF` and `INSTALL_ENV_FILE_EOF` (the unique terminator lets `install.sh --list-env-vars` extract names unambiguously). Add a `KEY=value` line. Use a literal default for fixed-value vars or `${SHELL_VAR}` interpolation for generated values (e.g. `DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}`).

4. **`local.env.example`** at the repo root — **do not hand-edit**. Regenerate from `env-generate.py`:

   ```shell
   python3 deploy/env-generate.py --example > local.env.example
   ```

## Verification

After the four edits, run the drift check:

```shell
make env-drift-check
```

It compares the variable-name sets across `install.sh`, `deploy/env-generate.py`, and `local.env.example` and fails with a labeled diff on mismatch. Also wired into `make check` and the `Check Env-Var Drift` step in `.github/workflows/django-tests.yml`.

## What drift-check does *not* cover

- **`EnvironmentSettings` (server.py)** — field names diverge from env-var names by design, so a structural cross-check would either be lossy or require a rename map per field. Verifying the dataclass change matches the env-var change is a **code-review responsibility**.
- **Other code paths that read `os.environ` directly** — app code should route env access through `EnvironmentSettings`, but nothing enforces it. If a contributor adds an `os.environ.get('HI_SOMETHING_NEW')` call elsewhere, only review catches it.

If a var reaches production without `install.sh` and the example file knowing about it, users won't have it set. The drift check is the first line; code review is the second.
