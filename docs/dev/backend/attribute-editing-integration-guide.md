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

### Step 1: Create AttributeEditContext Subclass

Create `yourapp/yourmodel_attribute_edit_context.py`:

```python
"""
YourModelAttributeEditContext - YourModel-specific context for attribute editing templates.
"""
from typing import Any
from hi.apps.attribute.edit_context import AttributeEditContext
from .models import YourModel

class YourModelAttributeEditContext(AttributeEditContext):
    """YourModel-specific context provider for attribute editing templates."""
    
    def __init__(self, your_model: YourModel) -> None:
        """Initialize context for YourModel attribute editing."""
        super().__init__(your_model, 'yourmodel')  # 'yourmodel' must match URL patterns
    
    @property
    def your_model(self) -> YourModel:
        """Get the YourModel instance (typed accessor)."""
        return self.owner
```

### Step 2: Create Form Handler Class

Create `yourapp/yourmodel_edit_form_handler.py`:

```python
"""
YourModelEditFormHandler - Handles form creation, validation, and processing.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from django.db import transaction
from django.http import HttpRequest
from django.db.models import QuerySet

from hi.apps.attribute.enums import AttributeValueType
from .models import YourModel, YourModelAttribute
from .forms import YourModelForm, YourModelAttributeRegularFormSet
from .yourmodel_attribute_edit_context import YourModelAttributeEditContext

logger = logging.getLogger(__name__)

class YourModelEditFormHandler:
    """Handles form creation, validation, and processing for yourmodel editing."""

    @staticmethod
    def get_formset_prefix(your_model: YourModel) -> str:
        """Get the formset prefix for regular attributes formset."""
        return f'yourmodel-{your_model.id}'

    def create_yourmodel_forms(
            self,
            your_model: YourModel,
            form_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[YourModelForm, QuerySet[YourModelAttribute], YourModelAttributeRegularFormSet]:
        """Create yourmodel forms used by both initial rendering and fragment updates."""
        
        # Create yourmodel form
        yourmodel_form = YourModelForm(form_data, instance=your_model)
        
        # Get file attributes for display
        file_attributes = your_model.attributes.filter(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id')
        
        # Regular attributes formset (excludes FILE attributes)
        regular_attributes_formset = YourModelAttributeRegularFormSet(
            form_data,
            instance=your_model,
            prefix=self.get_formset_prefix(your_model),
            form_kwargs={'show_as_editable': True}
        )
        
        return yourmodel_form, file_attributes, regular_attributes_formset

    def validate_forms(
            self,
            yourmodel_form: YourModelForm,
            regular_attributes_formset: YourModelAttributeRegularFormSet
    ) -> bool:
        """Validate yourmodel form and attributes formset."""
        return yourmodel_form.is_valid() and regular_attributes_formset.is_valid()

    def save_forms(
            self,
            yourmodel_form: YourModelForm,
            regular_attributes_formset: YourModelAttributeRegularFormSet,
            request: HttpRequest,
            your_model: YourModel
    ) -> None:
        """Save forms and process file operations within a transaction."""
        with transaction.atomic():
            yourmodel_form.save()
            regular_attributes_formset.save()
            # Add any custom file processing here

    def create_initial_context(self, your_model: YourModel) -> Dict[str, Any]:
        """Create initial template context for yourmodel editing form."""
        yourmodel_form, file_attributes, regular_attributes_formset = self.create_yourmodel_forms(your_model)
        
        # Create the attribute edit context for template generalization
        attr_context = YourModelAttributeEditContext(your_model)
        
        # Build context with both old and new patterns for compatibility
        context = {
            'your_model': your_model,
            'yourmodel_form': yourmodel_form,
            'owner_form': yourmodel_form,  # Generic alias for templates
            'file_attributes': file_attributes,
            'regular_attributes_formset': regular_attributes_formset,
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        return context
```

### Step 3: Create Response Renderer Class

Create `yourapp/yourmodel_edit_response_renderer.py`:

```python
"""
YourModelEditResponseRenderer - Handles template rendering and response generation.
"""
from typing import Any, Dict, Optional, Tuple
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse

import hi.apps.common.antinode as antinode
from hi.constants import DIVID
from .yourmodel_edit_form_handler import YourModelEditFormHandler
from .models import YourModel, YourModelAttribute
from .forms import YourModelForm, YourModelAttributeRegularFormSet
from .yourmodel_attribute_edit_context import YourModelAttributeEditContext

class YourModelEditResponseRenderer:
    """Handles template rendering and response generation for yourmodel editing."""

    def __init__(self) -> None:
        self.form_handler = YourModelEditFormHandler()

    def build_template_context(
            self,
            your_model: YourModel,
            yourmodel_form: YourModelForm,
            file_attributes: QuerySet[YourModelAttribute],
            regular_attributes_formset: YourModelAttributeRegularFormSet,
            success_message: Optional[str] = None,
            error_message: Optional[str] = None,
            has_errors: bool = False
    ) -> Dict[str, Any]:
        """Build context dictionary for template rendering."""
        
        # Create the attribute edit context for template generalization
        attr_context = YourModelAttributeEditContext(your_model)
        
        # Build context with both old and new patterns for compatibility
        context = {
            'your_model': your_model,
            'yourmodel_form': yourmodel_form,
            'owner_form': yourmodel_form,  # Generic alias for templates
            'file_attributes': file_attributes,
            'regular_attributes_formset': regular_attributes_formset,
            'success_message': success_message,
            'error_message': error_message,
            'has_errors': has_errors,
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        return context

    def render_success_response(
            self,
            request: HttpRequest,
            your_model: YourModel
    ) -> 'antinode.Response':
        """Render success response using antinode helpers."""
        # Re-render content with fresh forms
        yourmodel_form, file_attributes, regular_attributes_formset = self.form_handler.create_yourmodel_forms(your_model)
        
        context = self.build_template_context(
            your_model, yourmodel_form, file_attributes, regular_attributes_formset,
            success_message="Changes saved successfully"
        )
        
        # Render content body
        content_body = render_to_string('yourapp/panes/yourmodel_edit_content_body.html', context, request=request)
        
        # Render upload form
        file_upload_url = reverse('yourmodel_attribute_upload', kwargs={'yourmodel_id': your_model.id})
        upload_form = render_to_string(
            'attribute/components/upload_form.html',
            {'file_upload_url': file_upload_url},
            request=request
        )
        
        return antinode.response(
            insert_map={
                DIVID['ATTR_V2_CONTENT']: content_body,
                DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER']: upload_form
            }
        )
```

### Step 4: Create Content Body Template

Create `yourapp/templates/yourapp/panes/yourmodel_edit_content_body.html`:

```django
{% extends "attribute/components/edit_content_body.html" %}
{% comment %}
YourModel V2 Content Body Fragment
Extends the generic attribute edit content body with yourmodel-specific field layout.
{% endcomment %}

{% block owner_fields %}
<!-- YourModel-specific fields for modal editing -->
<div class="row">
  <div class="col-md-12">
    <div class="form-group mb-0">
      <small class="text-muted">Name</small>
      <input type="text" 
             id="{{ owner_form.name.id_for_label }}"
             name="{{ owner_form.name.html_name }}"
             value="{{ owner_form.name.value|default:'' }}"
             class="form-control form-control-sm"
             {% if owner_form.name.field.required %}required{% endif %}>
      {% if owner_form.name.errors %}
        <div class="invalid-feedback d-block">
          {{ owner_form.name.errors }}
        </div>
      {% endif %}
    </div>
  </div>
  <!-- Add additional yourmodel-specific fields here -->
</div>
{% endblock %}
```

### Step 5: Update Views to Use Handler/Renderer Pattern

Update your main edit view:

```python
from .yourmodel_edit_form_handler import YourModelEditFormHandler
from .yourmodel_edit_response_renderer import YourModelEditResponseRenderer

class YourModelEditView(HiModalView, YourModelViewMixin):
    """YourModel attribute editing modal with redesigned interface."""
    
    def get_template_name(self) -> str:
        return 'yourapp/modals/yourmodel_edit.html'
    
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        your_model = self.get_yourmodel(request, *args, **kwargs)
        
        # Delegate form creation and context building to handler
        form_handler = YourModelEditFormHandler()
        context = form_handler.create_initial_context(your_model)
        
        return self.modal_response(request, context)
    
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        your_model = self.get_yourmodel(request, *args, **kwargs)
        
        # Delegate form handling to specialized handlers
        form_handler = YourModelEditFormHandler()
        renderer = YourModelEditResponseRenderer()
        
        # Create forms with POST data
        yourmodel_form, file_attributes, regular_attributes_formset = form_handler.create_yourmodel_forms(
            your_model, request.POST
        )
        
        if form_handler.validate_forms(yourmodel_form, regular_attributes_formset):
            # Save forms and process files
            form_handler.save_forms(yourmodel_form, regular_attributes_formset, request, your_model)
            
            # Return success response
            return renderer.render_success_response(request, your_model)
        else:
            # Return error response
            return renderer.render_error_response(request, your_model, yourmodel_form, regular_attributes_formset)
```

### Step 6: Update Upload and History Views

Update your upload view:

```python
def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
    your_model = self.get_yourmodel(request, *args, **kwargs)
    # ... upload form validation ...
    
    if upload_form.is_valid():
        with transaction.atomic():
            upload_form.save()   
        
        # Render new file card HTML to append to file grid
        attr_context = YourModelAttributeEditContext(your_model)
        context = {'attribute': yourmodel_attribute, 'your_model': your_model}
        context.update(attr_context.to_template_context())
        
        file_card_html = render_to_string(
            'attribute/components/file_card.html',
            context,
            request=request
        )
        # ... return response ...
```

Update your history inline view:

```python
class YourModelAttributeHistoryInlineView(BaseAttributeHistoryView):
    """View for displaying YourModelAttribute history inline within the edit modal."""
    
    def get_template_name(self):
        return 'attribute/components/attribute_history_inline.html'
    
    def get(self, request: HttpRequest, yourmodel_id: int, attribute_id: int, *args, **kwargs) -> HttpResponse:
        # ... validation and history retrieval ...
        
        # Create the attribute edit context for template generalization
        attr_context = YourModelAttributeEditContext(attribute.your_model)
        
        context = {
            'your_model': attribute.your_model,
            'attribute': attribute,
            'history_records': history_records,
            'history_url_name': self.get_history_url_name(),
            'restore_url_name': self.get_restore_url_name(),
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        return render(request, self.get_template_name(), context)
```

### Step 7: Add URL Patterns

Add URL patterns for history and restore functionality:

```python
# yourapp/urls.py
urlpatterns = [
    # ... existing patterns ...
    
    # Attribute history and restore (inline)
    re_path(r'^yourmodel/(?P<yourmodel_id>\d+)/attribute/(?P<attribute_id>\d+)/history/inline/$', 
            views.YourModelAttributeHistoryInlineView.as_view(), 
            name='yourmodel_attribute_history_inline'),
    
    re_path(r'^yourmodel/(?P<yourmodel_id>\d+)/attribute/(?P<attribute_id>\d+)/restore/inline/(?P<history_id>\d+)/$', 
            views.YourModelAttributeRestoreInlineView.as_view(),
            name='yourmodel_attribute_restore_inline'),
    
    # File upload
    re_path(r'^yourmodel/(?P<yourmodel_id>\d+)/attribute/upload/$',
            views.YourModelAttributeUploadView.as_view(),
            name='yourmodel_attribute_upload'),
]
```

## Template Integration Details

### Using Template Filters and Tags

The generic templates use specialized filters and tags for dynamic functionality. Make sure to load them:

```django
{% load attribute_extras %}

<!-- Dynamic URL generation -->
{% attr_history_url attr_context attribute.id %}
{% attr_restore_url attr_context attribute.id history_record.pk %}

<!-- Dynamic field names -->
{{ attr_context|file_title_field_name:attribute.id }}
{{ attr_context|history_target_id:attribute.id }}
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

## Testing Integration

### Required Test Coverage

1. **Form Handler Tests**: Test form creation, validation, and saving
2. **Response Renderer Tests**: Test template context building and response generation  
3. **View Tests**: Test GET/POST behavior with proper context
4. **Template Tests**: Verify template rendering with context variables
5. **Upload/History Tests**: Test file upload and history functionality

### Example Test Structure

```python
class TestYourModelEditFormHandler(BaseTestCase):
    def test_create_initial_context(self):
        """Test that initial context includes AttributeEditContext variables."""
        your_model = self.create_test_yourmodel()
        form_handler = YourModelEditFormHandler()
        
        context = form_handler.create_initial_context(your_model)
        
        self.assertIn('attr_context', context)
        self.assertIn('owner_form', context)
        self.assertEqual(context['your_model'], your_model)
```

## Troubleshooting

### Common Issues

1. **Template Not Found**: Ensure template paths match your app structure
2. **Context Variables Missing**: Verify `attr_context.to_template_context()` is called
3. **URL Pattern Mismatch**: Check that `owner_type` in context matches URL pattern names
4. **Form Validation Errors**: Ensure formset prefixes are unique and consistent

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

- `attr_context` - The AttributeEditContext instance
- `owner_form` - Generic alias for model-specific form  
- `your_model` - Your specific model instance
- `file_attributes` - QuerySet of file attributes
- `regular_attributes_formset` - Formset for non-file attributes

## Conclusion

Following this guide ensures your new model integrates seamlessly with the established attribute editing patterns, providing consistent UI/UX while maintaining code reuse and type safety. The pattern scales well and provides a solid foundation for future attribute-owning models.