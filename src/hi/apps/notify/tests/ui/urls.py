from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUiNotifyHomeView.as_view(), 
             name='notify_tests_ui'),

    re_path( r'^email/view/(?P<name>\w+)$',
             views.TestUiViewEmailView.as_view(), 
             name='notify_tests_ui_view_email'),

    re_path( r'^email/send/(?P<name>\w+)$',
             views.TestUiSendEmailView.as_view(), 
             name='notify_tests_ui_send_email'),
]
