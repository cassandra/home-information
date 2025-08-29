"""
EntityTypeTransitionHandler - Handles entity type transitions and form saving logic.

This class encapsulates the complex entity type transition logic that was previously
embedded in EntityPropertiesEditView, following the "keep views simple" design philosophy.
"""
import logging
from typing import Optional, TYPE_CHECKING
from django.db import transaction
from django.http import HttpRequest, HttpResponse

import hi.apps.common.antinode as antinode
from hi.apps.location.location_manager import LocationManager
from .entity_manager import EntityManager
from .models import Entity
from .forms import EntityForm, EntityAttributeRegularFormSet

if TYPE_CHECKING:
    from hi.apps.location.models import LocationView

logger = logging.getLogger(__name__)


class EntityTypeTransitionHandler:
    """
    Handles entity type change detection, transitions, and form saving logic.
    
    This class encapsulates business logic for:
    - Detecting entity type changes
    - Handling entity type transitions with proper refresh logic
    - Determining when full page refresh is needed vs sidebar refresh
    - Managing form saving with transition detection
    """

    def handle_entity_form_save( self,
                                 request                  : HttpRequest,
                                 entity                   : Entity,
                                 entity_form              : EntityForm,
                                 entity_attribute_formset : Optional[EntityAttributeRegularFormSet] = None,
                                 original_entity_type_str : Optional[str] = None ) -> Optional[HttpResponse]:
        """Handle saving entity form and optional formset with transition logic.
        
        Args:
            request: HTTP request object
            entity: Entity instance
            entity_form: EntityForm instance
            entity_attribute_formset: Optional EntityAttributeFormSet instance
            original_entity_type_str: Original entity type string for change detection
            
        Returns:
            Response object if transition requires special handling, None otherwise
        """
        if original_entity_type_str is None:
            original_entity_type_str = entity.entity_type_str
        
        transition_response: Optional[HttpResponse] = None
        
        with transaction.atomic():
            entity_form.save()
            if entity_attribute_formset:
                entity_attribute_formset.save()
            
            # Handle transitions within same transaction but defer response
            entity_type_changed: bool = original_entity_type_str != entity.entity_type_str
            if entity_type_changed:
                transition_response = self.handle_entity_type_change(request, entity)
        
        return transition_response

    def handle_entity_type_change( self,
                                   request : HttpRequest,
                                   entity  : Entity      ) -> Optional[HttpResponse]:
        """Handle EntityType changes with appropriate transition logic.
        
        Args:
            request: HTTP request object
            entity: Entity instance with changed type
            
        Returns:
            Response object if full page refresh needed, None for sidebar refresh
        """
        try:
            # Always attempt advanced transition handling regardless of mode/view
            current_location_view: Optional['LocationView'] = LocationManager().get_default_location_view(request=request)
            transition_occurred: bool
            transition_type: str
            transition_occurred, transition_type = EntityManager().handle_entity_type_transition(
                entity=entity,
                location_view=current_location_view,
            )
            
            if self.needs_full_page_refresh(transition_occurred, transition_type):
                return antinode.refresh_response()
            
            # Simple transitions can continue with sidebar-only refresh
            # (will fall through to normal response method)
            return None
            
        except Exception as e:
            logger.warning(f'EntityType transition failed: {e}, falling back to page refresh')
            return antinode.refresh_response()

    def needs_full_page_refresh( self,
                                 transition_occurred : bool,
                                 transition_type     : str  ) -> bool:
        """Determine if EntityType change requires full page refresh.
        
        Args:
            transition_occurred: Boolean indicating if transition succeeded
            transition_type: String indicating type of transition
            
        Returns:
            bool: True if full page refresh needed, False for sidebar refresh only
        """
        if not transition_occurred:
            # Transition failed, use page refresh for safety
            return True
            
        if transition_type == "path_to_path":
            # Path style changes only, sidebar refresh sufficient
            return False
            
        # All other transitions need full refresh to show visual changes:
        # - icon_to_icon: New icon type needs to be visible
        # - icon_to_path: Database structure changed
        # - path_to_icon: Database structure changed
        return True
    
