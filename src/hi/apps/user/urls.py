from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [

    path( 'signin', 
          views.UserSigninView.as_view(), 
          name='user_signin'),

    path( "signin/magic/code",
          views.SigninMagicCodeView.as_view(),
          name="user_signin_magic_code"),

    re_path( r"^signin/magic/link/(?P<token>[\w\-]+)/(?P<email>.+)$",
             views.SigninMagicLinkView.as_view(),
             name="user_signin_magic_link"),
]
