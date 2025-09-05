# Attribute Editing Integration Guide

A comprehensive guide for integrating new models with the generic attribute editing system using the AttributeEditContext pattern.

## Overview

The AttributeEditContext pattern provides a standardized way to implement attribute editing across different model types (Entity, Location, etc.) while maintaining ~95% code reuse through generic templates and handlers.

### Benefits

- **Code Reuse**: Share 95% of template and handler logic across model types
- **Consistency**: Standardized UI/UX across all attribute editing interfaces
- **Type Safety**: Clean abstraction with type-safe owner-specific access
- **Maintainability**: Single source of truth for attribute editing functionality
- **Extensibility**: Easy to add new model types following established patterns

### When to Use

Use this pattern when you have:
- A model that owns attributes (like Entity owns EntityAttribute)
- Need for modal-based attribute editing with file upload support
- Requirements for attribute history and restore functionality
- Desire for consistent editing UI across different model types

## Prerequisites

### Required Model Structure

Your implementation needs:

1. **Owner Model**: The main model (e.g., `Entity`, `Location`)
   ```python
   class YourModel(models.Model):
       name = models.CharField(max_length=255)
       # other fields...
   ```

2. **Attribute Model**: Related attribute model (e.g., `EntityAttribute`, `LocationAttribute`)
   ```python
   class YourModelAttribute(models.Model):
       your_model = models.ForeignKey(YourModel, related_name='attributes')
       name = models.CharField(max_length=255)
       value = models.TextField()
       value_type_str = models.CharField(max_length=50)
       # history tracking fields...
   ```

3. **Template Directory Structure**:
   ```
   hi/apps/yourapp/templates/yourapp/
   ├── modals/
   │   └── yourmodel_edit.html
   └── panes/
       └── yourmodel_edit_content_body.html
   ```

## Step-by-Step Implementation

### Step 1: Create AttributeItemEditContext Subclass

Create `yourapp/yourmodel_attribute_edit_context.py`:

See the following existing integrations:
```
# Single instance/formset
src/hi/apps/entity/entity_attribute_edit_context.py
src/hi/apps/location/location_attribute_edit_context.py

# Multipla instance/formset
src/hi/apps/config/subsystem_attribute_edit_context.py
```

### Step 2: Create the needed views.

- Pick whether you need a single or multiple instance implementation
- Single instance view will include the mixin AttributeEditViewMixin
- Multiple instance views will include the mixin AttributeMultiEditViewMixin
- Your views get() method can render any sort of page or modal.
- The get() method must get its template comntext from the mixin
- The page or modal template must include a "content body" template (see below)
- The post always goes though a mixin method and returns custom JSON for front-end (attr.js)

The full set of views include:
- Main editing entry
- File upload handling (optional)
- Attribute History
- Atribute Value restore

### Step 3: Create Content Body Template

- Create `yourapp/templates/yourapp/panes/yourmodel_edit_content_body.html`:
- This template must extend `attribute/components/edit_content_body.html`
- Override content blocks as needed.

Example:
```
src/hi/apps/config/templates/config/panes/subsystem_edit_content_body.html
src/hi/apps/entity/templates/entity/panes/entity_edit_content_body.html
src/hi/apps/location/templates/location/panes/location_edit_content_body.html
```

### Step 4: Add URL Patterns

- Add URL patterns for the views.
- Follow the naming convenions in the attribute edit context classes or override them if needed

See:
```
src/hi/apps/entity/urls.py
src/hi/apps/location/urls.py
src/hi/apps/config/urls.py
```

### Customizing Owner Fields

Override the `owner_fields` block to define model-specific fields:

```django
{% block owner_fields %}
<div class="row">
  <div class="col-md-8">
    <!-- Name field -->
  </div>
  <div class="col-md-4">
    <!-- Type or other field -->
  </div>
</div>
{% endblock %}
```

### Template Debugging

Add this to templates for debugging context variables:

```django
{% comment %}DEBUG: Available context variables{% endcomment %}
{% if debug %}
  <pre>{{ attr_context|pprint }}</pre>
  <pre>Owner ID: {{ attr_context.owner_id }}</pre>
  <pre>Owner Type: {{ attr_context.owner_type }}</pre>
{% endif %}
```

### Context Variable Verification

Verify these key context variables are available:

- `attr_owner_context` - The AttributeEditContext instance
- `attr_item_context` - The AttributeEditContext instance
- `owner_form` - Generic alias for model-specific form  
- `your_model` - Your specific model instance
- `file_attributes` - QuerySet of file attributes
- `regular_attributes_formset` - Formset for non-file attributes
