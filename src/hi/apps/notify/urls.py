from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^email/unsubscribe/(?P<token>[\w-]+)/(?P<email>.+)$', 
             views.EmailUnsubscribeView.as_view(), 
             name='notify_email_unsubscribe'),
]
