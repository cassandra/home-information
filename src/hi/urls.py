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
    re_path( r'^start$', views.StartView.as_view(), name='start' ),
    re_path( r'^health$', views.HealthView.as_view(), name='health' ),

    re_path( r'^env/', include('hi.environment.urls' )),
    re_path( r'^user/', include('hi.apps.user.urls' )),
    re_path( r'^api/', include('hi.apps.api.urls' )),
    re_path( r'^config/', include('hi.apps.config.urls' )),
    re_path( r'^edit/', include('hi.apps.edit.urls' )),
    re_path( r'^integration/', include('hi.integrations.urls' )),
    re_path( r'^location/', include('hi.apps.location.urls' )),
    re_path( r'^entity/', include('hi.apps.entity.urls' )),
    re_path( r'^collection/', include('hi.apps.collection.urls' )),
    re_path( r'^sense/', include('hi.apps.sense.urls' )),
    re_path( r'^control/', include('hi.apps.control.urls' )),
    re_path( r'^event/', include('hi.apps.event.urls' )),
    re_path( r'^alert/', include('hi.apps.alert.urls' )),
    re_path( r'^security/', include('hi.apps.security.urls' )),
    re_path( r'^notify/', include('hi.apps.notify.urls' )),
    re_path( r'^console/', include('hi.apps.console.urls' )),
    re_path( r'^weather/', include('hi.apps.weather.urls' )),
    re_path( r'^audio/', include('hi.apps.audio.urls' )),
    re_path( r'^profiles/', include('hi.apps.profiles.urls' )),

    # Custom error pages
    re_path( r'^400.html$', views.bad_request_response, name='bad_request' ),
    re_path( r'^403.html$', views.not_authorized_response, name='not_authorized' ),
    re_path( r'^404.html$', views.page_not_found_response, name='page_not_found' ),
    re_path( r'^405.html$', views.method_not_allowed_response, name='method_not_allowed' ),
    re_path( r'^500.html$', views.internal_error_response, name='internal_error' ),
    re_path( r'^503.html$', views.transient_error_response, name='transient_error' ),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'hi.views.custom_404_handler'


if settings.DEBUG:
    urlpatterns += [
        re_path( r'^testing/', include('hi.testing.urls' )),
    ]
