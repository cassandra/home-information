---
allowed-tools: Bash, Read, Write, Edit, Grep, TodoWrite
description: Find existing icons or create new ones for the standardized icon system
model: claude-3-5-sonnet-20241120
argument-hint: [concept/action]
---

Find or create an icon for "$1":

## Icon Discovery & Creation Process

Find the best existing icon, or create a new one if needed:

1. **Use TodoWrite to plan icon workflow** - Track discovery and creation steps

2. **Search existing icons first** - Always prefer existing icons for consistency:
   - Check AVAILABLE_ICONS in `src/hi/apps/common/templatetags/icons.py`
   - Search icon templates in `src/hi/templates/icons/`
   - Look for semantic matches and universal conventions

3. **Analyze search results** - Determine best match or need for new icon

4. **Recommend existing icon OR create new one** - Based on search results

## Step 1: Search Existing Icons

**Searching for concept**: "$1"

### Current Available Icons
```python
# From src/hi/apps/common/templatetags/icons.py
AVAILABLE_ICONS = {
    'camera', 'cancel', 'check-circle', 'chevron-double-left',
    'chevron-double-right', 'chevron-down', 'chevron-left',
    'chevron-right', 'chevron-up', 'clock', 'close', 'cloud',
    'collection', 'delete', 'edit', 'eye', 'eye-off', 'history',
    'home', 'info-circle', 'layers', 'lightbulb', 'lock',
    'map-pin', 'move', 'path', 'play', 'plug', 'plus',
    'question-circle', 'rocket', 'rotate', 'save', 'settings',
    'shield', 'sync', 'upload', 'video', 'view', 'warning', 'zoom'
}
```

### Semantic Matching Strategy
Look for matches based on:
- **Action synonyms**:
  - Add/Create/New → `plus`
  - Edit/Modify/Change → `edit`
  - Delete/Remove/Trash → `delete`
  - Save/Submit/Confirm → `save` or `check-circle`
  - Cancel/Close/Dismiss → `cancel` or `close`
- **Universal conventions**:
  - Settings/Config → `settings`
  - Help/Support → `question-circle`
  - Alert/Attention → `warning`
  - Success → `check-circle`
  - Error → `close` or `cancel`
- **Navigation patterns**:
  - Back/Previous → `chevron-left`
  - Forward/Next → `chevron-right`
  - Up/Down → `chevron-up`/`chevron-down`

## Step 2: Decision - Use Existing or Create New

### IF good match found:
**Recommendation**: Use existing icon `[icon-name]`

**Usage example**:
```django
{% load icons %}
{% icon "[icon-name]" size="sm" css_class="hi-icon-left" %}
```

**Rationale**: [Why this icon matches the concept]

### IF no good match:
**Recommendation**: Create new icon `[proposed-name]`

**Rationale**: No existing icon adequately represents "$1" because [specific gap]

## Step 3: Create New Icon (if needed)

### Icon Creation Process

**1. Create SVG template file**:
```django
<!-- src/hi/templates/icons/[new-icon-name].html -->
<svg class="{{ class_attr }}" viewBox="0 0 24 24" fill="currentColor" {{ accessibility_attrs }}>
  <path d="[SVG PATH DATA]"/>
</svg>
```

**Requirements**:
- Viewbox MUST be `0 0 24 24`
- Use `fill="currentColor"` for CSS color inheritance
- Simple, optimized paths (single color)
- No transforms, groups, or unnecessary attributes

**2. Register in icon system**:
```python
# src/hi/apps/common/templatetags/icons.py
AVAILABLE_ICONS = {
    # ... existing icons ...
    '[new-icon-name]',  # Add alphabetically
}
```

**3. Test the new icon**:
```bash
# Verify icon renders at all sizes
# Test in template with different colors and sizes
```

## Icon Philosophy

**Key Principles**:
1. **Search first** - Use existing icons when possible for consistency
2. **Don't compromise** - Create new icons when existing ones don't fit
3. **Action-focused** - Icons represent actions/concepts, not specific objects
4. **Semantic naming** - Names should be intuitive and follow conventions

**Examples of when to create new icons**:
- Unique action with no close match (e.g., "calibrate", "sync-bidirectional")
- Domain-specific concept (e.g., "weather-alert", "zone-trigger")
- Better semantic clarity needed (e.g., "expand" vs generic "plus")

## Icon Naming Conventions

- **Actions**: verb or verb-noun (`edit`, `delete`, `save`)
- **Objects**: noun (`home`, `user`, `settings`)
- **Directional**: direction-shape (`chevron-up`, `arrow-left`)
- **Status**: state-shape (`check-circle`, `warning`)
- **Compound**: noun-modifier (`eye-off`, `cloud`)

**Concept to find/create**: "$1"

Begin icon discovery and recommendation now.