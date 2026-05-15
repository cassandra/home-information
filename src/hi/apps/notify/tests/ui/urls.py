from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [

    path( '',
          views.TestUiNotifyHomeView.as_view(), 
          name='notify_tests_ui'),

    re_path( r'^email/view/(?P<email_type>\w+)$',
             views.TestUiViewEmailView.as_view(), 
             name='notify_tests_ui_view_email'),

    re_path( r'^email/send/(?P<email_type>\w+)$',
             views.TestUiSendEmailView.as_view(), 
             name='notify_tests_ui_send_email'),
]
