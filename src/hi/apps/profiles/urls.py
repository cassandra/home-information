from django.urls import re_path
from . import views

urlpatterns = [

    re_path( r'^initialize/(?P<profile_type>\w+)/$', 
             views.ProfilesInitializeView.as_view(), 
             name='profiles_initialize'),
    
    re_path( r'^help/view-mode$', 
             views.ViewModeHelpView.as_view(), 
             name='profiles_help_view_mode'),
    
    re_path( r'^help/edit-mode$', 
             views.EditModeHelpView.as_view(), 
             name='profiles_help_edit_mode'),
    
]
