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
    path( 'favicon.ico',
          RedirectView.as_view( url = staticfiles_storage.url('favicon.ico'),
                                permanent = False),
          name="favicon"
          ),

    re_path(r'^(?P<filename>(service-worker.js))$',
            views.home_javascript_files, name='home-javascript-files'),

    path( 'manifest.json', views.ManifestView.as_view(), name='manifest' ),


    path('admin/', admin.site.urls),

    path( '', views.HomeView.as_view(), name='home' ),
    path( 'index.html', views.HomeView.as_view(), name='home_index' ),
    path( 'start', views.StartView.as_view(), name='start' ),
    path( 'health', views.HealthView.as_view(), name='health' ),
    path( 'snap-grid', views.SetSnapGridView.as_view(), name='set_snap_grid' ),

    path( 'env/', include('hi.environment.urls' )),
    path( 'user/', include('hi.apps.user.urls' )),
    path( 'api/', include('hi.apps.api.urls' )),
    path( 'config/', include('hi.apps.config.urls' )),
    path( 'edit/', include('hi.apps.edit.urls' )),
    path( 'integration/', include('hi.integrations.urls' )),
    path( 'location/', include('hi.apps.location.urls' )),
    path( 'entity/', include('hi.apps.entity.urls' )),
    path( 'collection/', include('hi.apps.collection.urls' )),
    path( 'sense/', include('hi.apps.sense.urls' )),
    path( 'control/', include('hi.apps.control.urls' )),
    path( 'event/', include('hi.apps.event.urls' )),
    path( 'alert/', include('hi.apps.alert.urls' )),
    path( 'security/', include('hi.apps.security.urls' )),
    path( 'notify/', include('hi.apps.notify.urls' )),
    path( 'console/', include('hi.apps.console.urls' )),
    path( 'weather/', include('hi.apps.weather.urls' )),
    path( 'audio/', include('hi.apps.audio.urls' )),
    path( 'profiles/', include('hi.apps.profiles.urls' )),
    path( 'system/', include('hi.apps.system.urls' )),

    # Custom error pages
    path( '400.html', views.bad_request_response, name='bad_request' ),
    path( '403.html', views.not_authorized_response, name='not_authorized' ),
    path( '404.html', views.page_not_found_response, name='page_not_found' ),
    path( '405.html', views.method_not_allowed_response, name='method_not_allowed' ),
    path( '500.html', views.internal_error_response, name='internal_error' ),
    path( '503.html', views.transient_error_response, name='transient_error' ),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'hi.views.custom_404_handler'


if settings.DEBUG:
    urlpatterns += [
        path( 'testing/', include('hi.testing.urls' )),
    ]
