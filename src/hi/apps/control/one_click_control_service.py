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


class OneClickControlNotSupportedException(Exception):
    """Raised when EntityStateType doesn't support one-click control."""
    pass


class OneClickControlService:
    """
    Service responsible for complete one-click control flow:
    - Priority resolution and controller selection
    - Current state detection for proper toggle behavior  
    - Control execution and outcome reporting
    """
    
    # Default toggle mappings for binary states
    TOGGLE_VALUE_MAP = {
        EntityStateValue.OFF: EntityStateValue.ON,
        EntityStateValue.ON: EntityStateValue.OFF,
        EntityStateValue.CLOSED: EntityStateValue.OPEN,
        EntityStateValue.OPEN: EntityStateValue.CLOSED,
        EntityStateValue.LOW: EntityStateValue.HIGH,
        EntityStateValue.HIGH: EntityStateValue.LOW,
        EntityStateValue.IDLE: EntityStateValue.ACTIVE,
        EntityStateValue.ACTIVE: EntityStateValue.IDLE,
    }
    
    def execute_one_click_control(
            self,
            entity              : Entity,
            location_view_type  : LocationViewType  = None ) -> ControllerOutcome:
        """
        Execute complete one-click control flow: decision, state detection, execution.
        Convenience wrapper around ControllerManager.do_control().
        Raises OneClickControlNotSupportedException if control cannot be attempted.
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
        """Find highest priority EntityState that has controllers and is supported."""

        if not location_view_type:
            location_view_type = LocationViewType.default()
        priority_list = location_view_type.entity_state_type_priority_list
        
        entity_state_queryset = entity.states.all()
        for state_type in priority_list:
            for entity_state in entity_state_queryset:
                if entity_state.entity_state_type == state_type:
                    controller = entity_state.controllers.first()
                    if controller:
                        return controller
                continue
            continue
        
        raise OneClickControlNotSupportedException(f'No priority states found for {entity}')
    
    def _get_current_state_value( self, entity_state: EntityState ) -> Optional[str]:
        try:
            sensor_response = StatusDisplayManager().get_latest_sensor_response(
                entity_state = entity_state,
            )
            if sensor_response:
                logger.debug( f'Latest response: {entity_state}'
                              f' = {sensor_response.value}' )
                return sensor_response.value
            logger.debug( f'No latest response for: {entity_state}' )
        except Exception as e:
            logger.warning( f'Problem getting latest response for: {entity_state} - {e}' )
            pass
        return None
    
    def _determine_control_value( self,
                                  entity_state   : EntityState,
                                  current_value  : Optional[str] ) -> str:
        entity_state_type = entity_state.entity_state_type

        # Handle special cases for specific state types
        if entity_state_type == EntityStateType.LIGHT_DIMMER:
            # For dimmers: current_value might be "0" (OFF) or ">0" (ON)
            try:
                if current_value and float(current_value) > 0:
                    return "0"  # Turn off
                else:
                    return "100"  # Turn on to full
            except (ValueError, TypeError):
                return "100"  # Default to on
        
        # If we have current value, try to toggle it
        if current_value:
            try:
                current_enum_value = EntityStateValue.from_name_safe( current_value )
                if current_enum_value in self.TOGGLE_VALUE_MAP:
                    return str(self.TOGGLE_VALUE_MAP[current_enum_value] )
            except ( ValueError, AttributeError ):
                pass
                
        # Fallback defaults for known controllable types
        if entity_state_type == EntityStateType.ON_OFF:
            return str(EntityStateValue.ON)
        elif entity_state_type == EntityStateType.OPEN_CLOSE:
            return str(EntityStateValue.OPEN)
        elif entity_state_type == EntityStateType.HIGH_LOW:
            return str(EntityStateValue.HIGH)
        elif entity_state_type == EntityStateType.LIGHT_LEVEL:
            return str(EntityStateValue.ON)
        
        # Final fallback
        return str(EntityStateValue.ON)
