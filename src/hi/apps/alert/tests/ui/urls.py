from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUiAlertHomeView.as_view(), 
             name='alert_tests_ui'),

    re_path( r'^alert/details/(?P<alert_type>\w+)$',
             views.TestUiAlertDetailsView.as_view(), 
             name='alert_tests_ui_alert_details'),
]
