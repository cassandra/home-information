from django.urls import path
from django.urls import include

from . import views


urlpatterns = [

    path( '', 
          views.TestingHomeView.as_view(), 
          name='testing_home'),

    path( 'ui/', include('hi.testing.ui.urls' )),
    path( 'devtools/', include('hi.testing.devtools.urls' )),

]
