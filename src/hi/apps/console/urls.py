from django.urls import path

from . import views


urlpatterns = [

    path( 'entity/video-dispatch/<int:entity_id>',
          views.EntityVideoDispatchView.as_view(),
          name='console_entity_video_dispatch'),

    path( 'entity/video/<int:entity_id>',
          views.EntityVideoView.as_view(),
          name='console_entity_video'),

    path( 'entity/video-history/<int:entity_id>',
          views.EntityVideoHistoryView.as_view(),
          name='console_entity_sensor_video_history_default'),

    path( 'entity/video-sensor-history/<int:entity_id>/<int:sensor_id>/', 
          views.EntityVideoSensorHistoryView.as_view(), 
          name='console_entity_video_sensor_history'),

    path(
        'entity/video-sensor-history/<int:entity_id>/<int:sensor_id>/<int:sensor_history_id>/',
        views.EntityVideoSensorHistoryView.as_view(),
        name='console_entity_video_sensor_history_detail'),

    path(
        'entity/video-sensor-history/<int:entity_id>/<int:sensor_id>/<int:sensor_history_id>/<int:window_start>/<int:window_end>/',
        views.EntityVideoSensorHistoryView.as_view(),
        name='console_entity_video_sensor_history_detail_with_context'),

    path('entity/video-sensor-history/<int:entity_id>/<int:sensor_id>/earlier/<int:timestamp>/',
         views.EntityVideoSensorHistoryEarlierView.as_view(),
         name='console_entity_video_sensor_history_earlier'),

    path('entity/video-sensor-history/<int:entity_id>/<int:sensor_id>/later/<int:timestamp>/',
         views.EntityVideoSensorHistoryLaterView.as_view(),
         name='console_entity_video_sensor_history_later'),

    path( 'lock', 
          views.ConsoleLockView.as_view(), 
          name='console_lock'),

    path( 'set-lock-password', 
          views.SetLockPasswordView.as_view(), 
          name='console_set_lock_password'),

    path( 'unlock', 
          views.ConsoleUnlockView.as_view(), 
          name='console_unlock'),
]
