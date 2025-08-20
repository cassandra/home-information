from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from hi.apps.alert.alert_mixins import AlertMixin
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.alert.views import AlertDetailsView


class TestUiAlertHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "alert/tests/ui/home.html", context )

    
class TestUiAlertDetailsView( AlertDetailsView, AlertMixin ):
    """
    View for testing alert details dialogs with various synthetic data scenarios.
    """

    def get( self, request, *args, **kwargs ):
        alert_type = kwargs.get('alert_type')
        
        # Create synthetic alert based on type
        alert = self._create_synthetic_alert( alert_type )
        
        # Store alert in alert manager for retrieval 
        alert_manager = self.alert_manager()
        alert_manager._alert_queue._alert_list.append(alert)
        
        # Use parent class logic with synthetic alert
        kwargs['alert_id'] = alert.id
        return super().get( request, *args, **kwargs )

    def _create_synthetic_alert( self, alert_type ):
        """Create different types of synthetic alerts for testing."""
        
        if alert_type == 'single_info':
            return self._create_single_alarm_alert( AlarmLevel.INFO, has_image=False )
        elif alert_type == 'single_warning_image':
            return self._create_single_alarm_alert( AlarmLevel.WARNING, has_image=True )
        elif alert_type == 'single_critical_video':
            return self._create_single_alarm_alert( AlarmLevel.CRITICAL, has_image=True, video_like=True )
        elif alert_type == 'multiple_alarms':
            return self._create_multiple_alarm_alert( alarm_count=3, has_image=True )
        elif alert_type == 'event_based':
            return self._create_event_based_alert( has_image=True )
        elif alert_type == 'weather_alert':
            return self._create_weather_alert( has_image=False )
        else:
            raise BadRequest( f'Unknown alert type: {alert_type}' )

    def _create_single_alarm_alert( self, alarm_level, has_image=False, video_like=False ):
        """Create alert with single alarm."""
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.alert import Alert
        from hi.apps.security.enums import SecurityLevel
        import hi.apps.common.datetimeproxy as datetimeproxy
        
        image_url = None
        detail_attrs = {'Location': 'Kitchen', 'Sensor': 'Motion-01'}
        
        if has_image:
            if video_like:
                # Simulate video stream URL
                image_url = '/static/img/hi-icon-196x196.png'  # In real system would be video
                detail_attrs.update({
                    'Camera': 'Kitchen Camera',
                    'Motion Detected': 'Yes',
                    'Video Stream': 'Available'
                })
            else:
                image_url = '/static/img/hi-icon-196x196.png'
                detail_attrs.update({'Image': 'Captured'})
        
        alarm = Alarm(
            alarm_source = AlarmSource.EVENT,
            alarm_type = 'Motion Detection',
            alarm_level = alarm_level,
            title = f'{alarm_level.label}: Motion detected in Kitchen',
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = detail_attrs,
                    image_url = image_url,
                ),
            ],
            security_level = SecurityLevel.LOW,
            alarm_lifetime_secs = 300,
            timestamp = datetimeproxy.now(),
        )
        
        return Alert( first_alarm = alarm )

    def _create_multiple_alarm_alert( self, alarm_count=3, has_image=False ):
        """Create alert with multiple alarms."""
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.alert import Alert
        from hi.apps.security.enums import SecurityLevel
        import hi.apps.common.datetimeproxy as datetimeproxy
        from datetime import timedelta
        
        # Create first alarm
        image_url = '/static/img/hi-icon-196x196.png' if has_image else None
        first_alarm = Alarm(
            alarm_source = AlarmSource.EVENT,
            alarm_type = 'Repeated Motion',
            alarm_level = AlarmLevel.WARNING,
            title = 'WARNING: Repeated motion detected',
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = {
                        'Location': 'Living Room',
                        'Sensor': 'Motion-02',
                        'Count': '1 of 3'
                    },
                    image_url = image_url,
                ),
            ],
            security_level = SecurityLevel.LOW,
            alarm_lifetime_secs = 600,
            timestamp = datetimeproxy.now() - timedelta(minutes=5),
        )
        
        alert = Alert( first_alarm = first_alarm )
        
        # Add additional alarms
        for i in range(2, alarm_count + 1):
            additional_alarm = Alarm(
                alarm_source = AlarmSource.EVENT,
                alarm_type = 'Repeated Motion',
                alarm_level = AlarmLevel.WARNING,
                title = f'WARNING: Motion detected again ({i})',
                source_details_list = [
                    AlarmSourceDetails(
                        detail_attrs = {
                            'Location': 'Living Room',
                            'Sensor': 'Motion-02',
                            'Count': f'{i} of {alarm_count}'
                        },
                        image_url = image_url if i == 2 else None,  # Only second alarm has image
                    ),
                ],
                security_level = SecurityLevel.LOW,
                alarm_lifetime_secs = 600,
                timestamp = datetimeproxy.now() - timedelta(minutes=5 - i),
            )
            alert.add_alarm( additional_alarm )
        
        return alert

    def _create_event_based_alert( self, has_image=False ):
        """Create alert that simulates event-based triggering."""
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.alert import Alert
        from hi.apps.security.enums import SecurityLevel
        import hi.apps.common.datetimeproxy as datetimeproxy
        
        image_url = '/static/img/hi-icon-196x196.png' if has_image else None
        alarm = Alarm(
            alarm_source = AlarmSource.EVENT,
            alarm_type = 'Door Open Event',
            alarm_level = AlarmLevel.INFO,
            title = 'INFO: Front door opened',
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = {
                        'Event': 'Door State Change',
                        'Location': 'Front Door',
                        'Previous State': 'Closed',
                        'Current State': 'Open',
                        'Entity': 'front-door-sensor'
                    },
                    image_url = image_url,
                ),
            ],
            security_level = SecurityLevel.LOW,
            alarm_lifetime_secs = 180,
            timestamp = datetimeproxy.now(),
        )
        
        return Alert( first_alarm = alarm )

    def _create_weather_alert( self, has_image=False ):
        """Create weather-based alert."""
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.alert import Alert
        from hi.apps.security.enums import SecurityLevel
        import hi.apps.common.datetimeproxy as datetimeproxy
        
        image_url = '/static/img/hi-icon-196x196.png' if has_image else None
        alarm = Alarm(
            alarm_source = AlarmSource.WEATHER,
            alarm_type = 'Severe Weather',
            alarm_level = AlarmLevel.CRITICAL,
            title = 'CRITICAL: Tornado Warning issued',
            source_details_list = [
                AlarmSourceDetails(
                    detail_attrs = {
                        'Alert Type': 'Tornado Warning',
                        'Location': 'Travis County, TX',
                        'Urgency': 'Immediate',
                        'Severity': 'Extreme',
                        'Event': 'Tornado',
                        'Effective': 'Now',
                        'Expires': 'In 45 minutes'
                    },
                    image_url = image_url,
                ),
            ],
            security_level = SecurityLevel.HIGH,
            alarm_lifetime_secs = 2700,  # 45 minutes
            timestamp = datetimeproxy.now(),
        )
        
        return Alert( first_alarm = alarm )
