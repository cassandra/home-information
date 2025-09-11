import logging
from typing import Optional

from hi.apps.control.controller_manager import ControllerManager
from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateType, EntityStateValue
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.enums import LocationViewType
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.integrations.transient_models import IntegrationControlResult

from .controller_history_manager import ControllerHistoryManager
from .transient_models import ControllerOutcome

logger = logging.getLogger(__name__)


class OneClickNotSupported(Exception):
    """Raised when EntityStateType doesn't support one-click control."""
    pass


class OneClickError(Exception):
    """Raised when EntityStateType has erro being set."""
    pass


class OneClickControlService:
    """
    Service responsible for complete one-click control flow:
    - Priority resolution and controller selection
    - Current state detection for proper toggle behavior  
    - Control execution and outcome reporting
    """

    # Although we can cycle through a value enumeration of any length to
    # have a one-click behavior. This is not going to be useful past a
    # certain point, so we best limit one-click behavior to simpler
    # controllers.
    #
    ONE_CLICK_CHOICE_LIMIT = 3
    
    def execute_one_click_control(
            self,
            entity              : Entity,
            location_view_type  : LocationViewType  = None ) -> ControllerOutcome:
        """
        Execute complete one-click control flow: decision, state detection, execution.
        Convenience wrapper around ControllerManager.do_control().
        Raises OneClickNotSupported if control cannot be attempted.
        """
        controller = self._find_controller(
            entity = entity,
            location_view_type = location_view_type,
        )
        current_value = self._get_current_state_value(
            entity_state = controller.entity_state,
        )
        target_value = self._determine_control_value(
            entity_state = controller.entity_state,
            current_value = current_value,
        )
        logger.debug( f'Calling control: {entity} : {current_value} -> {target_value}' )
        
        return ControllerManager().do_control(
            controller = controller,
            control_value = target_value,
        )
    
    def _find_controller( self,
                          entity              : Entity,
                          location_view_type  : LocationViewType  = None ) -> Controller:
        """Find highest priority EntityState that has controllers and is supported.

        We only want one-click controls to apply the entity state being
        used in the display status.  Thus, we make sure we use the same
        logic to pick the entity state, then see if it has a controller.
        """

        if not location_view_type:
            location_view_type = LocationViewType.default()
        priority_list = location_view_type.entity_state_type_priority_list

        entity_state_list = StatusDisplayManager().get_entity_state_list_for_status(
            entity = entity,
            entity_state_type_priority_list = priority_list,
        )

        for entity_state in entity_state_list:
            if entity_state.entity_state_type:
                controller = entity_state.controllers.first()
                if controller:
                    return controller
            continue
        
        raise OneClickNotSupported(f'No priority states found for {entity}')
    
    def _get_current_state_value( self, entity_state: EntityState ) -> Optional[str]:
        try:
            sensor_response = StatusDisplayManager().get_latest_sensor_response(
                entity_state = entity_state,
            )
            if sensor_response:
                logger.debug( f'Latest response: {entity_state}'
                              f' = {sensor_response.value}' )
                current_state_value = sensor_response.value

                # Normalize the value in case non-discrete and toggle-able (e.g., dimmers)
                return entity_state.to_toggle_value(
                    actual_value = current_state_value,
                )
            logger.debug( f'No latest response for: {entity_state}' )
        except Exception as e:
            logger.warning( f'Problem getting latest response for: {entity_state} - {e}' )
            pass
        return None
    
    def _determine_control_value( self,
                                  entity_state   : EntityState,
                                  current_value  : Optional[str] ) -> str:
        toggle_state_value_list = entity_state.toggle_values()
        logger.debug( f' Next for {current_value} : {toggle_state_value_list}' )
        if not toggle_state_value_list:
            raise OneClickNotSupported(f'No toggle value list found for {entity_state}')

        if len(toggle_state_value_list) > self.ONE_CLICK_CHOICE_LIMIT:
            raise OneClickNotSupported(f'Too many values to toggle for {entity_state}')
            
        for idx, toggle_state_value in enumerate( toggle_state_value_list ):
            if toggle_state_value != current_value:
                continue

            next_idx = idx + 1
            if next_idx < len(toggle_state_value_list):
                return toggle_state_value_list[next_idx]
            return toggle_state_value_list[0]

        return toggle_state_value_list[0]
