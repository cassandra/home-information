from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from . import views

urlpatterns = [

    # Favicons are tricky to get 100% right and some browsers will try
    # this no matter what.
    re_path( r'^favicon.ico$',
             RedirectView.as_view( url = staticfiles_storage.url('favicon.ico'),
                                   permanent = False),
             name="favicon"
             ),

    path('admin/', admin.site.urls),

    re_path( r'^$', views.HomeView.as_view(), name='home' ),
    re_path( r'^index.html$', views.HomeView.as_view(), name='home_index' ),
]
