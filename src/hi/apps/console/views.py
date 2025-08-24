from django.core.exceptions import BadRequest
from django.http import Http404
from django.views.generic import View

from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor, SensorHistory
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
        sensor_history_id = kwargs.get('sensor_history_id')
        
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
        
        # Smart query strategy: get timeline window based on whether we have a specific record
        if sensor_history_id:
            # Specific record requested - get timeline window centered around it
            try:
                current_history_record = SensorHistory.objects.get(
                    id=sensor_history_id,
                    sensor=sensor,
                    has_video_stream=True
                )
                # Get timeline window centered around this record
                sensor_responses, pagination_metadata = self._get_timeline_window(
                    sensor, current_history_record
                )
                # Current record is guaranteed to be in the timeline
                current_sensor_response = next(
                    (r for r in sensor_responses 
                     if r.detail_attrs and r.detail_attrs.get('sensor_history_id') == str(sensor_history_id)),
                    None
                )
            except SensorHistory.DoesNotExist:
                # Record not found - fall back to most recent window
                sensor_responses, pagination_metadata = self._get_timeline_window(sensor, None)
                current_sensor_response = sensor_responses[0] if sensor_responses else None
        else:
            # No specific record - get most recent window
            sensor_responses, pagination_metadata = self._get_timeline_window(sensor, None)
            current_sensor_response = sensor_responses[0] if sensor_responses else None
        
        # Group sensor responses by time period using helper
        timeline_groups = VideoStreamBrowsingHelper.group_responses_by_time(sensor_responses)
        
        # Find previous and next responses for efficient navigation
        current_history_id = sensor_history_id if sensor_history_id else None
        prev_sensor_response, next_sensor_response = self._find_adjacent_records(
            sensor, current_history_id
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
            'sensor_responses': sensor_responses,
            'pagination_metadata': pagination_metadata,  # For future pagination feature
        }
    
    def _find_adjacent_records(self, sensor: Sensor, current_history_id: int) -> tuple:
        """
        Find previous and next SensorHistory records for navigation.
        Uses database queries for efficient navigation.
        
        Args:
            sensor: Sensor to find records for
            current_history_id: ID of current SensorHistory record
            
        Returns:
            Tuple of (prev_sensor_response, next_sensor_response), either can be None
        """
        if not current_history_id:
            return (None, None)
        
        try:
            current_record = SensorHistory.objects.get(
                id=current_history_id,
                sensor=sensor,
                has_video_stream=True
            )
        except SensorHistory.DoesNotExist:
            return (None, None)
        
        # Find previous record (older timestamp)
        prev_record = SensorHistory.objects.filter(
            sensor=sensor,
            has_video_stream=True,
            response_datetime__lt=current_record.response_datetime
        ).order_by('-response_datetime').first()
        
        prev_sensor_response = None
        if prev_record:
            prev_sensor_response = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(prev_record)
        
        # Find next record (newer timestamp)
        next_record = SensorHistory.objects.filter(
            sensor=sensor,
            has_video_stream=True,
            response_datetime__gt=current_record.response_datetime
        ).order_by('response_datetime').first()
        
        next_sensor_response = None
        if next_record:
            next_sensor_response = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(next_record)
        
        return (prev_sensor_response, next_sensor_response)
    
    def _get_timeline_window(self, sensor: Sensor, center_record: SensorHistory = None, window_size: int = 50):
        """
        Get a timeline window of SensorHistory records around a center record.
        Designed to support future pagination functionality.
        
        Args:
            sensor: Sensor to get records for
            center_record: Record to center the window around (None for most recent)
            window_size: Total number of records to include
            
        Returns:
            Tuple of (sensor_responses_list, pagination_metadata)
        """
        if center_record is None:
            # No center record - get most recent records (default behavior)
            history_records = SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True
            ).order_by('-response_datetime')[:window_size]
            
            has_older_records = len(history_records) == window_size
            has_newer_records = False
            window_center_timestamp = history_records[0].response_datetime if history_records else None
        else:
            # Center window around specific record
            half_window = window_size // 2
            
            # Get records before center (older timestamps)
            before_records = list(SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True,
                response_datetime__lt=center_record.response_datetime
            ).order_by('-response_datetime')[:half_window])
            
            # Get records after center (newer timestamps) 
            after_records = list(SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True,
                response_datetime__gt=center_record.response_datetime
            ).order_by('response_datetime')[:half_window])
            
            # Combine all records in chronological order (newest first)
            history_records = list(reversed(after_records)) + [center_record] + before_records
            
            # Pagination metadata for future use
            has_older_records = len(before_records) == half_window
            has_newer_records = len(after_records) == half_window
            window_center_timestamp = center_record.response_datetime
        
        # Convert to SensorResponse objects
        sensor_responses = []
        for record in history_records:
            sensor_response = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record)
            sensor_responses.append(sensor_response)
        
        # Pagination metadata for future pagination feature
        pagination_metadata = {
            'has_older_records': has_older_records,
            'has_newer_records': has_newer_records,
            'window_center_timestamp': window_center_timestamp,
            'window_size': window_size,
        }
        
        return sensor_responses, pagination_metadata


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
