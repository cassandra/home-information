from django.core.exceptions import BadRequest
from django.http import Http404
from django.views.generic import View

from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor
from hi.apps.sense.tests.synthetic_data import SensorHistorySyntheticData
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


class EntityVideoSensorHistoryView( HiGridView ):
    """View for browsing sensor history records with video streams."""
    
    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_sensor_history.html'
    
    def get_main_template_context( self, request, *args, **kwargs ):
        entity_id = kwargs.get('entity_id')
        sensor_id = kwargs.get('sensor_id')
        integration_key = kwargs.get('integration_key')
        
        # Get the entity
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404('Entity not found.')
        
        # Check if entity has video stream capability
        if not entity.has_video_stream:
            raise BadRequest( 'Entity does not have video stream capability.' )
        
        # Get the sensor
        try:
            sensor = Sensor.objects.get( id = sensor_id, entity_state__entity = entity )
        except Sensor.DoesNotExist:
            raise Http404('Sensor not found for this entity.')
        
        # For Phase 1: Create mock sensor response data using synthetic data generator
        mock_sensor_responses = SensorHistorySyntheticData.create_mock_sensor_responses(
            sensor=sensor,
            current_id=integration_key
        )
        
        # Determine the current sensor response to display
        if integration_key:
            current_sensor_response = next(
                (r for r in mock_sensor_responses if str(r.integration_key) == integration_key), 
                None
            )
            if not current_sensor_response:
                current_sensor_response = mock_sensor_responses[0] if mock_sensor_responses else None
        else:
            # Default to most recent
            current_sensor_response = mock_sensor_responses[0] if mock_sensor_responses else None
        
        # Group sensor responses by time period using helper
        timeline_groups = VideoStreamBrowsingHelper.group_responses_by_time(mock_sensor_responses)
        
        # Find previous and next responses for navigation using helper
        current_key = str(current_sensor_response.integration_key) if current_sensor_response else None
        prev_sensor_response, next_sensor_response = VideoStreamBrowsingHelper.find_navigation_items(
            mock_sensor_responses, 
            current_key
        )
        
        request.view_parameters.view_type = ViewType.ENTITY_VIDEO_STREAM
        request.view_parameters.to_session( request )
        
        return {
            'entity': entity,
            'sensor': sensor,
            'current_sensor_response': current_sensor_response,
            'timeline_groups': timeline_groups,
            'prev_sensor_response': prev_sensor_response,
            'next_sensor_response': next_sensor_response,
            'sensor_responses': mock_sensor_responses,
        }


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
