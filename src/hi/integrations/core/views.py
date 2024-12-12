import logging

from django.core.exceptions import BadRequest
from django.db import transaction
from django.urls import reverse
from django.views.generic import View

from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView

from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView

from .forms import IntegrationAttributeFormSet
from .helpers import IntegrationHelperMixin
from .integration_manager import IntegrationManager
from .integration_data import IntegrationData

logger = logging.getLogger(__name__)


class IntegrationPageView( ConfigPageView ):
    """
    The integrations page is shown as a vertically tabbed pane with one tab
    for each separate integration.  We want them to share some standard
    state tracking and consistent page rendering.  However, we also want
    the different integrations to remain somewhat independent.

    We do this with these:

      - IntegrationMetaData - Integrations discovered with the
        IntegrationManager defines their existence and common
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
        request.integration_data_list = IntegrationManager().get_integration_data_list( enabled_only = True )
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

        integration_data = IntegrationManager().get_default_integration_data()
        if not integration_data:
            return dict()

        redirect_url = reverse( integration_data.integration_metadata.manage_url_name )
        raise ForceRedirectException( redirect_url )

    
class IntegrationsManageView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'core/modals/integrations_manage.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'integration_data_list': IntegrationManager().get_integration_data_list(),
        }
        return self.modal_response( request, context )


class IntegrationsEnableView( HiModalView, IntegrationHelperMixin ):

    def get_template_name( self ) -> str:
        return 'core/modals/integration_enable.html'

    def get(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = IntegrationManager().get_integration_data(
            integration_id = integration_id,
        )
        if integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already enabled' )

        self._ensure_all_attributes_exist(
            integration_metadata = integration_data.integration_metadata,
            integration = integration_data.integration,
        )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration_data.integration,
            prefix = f'integration-{integration_id}',
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        context = {
            'integration_data': integration_data,
            'integration_attribute_formset': integration_attribute_formset,
        }
        return self.modal_response( request, context )

    def post(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = IntegrationManager().get_integration_data(
            integration_id = integration_id,
        )
        if integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already enabled' )
        
        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration_data.integration,
            prefix = f'integration-{integration_id}',
        )
        if not integration_attribute_formset.is_valid():
            context = {
                'integration_data': integration_data,
                'integration_attribute_formset': integration_attribute_formset,
            }
            return self.modal_response( request, context, status_code = 400 )

        with transaction.atomic():
            integration_data.integration.is_enabled = True
            integration_data.integration.save()
            integration_attribute_formset.save()

        redirect_url = reverse( 'integrations_home' )
        return self.redirect_response( request, redirect_url )

    
class IntegrationsDisableView( HiModalView, IntegrationHelperMixin ):

    def get_template_name( self ) -> str:
        return 'core/modals/integration_disable.html'

    def get(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = IntegrationManager().get_integration_data(
            integration_id = integration_id,
        )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already disabled' )

        context = {
            'integration_data': integration_data,
        }
        return self.modal_response( request, context )
    
    def post(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = IntegrationManager().get_integration_data(
            integration_id = integration_id,
        )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already disabled' )

        with transaction.atomic():
            integration_data.integration.is_enabled = False
            integration_data.integration.save()

        redirect_url = reverse( 'integrations_home' )
        return self.redirect_response( request, redirect_url )
        
