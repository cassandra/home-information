# Commenting Guidelines

These guidelines govern the **content and semantics** of code comments and docstrings across Python, JavaScript, CSS, and Django templates. Syntactic rules (which comment delimiter to use, formatting, etc.) live in [Coding Standards](coding-standards.md).

The audience for these guidelines is the cleanup pass that runs before a PR opens, but the same rules apply any time a comment is being judged on its merits.

## The Reader Frame

Every comment is judged from the perspective of a **future developer reading the code cold**, with no knowledge of:
- The conversation, ticket, or PR that produced the change.
- What the code used to do.
- The bug that motivated the current shape.
- Which session, phase, or work stream the change belonged to.

If a comment only makes sense with that missing context, it does not belong in the code. That context belongs in the commit message or PR description.

## The Default Is No Comment

Start from zero. A comment must earn its place. Before writing one, try in order:

1. **Rename.** If a better variable, method, or class name would convey the same information, rename instead of commenting.
2. **Restructure.** If extracting a helper, splitting a function, or reorganizing the code would make the intent obvious, do that instead.
3. **Delete.** If the comment restates what the code already says, do not write it.

Only when none of the above work does a comment become the right tool.

## When a Comment Earns Its Place

A comment is justified when a future cold reader would be misled, confused, or surprised by the code without it. The legitimate categories are narrow:

- **Non-obvious *why* behind a design decision.** Why this approach was chosen over an alternative that would seem equally reasonable on inspection.
- **Hidden constraints or invariants.** Assumptions the code depends on that are not visible at the call site.
- **External system quirks and workarounds.** Library bugs, API rate limits, protocol oddities, third-party behavior the reader cannot infer from the code.
- **Cross-file coordination.** A value here must match a value there; changing one without the other breaks something.
- **Surprising behavior.** The code does something correct but counterintuitive that a reader would otherwise "fix" and regress.
- **Genuinely complex domain or algorithmic logic.** Business rules or math that cannot be made obvious through naming and structure alone.
- **Bug-fix invariants that prevent regression.** Only when the comment documents the *invariant the code now maintains*, not the story of the bug.

A useful comment in any of these categories is short, points at the non-obvious thing, and would still make sense to a reader who has never heard of the original problem.

### Brevity Even for Keeps

Earning a place is the first bar; earning the current *length* is the second. Many genuinely useful comments are wordier than the substance warrants — extra qualifications, restated context, parenthetical examples that no longer pull their weight. When keeping a comment, ask whether the same substance reads cleaner in half the words. Bias toward shorter even when keeping.

### WHY vs WHAT — The One-Liner Override Test

When a method overrides a public contract (a base-class method, a `requires_X() -> bool`-style configuration hook), a one-line docstring is keep-worthy when it explains *why* the method returns the specific value it does — domain knowledge the signature cannot carry. Example:

```python
def requires_api_key(self) -> bool:
    """NWS does not require an API key."""
    return False
```

The docstring tells the reader *why* (the NWS API's actual policy), not just *what* (returns False). Without it, the reader infers the policy by absence — workable but worse than knowing.

The keep applies when:
- The override implements a public contract where the choice of return value carries domain meaning.
- The docstring names that meaning in terms the signature cannot.

The keep does **not** apply when:
- A higher-level docstring (class, module) already establishes the WHY. For example, a `ProfileManager` class that documents its robust-loading strategy makes per-method `"""Create X with error tracking..."""` docstrings redundant — the WHY lives once at the class level.
- The docstring restates only the WHAT (`"""Return False."""`, `"""Returns the integration's id."""`).
- The override is mechanical, with no domain knowledge to convey.

### Disambiguating Adjacent Similar Patterns

When two visually similar code patterns appear in the same file but serve different purposes, comments that disambiguate which case each instance is are keep-worthy — even when each individual comment looks like a section label. Example:

```python
if entity_id not in lookup:
    continue  # Skip comment-only entries

# ... different method ...

if entity_id not in lookup:
    continue  # Skip if entity creation failed upstream
```

Both comments label an `if X not in lookup: continue` line, which alone reads as the "section labels restating well-named code" anti-pattern. But each comment names a *different reason* for the same code shape (skip-by-design vs skip-due-to-error), and that disambiguation is the load-bearing information.

The keep applies when removing the comment would leave a reader uncertain which of two valid behaviors the code is implementing.

## When a Comment Does Not Belong

Remove comments that fall into any of these categories. These are the patterns observed most often.

### Restating what the code already conveys
- Comments that paraphrase a well-named method, variable, or class.
- Docstrings that restate the method name and parameter types in prose.
- Inline comments that describe *what* the next line does when the line itself says it.
- Comments on conditionals, loops, or assignments that add no information beyond the expression.
- **Section labels and step markers** (`# Get the X`, `# Remove the Y`, `# Stage 1: …`, `# Discover Z by scanning W`) when the next 2-3 lines have well-named variables performing exactly what the label claims. Factory-method docstrings like `"""Create a successful result."""` for `success()` are the same anti-pattern. This rule applies to languages with structural grouping (Python, JavaScript). For CSS and other languages without native grouping, see [Per-Language Notes](#per-language-notes).

### Information a reader can trivially discover
- Argument types and return types already in the signature.
- Class purpose already obvious from the class name and module location.
- Default values, exception types, or call sites that are one search away.

### Archeology and historical narrative
- "This used to do X, now does Y."
- "Previously we Z, but we changed it because…"
- "This fixes the bug where…" (the fix is the code; the bug story is the commit).
- "Mirrors how X does it" / "Same pattern as Y."
- **Parallel-integration archeology**: "Like the paperless simulator…" / "Same shape as the homebox integration…" / "(same lifecycle as `_fault_mode` on the base class)" / "Same approach HomeBox uses for Z." Recurs heavily when a new integration is written by mirroring a sister integration — the parallel is real *for the author*, but the cold reader only needs the current file's contract, not a pointer to chase the sister file. Strip the cross-reference; keep any standalone substance the surrounding sentence carries.
- "Without this, Z happens" / "We use A rather than B because of bug C."

These narrate the path to the current code. The reader only needs the current code.

### Forward-looking placeholders and hedges
The mirror of archeology — comments that look forward to changes that may or may not happen. They add no information for the cold reader (any code can be changed later; that's the default).
- `(as of yet)` / `(for now)` / `today` / `currently` / `in the future` / `eventually`.
- "The proper fix is X; deferred because Y" (aspirational alternative designs).
- "Each entry is a small dict so additional metadata can be added later without changing the API surface" (extension-point speculation).
- "deferred to the broader X redesign" (deferral language).

When the substance is genuinely useful — for example, "this is a workaround, not the canonical pattern" — keep that signal but drop the speculation about what the canonical pattern would be.

### Session, PR, or work-stream context
- "Phase 3 / Phase 4" references.
- "Added in this PR / removed in this PR."
- Comments explaining why other code was deleted, moved, or refactored.
- Anything that reads like a debugging conversation, status update, or progress note.
- **Issue number references** (`(Issue #281)`, `(#263)`, `Per issue #N`, `Issue #283 sync-check probe`). GitHub holds the historical record; the docstring is the future contract. The issue number is workflow metadata, not code documentation.

These have a half-life measured in days. They become noise immediately after merge.

### Re-explaining the same architectural fact in every touched location
When a change spans many files, there is a temptation to drop a paragraph about the new architecture into every file that participates. Resist this. The architectural explanation belongs in **one** place — usually the module, class, or docstring that owns the concept. Other call sites should be self-explanatory through naming, not re-explanation.

### Comments that describe the caller, not the callee
A method's comment should describe what the method does and the contract it offers, not how a specific caller happens to use it. Caller-specific context lives at the call site (or, better, in the call-site code itself).

Common sub-patterns to delete on sight:
- **Caller-name lists**: `"Used by DELETE SAFE on disable and by sync-time refresh removals"`, `"Used by Disable-ALL and as a backstop"`. The list rots whenever a caller is renamed, added, or removed.
- **"for use from X" tails**: `"Async variant of get_entry for use from async monitor / converter paths"` — the `async def` already says "from async contexts"; the specific caller-class enumeration adds nothing.
- **Sibling cross-references**: `"Parallel to get_connector() and get_importer()"` once a reader has scanned the three methods, the parallelism is self-evident. The reference adds maintenance burden without information.

### UI element name-dropping in backend code
Backend comments and docstrings that quote specific UI element labels rot the moment the UI changes — and UI copy changes far more often than the backend code that supports it. Examples seen in practice:
- Button labels: `"REFINE button"`, `"APPLY"`, `"NOT NOW"`, `"GO BACK"`.
- Tile / section / badge names: `"'Detached' tile"`, `"From X UI badge"`, `"Content Sources header"`.
- Modal section references: `"the collapsed Details section"`, `"the sidebar Cameras list"`.

When the backend genuinely needs to mention UI behavior, describe it functionally: "the operator-visible summary", "the details view", "the dismiss action" — not by the current UI label. View-layer files are the hot spot for this pattern; treat them with extra scrutiny.

### Implementation details that belong somewhere else
- Details about a collaborator's internals showing up at a usage point.
- Details about a caller's flow showing up inside the callee.
- Cross-cutting design rationale buried in a leaf function instead of stated once at the owning abstraction.

### Maintenance liabilities
- File paths, line numbers, class names, or method names quoted in comments. These rot the moment the referenced thing moves or renames.
- Counts, lists, or enumerations that must be kept in sync with code elsewhere.
- "See also" pointers to specific lines.

If a cross-reference is genuinely load-bearing, prefer a stable signal: a shared constant, an explicit import, or a name match enforced by the code itself.

**Carve-out: external API documentation URLs are keep-worthy.** A URL to the definitive contract documentation for an external system the code depends on (e.g., `https://api.weather.gov/openapi`, `https://open-meteo.com/en/docs`, an RFC, WMO/METAR specs) is a bookmark to the source of truth — not a maintenance liability. If the URL rots, the implementation that depends on the underlying API has a bigger problem than the comment.

The distinction from the bullets above: internal code references (file paths, method names) rot when *internal* code is renamed; external API URLs rot only when the external system itself changes, which is precisely the event the URL is helping the reader trace.

### Commented-out code
Delete it. Version control retains the history. Commented blocks create ambiguity about whether the code should be active and tend to drift out of compilability.

### Speculative TODOs
Vague intentions ("TODO: clean this up later", "TODO: maybe refactor") have a very high bar. If the work is worth doing, it is worth an issue. A TODO is acceptable only when it is specific, actionable, and there is a real reason it cannot be done now.

## Archeology Smells — Phrasings That Signal a Delete

Treat the following phrasings as strong signals that the comment is narrating history rather than helping a future reader. When found, default to deletion unless the substance is clearly load-bearing:

- "Used to…" / "Previously…" / "We changed this because…"
- "Now does…" / "Now we…" / "We no longer…"
- "This fixes…" / "Fixes the bug where…"
- "Mirrors…" / "Same pattern as…" / "Like in X…"
- "Without this, …" / "Otherwise …" (when describing the bug it would cause, not the invariant it maintains)
- "Phase N" / "Step N of the migration" / "TODO from issue #…"
- "Added for X" / "Per the discussion in…" / "Per request from…"
- "(Issue #N)" / "(#N)" / "Per issue #N" — workflow-tracker references; same delete signal.

## Forward-Looking Smells — Phrasings That Signal a Delete

Parallel to the archeology smells but pointing the other direction. Default to deletion unless the substance is clearly load-bearing:

- "(as of yet)" / "(for now)" / "today" / "currently" / "in the future" / "eventually"
- "The proper fix is…" / "deferred because…" / "deferred to the broader X redesign"
- "future call sites that…" / "callers may eventually need…" / "extension point for…"
- "Future:" / "TODO: maybe…" / vague placeholders for not-yet-real features.

## Docstrings

The same content rules apply to docstrings as to inline comments. In particular:

- A docstring that restates the method name and parameter types should be removed.
- Public API methods may warrant docstrings even when the name is clear, when they document contract, side effects, or invariants a caller cannot see.
- Private and internal methods rarely need docstrings; their names and bodies should suffice.
- A long docstring that recounts the design history of the class is archeology. The part of it that describes the current contract may be worth keeping; the rest should go.

## The Cleanup Pass — Decision Rules

When reviewing comments on a branch or in a directory, decide per comment:

### Keep
- Falls into one of the earned-place categories above.
- Would be missed by a cold reader if removed.
- Is concise and focused on the non-obvious *why*.

### Rewrite
- The substance is load-bearing but the framing is archeological (narrates the change rather than stating the invariant). Rewrite to state the invariant directly, without reference to what came before.
- The comment is correct but verbose or scattered across multiple lines that could be one.
- The comment mixes a useful note with debugging narrative — keep the note, drop the narrative.
- **Preserve bracing/warning framing.** When a comment's job is "your default mental model is wrong, brace yourself" (e.g., `"""Counterintuitive: Django's ready() does not behave the way the docs suggest..."""`), the warning role itself is load-bearing. Don't dissolve the bracing into distributed facts — keep the explicit "be surprised here" signal.

### Remove
- Restates the code, the name, or the type.
- Narrates history, the session, or the work stream.
- Re-explains an architectural fact already stated elsewhere.
- Is a stale maintenance liability (file:line refs, name quotes, counts).
- Is commented-out code or a vague TODO.
- **Flatten module-vs-class docstring duplication.** When a module docstring and a class docstring in the same file repeat the same content, keep what's unique at each level. The module docstring is the right home for cross-class wire formats and inter-class contracts; the class docstring is the right home for the class's own scope and invariants.

### Partial Removal — Strip and Salvage

The remove-on-sight patterns in "When a Comment Does Not Belong" are shortcuts. The fuller rule for any comment that *contains* an offending element (issue number, "Phase N" prefix, "(as of yet)" hedge, caller-name parenthetical, "Mirrors X" framing, UI label outside the per-language carve-outs, etc.):

1. **Strip the offending substring** — prefix, parenthetical, sentence, or fragment.
2. **Examine the residue.** Is it load-bearing on its own? Does it state a contract, invariant, design rationale, or non-obvious WHY?
3. **Act on what remains:**
   - Substantive residue → **REWRITE** to a tight standalone form.
   - Trivial residue (the offending part was carrying most of the weight) → **REMOVE** the whole comment.

Examples:
- `"Phase 5: CONFIRM IMPORT on the preview modal posts to the run view."` → strip `"Phase 5: "`, residue describes a real workflow → REWRITE (keep the workflow description).
- `"Issue #283 sync-check probe rides on the connector."` → strip `"Issue #283 "`, residue is informational about the connector → REWRITE.
- `"Per the discussion in #281, we removed this branch."` → strip the work-stream reference, residue (`"we removed this branch"`) is itself archeology → REMOVE the whole comment.

The "if it has X, remove" shortcut is fine when the X-bearing comments are almost always entirely noise. Use the strip-and-salvage check whenever the comment shows any sign of independent substance — better to keep a substantive sentence with the work-stream prefix shaved off than to drop both.

### When Unsure — Keep and Flag

Removing a *bad* comment is free. Removing a *load-bearing* comment is expensive and easy to miss in review. When in doubt:

- Keep the comment.
- Flag it for human review with the specific reason for uncertainty.

A cleanup pass that errs toward keeping ambiguous comments is correct. A cleanup pass that silently deletes load-bearing context is a regression.

**Multi-rule conflict counts as uncertainty.** When a single comment hits two rules that point in opposite directions — for example, Comment-vs-Code Drift says "fix it" while a remove-on-sight pattern says "remove it" — that is, by definition, uncertainty about the right action. KEEP and FLAG. Don't pick a side silently.

### Typo Fixes — Comments and Docstrings Only

Obvious typos in comments and docstrings are fixable by the cleanup pass. Treat them like ASCII normalization: a syntactic concern applied during cleanup as a courtesy when the agent is already touching the file.

In scope:
- Misspellings (`Attrribute` → `Attribute`, `recieve` → `receive`).
- Duplicate words (`the the`, `placement placement`, `is is`).
- Obvious transpositions (`teh` → `the`).
- Missing capitalization on sentence starts.

Out of scope:
- **Typos in code identifiers** (variable, method, class, attribute names) — those are renaming refactors with much broader implications. Even if a typo appears in a public class name, the cleanup pass does not rename it.
- **Typos in user-facing strings** (HTML body text, button labels, `help_text`, error messages, log messages) — those follow the user-facing-strings hard constraint and have their own review process.

If the typo's intent is ambiguous — the misspelling might be a deliberate word choice, or the apparent "typo" might be a domain-specific term — KEEP and FLAG rather than fix.

### Authoring Boundary — Don't Insert Missing Comments

The cleanup pass operates on *existing* comments. It does not insert comments where there are none — even when a file would clearly benefit from one (a missing Context block in a template, a missing docstring on a public method, a missing invariant note next to a non-obvious guard).

Identifying these gaps is valuable but is a separate authoring task with different inputs (design intent, contract knowledge) than what the cleanup pass operates on. Surface the gap as a flagged observation if useful; do not silently fill it.

**Rewriting is editing, not authoring.** When an existing comment has substance worth preserving but framing or structure that needs to change, rewriting it — including significant restructuring, stripping offending prefixes or parentheticals, reshaping a multi-paragraph block into a single sentence, or salvaging the substance and discarding everything around it — is part of normal cleanup work. The boundary is about *inserting* where there was nothing, not about how aggressively to *reshape* what was there.

### Substance-at-Wrong-Location — Stay Myopic

A comment may describe semantics owned by another module — for example, an enum docstring that explains the implementation's behavior rather than just naming the choice. The cleanup pass is myopic by design: it does **not** cross files to verify whether the substance exists at its canonical location.

The rule:
- If the comment looks load-bearing reading just this file, **KEEP and FLAG**.
- If it is obviously redundant given the code in this file, REMOVE.
- The cleanup pass does not perform cross-file substance reconciliation.

If a removed (or flagged) comment turns out to have been the only documentation of a piece of substance, that is a pre-existing codebase gap that the cleanup *surfaced*, not one it created. The remediation is a separate piece of work (move the substance to its canonical location), not a reason to retain a misplaced comment.

### Comment-vs-Code Drift — Fix If Local, Flag If Cross-File

When a comment references a name (API hook, method, constant, file path) that no longer matches the code, OR when two comments in the same file disagree, the cleanup pass acts based on where the corrective evidence lives:

- **If the same file makes the canonical name obvious** — the actual code in this file uses the canonical name, or another comment in agreement with the code does — **fix** the drifted comment to match.
- **If determining the canonical name requires reading other files, library docs, or guessing**, **flag** the inconsistency. Picking the wrong side silently is a worse outcome than flagging.

The agent does not go off on cross-file explorations to resolve a drift. The same myopia principle as Substance-at-Wrong-Location: the evidence available in the file under review is the only evidence the cleanup pass uses.

In both cases — fix or flag — leaving the inconsistency in place is the wrong outcome.

## Per-Language Notes

Some languages and formats lack the structural features that Python and JavaScript provide (type signatures, class/function nesting, etc.). When a general rule depends on a missing feature, the rule shifts. The exceptions below are not free passes — they apply only when the cited structural gap is real.

### Templates (Django)

Django templates have no type signatures, which shifts how some general rules apply.

**Context contract blocks are keep-worthy.** A top-of-file block listing the template's context variables and their types — for example:

```django
{% comment %}
Context:
  health_status     : HealthStatus (optional)
  integration_data  : IntegrationData (required)
{% endcomment %}
```

— is keep-worthy in a way that a Python function's parameter-listing docstring is not. Python has type hints; templates have nothing equivalent. The Context block is the closest thing to a signature, and serves the same purpose: telling a caller (or reader) what to pass in. Preserve these blocks even when they look long, but strip the surrounding caller-naming (which caller passes what is the caller's concern, not the template's).

**UI labels that the template itself renders are not pattern #4 violations.** The "UI element name-dropping in backend code" rule targets backend comments that quote UI labels living elsewhere — those references rot when the UI changes. A template that *renders* a button labeled `UPDATE` and refers to "UPDATE" in its top comment is a different case: the label and the comment about it live in the same file and change together. The cleanup pass can leave these in place. Backend code that references the same `UPDATE` button by name is still pattern #4 — the rule applies to cross-file references, not local self-reference.

**Section labels are keep-worthy for navigation.** Templates have nominal grouping constructs (`{% block %}`, `{% if %}`, `{% for %}`, etc.) but they are not visually distinct without IDE-level Django template syntax awareness. Banner-style and short single-line section labels (`{# ----- Search form ----- #}`, `{# Cancel + Add row #}`, `{# Sticky header #}`) earn their place as navigation aids in dense templates. The bar for removing a template section label is high: only remove when the label adds *zero* information and the next block's content is completely self-explanatory.

**`<!-- -->` HTML comments in templates — flag, don't convert.** Django templates should use `{# ... #}` (single-line) or `{% comment %} ... {% endcomment %}` (multi-line) for developer comments, because `<!-- -->` comments render in the browser. When the cleanup pass encounters an `<!-- -->` comment inside a Django template, it should **FLAG** the syntactic mismatch but **not convert** it. A future intentional use — for example, a comment deliberately rendered in the browser HTML as documentation for downstream consumers — would be silently broken by automatic conversion. The conversion is a coding-standards decision that requires human verification of intent.

### CSS

CSS has no nesting, no module system, and no function/class structure. Section labels are the only grouping construct the language offers.

**Section labels — banner-style or single-line — are keep-worthy.** Both visually-prominent dividers (`/* ==== SECRET FIELD STYLING ==== */`) and short single-line labels above clusters of related rules (`/* Action Bar */`, `/* Drag and Drop Styling */`) serve as the file's only navigation aid. The pattern "section labels restating well-named code" applies far less strictly to CSS than to languages with structural grouping. The bar for removing a CSS section label is high: only remove it when the label adds *zero* information and the next rule's class names are completely self-explanatory.

**UI labels in CSS comments follow the same rule as templates.** When a rule styles a button labeled `UPDATE` and the comment mentions `UPDATE`, the label and the rule live and change together. Pattern #4 does not apply within the file that *implements* the UI element.

**Inline trailing comments on property values are useful and should be kept** when they explain a magic value (`min-height: 44px; /* Touch-friendly minimum */`), a behavioral choice (`flex-shrink: 0; /* Don't shrink button */`), or a browser-compat reason (`border-width: 0.5px; /* Sharper on retina */`). They are pure WHY at the most precise location.

### Django Views

Django view classes (`HiModalView`, `View`, `ConfigPageView` subclasses, etc.) sit at the boundary between backend logic and rendered UI. The same UI-label exception that applies to templates and CSS applies here: the view is the file that *defines* the rendering for the UI surface it owns.

**UI labels that the view directly renders, dispatches on, or names in its modal/page contract are keep-worthy.** Examples that earned their place across the codebase:

- Button labels rendered by the view's template: `UPDATE`, `CONNECT`, `Sync / Not now`, `Refresh and Retain` / `Refresh and Remove`.
- Mode names dispatched by the view's POST: `DELETE`, `DELETE SAFE`, `DELETE ALL`, `SAFE` / `ALL`.
- CTAs and modal flows the view assembles: `'Place N new items' CTA`, "the manage page", "the sync result modal".

The reasoning matches templates and CSS: the label and the comment about it live in the same file (or in the view's own contract with its template) and change together. Stripping these labels in favor of generic phrasing ("preserve/hard-delete pair", "confirm/cancel actions") loses precision without gaining stability — when the button label changes, the view's logic has to change too, and the comment will surface as part of that change.

Pattern #4 still applies when a backend non-view file references UI labels owned elsewhere (e.g., a manager class mentioning the "Detached" tile). The view-layer carve-out is for the view itself.

## What Is Out of Scope for the Cleanup Pass

The cleanup pass is about **content and semantics**. The following are syntactic concerns that belong to general code review and to [Coding Standards](coding-standards.md):

- Which comment delimiter to use (`#` vs docstring, `//` vs JSDoc, `{# #}` vs `<!-- -->`).
- Comment formatting, indentation, and line length.
- Where in a file comments are placed.

The cleanup pass should not rewrite a comment purely for syntactic reasons. If a comment's *content* earns its place, leave its form alone.

### User-Facing Strings — Hard Constraint

The cleanup pass does **not** touch strings whose audience is anyone other than a future developer reading the code. These are functional UI / operator copy with a different audience and a different review process:

- Django field metadata: `help_text`, `verbose_name`, `verbose_name_plural`, `choices` labels.
- Error messages displayed to operators (raised exceptions intended to surface in UI, form errors).
- Log messages intended for operators or for downstream log analysis.
- Any string that is rendered in a UI, sent in an email, written to a user-visible report, etc.

These strings may contain content that would otherwise match remove-on-sight patterns (specific UI references, integration names, example values). The audience justifies them; leave them alone. If in doubt about whether a string is user-facing, leave it.

### ASCII Normalization

The cleanup pass also normalizes non-ASCII characters in comments and docstrings to ASCII equivalents per [Coding Standards](coding-standards.md). This is a syntactic concern but is applied during the cleanup pass for convenience. Common substitutions: `—` / `–` → `--`, `→` → `->`, `…` → `...`, `×` → `x`, `°` → drop or restructure.
