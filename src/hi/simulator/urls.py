from django.urls import re_path
from . import views

urlpatterns = [
    re_path( r'^simulate$', views.simulate, name = 'simulator_home' ),
    re_path( r'^setup$', views.setup, name = 'simulator_setup' ),
]
