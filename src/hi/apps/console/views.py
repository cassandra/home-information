from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import View
import dataclasses
from datetime import datetime
from typing import List
from django.utils import timezone

import hi.apps.common.antinode as antinode
from hi.apps.common.keypad_spec import KeypadEntry, KeypadField
from hi.apps.entity.view_mixins import EntityViewMixin
from hi.apps.sense.models import Sensor
from hi.apps.sense.view_mixins import SenseViewMixin

from hi.constants import DIVID
from hi.enums import ViewType
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView

from .constants import ConsoleConstants
from .console_helper import ConsoleSettingsHelper
from .device_capabilities import DeviceCapabilitiesCodec, DeviceCapabilitiesCookie
from .enums import VideoDispatchType
from .unlock_throttle import UnlockThrottle
from .video_stream_browsing_helper import VideoStreamBrowsingHelper


class EntityVideoDispatchView( View, EntityViewMixin ):
    """
    Simple dispatch view for camera sidebar navigation.
    Routes to existing views based on referrer context.
    """
    
    def get( self, request, *args, **kwargs ):

        if not request.view_parameters.view_type.is_video_browse:
            return EntityVideoView().get( request, **kwargs )

        entity = self.get_entity( request, *args, **kwargs )
        
        # Get video dispatch decision based on referrer context
        referrer_url = request.headers.get('referer', '')
        dispatch_result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            entity = entity,
            referrer_url = referrer_url,
        )
        
        # Update kwargs with the dispatch parameters
        kwargs.update( dispatch_result.get_view_kwargs() )
        
        # Route to appropriate view based on dispatch type
        if dispatch_result.dispatch_type == VideoDispatchType.LIVE_STREAM:
            return EntityVideoView().get( request, **kwargs )
        elif dispatch_result.dispatch_type == VideoDispatchType.HISTORY_EARLIER:
            return EntityVideoSensorHistoryEarlierView().get( request, **kwargs )
        elif dispatch_result.dispatch_type == VideoDispatchType.HISTORY_LATER:
            return EntityVideoSensorHistoryLaterView().get( request, **kwargs )
        else:  # VideoDispatchType.HISTORY_DEFAULT
            return EntityVideoSensorHistoryView().get( request, **kwargs )


class EntityVideoView( HiGridView, EntityViewMixin ):
    """View for displaying entity-based video streams."""

    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_pane.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        video_sensor = VideoStreamBrowsingHelper.find_video_sensor_for_entity(entity)

        if not entity.has_live_view and not video_sensor:
            raise BadRequest( 'Entity provides neither a live view nor a video timeline.' )

        request.view_parameters.view_type = ViewType.ENTITY_VIDEO
        request.view_parameters.to_session( request )
        return {
            'entity': entity,
            'video_sensor': video_sensor,
        }

    
class EntityVideoHistoryView( View, EntityViewMixin ):
    """For sensor history for an entity's default sensor (with video).
       Note: An entity having a video stream is independent of whether
       it may have sensors with video streams.
    """

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        sensor = VideoStreamBrowsingHelper.find_video_sensor_for_entity(
            entity = entity,
        )
        if not sensor:
            raise Http404( request )

        kwargs.update({ 'sensor_id': sensor.id })
        return EntityVideoSensorHistoryView().get( request = request, *args, **kwargs )
        

class BaseEntityVideoSensorHistoryView( HiGridView, EntityViewMixin, SenseViewMixin ):
    """Base view for browsing sensor history records with video streams."""
    
    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_sensor_history.html'
    
    def get_main_template_context( self, request, *args, **kwargs ):
        """Common context building logic shared by all sensor history views."""

        entity = self.get_entity( request, *args, **kwargs )
        sensor = self.get_sensor( request, *args, **kwargs )
        
        # Check if sensor provides video stream capability
        if not sensor.provides_event_video_clip:
            raise BadRequest( 'Sensor does not provide video stream capability.' )
                
        # Build sensor history data using subclass-specific method
        sensor_history_data = self.get_sensor_history_data(
            sensor = sensor,
            request = request,
            **kwargs,
        )
        
        request.view_parameters.view_type = ViewType.SENSOR_VIDEO_BROWSE
        request.view_parameters.to_session( request )
        
        return {
            'entity': entity,
            'sensor': sensor,
            'sensor_history_data': sensor_history_data,
        }
    
    def get_sensor_history_data( self, sensor : Sensor, request : HttpRequest, **kwargs ):
        """Override in subclasses to provide specific sensor history data building logic."""
        raise NotImplementedError("Subclasses must implement get_sensor_history_data")


class EntityVideoSensorHistoryView( BaseEntityVideoSensorHistoryView ):
    """Default view for browsing sensor history records with video streams."""
    
    def get_sensor_history_data(self, sensor : Sensor, request : HttpRequest, **kwargs):
        """Get default sensor history data or handle window context."""
        sensor_history_id = kwargs.get('sensor_history_id')
        window_start = kwargs.get('window_start')
        window_end = kwargs.get('window_end')
        
        if window_start and window_end:
            try:
                preserve_window_start = timezone.make_aware(
                    datetime.fromtimestamp(int(window_start))
                )
                preserve_window_end = timezone.make_aware(
                    datetime.fromtimestamp(int(window_end))
                )
                # Get user timezone for proper timeline grouping
                user_timezone = ConsoleSettingsHelper().get_tz_name()
                
                return VideoStreamBrowsingHelper.build_sensor_history_data_with_window(
                    sensor, sensor_history_id, preserve_window_start, preserve_window_end, user_timezone
                )
            except (ValueError, OSError):
                # Invalid timestamp format - fall back to default
                pass
        
        # Get user timezone for proper timeline grouping
        user_timezone = ConsoleSettingsHelper().get_tz_name()
        
        return VideoStreamBrowsingHelper.build_sensor_history_data_default(
            sensor = sensor,
            sensor_history_id = sensor_history_id,
            user_timezone = user_timezone
        )


class EntityVideoSensorHistoryEarlierView( BaseEntityVideoSensorHistoryView ):
    """View for browsing earlier sensor history records (pagination)."""
    
    def get_sensor_history_data(self, sensor : Sensor, request : HttpRequest, **kwargs):
        """Get earlier sensor history data based on timestamp."""
        timestamp = kwargs.get('timestamp')
        if not timestamp:
            raise BadRequest('Timestamp parameter is required for earlier pagination.')
        
        # Get user timezone for proper timeline grouping
        user_timezone = ConsoleSettingsHelper().get_tz_name()
        
        try:
            return VideoStreamBrowsingHelper.build_sensor_history_data_earlier(
                sensor, int(timestamp), user_timezone
            )
        except (ValueError, TypeError):
            raise BadRequest('Invalid timestamp format.')


class EntityVideoSensorHistoryLaterView( BaseEntityVideoSensorHistoryView ):
    """View for browsing later sensor history records (pagination)."""
    
    def get_sensor_history_data(self, sensor : Sensor, request : HttpRequest, **kwargs):
        """Get later sensor history data based on timestamp."""
        timestamp = kwargs.get('timestamp')
        if not timestamp:
            raise BadRequest('Timestamp parameter is required for later pagination.')
        
        # Get user timezone for proper timeline grouping
        user_timezone = ConsoleSettingsHelper().get_tz_name()
        
        try:
            return VideoStreamBrowsingHelper.build_sensor_history_data_later(
                sensor, int(timestamp), user_timezone
            )
        except (ValueError, TypeError):
            raise BadRequest('Invalid timestamp format.')


class ConsoleLockView( View ):

    def post( self, request, *args, **kwargs ):
        if not ConsoleSettingsHelper().get_console_lock_pin():
            return SetLockPinView().get( request, *args, **kwargs )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )


class LockPinModalView( HiModalView ):
    """ Modal whose body is the lock PIN keypad over KEYPAD_FIELDS. """

    KEYPAD_FIELDS : List[ KeypadField ] = []
    KEYPAD_HTML_ID : str = None

    def keypad_entry( self, request, error_message : str = None ) -> KeypadEntry:
        return KeypadEntry(
            spec = ConsoleConstants.LOCK_PIN_KEYPAD,
            fields = self.KEYPAD_FIELDS,
            error_message = error_message,
            html_id = self.KEYPAD_HTML_ID,
        )

    def keypad_response( self, request, status : int, error_message : str = None ):
        return self.modal_response(
            request,
            context = { 'keypad_entry': self.keypad_entry( request, error_message = error_message ) },
            status = status,
        )

    def keypad_replace_response( self, request, status : int, error_message : str = None ):
        """ Re-renders only the keypad, for forms that stay in the modal. """
        content = render_to_string(
            'panes/keypad_entry.html',
            { 'keypad_entry': self.keypad_entry( request, error_message = error_message ) },
            request = request,
        )
        return antinode.response(
            replace_map = { self.KEYPAD_HTML_ID: content },
            status = status,
        )

    
class SetLockPinView( LockPinModalView ):

    PIN_FIELD = KeypadField( name = 'pin', label = 'New PIN' )
    CONFIRM_FIELD = KeypadField( name = 'pin_confirm', label = 'Confirm PIN' )
    KEYPAD_FIELDS = [ PIN_FIELD, CONFIRM_FIELD ]

    def get_template_name( self ) -> str:
        return 'console/modals/set_lock_pin.html'
    
    def get( self, request, *args, **kwargs ):
        return self.keypad_response( request, status = 200 )
    
    def post( self, request, *args, **kwargs ):
        input_pin = request.POST.get( self.PIN_FIELD.name )
        confirm_pin = request.POST.get( self.CONFIRM_FIELD.name )
        if not ConsoleConstants.LOCK_PIN_KEYPAD.is_valid( input_pin ):
            return self.keypad_response(
                request,
                status = 400,
                error_message = f'PIN must be exactly {ConsoleConstants.LOCK_PIN_KEYPAD.length} digits.',
            )
        if confirm_pin != input_pin:
            return self.keypad_response(
                request,
                status = 400,
                error_message = 'PINs did not match. Try again.',
            )

        ConsoleSettingsHelper().set_console_lock_pin( pin = input_pin )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )

    
class ConsoleUnlockView( LockPinModalView ):

    PIN_FIELD = KeypadField( name = 'pin' )
    KEYPAD_FIELDS = [ PIN_FIELD ]
    KEYPAD_HTML_ID = 'hi-console-unlock-keypad'

    def keypad_entry( self, request, error_message : str = None ) -> KeypadEntry:
        return dataclasses.replace(
            super().keypad_entry( request, error_message = error_message ),
            disabled_secs = UnlockThrottle( request.session ).remaining_lockout_secs(),
        )

    def get_template_name( self ) -> str:
        return 'console/modals/console_unlock.html'

    def get(self, request, *args, **kwargs):
        return self.keypad_response( request, status = 403 )
                                    
    def post(self, request, *args, **kwargs):

        # N.B. Simplified security of console locking for now. Just meant
        # to be used when visitors in the house to prevent snooping. Beef
        # up security here if/when needed, but eventual login requirements
        # and its session will be the main auth method.
        
        throttle = UnlockThrottle( request.session )
        if throttle.remaining_lockout_secs():
            return self.keypad_replace_response( request, status = 429 )

        input_pin = request.POST.get( self.PIN_FIELD.name )
        lock_pin = ConsoleSettingsHelper().get_console_lock_pin()

        # N.B. The console can be locked without a valid PIN (e.g., the
        # stored value is a legacy password). Since it would then be
        # impossible to unlock, we unlock in that case.

        if lock_pin and ( input_pin != lock_pin ):
            throttle.record_failure()
            status = 429 if throttle.remaining_lockout_secs() else 400
            return self.keypad_replace_response( request, status = status, error_message = 'Incorrect PIN' )

        throttle.reset()
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = False
        return self.refresh_response( request= request )


class DeviceCapabilitiesView( View ):
    """
    Kiosk entry point for declaring device capabilities via query
    parameters (e.g. ?keyboard=none&browser_nav=none). Each declared
    capability is merged into the persisted cookie independently; others
    keep their values. Exempt from authentication and console lock so a
    signed-out or locked device can still be configured.
    """

    def get( self, request, *args, **kwargs ):
        declarations = DeviceCapabilitiesCodec.declarations_from_query_params( request.GET )
        device_capabilities = request.device_capabilities.with_declarations( declarations )
        response = HttpResponseRedirect( reverse( 'home' ))
        if declarations:
            DeviceCapabilitiesCookie.write( response, device_capabilities )
        return response


class DeviceCapabilityUnavailableView( HiModalView ):
    """ Explains why an action needing missing device capabilities was blocked. """

    def get_template_name( self ) -> str:
        return 'console/modals/device_capability_unavailable.html'

    def get( self, request, *args, **kwargs ):
        capabilities = DeviceCapabilitiesCodec.capabilities_from_names(
            request.GET.getlist( DIVID['DEVICE_REQUIRES_FIELD'] )
        )
        context = {
            'capabilities': capabilities,
        }
        return self.modal_response( request, context = context )
