from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [

    path( '',
          views.TestUiUserHomeView.as_view(), 
          name='user_tests_ui'),

    re_path( r'^signin/code/(?P<state>\w+)$',
             views.TestUiMagicCodePageView.as_view(), 
             name='user_tests_ui_magic_code_page'),

    re_path( r'^email/signin/view/(?P<email_type>\w+)$',
             views.TestUiViewSigninEmailView.as_view(), 
             name='user_tests_ui_view_signin_email'),

    re_path( r'^email/signin/send/(?P<email_type>\w+)$',
             views.TestUiSendSigninEmailView.as_view(), 
             name='user_tests_ui_send_signin_email'),
]
