# Frontend Guidelines

## Django Template Guidelines

### Core Principles

1. **Minimal Business Logic**: Keep business logic out of templates. Complex loops, conditionals, and data processing belong in views or custom template tags/filters. No ORM operations in tempate tags.

2. **View Preparation**: Views should prepare all data that templates need. Templates should primarily display pre-processed data.

3. **Simple Conditionals**: Use only simple `{% if %}` statements for display logic. Avoid complex nested loops or data manipulation.

4. **Custom Template Tags**: Create custom template tags or filters for reusable template logic instead of embedding it directly.

5. **Data Structure**: Structure context data in views to match template needs rather than making templates adapt to raw data.

6. **Load Directives**: All template `load` directives should appear at the top of the file, or just below the `extends` directive if there is one.


**Good examples:**
```python
# In view
context = {
    'alert': alert,
    'alert_has_visual_content': bool(alert.get_first_image_url()),
    'alert_first_image': alert.get_first_image_url(),
}
```

**Avoid:**
```django
<!-- Complex business logic in template -->
{% for alarm in alert.alarm_list %}
  {% for source_details in alarm.source_details_list %}
    {% if source_details.image_url %}
      <!-- Complex nested logic -->
    {% endif %}
  {% endfor %}
{% endfor %}
```

## Template Naming Conventions

- `pages/` - For full HTML pages
- `modals/` - For HTML modals
- `panes/` - For all other HTML page fragments
- `email/` - For email templates
- `svg/` - For SVG files

For app modules with separate "edit" views, use the same structure in an `edit/` subdirectory.

## Template Contexts

We have another code factoring guideline for views that says once the template context begins to contain a large number of entries, we should encapsulate them in a dataclass and use typed attributes instead of strings. For example, instead of a template contents like this:
```
return {
            'entity': entity,
            'sensor': sensor,
            'current_history': current_history,
            'timeline_groups': timeline_groups,
            'prev_history': prev_history,
            'next_history': next_history,
            'sensor_history_items': mock_history_items,
        }
```
We would define a dataclass like EntitySensorHistoryData and delegate a helper class to build it, then be left with:
```
sensor_history_data = some_helper.build_sensor_history_data( some, args )
return {
            'sensor_history_data': sensor_history_data,
        }
```

## Client-Server Namespace Sharing

- We do not use magic strings as they need to be referenced in multiple places.
- We gathered strings that need to be shared between client and server in `src/hi/constants.py:DIVID`:
- This `DIVID` dict are injected into the template context automatically. 
- On the Javascript side, we gather all these same ids in a single place at the beginning of the main.css.
- All other Javascript modules use the Hi.<NAME> namespacing to refer to these.
- All DOM ids and classes that are shared between client and server must adhere to our `DIVID` pattern

In this way, there is at most two places these ids are used as strings, and both client and server can referenced more safely.

## JavaScript Standards

**Minimize Javascript**: We should strive for the minimal amount of new Javascript. There are many special-purpose needs in the app that require Javascript, but we should never do in Javascfript what we can achieve on the backend.

**Server Side Rendering**: We strive to generate all HTML content on the server side.

**Prefer Asynchronous Updates**: The application closely mimics a single page application that always tries to avoid full page loads. Dynamic updates are preferred over full pages, especially for frequently use view changes. 

**Javascript in Templates**:  We should never put Javascript in templates, or otherwise have inline `<script>` blocks.  There are rare exceptions for very focused, specialized manipulations, but all Javascript should be put in a file in the `src/hi/static/js` directory.

### Core Technologies
- jQuery 3.7 for DOM manipulation
- Bootstrap 4 for UI components
- Custom SVG manipulation library

**Django Pipeline**: We use the Django pipeline library for injecting minimized, cache-busting Javascript (and CSS) into pages. Any new files must be defined in `src/hi/settings/base.py`.


### Asynchronous/AJAX Updates

By default, we use the `src/hi/static/js/antinode.js` module for performing DOM async DOM manipulations. This is meant to be a generically useful library that does not contain any application-specific code. It provides the necessary mechanisms for most needed. See the file itself for details of its operation.

### Polling and Updates

The `polling.js` module polls the server for latest sensor values:
- Fetches latest sensor values via `StatusDataHelper`
- Computes visual display using `StatusDisplayData`
- Returns JSON dictionary mapping CSS class names to attribute updates
- Updates SVG `g` and `path` tags, `select` tags for controllers, `div` elements for non-SVG displays

For complete implementation details of the polling system, CSS class application, and troubleshooting, see [Entity Status Display](entity-status-display.md).

### JavaScript Conventions

1. **Module Pattern**: Use revealing module pattern for organization
2. **jQuery Usage**: Prefix jQuery over native DOM query/manipulation
3. **jQuery Usage**: Use `$` prefix for jQuery objects
4. **Event Delegation**: Use delegated events for dynamic content

Example:
```javascript
var MyModule = (function() {
    var privateVar = 'value';
    
    function init() {
        // Delegated event handling
        $(document).on('click', '.dynamic-button', handleClick);
    }
    
    function handleClick(e) {
        e.preventDefault();
        var $button = $(e.currentTarget);
        // Handle click
    }
    
    return {
        init: init
    };
})();

$(document).ready(function() {
    MyModule.init();
});
```

## CSS Standards

**CSS in Templates**:  We should never put CSS in templates, or otherwise have inline `<style>` blocks.  All CSS should be put in a file in the `src/hi/static/css` directory.

**Main CSS**: Use `src/hi/static/css/main.css` for most needs.  Some special-purpose, high-volume CSS modules may justify creating a nw CSS file.

**No Emojis**: No Emojis anywhere: not in user-facing messaging, not in log messages, not in the comments.

### Core Technologies
- Bootstrap 4 for UI components

**Django Pipeline**: We use the Django pipeline library for injecting minimized, cache-busting CSS (and javascript) into pages. Any new files must be defined in `src/hi/settings/base.py`.

### Responsive Design Principles

The predominant use of this app is on a tablet in landscape mode with a touch screen. Secondary usage is laptop or desktop. For mobile phones, we only need to render well enough to be usable in landscape mode.

### CSS Organization

1. **Component-based**: Organize CSS by component, not by page
2. **BEM Naming**: Use BEM methodology for class naming when appropriate
3. **Bootstrap Extensions**: Extend Bootstrap classes rather than overriding
4. **Custom Properties**: Use CSS custom properties for theming

Example:
```css
/* Component: Alert Card */
.alert-card {
    /* Base styles */
}

.alert-card__header {
    /* Header specific styles */
}

.alert-card--critical {
    /* Modifier for critical alerts */
}
```

## SVG Manipulation

### Status Display System

Entity SVG appearance changes based on sensor readings:

1. **CSS Class Mapping**: Normalized sensor values added as CSS class names
2. **Predefined Icons**: Alternative SVG icons for well-known sensor values
3. **Color Schemes**: Map sensor values to SVG fill, stroke, and opacity attributes

### Value Decaying

For motion/presence sensors, visual states decay over time:
- Active (red) → Recent (orange) → Past (yellow) → Idle (green/gray)
- Creates intuitive visual "cooling off" effect
- Centralized in `StatusDisplayData` and `StatusDisplayManager` classes

### Multiple Sensors Priority

- At most one entity state determines visual representation
- Priority configured per LocationView via `location_view_type`
- Different priorities for different views (e.g., climate vs security)

## View Testing

### Testing Patterns by View Type

#### Synchronous HTML Views
```python
def test_location_view_renders_correctly(self):
    location = Location.objects.create(name='Test Location')
    url = reverse('location_detail', kwargs={'location_id': location.id})
    response = self.client.get(url)
    
    self.assertSuccessResponse(response)
    self.assertHtmlResponse(response)
    self.assertTemplateRendered(response, 'location/detail.html')
    self.assertEqual(response.context['location'], location)
```

#### Asynchronous HTML Views (AJAX)
```python
def test_async_html_view_with_ajax_header(self):
    url = reverse('console_sensor_view', kwargs={'sensor_id': 1})
    response = self.async_get(url)  # Includes HTTP_X_REQUESTED_WITH header
    
    self.assertSuccessResponse(response)
    self.assertJsonResponse(response)
    data = response.json()
    self.assertIn('insert_map', data)
```

#### Dual-Mode Views
```python
def test_modal_view_sync_request(self):
    url = reverse('weather_current_conditions_details')
    response = self.client.get(url)
    
    self.assertSuccessResponse(response)
    self.assertHtmlResponse(response)
    self.assertTemplateRendered(response, 'pages/main_default.html')
    self.assertTemplateRendered(response, 'weather/modals/conditions_details.html')

def test_modal_view_async_request(self):
    url = reverse('weather_current_conditions_details')
    response = self.async_get(url)
    
    self.assertSuccessResponse(response)
    self.assertJsonResponse(response)
    data = response.json()
    self.assertIn('modal', data)
```

### View Testing Guidelines

**DO:**
- Use `reverse()` with URL names instead of hardcoded URLs
- Use `async_get()`, `async_post()` for AJAX requests
- Test status codes, response types, and templates separately
- Use real database operations and test data setup
- Test actual request/response flows

**DON'T:**
- Use hardcoded URL strings
- Use regular `client.get()` for AJAX requests
- Mix status code, response type, and template assertions
- Test template content text that may change
- Mock internal Django components

## Related Documentation
- Icon system: [Icon System](icon-system.md)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Template conventions: [Template Conventions](template-conventions.md)
- UI testing: [UI Testing](ui-testing.md)
- Testing patterns: [Testing Patterns](../testing/testing-patterns.md)
