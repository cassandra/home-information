from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^view/(?P<id>\d+)$', 
             views.CollectionView.as_view(), 
             name='collection_view'),

    re_path( r'^view$', 
             views.CollectionViewDefaultView.as_view(), 
             name='collection_view_default'),

    re_path( r'^edit/', include('hi.apps.collection.edit.urls' )),
]
