from django.urls import path
from django.urls import include

from . import views


urlpatterns = [

    path( 'view/<int:collection_id>', 
          views.CollectionViewView.as_view(), 
          name='collection_view'),

    path( 'view', 
          views.CollectionViewDefaultView.as_view(), 
          name='collection_view_default'),


    path( 'edit/', include('hi.apps.collection.edit.urls' )),
]
