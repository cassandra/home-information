from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest
from django.views.generic import View
from datetime import datetime
from django.utils import timezone

from hi.apps.entity.view_mixins import EntityViewMixin
from hi.apps.sense.models import Sensor
from hi.apps.sense.view_mixins import SenseViewMixin
from hi.integrations.integration_manager import IntegrationManager

from hi.enums import ViewType
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView

from .constants import ConsoleConstants
from .console_helper import ConsoleSettingsHelper
from .enums import VideoDispatchType
from .video_stream_browsing_helper import VideoStreamBrowsingHelper


class EntityVideoStreamDispatchView( View, EntityViewMixin ):
    """
    Simple dispatch view for camera sidebar navigation.
    Routes to existing views based on referrer context.
    """
    
    def get( self, request, *args, **kwargs ):

        if not request.view_parameters.view_type.is_video_browse:
            return EntityVideoStreamView().get( request, **kwargs )

        entity = self.get_entity( request, *args, **kwargs )
        
        # Get video dispatch decision based on referrer context
        referrer_url = request.META.get('HTTP_REFERER', '')
        dispatch_result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            entity = entity,
            referrer_url = referrer_url,
        )
        
        # Update kwargs with the dispatch parameters
        kwargs.update( dispatch_result.get_view_kwargs() )
        
        # Route to appropriate view based on dispatch type
        if dispatch_result.dispatch_type == VideoDispatchType.LIVE_STREAM:
            return EntityVideoStreamView().get( request, **kwargs )
        elif dispatch_result.dispatch_type == VideoDispatchType.HISTORY_EARLIER:
            return EntityVideoSensorHistoryEarlierView().get( request, **kwargs )
        elif dispatch_result.dispatch_type == VideoDispatchType.HISTORY_LATER:
            return EntityVideoSensorHistoryLaterView().get( request, **kwargs )
        else:  # VideoDispatchType.HISTORY_DEFAULT
            return EntityVideoSensorHistoryView().get( request, **kwargs )


class EntityVideoStreamView( HiGridView, EntityViewMixin ):
    """View for displaying entity-based video streams."""

    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_pane.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        # Check if entity has video stream capability
        if not entity.has_video_stream:
            raise BadRequest( 'Entity does not have video stream capability.' )

        # Get the integration gateway for this entity (Do we really need this check?)
        integration_gateway = IntegrationManager().get_integration_gateway( entity.integration_id )
        if not integration_gateway:
            raise BadRequest( 'Integration not available for video stream.' )

        # Find the first sensor with video capability for history browsing
        video_sensor = VideoStreamBrowsingHelper.find_video_sensor_for_entity(entity)

        if not video_sensor:
            raise BadRequest( 'Entity does not have any video stream sensors.' )
        
        request.view_parameters.view_type = ViewType.ENTITY_VIDEO_STREAM
        request.view_parameters.to_session( request )
        return {
            'entity': entity,
            'video_sensor': video_sensor,  # May be None if no video sensors
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
        if not sensor.provides_video_stream:
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
        lock_password = ConsoleSettingsHelper().get_console_lock_password()
        if not lock_password:
            return SetLockPasswordView().get( request, *args, **kwargs )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )

    
class SetLockPasswordView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'console/modals/set_lock_password.html'
    
    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )
    
    def post( self, request, *args, **kwargs ):
        input_password = request.POST.get('password')
        if not input_password:
            raise BadRequest( 'No password provided.' )
        ConsoleSettingsHelper().set_console_lock_password( password = input_password )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )

    
class ConsoleUnlockView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'console/modals/console_unlock.html'

    def get(self, request, *args, **kwargs):
        return self.modal_response( request, status = 403 )
                                    
    def post(self, request, *args, **kwargs):

        # N.B. Simplified security of console locking for now. Just meant
        # to be used when visitors in the house to prevent snooping. Beef
        # up security here if/when needed, but eventual login requirements
        # and its session will be the main auth method.
        
        input_password = request.POST.get('password')
        if not input_password:
            raise BadRequest( 'No password provided.' )

        lock_password = ConsoleSettingsHelper().get_console_lock_password()

        if lock_password and ( input_password != lock_password ):
            raise BadRequest( 'Invalid password.' )
                               
        # N.B. It should not be possible to get into state where console is
        # locked without a password set.  However, if it happens, it would
        # be impossible to unlock the console. Thus, we'll unlock in that
        # exceptional case.

        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = False
        return self.refresh_response( request= request )
