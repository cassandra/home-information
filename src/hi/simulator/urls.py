from django.apps import apps
from django.urls import include, re_path

from hi.apps.common.module_utils import import_module_safe

from . import views

urlpatterns = [

    re_path( r'^$',
             views.HomeView.as_view(),
             name = 'simulator_home' ),
    
    re_path( r'^profile/create$',
             views.ProfileCreateView.as_view(),
             name = 'simulator_profile_create' ),
    
    re_path( r'^profile/edit/(?P<profile_id>\d+)$',
             views.ProfileEditView.as_view(),
             name = 'simulator_profile_edit' ),
    
    re_path( r'^profile/delete/(?P<profile_id>\d+)$',
             views.ProfileDeleteView.as_view(),
             name = 'simulator_profile_delete' ),
    
    re_path( r'^profile/switch/(?P<profile_id>\d+)$',
             views.ProfileSwitchView.as_view(),
             name = 'simulator_profile_switch' ),
    
    re_path( r'^add-entity/(?P<simulator_id>[\w_]+)$',
             views.AddEntityView.as_view(),
             name = 'simulator_add_entity' ),
]


def discover_urls():
    """ Add urls (if any) from all simulated integration services """
    
    discovered_url_modules = dict()
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith( 'hi.simulator.services' ):
            continue
        module_name = f'{app_config.name}.urls'
        short_name = app_config.name.split('.')[-1]
        try:
            urls_module = import_module_safe( module_name = module_name )
            if not urls_module:
                continue

            discovered_url_modules[short_name] = urls_module

        except Exception:
            pass
        continue

    return discovered_url_modules


for short_name, urls_module in discover_urls().items():
    urlpatterns.append(
        re_path(f"services/{short_name}/", include( urls_module ))
    )
    continue
