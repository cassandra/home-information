from asgiref.sync import sync_to_async
import asyncio
import logging

from django.core.exceptions import BadRequest
from django.http import Http404

from .models import Subsystem
from .settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class SettingsMixin:
    
    def settings_manager(self):
        if not hasattr( self, '_settings_manager' ):
            self._settings_manager = SettingsManager()
            self._settings_manager.ensure_initialized()
        return self._settings_manager
        
    async def settings_manager_async(self):
        if not hasattr( self, '_settings_manager' ):
            self._settings_manager = SettingsManager()
            try:
                await asyncio.shield( sync_to_async( self._settings_manager.ensure_initialized,
                                                     thread_sensitive = True )())

            except asyncio.CancelledError:
                logger.warning( 'Settings init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'Settings init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
            
        return self._settings_manager
    
    def get_subsystem( self, request, *args, **kwargs ) -> Subsystem:
        """ Assumes there is a required subsystem_id in kwargs """
        try:
            subsystem_id = int( kwargs.get( 'subsystem_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid subsystem id.' )
        try:
            return Subsystem.objects.get( id = subsystem_id )
        except Subsystem.DoesNotExist:
            raise Http404( request )
