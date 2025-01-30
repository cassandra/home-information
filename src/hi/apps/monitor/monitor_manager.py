import asyncio
import logging
import threading
from typing import List, Type

from django.apps import apps
from django.conf import settings

import hi.apps.common.debug_utils as debug_utils
from hi.apps.common.singleton import Singleton, SingletonGemini
from hi.apps.common.module_utils import import_module_safe

from .periodic_monitor import PeriodicMonitor

logger = logging.getLogger(__name__)


class AppMonitorManager( SingletonGemini ):

    def __init_singleton__( self ):
        print( 'START-USER-INIT' )

        

        
        self._monitor_map = dict()
        self._initialized = False
        self._data_lock = threading.Lock()


        import os
        pid = os.getpid()
        tid = threading.get_ident()
        logger.info( f'AppMonitorManager.__init__: self={self}, PID={pid}, TID={tid}' )


        print( 'END-USER-INIT' )

        
        return
    
    async def initialize(self) -> None:
        with self._data_lock:



            
            import os
            pid = os.getpid()
            tid = threading.get_ident()
            logger.info( f'AppMonitorManager.initialize: self={self}, PID={pid}, TID={tid}, init={self._initialized}' )



        

        
        
            if self._initialized:
                logger.info('MonitorManager already initialize. Skipping.')
                return
            self._initialized = True



            # INDENT HERE



            
        logger.info('Discovering and starting app monitors...')
        periodic_monitor_class_list = self._discover_periodic_monitors()        
        for monitor_class in periodic_monitor_class_list:
            monitor = monitor_class()



            print( f'MONITOR TRY {monitor.id}' )



            self._monitor_map[monitor.id] = monitor
            if not monitor.is_running:


                print( f'MONITOR NOT RUNNING {monitor.id}' )


                if settings.DEBUG and settings.SUPPRESS_MONITORS:
                    logger.debug(f'Skipping app monitor: {monitor.id}. See SUPPRESS_MONITORS = True')
                    continue

                logger.debug( f'Starting app monitor: {monitor.id}' )


                
                print( f'PRE-MONITOR-START: %s' % debug_utils.get_event_loop_context() )

                
                
                asyncio.create_task( monitor.start() )


                
                print( f'POST-CREATE-TASK {monitor.id}' )
                print( f'POST-CREATE {monitor.id}: %s' % debug_utils.get_event_loop_context() )



            else:
                print( f'MONITOR ALREADY RUNNING {monitor.id}' )

            continue
        return

    async def shutdown(self) -> None:
        logger.info('Stopping all registered app monitors...')
        for monitor in self._monitor_map.values():
            logger.debug( f'Stopping app monitor: {monitor.id}' )
            monitor.stop()
            continue
        return

    def _discover_periodic_monitors(self) -> List[ Type[ PeriodicMonitor ]]:
        periodic_monitor_class_list = list()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi.apps' ):
                continue
            module_name = f'{app_config.name}.monitors'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    continue

                logger.debug( f'Found monitor module for {app_config.name}' )
                
                for attr_name in dir(app_module):
                    attr = getattr( app_module, attr_name )
                    if ( isinstance( attr, type )
                         and issubclass( attr, PeriodicMonitor )
                         and attr is not PeriodicMonitor ):
                        logger.debug(f'Found periodic monitor: {attr_name}')
                        periodic_monitor_class_list.append( attr )
                    continue                
                
            except Exception as e:
                logger.exception( f'Problem loading monitor for {module_name}.', e )
            continue

        return periodic_monitor_class_list
       
