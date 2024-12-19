from django.urls import re_path
from . import views

urlpatterns = [
    re_path( r'^$', views.simulate, name = 'home' ),
    re_path( r'^setup$', views.setup, name = 'setup' ),
]
