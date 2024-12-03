import logging
from typing import Dict, List

from hi.apps.common.singleton import Singleton
from hi.apps.monitor.monitor_manager import MonitorManager
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .integration_gateway import IntegrationGateway
from .models import Integration
from .transient_models import IntegrationData

logger = logging.getLogger(__name__)


class IntegrationFactory( Singleton ):

    def __init_singleton__( self ):
        self._integration_gateway_map : Dict[ str, IntegrationGateway ] = dict()
        self._integration_monitor_map : Dict[ str, PeriodicMonitor ] = dict()
        return

    def get_default_integration_data( self ):
        integration_data_list = self.get_integration_data_list( enabled_only = True )
        if not integration_data_list:
            return None
        return integration_data_list[0]

    def get_integration_data_list( self, enabled_only = False ) -> List[ IntegrationData ]:
        integration_data_list = list()
        if enabled_only:
            integration_queryset = Integration.objects.filter( is_enabled = True )
        else:
            integration_queryset = Integration.objects.all()
        integration_map = { x.integration_id: x for x in integration_queryset }

        for integration_id, integration_gateway in self._integration_gateway_map.items():
            integration_metadata = integration_gateway.get_meta_data()
            integration = integration_map.get( integration_id )
            if not integration and enabled_only:
                continue
            elif not integration:
                integration = Integration(
                    integration_id = integration_id,
                    is_enabled = False,
                )
            integration_data = IntegrationData(
                integration_metadata = integration_metadata,
                integration = integration,
            )
            integration_data_list.append( integration_data )
            continue

        integration_data_list.sort( key = lambda data : data.integration_metadata.label )
        return integration_data_list
    
    def get_integration_gateway( self, integration_id : str ) -> IntegrationGateway:
        if integration_id in self._integration_gateway_map:
            return self._integration_gateway_map[integration_id]
        raise KeyError( f'Unknown integration id "{integration_id}".' )
        
    def get_integration_monitor( self, integration_id : str ) -> PeriodicMonitor:
        return self._integration_monitor_map.get( integration_id )
        
    def register( self, integration_gateway  : IntegrationGateway ):
        integration_metadata = integration_gateway.get_meta_data()
        integration_id = integration_metadata.integration_id
        if integration_id in self._integration_gateway_map:
            logger.debug( f'Ignoring repeat integration registration: {integration_metadata.label}' )
            return
        logger.debug( f'Registering integration: {integration_metadata.label}' )
        self._integration_gateway_map[integration_id] = integration_gateway
        try:
            integration = Integration.objects.get( integration_id = integration_id )
            if integration.is_enabled:
                periodic_monitor = integration_gateway.get_sensor_monitor()
                self._integration_monitor_map[integration_id] = periodic_monitor
                MonitorManager().register( periodic_monitor )
        except Integration.DoesNotExist:
            pass
        return

