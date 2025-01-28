from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUiUserHomeView.as_view(), 
             name='user_tests_ui'),

    re_path( r'^email/signin/view/(?P<email_type>\w+)$',
             views.TestUiViewSigninEmailView.as_view(), 
             name='user_tests_ui_view_signin_email'),

    re_path( r'^email/signin/send/(?P<email_type>\w+)$',
             views.TestUiSendSigninEmailView.as_view(), 
             name='user_tests_ui_send_signin_email'),
]
