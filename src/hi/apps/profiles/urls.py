from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^initialize/(?P<profile_type>\w+)/$', 
            views.ProfilesInitializeView.as_view(), 
            name='profiles_initialize'),
]