import logging
from threading import Timer, Lock

from django.core.exceptions import BadRequest

from hi.apps.common.singleton import Singleton
from hi.apps.config.enums import SubsystemAttributeType
from hi.apps.config.settings_manager import SettingsManager

from .enums import SecurityLevel, SecurityState, SecurityStateAction
from .transient_models import SecurityStatusData

logger = logging.getLogger(__name__)


class SecurityManager(Singleton):

    DEFAULT_TRANSITION_DELAY_SECS = 5 * 60
    
    def __init_singleton__(self):
        self._security_state = SecurityState.DISABLED
        self._security_level = SecurityLevel.OFF

        self._delayed_security_state_timer = None
        self._delayed_security_state = None
        
        self._security_status_lock = Lock()
        self._initialize_security_state()
        return

    @property
    def security_state(self) -> SecurityState:
        return self._security_state

    @property
    def security_level(self) -> SecurityLevel:
        return self._security_level
    
    def get_security_status_data(self) -> SecurityStatusData:
        try:
            self._security_status_lock.acquire()
            
            return SecurityStatusData(
                current_security_level = self._security_level,
                current_security_state = self._security_state,
            )
        finally:
            self._security_status_lock.release()
        return

    def set_security_state( self, security_state_action : SecurityStateAction ):

        delay_mins_str = None
        future_security_state = None
        if security_state_action == SecurityStateAction.DISABLE:
            immediate_security_state = SecurityState.DISABLED

        elif security_state_action == SecurityStateAction.DAY:
            immediate_security_state = SecurityState.DAY

        elif security_state_action == SecurityStateAction.NIGHT:
            immediate_security_state = SecurityState.NIGHT

        elif security_state_action == SecurityStateAction.AWAY:
            immediate_security_state = SecurityState.DISABLED
            future_security_state = SecurityState.AWAY
            delay_mins_str = SettingsManager().get_setting_value(
                SubsystemAttributeType.ALERTS_AWAY_DELAY_MINS,
            )

        elif security_state_action == SecurityStateAction.SNOOZE:
            immediate_security_state = SecurityState.DISABLED
            future_security_state = self._security_state
            delay_mins_str = SettingsManager().get_setting_value(
                SubsystemAttributeType.ALERTS_SNOOZE_DELAY_MINS,
            )
            
        else:
            logger.error( f'Unsupported security state action "{security_state_action}"' )
            raise BadRequest( 'Unsupported security state action.' )

        if delay_mins_str:
            try:
                delay_secs = int(delay_mins_str) * 60
            except (TypeError,ValueError):
                logger.error( f'Bad security state delay minutes setting "{delay_mins_str}"' )
                delay_secs = self.DEFAULT_TRANSITION_DELAY_SECS
        else:
            delay_secs = 0

        self._update_security_state(
            immediate_security_state = immediate_security_state,
            future_security_state = future_security_state,
            delay_secs = delay_secs,
        )
        return
        
    def _update_security_state( self,
                                immediate_security_state  : SecurityState,
                                future_security_state     : SecurityState,
                                delay_secs                : int ):

        self._update_security_state_immediate( new_security_state = immediate_security_state )
        if delay_secs > 0:
            self._update_security_state_delayed(
                target_security_state = future_security_state,
                delay_secs = delay_secs,
            )
        return

    def _update_security_state_delayed( self,
                                        target_security_state  : SecurityState,
                                        delay_secs             : int ):
        try:
            self._security_status_lock.acquire()

            self._delayed_security_state = target_security_state
            if self._delayed_security_state_timer:
                self._delayed_security_state_timer.cancel()
            self._delayed_security_state_timer = Timer( delay_secs, self._apply_delayed_state )
            self._delayed_security_state_timer.start()
            
        finally:
            self._security_status_lock.release()
        return

    def _apply_delayed_state( self ):
        self._update_security_state_immediate(
            new_security_state  = self._delayed_security_state,
        )
        return
    
    def _update_security_state_immediate(self, new_security_state  : SecurityState ):
        try:
            self._security_status_lock.acquire()
            self._cancel_security_state_transition()
            
            if new_security_state == SecurityState.DISABLED:
                self._security_level = SecurityLevel.OFF

            elif new_security_state == SecurityState.DAY:
                self._security_level = SecurityLevel.LOW

            elif new_security_state == SecurityState.NIGHT:
                self._security_level = SecurityLevel.HIGH

            elif new_security_state == SecurityState.AWAY:
                self._security_level = SecurityLevel.HIGH
            else:
                logger.error( f'Unsupported security state "{new_security_state}"' )
                return

            self._security_state = new_security_state

        finally:
            self._security_status_lock.release()
        return

    def _cancel_security_state_transition(self):
        self._delayed_security_state = None
        if self._delayed_security_state_timer:
            self._delayed_security_state_timer.cancel()
            self._delayed_security_state_timer = None
        return

    def _initialize_security_state(self):

        settings_manager = SettingsManager()
        default_security_state_str = settings_manager.get_setting_value(
            SubsystemAttributeType.ALERTS_STARTUP_SECURITY_STATE,
        )
        default_security_state_str = SecurityState.from_name_safe( default_security_state_str )
        self._update_security_state_immediate( new_security_state = default_security_state_str )
        return
    
            
