from dataclasses import dataclass
from typing import Optional

from hi.apps.control.controller_manager import ControllerManager
from hi.apps.entity.enums import EntityStateType, EntityStateValue
from hi.apps.entity.models import Entity, EntityState
from hi.apps.monitor.status_display_manager import StatusDisplayManager


@dataclass
class OneClickControlOutcome:
    """Result of one-click control execution for UI handling."""
    success: bool
    executed_control: bool
    control_value_sent: Optional[str] = None
    error_message: Optional[str] = None
    should_show_status_modal: bool = False


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
    
    # EntityStateTypes that support one-click control
    SUPPORTED_STATE_TYPES = {
        EntityStateType.ON_OFF,
        EntityStateType.LIGHT_LEVEL, 
        EntityStateType.LIGHT_DIMMER,  # Treat as on/off (0% = OFF, >0% = ON)
        EntityStateType.OPEN_CLOSE,
        EntityStateType.HIGH_LOW,
    }
    
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
        EntityStateValue.DISCONNECTED: EntityStateValue.CONNECTED,
        EntityStateValue.CONNECTED: EntityStateValue.DISCONNECTED,
    }
    
    def execute_one_click_control(self, entity: Entity, location_view_type) -> OneClickControlOutcome:
        """
        Execute complete one-click control flow: decision, state detection, execution.
        Returns outcome for view to handle UI appropriately.
        """
        try:
            # Find controllable state based on priority
            controllable_state = self._find_controllable_entity_state(entity, location_view_type)
            if not controllable_state:
                return OneClickControlOutcome(
                    success=False, 
                    executed_control=False,
                    should_show_status_modal=True
                )
            
            # Get controller for this state
            controller = controllable_state.controllers.first()
            if not controller:
                return OneClickControlOutcome(
                    success=False, 
                    executed_control=False,
                    should_show_status_modal=True
                )
            
            # Get current state for proper toggle behavior
            current_value = self._get_current_state_value(controllable_state)
            
            # Determine target value for control
            target_value = self._determine_control_value(controllable_state, current_value)
            
            # Execute control
            control_result = ControllerManager().do_control(
                controller=controller,
                control_value=target_value
            )
            
            return OneClickControlOutcome(
                success=not control_result.has_errors,
                executed_control=True,
                control_value_sent=target_value,
                error_message=control_result.error_message if control_result.has_errors else None
            )
            
        except OneClickControlNotSupportedException:
            return OneClickControlOutcome(
                success=False, 
                executed_control=False,
                should_show_status_modal=True
            )
        except Exception as e:
            return OneClickControlOutcome(
                success=False, 
                executed_control=False,
                error_message=str(e),
                should_show_status_modal=True
            )
    
    def _find_controllable_entity_state(self, entity: Entity, location_view_type) -> Optional[EntityState]:
        """Find highest priority EntityState that has controllers and is supported."""
        if not location_view_type or not location_view_type.entity_state_type_priority_list:
            return None
            
        priority_list = location_view_type.entity_state_type_priority_list
        
        for state_type in priority_list:
            # Only consider supported state types
            if state_type not in self.SUPPORTED_STATE_TYPES:
                continue
                
            for entity_state in entity.entity_states.all():
                if entity_state.entity_state_type == state_type:
                    if entity_state.controllers.exists():
                        return entity_state
        return None
    
    def _get_current_state_value(self, entity_state: EntityState) -> Optional[str]:
        """Get current state value from latest sensor response."""
        try:
            sensor_response = StatusDisplayManager().get_latest_sensor_response(entity_state)
            if sensor_response:
                return sensor_response.value_str
        except Exception:
            pass
        return None
    
    def _determine_control_value(self, entity_state: EntityState, current_value: Optional[str]) -> str:
        """Determine what control value to send based on current state."""
        entity_state_type = entity_state.entity_state_type
        
        # If we have current value, try to toggle it
        if current_value:
            try:
                current_enum_value = EntityStateValue.from_name_safe(current_value)
                if current_enum_value in self.TOGGLE_VALUE_MAP:
                    return str(self.TOGGLE_VALUE_MAP[current_enum_value])
            except (ValueError, AttributeError):
                pass
        
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
        
        # Fallback defaults for known controllable types
        if entity_state_type == EntityStateType.ON_OFF:
            return str(EntityStateValue.ON)
        elif entity_state_type == EntityStateType.OPEN_CLOSE:
            return str(EntityStateValue.OPEN)
        elif entity_state_type == EntityStateType.HIGH_LOW:
            return str(EntityStateValue.HIGH)
        elif entity_state_type == EntityStateType.LIGHT_LEVEL:
            return str(EntityStateValue.ON)
        
        # Try to get first choice from controller if available
        controller = entity_state.controllers.first()
        if controller:
            choices = controller.choices
            if choices:
                return choices[0][0]  # Return first choice key
        
        # Final fallback
        return str(EntityStateValue.ON)