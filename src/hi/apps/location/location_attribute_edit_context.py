"""
LocationAttributeItemEditContext - Location-specific context for attribute editing templates.

This module contains Location-specific implementations of the AttributeItemEditContext
pattern, encapsulating location-specific domain knowledge while maintaining
the generic template interface.
"""
from functools import cached_property
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet
from django.urls import reverse

from hi.apps.attribute.edit_context import AttributeItemEditContext
from hi.apps.attribute.enums import AttributeValueType
from hi.apps.attribute.forms import AttributeUploadForm
from hi.apps.attribute.models import AttributeModel
from hi.enums import ViewDataPriority

from .forms import LocationForm, LocationAttributeRegularFormSet, LocationAttributeUploadForm
from .models import Location, LocationAttribute


class LocationAttributeItemEditContext( AttributeItemEditContext ):
    """
    Location-specific context provider for attribute editing templates.
    
    This class encapsulates Location-specific knowledge while providing
    the generic interface expected by attribute editing templates.
    """
    
    def __init__(self,
                 location                : Location,
                 data_priority_override  : Optional[str] = None ) -> None:
        """
        Initialize context for Location attribute editing.

        Args:
            location: The Location instance that owns the attributes
            data_priority_override: Optional ViewDataPriority name for
                the initially active tab (e.g., landing on Linked
                Content after the reference picker). Only the initial
                open passes this.
        """
        super().__init__(
            owner_type = 'location',
            owner = location,
        )
        self._data_priority_override = data_priority_override
        return

    @property
    def location(self) -> Location:
        """Get the Location instance (typed accessor)."""
        return self.owner

    def extra_template_context(self) -> Dict[str, Any]:
        return self._location_template_context

    @cached_property
    def _location_template_context(self) -> Dict[str, Any]:
        external_references = self.location.external_references.all()
        return {
            'external_references': external_references,
            'data_priority': self._resolve_data_priority(
                external_references = external_references,
            ),
        }

    def _resolve_data_priority( self, external_references ) -> ViewDataPriority:
        """Precedence: caller override (e.g., post-picker landing on
        Linked Content), then INTERNAL > REFERENCE. Locations have no
        EXTERNAL view-data category. An invalid override name
        silently falls through to the data-derived computation."""
        if self._data_priority_override:
            try:
                override_value = ViewDataPriority.from_name( self._data_priority_override )
            except ValueError:
                override_value = None
            if override_value is not None:
                return override_value
        file_type = str( AttributeValueType.FILE )
        has_files = self.location.attributes.filter(
            value_type_str = file_type,
        ).exists()
        has_regulars = self.location.attributes.exclude(
            value_type_str = file_type,
        ).exists()
        has_deleted = (
            LocationAttribute.deleted_objects.filter( location = self.location ).exists()
            if getattr( LocationAttribute, 'supports_soft_delete', False )
            else False
        )
        has_internal = has_files or has_regulars or has_deleted
        if has_internal:
            return ViewDataPriority.INTERNAL
        if external_references:
            return ViewDataPriority.REFERENCE
        return ViewDataPriority.default()
    
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
    
