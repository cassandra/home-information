from django.urls import path

from . import views


urlpatterns = [

    path( '',
          views.ProfileDevtoolsHomeView.as_view(), 
          name='profiles_devtools'),

    path('snapshot',
         views.ProfileDevtoolsSnapshotView.as_view(), 
         name='profiles_devtools_snapshot'),
]
