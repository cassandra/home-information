from django.core.exceptions import BadRequest
from django.http import Http404, JsonResponse
from django.views.generic import View
from datetime import datetime
from django.utils import timezone

from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor
from hi.integrations.integration_manager import IntegrationManager

from hi.enums import ViewType
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView

from .constants import ConsoleConstants
from .console_helper import ConsoleSettingsHelper
from .video_stream_browsing_helper import VideoStreamBrowsingHelper


class EntityVideoStreamView( HiGridView ):
    """View for displaying entity-based video streams."""

    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_pane.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        entity_id = kwargs.get('entity_id')
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404('Entity not found.')

        # Check if entity has video stream capability
        if not entity.has_video_stream:
            raise BadRequest( 'Entity does not have video stream capability.' )

        # Get the integration gateway for this entity
        integration_gateway = IntegrationManager().get_integration_gateway( entity.integration_id )
        if not integration_gateway:
            raise BadRequest( 'Integration not available for video stream.' )

        # Get the video stream using the integration gateway
        if not entity.has_video_stream:
            raise BadRequest( 'Video stream is not currently available.' )

        # Find the first sensor with video capability for history browsing
        video_sensor = VideoStreamBrowsingHelper.find_video_sensor_for_entity(entity)
        
        request.view_parameters.view_type = ViewType.ENTITY_VIDEO_STREAM
        request.view_parameters.to_session( request )
        return {
            'entity': entity,
            'video_sensor': video_sensor,  # May be None if no video sensors
        }


class BaseEntityVideoSensorHistoryView( HiGridView ):
    """Base view for browsing sensor history records with video streams."""
    
    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_sensor_history.html'
    
    def get_main_template_context( self, request, *args, **kwargs ):
        """Common context building logic shared by all sensor history views."""
        entity_id = kwargs.get('entity_id')
        sensor_id = kwargs.get('sensor_id')
        
        # Get the entity
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404('Entity not found.')
        
        # Get the sensor
        try:
            sensor = Sensor.objects.get( id = sensor_id, entity_state__entity = entity )
        except Sensor.DoesNotExist:
            raise Http404('Sensor not found for this entity.')
        
        # Check if sensor provides video stream capability
        if not sensor.provides_video_stream:
            raise BadRequest( 'Sensor does not provide video stream capability.' )
        
        # Build sensor history data using subclass-specific method
        sensor_history_data = self.get_sensor_history_data(sensor, request, **kwargs)
        
        request.view_parameters.view_type = ViewType.ENTITY_VIDEO_STREAM
        request.view_parameters.to_session( request )
        
        return {
            'entity': entity,
            'sensor': sensor,
            'sensor_history_data': sensor_history_data,
        }
    
    def get_sensor_history_data(self, sensor, request, **kwargs):
        """Override in subclasses to provide specific sensor history data building logic."""
        raise NotImplementedError("Subclasses must implement get_sensor_history_data")


class EntityVideoSensorHistoryView( BaseEntityVideoSensorHistoryView ):
    """Default view for browsing sensor history records with video streams."""
    
    def get_sensor_history_data(self, sensor, request, **kwargs):
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
                return VideoStreamBrowsingHelper.build_sensor_history_data_with_window(
                    sensor, sensor_history_id, preserve_window_start, preserve_window_end
                )
            except (ValueError, OSError):
                # Invalid timestamp format - fall back to default
                pass
        
        # Default behavior
        return VideoStreamBrowsingHelper.build_sensor_history_data_default(
            sensor, sensor_history_id
        )


class EntityVideoSensorHistoryEarlierView( BaseEntityVideoSensorHistoryView ):
    """View for browsing earlier sensor history records (pagination)."""
    
    def get_sensor_history_data(self, sensor, request, **kwargs):
        """Get earlier sensor history data based on timestamp."""
        timestamp = kwargs.get('timestamp')
        if not timestamp:
            raise BadRequest('Timestamp parameter is required for earlier pagination.')
        
        try:
            return VideoStreamBrowsingHelper.build_sensor_history_data_earlier(
                sensor, int(timestamp)
            )
        except (ValueError, TypeError):
            raise BadRequest('Invalid timestamp format.')


class EntityVideoSensorHistoryLaterView( BaseEntityVideoSensorHistoryView ):
    """View for browsing later sensor history records (pagination)."""
    
    def get_sensor_history_data(self, sensor, request, **kwargs):
        """Get later sensor history data based on timestamp."""
        timestamp = kwargs.get('timestamp')
        if not timestamp:
            raise BadRequest('Timestamp parameter is required for later pagination.')
        
        try:
            return VideoStreamBrowsingHelper.build_sensor_history_data_later(
                sensor, int(timestamp)
            )
        except (ValueError, TypeError):
            raise BadRequest('Invalid timestamp format.')


class EntityVideoStreamDispatchView( View ):
    """
    Simple dispatch view for camera sidebar navigation.
    Routes to existing views based on referrer context.
    """
    
    def get( self, request, *args, **kwargs ):
        # Detect context from referrer URL
        referrer = request.META.get('HTTP_REFERER', '')
        is_history_context = VideoStreamBrowsingHelper.is_video_history_context(referrer)
        
        if is_history_context:
            # Route to history view with timeline preservation
            return self._dispatch_to_history_view(request, referrer, **kwargs)
        else:
            # Route to live stream view
            return self._dispatch_to_live_view(request, **kwargs)
    
    def _dispatch_to_live_view( self, request, **kwargs ):
        """Dispatch to EntityVideoStreamView and return JSON response."""
        view = EntityVideoStreamView()
        response = view.get(request, **kwargs)
        
        # Convert HiGridView response to JSON for JavaScript consumption
        if hasattr(response, 'content'):
            # Extract main content from the response
            html_content = response.content.decode('utf-8')
            return JsonResponse({
                'html': html_content,
                'navigation_type': 'live'
            })
        return response
    
    def _dispatch_to_history_view( self, request, referrer_url, **kwargs ):
        """Dispatch to EntityVideoSensorHistoryView with timeline preservation."""
        entity_id = kwargs.get('entity_id')
        
        # Get video sensor and timeline context from helper
        history_kwargs = VideoStreamBrowsingHelper.build_history_navigation_context(
            entity_id, referrer_url
        )
        
        # Update kwargs with history navigation context
        kwargs.update(history_kwargs)
        
        view = EntityVideoSensorHistoryView()
        response = view.get(request, **kwargs)
        
        # Convert HiGridView response to JSON for JavaScript consumption
        if hasattr(response, 'content'):
            html_content = response.content.decode('utf-8')
            return JsonResponse({
                'html': html_content,
                'navigation_type': 'history'
            })
        return response


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
        return self.modal_response( request )
                                    
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
