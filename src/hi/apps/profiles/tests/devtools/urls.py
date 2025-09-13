from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.ProfileDevtoolsHomeView.as_view(), 
             name='profiles_devtools'),

    re_path(r'^snapshot$',
            views.ProfileDevtoolsSnapshotView.as_view(), 
            name='profiles_devtools_snapshot'),
]
