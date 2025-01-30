from asgiref.sync import sync_to_async

from .alert_manager import AlertManager


class AlertMixin:
    
    def alert_manager(self):
        if not hasattr( self, '_alert_manager' ):
            self._alert_manager = AlertManager()
            self._alert_manager.ensure_initialized()
        return self._alert_manager
        
    async def alert_manager_async(self):
        if not hasattr( self, '_alert_manager' ):
            self._alert_manager = AlertManager()



            import asyncio
            import hi.apps.common.debug_utils as debug_utils
            print( f'ALERT_MGR-ASYNC: %s' % debug_utils.get_event_loop_context() )



            
            try:

                
                #await asyncio.shield(sync_to_async(self._alert_manager.ensure_initialized)())
                self._alert_manager.ensure_initialized()


                
            except asyncio.CancelledError:
                print("⚠️ sync_to_async() was cancelled! Handling gracefully.")
                return None

            except Exception:
                print("⚠️ sync_to_async() raised an Exception.")
                return None

            
            
        return self._alert_manager
