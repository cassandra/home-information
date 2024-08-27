from django.conf import settings
from django.conf.urls.static import static
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

    re_path(r'^(?P<filename>(service-worker.js))$',
            views.home_javascript_files, name='home-javascript-files'),


    path('admin/', admin.site.urls),

    re_path( r'^$', views.HomeView.as_view(), name='home' ),
    re_path( r'^index.html$', views.HomeView.as_view(), name='home_index' ),

    re_path( r'^config/', include('hi.apps.config.urls' )),
    re_path( r'^edit/', include('hi.apps.edit.urls' )),
    re_path( r'^integration/', include('hi.integrations.core.urls' )),
    re_path( r'^location/', include('hi.apps.location.urls' )),
     
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
