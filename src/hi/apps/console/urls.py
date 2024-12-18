from django.urls import re_path

from . import views


urlpatterns = [

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
