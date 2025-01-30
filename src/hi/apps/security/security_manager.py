import logging
from threading import Timer, Lock
from typing import Dict

from django.core.exceptions import BadRequest
from django.http import HttpRequest
from django.template.loader import get_template

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.redis_client import get_redis_client
from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.console.settings import ConsoleSetting

from hi.constants import DIVID

from .constants import SecurityConstants
from .enums import SecurityLevel, SecurityState, SecurityStateAction
from .settings import SecuritySetting
from .transient_models import SecurityStatusData

logger = logging.getLogger(__name__)


class SecurityManager( Singleton, SettingsMixin ):

    DEFAULT_TRANSITION_DELAY_SECS = 5 * 60
    SECURITY_STATE_LABEL_DELAYED_AWAY = 'Away (Delayed)'
    SECURITY_STATE_LABEL_SNOOZED = 'Snoozed'

    SECURITY_STATE_CACHE_KEY = 'hi.security.state'
    
    def __init_singleton__(self):
        self._security_state = SecurityState.default()
        self._security_level = SecurityLevel.OFF

        self._delayed_security_state_timer = None
        self._delayed_security_state = None
        
        self._security_status_lock = Lock()
        self._redis_client = get_redis_client()
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        try:
            self._initialize_security_state()
        except Exception as e:
            logger.exception( 'Problem trying to initialize security state', e )
            self._security_state = SecurityState.DISABLED
        self._was_initialized = True
        return
    
    @property
    def security_state(self) -> SecurityState:
        return self._security_state

    @property
    def security_level(self) -> SecurityLevel:
        return self._security_level
    
    def get_security_status_data(self) -> SecurityStatusData:
        with self._security_status_lock:
            current_action_label = self._security_state.label
            if self._security_state == SecurityState.DAY:
                current_action_value = str(SecurityStateAction.SET_DAY)
            elif self._security_state == SecurityState.NIGHT:
                current_action_value = str(SecurityStateAction.SET_NIGHT)
            elif self._security_state == SecurityState.AWAY:
                current_action_value = str(SecurityStateAction.SET_AWAY)
            else:
                current_action_value = str(SecurityStateAction.DISABLE)

            if self._delayed_security_state:
                if self._delayed_security_state == SecurityState.AWAY:
                    current_action_label = self.SECURITY_STATE_LABEL_DELAYED_AWAY
                    current_action_value = str(SecurityStateAction.SET_AWAY)
                else:
                    current_action_label = self.SECURITY_STATE_LABEL_SNOOZED
                    current_action_value = str(SecurityStateAction.SNOOZE)
                    
            return SecurityStatusData(
                current_security_level = self._security_level,
                current_security_state = self._security_state,
                current_action_value = current_action_value,
                current_action_label = current_action_label,
            )
        return

    def get_status_id_replace_map( self, request : HttpRequest ) -> Dict[ str, str ]:

        security_status_data = self.get_security_status_data()
        context = { 'security_status_data': security_status_data }
        template = get_template( SecurityConstants.SECURITY_STATE_CONTROL_TEMPLATE_NAME )
        security_control_html_str = template.render( context, request = request )
        return {
            DIVID['SECURITY_STATE_CONTROL']: security_control_html_str,
        }

    def update_security_state_user( self, security_state_action : SecurityStateAction ):

        future_security_state = None
        delay_mins_str = None

        if security_state_action == SecurityStateAction.DISABLE:
            immediate_security_state = SecurityState.DISABLED

        elif security_state_action == SecurityStateAction.SET_DAY:
            immediate_security_state = SecurityState.DAY

        elif security_state_action == SecurityStateAction.SET_NIGHT:
            immediate_security_state = SecurityState.NIGHT

        elif security_state_action == SecurityStateAction.SET_AWAY:
            immediate_security_state = SecurityState.DISABLED
            future_security_state = SecurityState.AWAY
            delay_mins_str = self.settings_manager().get_setting_value(
                SecuritySetting.SECURITY_AWAY_DELAY_MINS,
            )

        elif security_state_action == SecurityStateAction.SNOOZE:
            immediate_security_state = SecurityState.DISABLED
            future_security_state = self._security_state
            delay_mins_str = self.settings_manager().get_setting_value(
                SecuritySetting.SECURITY_SNOOZE_DELAY_MINS,
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
        with self._security_status_lock:
            self.update_security_state_immediate(
                new_security_state = immediate_security_state,
                lock_acquired = True,
            )
            if delay_secs > 0:
                self._update_security_state_delayed(
                    target_security_state = future_security_state,
                    delay_secs = delay_secs,
                    lock_acquired = True,
                )
        return

    def _update_security_state_delayed( self,
                                        target_security_state  : SecurityState,
                                        delay_secs             : int,
                                        lock_acquired          : bool          = False ):
        if not lock_acquired:
            self._security_status_lock.acquire()
        try:
            self._delayed_security_state = target_security_state
            if self._delayed_security_state_timer:
                self._delayed_security_state_timer.cancel()
            self._delayed_security_state_timer = Timer( delay_secs, self._apply_delayed_state )
            self._delayed_security_state_timer.start()

            # N.B. We want to set the cached security state to the desired
            # future state.  Otherwise, if system restarts during the
            # SNOOZE or SET_AWAY transition period, it will come back up in
            # the (transitional) DISABLED state, which is undesirable.
            #
            self._redis_client.set( self.SECURITY_STATE_CACHE_KEY, str(self._delayed_security_state ))
            
        finally:
            if not lock_acquired:
                self._security_status_lock.release()
        return

    def _apply_delayed_state( self ):
        logger.debug( f'Applying delayed security state = {self._delayed_security_state}' )
        self.update_security_state_immediate( new_security_state = self._delayed_security_state )
        return
    
    def update_security_state_auto( self, new_security_state  : SecurityState ):
        """Special updating when coming from automation since extra handling is
        needed if state is in a delayed transition (via SET_AWAY or SNOOZE)."""
        with self._security_status_lock:
            if not self._security_state.auto_change_allowed:
                logger.warning( f'Security state auto update but state={self._security_state}' )
                return
            
            if not self._delayed_security_state:
                self.update_security_state_immediate(
                    new_security_state = new_security_state,
                    lock_acquired = True,
                )
                return

            # If the delayed state is from SET_AWAY, we do not want the
            # automation to risk changing it to a lessere security state.
            #
            if not self._delayed_security_state.auto_change_allowed:
                logger.info( f'Security state auto update but delayed={self._delayed_security_state}' )
                return

            # Arriving ar this point in the code means it is likely in a
            # SNOOZE state. When it comes out of snooze, it should honor
            # the state the automation believes it should now be in.  e.g.,
            # If SNOOZE in NIGHT state just before the configured DAY start
            # time of day, then after SNOOZE it should be in DAY state.
            #
            self._delayed_security_state = new_security_state
            return
        
        return
        
    def update_security_state_immediate( self,
                                         new_security_state  : SecurityState,
                                         lock_acquired       : bool          = False ):
        if not lock_acquired:
            self._security_status_lock.acquire()
        try:
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
            self._redis_client.set( self.SECURITY_STATE_CACHE_KEY, str( self._security_state ))
            
        finally:
            if not lock_acquired:
                self._security_status_lock.release()
        return

    def _cancel_security_state_transition(self):
        self._delayed_security_state = None
        if self._delayed_security_state_timer:
            self._delayed_security_state_timer.cancel()
            self._delayed_security_state_timer = None
        return

    def _initialize_security_state(self):
        
        # This makes sure any DISABLED or AWAY state is preserved.
        previous_security_state_str = self._redis_client.get( self.SECURITY_STATE_CACHE_KEY )
        if previous_security_state_str:
            previous_security_state = SecurityState.from_name_safe( previous_security_state_str )
            if not previous_security_state.auto_change_allowed:
                self.update_security_state_immediate( new_security_state = previous_security_state )
                return
        
        # Else, revert to look at time of day to initialize the state.
        settings_manager = self.settings_manager()

        tz_name = settings_manager.get_setting_value(
            ConsoleSetting.TIMEZONE,
        )
        day_start_time_of_day_str = settings_manager.get_setting_value(
            SecuritySetting.SECURITY_DAY_START,
        )
        night_start_time_of_day_str = settings_manager.get_setting_value(
            SecuritySetting.SECURITY_NIGHT_START,
        )
        
        current_datetime = datetimeproxy.now()
        start_of_day_datetime = current_datetime.replace( hour=0, minute=0, second=0, microsecond=0 )
        end_of_day_datetime = current_datetime.replace( hour=23, minute=59, second=59, microsecond=999999 )

        # Normally, one would expect the day start to be defined before the
        # night start, but we do not want to assume or enforce this.  e.g.,
        # Someone working a night shift may have an inverted sense of the
        # lower security DAY hours.
        #
        if day_start_time_of_day_str < night_start_time_of_day_str:
            if datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = day_start_time_of_day_str,
                    tz_name = tz_name,
                    start_datetime = start_of_day_datetime,
                    end_datetime = current_datetime ):
                initial_security_state = SecurityState.NIGHT
            elif datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = night_start_time_of_day_str,
                    tz_name = tz_name,
                    start_datetime = current_datetime,
                    end_datetime = end_of_day_datetime ):
                initial_security_state = SecurityState.NIGHT
            else:
                initial_security_state = SecurityState.DAY

        else:
            if datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = night_start_time_of_day_str,
                    tz_name = tz_name,
                    start_datetime = start_of_day_datetime,
                    end_datetime = current_datetime ):
                initial_security_state = SecurityState.DAY
            elif datetimeproxy.is_time_of_day_in_interval(
                    time_of_day_str = day_start_time_of_day_str,
                    tz_name = tz_name,
                    start_datetime = current_datetime,
                    end_datetime = end_of_day_datetime ):
                initial_security_state = SecurityState.DAY
            else:
                initial_security_state = SecurityState.NIGHT
            
        self.update_security_state_immediate( new_security_state = initial_security_state )
        return
        
