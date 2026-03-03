from django.urls import re_path

from . import views


urlpatterns = [

    re_path(
        r'^sync$',
        views.HbSyncView.as_view(),
        name='hb_sync',
    ),

]
