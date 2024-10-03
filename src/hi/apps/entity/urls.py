from django.urls import include, re_path


urlpatterns = [

    re_path( r'^edit/', include('hi.apps.entity.edit.urls' )),

]
