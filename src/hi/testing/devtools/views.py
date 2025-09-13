import logging

from django.apps import apps
from django.shortcuts import render
from django.views.generic import View

from hi.apps.common.module_utils import import_module_safe

logger = logging.getLogger(__name__)


class DevtoolsHomeView( View ):

    def get(self, request, *args, **kwargs):

        app_url_list = []
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi' ):
                continue
            module_name = f'{app_config.name}.tests.devtools.urls'
            short_name = app_config.name.split('.')[-1]
            try:
                module = import_module_safe( module_name = module_name )
                if module:
                    app_url_list.append( ( short_name, f'{short_name}/' ) )
                
            except Exception as e:
                logger.exception( f'Problem loading DevTools for {short_name}.', e )

            continue
        context = {
            'app_url_list': app_url_list,
        }
        return render(request, 'testing/devtools/pages/testing_devtools_home.html', context )
