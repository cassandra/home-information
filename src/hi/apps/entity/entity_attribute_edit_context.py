"""
Entity Attribute Edit Context - Entity-specific context for attribute editing templates.

This module contains Entity-specific implementations of the AttributeItemEditContext
pattern, encapsulating entity-specific domain knowledge while maintaining
the generic template interface.
"""
import logging
from functools import cached_property
from typing import Any, Dict, Optional, Type

from django.forms import ModelForm, BaseInlineFormSet
from django.urls import reverse

from hi.apps.attribute.edit_context import AttributeItemEditContext
from hi.apps.attribute.enums import AttributeValueType
from hi.apps.attribute.forms import AttributeUploadForm
from hi.apps.attribute.models import AttributeModel
from hi.enums import ViewDataPriority
from hi.integrations.integration_manager import IntegrationManager

from .forms import EntityForm, EntityAttributeRegularFormSet, EntityAttributeUploadForm
from .models import Entity, EntityAttribute

logger = logging.getLogger(__name__)


class EntityAttributeItemEditContext(AttributeItemEditContext):
    """
    Entity-specific context provider for attribute editing templates.

    This class encapsulates Entity-specific knowledge while providing
    the generic interface expected by attribute editing templates.
    """

    def __init__(self,
                 entity                  : Entity,
                 data_priority_override  : Optional[str] = None ) -> None:
        """
        Initialize context for Entity attribute editing.

        Args:
            entity: The Entity instance that owns the attributes
            data_priority_override: Optional ViewDataPriority name for
                the initially active tab (e.g., landing on Linked
                Content after the reference picker). Only the initial
                open passes this.
        """
        super().__init__(
            owner_type = 'entity',
            owner = entity,
        )
        self._data_priority_override = data_priority_override
        return

    @property
    def entity(self) -> Entity:
        """Get the Entity instance (typed accessor)."""
        return self.owner

    def extra_template_context(self) -> Dict[str, Any]:
        return self._entity_template_context

    @cached_property
    def _entity_template_context(self) -> Dict[str, Any]:
        external_view_data = self._get_external_view_data()
        external_references = self.entity.external_references.all()
        return {
            'external_view_data': external_view_data,
            'external_references': external_references,
            'data_priority': self._resolve_data_priority(
                external_view_data = external_view_data,
                external_references = external_references,
            ),
        }

    def _resolve_data_priority( self, external_view_data,
                                external_references ) -> ViewDataPriority:
        """Precedence: caller override (e.g., post-picker landing on
        Linked Content), then INTERNAL > EXTERNAL > REFERENCE. Falls
        back to INTERNAL when no category has content. An invalid
        override name silently falls through to the data-derived
        computation rather than erroring -- the override is an
        optional UX hint, not a contract."""
        if self._data_priority_override:
            try:
                override_value = ViewDataPriority.from_name( self._data_priority_override )
            except ValueError:
                override_value = None
            if override_value is not None:
                return override_value
        file_type = str( AttributeValueType.FILE )
        has_files = self.entity.attributes.filter(
            value_type_str = file_type,
        ).exists()
        has_regulars = self.entity.attributes.exclude(
            value_type_str = file_type,
        ).exists()
        has_deleted = (
            EntityAttribute.deleted_objects.filter( entity = self.entity ).exists()
            if getattr( EntityAttribute, 'supports_soft_delete', False )
            else False
        )
        has_internal = has_files or has_regulars or has_deleted
        if has_internal:
            return ViewDataPriority.INTERNAL
        if external_view_data and external_view_data.has_content:
            return ViewDataPriority.EXTERNAL
        if external_references:
            return ViewDataPriority.REFERENCE
        return ViewDataPriority.default()

    def _get_external_view_data( self ):
        if not self.entity.integration_id:
            return None
        try:
            gateway = IntegrationManager().get_integration_gateway( self.entity.integration_id )
        except KeyError:
            logger.warning(
                'No integration gateway registered for entity '
                f'{self.entity.id} (integration_id={self.entity.integration_id!r}).'
            )
            return None
        connector = gateway.get_connector()
        if connector is None:
            return None
        return connector.get_external_view_data( self.entity )

    @property
    def attribute_model_subclass(self) -> Type[AttributeModel]:
        return EntityAttribute

    @property
    def attribute_upload_form_class(self) -> Type[AttributeUploadForm]:
        return EntityAttributeUploadForm
    
    def create_owner_form( self, form_data : Optional[ Dict[str, Any] ] = None ) -> ModelForm:
        return EntityForm( form_data, instance = self.entity )

    def create_attribute_model( self ) -> AttributeModel:
        return EntityAttribute( entity = self.entity )
    
    def create_regular_attributes_formset(
            self, form_data : Optional[ Dict[str, Any] ] = None ) -> BaseInlineFormSet:
        return EntityAttributeRegularFormSet(
            form_data,
            instance = self.entity,
            prefix = self.formset_prefix,
        )

    @property
    def can_restore_default(self):
        return False
    
    @property
    def content_body_template_name(self):
        return 'entity/panes/entity_edit_content_body.html'
    
    @property
    def file_upload_url(self) -> str:
        return reverse( 'entity_attribute_upload',
                        kwargs = { 'entity_id': self.entity.id })

    @property
    def allow_internal_attributes(self) -> bool:
        return self.entity.allow_internal_attributes
