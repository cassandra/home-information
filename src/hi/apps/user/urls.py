from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^signin$', 
             views.UserSigninView.as_view(), 
             name='user_signin'),

    re_path( r"^signin/magic/code$",
             views.SigninMagicCodeView.as_view(),
             name="user_signin_magic_code"),

    re_path( r"^signin/magic/link/(?P<token>[\w\-]+)/(?P<email>.+)$",
             views.SigninMagicLinkView.as_view(),
             name="user_signin_magic_link"),
]
