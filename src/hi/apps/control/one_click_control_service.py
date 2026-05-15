import logging
from typing import Optional

from hi.apps.control.controller_manager import ControllerManager
from hi.apps.control.models import Controller
from hi.apps.entity.entity_state_role_order import ENTITY_CONTROL_STATE_ORDERING
from hi.apps.entity.models import Entity, EntityState
from hi.apps.monitor.status_display_manager import StatusDisplayManager

from .transient_models import ControllerOutcome

logger = logging.getLogger(__name__)


class OneClickNotSupported(Exception):
    """Raised when an entity has no one-click control target."""
    pass


class OneClickError(Exception):
    """Raised when a one-click control attempt fails."""
    pass


class OneClickControlService:
    """One-click control flow: pick a target state via role priority,
    determine the next toggle value, dispatch the control. Whether
    one-click is *invoked* in a given context is the caller's
    decision (currently only the AUTOMATION LocationViewType does so);
    this service answers "for this entity, what would one-click do?"
    """

    # Toggling cycles through ``EntityState.toggle_values()``. Past a
    # certain length the cycle stops being a usable one-click
    # affordance, so we cap discrete one-click eligibility here.
    ONE_CLICK_CHOICE_LIMIT = 3

    def execute_one_click_control( self, entity : Entity ) -> ControllerOutcome:
        controller = self._find_controller( entity = entity )
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

    def _find_controller( self, entity : Entity ) -> Controller:
        """Find a toggle-eligible controller on a state whose role
        is listed in ``ENTITY_CONTROL_STATE_ORDERING.order_for`` for
        the entity's EntityType. Walks the role order strictly: only
        states with roles in that list are considered. States with
        unlisted roles (e.g., a thermostat's
        ``THERMOSTAT_TARGET_TEMPERATURE``) are not eligible for
        one-click even when controllable. Raises
        ``OneClickNotSupported`` when no listed role yields a
        toggle-eligible controller."""

        all_states = StatusDisplayManager().all_entity_states_including_delegations(
            entity = entity,
        )
        states_by_role = {}
        for state in all_states:
            states_by_role.setdefault( state.entity_state_role, [] ).append( state )

        role_order = ENTITY_CONTROL_STATE_ORDERING.order_for( entity.entity_type )
        for role in role_order:
            for state in states_by_role.get( role, [] ):
                controller = state.controllers.first()
                if controller and self._is_toggle_eligible( state ):
                    return controller
                continue
            continue
        raise OneClickNotSupported( f'No one-click target for {entity}' )

    def _is_toggle_eligible( self, entity_state : EntityState ) -> bool:
        """A state is toggle-eligible when it has a non-empty
        ``toggle_values`` list within ``ONE_CLICK_CHOICE_LIMIT``.
        States outside this range exist (continuous sensors, large
        discrete enums) but don't have a meaningful one-click
        affordance."""
        toggle_values = entity_state.toggle_values()
        if not toggle_values:
            return False
        if len( toggle_values ) > self.ONE_CLICK_CHOICE_LIMIT:
            return False
        return True

    def _get_current_state_value( self, entity_state : EntityState ) -> Optional[str]:
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
