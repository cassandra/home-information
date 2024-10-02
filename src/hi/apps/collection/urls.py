from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^view/(?P<id>\d+)$', 
             views.CollectionView.as_view(), 
             name='collection_view'),

    re_path( r'^view$', 
             views.CollectionViewDefaultView.as_view(), 
             name='collection_view_default'),
]
