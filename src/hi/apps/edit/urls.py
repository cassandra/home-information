from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^start$', 
             views.EditStartView.as_view(), 
             name='edit_start' ),

    re_path( r'^end$', 
             views.EditEndView.as_view(), 
             name='edit_end' ),
]
