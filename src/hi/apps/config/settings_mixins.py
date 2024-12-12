from asgiref.sync import sync_to_async

from .settings_manager import SettingsManager


class SettingsMixin:
    
    def settings_manager(self):
        if not hasattr( self, '_settings_manager' ):
            self._settings_manager = SettingsManager()
        return self._settings_manager
        
    async def settings_manager_async(self):
        if not hasattr( self, '_settings_manager' ):
            self._settings_manager = await sync_to_async( SettingsManager )()
        return self._settings_manager
    
    
