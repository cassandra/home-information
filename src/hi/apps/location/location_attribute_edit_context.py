"""
LocationAttributeItemEditContext - Location-specific context for attribute editing templates.

This module contains Location-specific implementations of the AttributeItemEditContext
pattern, encapsulating location-specific domain knowledge while maintaining
the generic template interface.
"""
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet
from django.urls import reverse

from hi.apps.attribute.edit_context import AttributeItemEditContext
from hi.apps.attribute.forms import AttributeUploadForm
from hi.apps.attribute.models import AttributeModel

from .forms import LocationForm, LocationAttributeRegularFormSet, LocationAttributeUploadForm
from .models import Location, LocationAttribute


class LocationAttributeItemEditContext( AttributeItemEditContext ):
    """
    Location-specific context provider for attribute editing templates.
    
    This class encapsulates Location-specific knowledge while providing
    the generic interface expected by attribute editing templates.
    """
    
    def __init__(self,
                 location               : Location,
                 extra_template_context : Optional[Dict[str, Any]] = None ) -> None:
        """
        Initialize context for Location attribute editing.

        Args:
            location: The Location instance that owns the attributes
            extra_template_context: View-supplied template variables
                (external_references, data_priority, etc.). The view
                computes them once and threads them through the
                context so the framework's GET and async-POST
                renderers both see them.
        """
        super().__init__(
            owner_type = 'location',
            owner = location,
            extra_template_context = extra_template_context,
        )
        return
    
    @property
    def location(self) -> Location:
        """Get the Location instance (typed accessor)."""
        return self.owner
    
    @property
    def attribute_model_subclass(self) -> Type[AttributeModel]:
        return LocationAttribute

    @property
    def attribute_upload_form_class(self) -> Type[AttributeUploadForm]:
        return LocationAttributeUploadForm
    
    def create_owner_form( self, form_data : Optional[ Dict[str, Any] ] = None ) -> ModelForm:
        return LocationForm( form_data, instance = self.location )
    
    def create_attribute_model( self ) -> AttributeModel:
        return LocationAttribute( location = self.location )
    
    def create_regular_attributes_formset(
            self, form_data : Optional[ Dict[str, Any] ] = None ) -> BaseInlineFormSet:
        return LocationAttributeRegularFormSet(
            form_data,
            instance = self.location,
            prefix = self.formset_prefix,
        )

    @property
    def can_restore_default(self):
        return False
    
    @property
    def content_body_template_name(self):
        return 'location/panes/location_edit_content_body.html'
    
    @property
    def file_upload_url(self) -> str:
        return reverse( 'location_attribute_upload',
                        kwargs = { 'location_id': self.location.id })
    
