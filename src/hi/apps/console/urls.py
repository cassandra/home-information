from django.urls import re_path

from . import views


urlpatterns = [


    re_path( r'^entity/video-stream/(?P<entity_id>\d+)$', 
             views.EntityVideoStreamView.as_view(), 
             name='console_entity_video_stream'),

    re_path( r'^entity/video-sensor-history/(?P<entity_id>\d+)/(?P<sensor_id>\d+)/$', 
             views.EntityVideoSensorHistoryView.as_view(), 
             name='console_entity_video_sensor_history'),

    re_path( r'^entity/video-sensor-history/(?P<entity_id>\d+)/(?P<sensor_id>\d+)/(?P<integration_key>.+)/$', 
             views.EntityVideoSensorHistoryView.as_view(), 
             name='console_entity_video_sensor_history_detail'),

    re_path( r'^lock$', 
             views.ConsoleLockView.as_view(), 
             name='console_lock'),

    re_path( r'^set-lock-password$', 
             views.SetLockPasswordView.as_view(), 
             name='console_set_lock_password'),

    re_path( r'^unlock$', 
             views.ConsoleUnlockView.as_view(), 
             name='console_unlock'),
]
