import logging

from django.core.exceptions import BadRequest
from django.http import Http404
from django.urls import reverse
from django.views.generic import View

from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.sense.models import SensorHistory

from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView

from .integration_factory import IntegrationFactory
from .transient_models import IntegrationData

logger = logging.getLogger(__name__)


class IntegrationPageView( ConfigPageView ):
    """
    The integrations page is shown as a vertically tabbed pane with one tab
    for each separate integration.  We want them to share some standard
    state tracking and consistent page rendering.  However, we also want
    the different integrations to remain somewhat independent.

    We do this with these:

      - IntegrationMetaData - Integrations register this with the
        IntegrationFactory to define their exisatence and common
        properties.

      - IntegrationPageView (this view) - Each integration should subclass
        this for their main default view. It contains some state management
        and common needs for rendering itself in the overall
        IntegrationPageView, ConfigPageView and HiGridView view paradigms.

      - core/pages/integration_base.html (template) - The companion
        template for the main/entry view that ensure the integration pages
        are visually consistent (appearing as a tabbed pane) with
        navigation between integrations (and config sections).

    """

    def dispatch( self, request, *args, **kwargs ):
        request.integration_data_list = IntegrationFactory().get_integration_data_list( enabled_only = True )
        request.current_integration_metadata = self.integration_metadata
        return super().dispatch( request, *args, **kwargs )
    
    @property
    def integration_metadata(self) -> IntegrationData:
        raise NotImplementedError('Subclasses must override this method.')

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS
  
     
class IntegrationsHomeView( ConfigPageView ):

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS

    def get_main_template_name( self ) -> str:
        return 'core/pages/no_integrations.html'

    def get_template_context( self, request, *args, **kwargs ):

        integration_data = IntegrationFactory().get_default_integration_data()
        if not integration_data:
            return dict()

        redirect_url = reverse( integration_data.integration_metadata.manage_url_name )
        raise ForceRedirectException( redirect_url )

    
class IntegrationsManageView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'core/modals/integrations_manage.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'integration_data_list': IntegrationFactory().get_integration_data_list(),
        }
        return self.modal_response( request, context )

    
class IntegrationActionView( View ):

    def get(self, request, *args, **kwargs):

        error_message = None
        try:        
            integration_id = kwargs.get('integration_id')
            action = kwargs.get('action')

            integration_gateway = IntegrationFactory().get_integration_gateway(
                integration_id = integration_id,
            )
        
            if action == 'enable':
                return integration_gateway.enable_modal_view( request = request, *args, **kwargs )
            elif action == 'disable':
                return integration_gateway.disable_modal_view( request = request, *args, **kwargs )

            error_message = f'Unknown integration action "{action}".'
        except Exception as e:
            error_message = str(e)

        raise BadRequest( error_message )
