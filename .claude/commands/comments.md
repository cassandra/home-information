# /comments Command

Focused comment cleanup pass. Reviews, rewrites, or removes code comments and docstrings according to `docs/dev/shared/commenting-guidelines.md`. Operates in three modes: a pre-PR pass over the current branch's changes, a directory-scoped sweep, or a glob-pattern sweep.

## Usage

```
/comments                       Branch mode (default) — review comments touched on the current branch
/comments <path>                Directory mode — recursively sweep all in-scope files under <path>
/comments <pattern>             Glob mode — review only files matching the glob pattern
/comments --base <ref>          Branch mode with explicit diff base override
```

The mode is chosen by detecting glob metacharacters (`*`, `?`, `[`, `]`) in the argument. An argument containing any of these is treated as a glob pattern; an argument with none is treated as a directory path.

## Examples

```
/comments
/comments --base origin/staging
/comments src/hi/apps/entity                       # recurse the directory
/comments src/hi/apps/weather/*.py                 # top-level Python files only
/comments src/hi/apps/weather/weather_sources/     # recurse this subdir
/comments src/hi/integrations/templates/           # recurse this whole template tree
/comments src/hi/apps/weather/**/*.py              # recursive glob (Python files only, any depth)
```

## What It Does

Delegates the actual review to the **comment-reviewer** sub-agent, which loads only the commenting guidelines and the in-scope files (narrow context by design). This command owns:

- Argument parsing and mode selection.
- Diff base detection for branch mode.
- Invoking the sub-agent with the resolved scope.
- Surfacing the sub-agent's report to the user.

The sub-agent applies edits directly. The user reviews changes via `git diff` and commits separately. This command does **not** commit.

## Modes

### Branch mode (default)

Reviews comments **touched by the current branch only**. Specifically:

- Comment lines the diff added or modified.
- Existing comment lines that fall inside diff hunks (their context shifted).

Pre-existing comments in unmodified parts of touched files are **not** reviewed.

### Directory mode

Reviews **all** in-scope comments in **all** in-scope files under `<path>`, recursively. Intended for one-module-at-a-time sweeps of existing code. Discouraged for whole-repo runs — keep scope small enough that the resulting diff is reviewable as a normal refactor PR.

### Glob mode

Reviews **only the files matching the glob pattern**. Use this when you want to scope to a slice that a single directory path can't express: top-level files only (`weather/*.py`), a specific file type across siblings (`weather/sources/*.py`), or a deeper selective walk (`weather/**/*.py`).

Typical use: a directory has shared base files at the top level and feature-specific subdirectories beneath. The natural review cadence is "shared first, then each feature":

```
/comments src/hi/apps/weather/*.py                 # base/shared files
/comments src/hi/apps/weather/weather_sources/     # each feature subdir, one at a time
/comments src/hi/apps/weather/templates/           # templates separately
```

The pattern is shell-style glob with `*`, `?`, `[`, `]`, and `**` (recursive). The pattern is matched against the filesystem; the agent then applies the standard exclusion list (tests, migrations, generated, vendored, `.min.*`).

## Process Flow

### Phase 1: Resolve scope

**Branch mode:**

1. Determine the diff base:
   - If `--base <ref>` provided, use it.
   - Else if upstream tracking branch is set (`git rev-parse --abbrev-ref @{u}` succeeds), use `git merge-base HEAD @{u}`.
   - Else fall back to `git merge-base HEAD origin/staging`.
2. Print the resolved base so the user can spot and override misdetection. Example: `Diff base: origin/staging (merge-base 1a6a7048)`.
3. Confirm the working tree is clean before proceeding — refuse if there are uncommitted changes, since the agent's edits would mingle with the user's in-progress work.

**Directory mode:**

1. Verify `<path>` exists and is inside the repo.
2. Confirm the working tree is clean.

**Glob mode:**

1. Detect the glob mode by the presence of glob metacharacters (`*`, `?`, `[`, `]`) in the argument.
2. Expand the pattern against the filesystem (e.g., via Bash `ls` or the Glob tool) to produce a concrete file list.
3. Verify the resolved list is non-empty and that every resolved file is inside the repo.
4. Apply the standard exclusion list (tests, migrations, generated, vendored, `.min.*`); report any files dropped by exclusion.
5. Confirm the working tree is clean.

### Phase 2: Invoke the sub-agent

Launch the **comment-reviewer** sub-agent with a prompt containing:

- The mode (branch, directory, or glob).
- For branch mode: the resolved diff base and HEAD.
- For directory mode: the absolute path; the agent recursively walks.
- For glob mode: the resolved list of absolute file paths; the agent reviews exactly those files (no recursion beyond what the glob expressed).
- The hard exclusion list: migrations, generated files, vendored code, `.min.*`, **test files of any kind** (under any `tests/` directory or matching `test_*.py` / `*_test.py` / `*.test.js`).
- The in-scope file types: `.py`, `.js`, `.css`, Django templates (`.html` under template directories).

### Phase 3: Surface the report

Display the sub-agent's structured report verbatim. The two sections the user should pay close attention to:

- **Flagged for human review** — comments the agent kept-but-was-uncertain-about, plus any rare cases where it removed something it wasn't fully sure about. These need eyes.
- **Borderline cases worth discussing** — 3-5 most-instructive decisions. Over time, patterns here become updates to `commenting-guidelines.md` (handled as a normal edit conversation, not automated).

After the report, remind the user:

```
Review with: git diff
Commit when satisfied.
```

## Quality Gates

The command will STOP if:

- The working tree has uncommitted changes (would conflate agent edits with user work).
- Branch mode is invoked outside a git repo.
- Directory mode is invoked with a path that doesn't exist or sits outside the repo.
- Glob mode is invoked with a pattern that resolves to zero files, or to files outside the repo.
- The diff base cannot be resolved (no upstream, no `origin/staging`).

## Sub-Agent Coordination

### Agent: comment-reviewer

- **Role**: Apply the commenting guidelines to the in-scope comments — keep, rewrite, remove, or flag.
- **Context loaded**: `docs/dev/shared/commenting-guidelines.md` and the in-scope files only. No broader docs.
- **Output**: Structured report (see expected output below).
- **Authority**: May edit files directly. May not commit. May not modify non-comment code.

## Expected Output

```
Resolving scope...
Diff base: origin/staging (merge-base 1a6a7048)
Working tree clean. Proceeding.

Launching comment-reviewer (branch mode)...

[sub-agent report]

## Files reviewed: 14
## Files modified: 9

## Counts
- Kept:    23
- Rewrote: 6
- Removed: 41
- Flagged: 4

## Flagged for human review

src/hi/apps/entity/managers.py:88 — kept — Cross-file constant reference;
   could not verify the named constant in the other file.
src/hi/services/frigate/api.py:142 — kept — Docstring on what looks like
   a public API method; uncertain whether external callers depend on it.
src/hi/apps/control/views.py:201 — removed-uncertain — Said "Mirrors
   pattern in alarm_views"; checked alarm_views and the pattern is no
   longer there, but flagging in case the comment was load-bearing for
   navigation.
src/hi/templates/panes/entity.html:14 — kept — HTML comment (<!-- -->)
   that should be {# #}; left content alone, flagging form per
   coding-standards rule.

## Borderline cases worth discussing

1. src/hi/apps/weather/usno.py:59 — kept — Documents API rate limits and
   polling intervals. Fits the "external service config rationale" pattern
   but was at the edge of being just configuration metadata.

2. src/hi/services/frigate/integration.py:88 — removed — "Without this,
   the reload spams the log" felt borderline. Rewrote the surrounding
   code's intent into the variable name instead; comment became redundant.

3. ...

Review with: git diff
Commit when satisfied.
```

## Error Handling

- **Dirty working tree**: Abort. Ask the user to commit or stash before running.
- **Diff base cannot be resolved**: Abort. Suggest `/comments --base origin/staging` (or whatever the project base is).
- **Sub-agent reports an internal error**: Surface the error and abort without committing partial state. Edits already on disk remain visible in `git diff` for the user to inspect or discard.

## Important Notes

- **Test files are excluded.** Until the test directory organization is revised, the agent does not touch test files in either mode.
- **The agent does not commit.** This is deliberate. The user reviews via `git diff`.
- **Borderline cases drive guideline improvements.** Use the Borderline section to spot patterns and refine `docs/dev/shared/commenting-guidelines.md` over time.
- **Flagged items are the safety mechanism.** Treat the Flagged section as a small to-do list before opening the PR.

## Limitations

- Reviews comments and docstrings only — does not touch code structure, naming, or formatting.
- Branch mode only reviews comments inside changed hunks; legacy comments in untouched parts of touched files are left alone (by design).
- Directory mode performs better on smaller scopes. Avoid running it on whole apps or the repo root in a single invocation.
- The agent cannot verify cross-file claims (e.g., "matches constant X in file Y") — these consistently end up in the Flagged section.

## Related

- Guidelines (the rulebook): `docs/dev/shared/commenting-guidelines.md`
- Coding standards (syntactic): `docs/dev/shared/coding-standards.md`
- Sub-agent definition: `.claude/agents/comment-reviewer.md`
