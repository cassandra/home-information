from django.urls import include, re_path

from . import async_views
from . import views


urlpatterns = [

    re_path( r'^view/(?P<id>\d+)$', 
             views.CollectionView.as_view(), 
             name='collection_view'),

    re_path( r'^view$', 
             views.CollectionViewDefaultView.as_view(), 
             name='collection_view_default'),

    re_path( r'^details/(?P<collection_id>\d+)$', 
             async_views.CollectionDetailsView.as_view(), 
             name='collection_details' ),

    re_path( r'^edit/', include('hi.apps.collection.edit.urls' )),
]
