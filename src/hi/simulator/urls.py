import logging

from django.apps import apps
from django.contrib import admin
from django.urls import include, path, re_path

from hi.apps.common.module_utils import import_module_safe

from . import views

logger = logging.getLogger(__name__)


urlpatterns = [
    path( 'admin/', admin.site.urls ),

    path( '',
          views.HomeView.as_view(),
          name = 'simulator_home' ),
    
    path( 'profile/create',
          views.ProfileCreateView.as_view(),
          name = 'simulator_profile_create' ),
    
    path( 'profile/edit/<int:profile_id>',
          views.ProfileEditView.as_view(),
          name = 'simulator_profile_edit' ),
    
    path( 'profile/delete/<int:profile_id>',
          views.ProfileDeleteView.as_view(),
          name = 'simulator_profile_delete' ),

    path( 'profile/clone/<int:profile_id>',
          views.ProfileCloneView.as_view(),
          name = 'simulator_profile_clone' ),
    
    path( 'profile/switch/<int:profile_id>',
          views.ProfileSwitchView.as_view(),
          name = 'simulator_profile_switch' ),
    
    re_path( r'^entity/add/(?P<simulator_id>[\w_\-\.\:]+)/(?P<class_id>[\w\.\_]+)$',
             views.SimEntityAddView.as_view(),
             name = 'simulator_entity_add' ),
    
    path( 'entity/edit/<int:sim_entity_id>',
          views.SimEntityEditView.as_view(),
          name = 'simulator_entity_edit' ),
    
    path( 'entity/delete/<int:sim_entity_id>',
          views.SimEntityDeleteView.as_view(),
          name = 'simulator_entity_delete' ),
    
    re_path( r'^entity/state/set/(?P<simulator_id>[\w_\-\.\:]+)/(?P<sim_entity_id>\d+)/(?P<sim_state_id>[\w\-]+)$',
             views.SimStateSetView.as_view(),
             name = 'simulator_entity_state_set' ),

    re_path( r'^fault-mode/set/(?P<simulator_id>[\w_\-\.\:]+)$',
             views.SetSimulatorFaultModeView.as_view(),
             name = 'simulator_fault_mode_set' ),

    path( 'runtime/temperature-unit-override',
          views.TemperatureUnitOverrideSetView.as_view(),
          name = 'simulator_temperature_unit_override_set' ),
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
            logger.exception( f'Problem importing URL module: {module_name}' )
            pass
        continue

    return discovered_url_modules


for short_name, urls_module in discover_urls().items():
    urlpatterns.append(
        re_path(f"services/{short_name}/", include( urls_module ))
    )
    continue
