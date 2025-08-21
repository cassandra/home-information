import os
import json
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class DevInjectionManager:
    """
    External data injection for development testing.
    
    THEORY OF OPERATION:
    Injects test data into API responses for frontend testing without modifying
    backend state or triggering Django auto-reload. Requires DEBUG=True and 
    specific DEBUG_FORCE_* flags enabled.
    
    USAGE:
    # Inject test data
    python manage.py dev_inject transient_view '{"url":"/test","durationSeconds":10}'
    
    # Options: --persistent, --cache, --list, --clear
    
    ADDING NEW INJECTION POINTS:
    1. Add DEBUG_FORCE_<NAME>_OVERRIDE = False to settings/base.py and development.py
    2. Add get_<name>_override() and inject_<name>() methods to this class
    3. Update inject_override_if_available() method
    4. Add single line check to target view:
       if settings.DEBUG and getattr(settings, 'DEBUG_FORCE_<NAME>_OVERRIDE', False):
           DevInjectionManager.inject_override_if_available('<name>', data, 'key')
    5. Update management command with new injection type
    """
    
    CACHE_PREFIX = 'dev_inject_'
    DATA_DIR = '/tmp/hi_dev_overrides'
    
    @classmethod
    def _ensure_data_dir(cls):
        """Create data directory if it doesn't exist."""
        if not os.path.exists(cls.DATA_DIR):
            os.makedirs(cls.DATA_DIR, exist_ok=True)
    
    @classmethod
    def _get_file_path(cls, key):
        """Get file path for given injection key."""
        cls._ensure_data_dir()
        return os.path.join(cls.DATA_DIR, f"{key}.json")
    
    @classmethod
    def get_transient_view_override(cls):
        """
        Get transient view override data if force flag is enabled.
        Returns None if not enabled or no data available.
        """
        if not (settings.DEBUG and 
                getattr(settings, 'DEBUG_FORCE_TRANSIENT_VIEW_OVERRIDE', False)):
            return None
        
        # Check cache first (for one-time use)
        cache_key = f"{cls.CACHE_PREFIX}transient_view"
        cached_data = cache.get(cache_key)
        if cached_data:
            if cached_data.get('one_time', True):
                cache.delete(cache_key)
                if settings.DEBUG:
                    logger.info("DevInjection: Used one-time transient view override from cache")
            else:
                if settings.DEBUG:
                    logger.info("DevInjection: Used persistent transient view override from cache")
            return cached_data['data']
        
        # Check file (for persistent or file-based overrides)
        file_path = cls._get_file_path('transient_view')
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    file_data = json.load(f)
                
                payload = file_data.get('payload')
                if file_data.get('one_time', True):
                    os.remove(file_path)  # One-time use
                    if settings.DEBUG:
                        logger.info("DevInjection: Used one-time transient view override from file")
                else:
                    if settings.DEBUG:
                        logger.info("DevInjection: Used persistent transient view override from file")
                
                return payload
                
            except (json.JSONDecodeError, IOError) as e:
                if settings.DEBUG:
                    logger.warning(f"DevInjection: Error reading transient view override file: {e}")
                # Clean up bad file
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        
        return None
    
    @classmethod
    def inject_transient_view(cls, payload, one_time=True, use_cache=False):
        """
        Inject transient view data externally.
        
        Args:
            payload (dict): The transient view data to inject
            one_time (bool): Whether this should be consumed once or persist
            use_cache (bool): Whether to use cache (faster) or file (survives restarts)
        
        Returns:
            bool: True if injection was set up successfully
        """
        if not settings.DEBUG:
            if settings.DEBUG:
                logger.warning("DevInjection: Attempted injection in non-DEBUG mode")
            return False
        
        data = {'data': payload, 'one_time': one_time}
        
        if use_cache:
            cache_key = f"{cls.CACHE_PREFIX}transient_view"
            timeout = 300 if one_time else None  # 5 min timeout for one-time, none for persistent
            cache.set(cache_key, data, timeout=timeout)
            if settings.DEBUG:
                logger.info(f"DevInjection: Set transient view override in cache (one_time={one_time})")
        else:
            file_data = {'payload': payload, 'one_time': one_time}
            file_path = cls._get_file_path('transient_view')
            try:
                with open(file_path, 'w') as f:
                    json.dump(file_data, f, indent=2)
                if settings.DEBUG:
                    logger.info(f"DevInjection: Set transient view override in file (one_time={one_time})")
            except IOError as e:
                if settings.DEBUG:
                    logger.error(f"DevInjection: Failed to write override file: {e}")
                return False
        
        return True
    
    @classmethod
    def inject_override_if_available(cls, override_type, data_dict, key):
        """
        Single utility method for all injection points.
        This is the method called from the main code with your single-line pattern.
        
        Args:
            override_type (str): Type of override ('transient_view', etc.)
            data_dict (dict): The response dictionary to modify
            key (str): The key in data_dict to override
        """
        override_data = None
        
        if override_type == 'transient_view':
            override_data = cls.get_transient_view_override()
        # Future: Add other override types here
        # elif override_type == 'alert_status':
        #     override_data = cls.get_alert_status_override()
        
        if override_data:
            data_dict[key] = override_data
            if settings.DEBUG:
                logger.info(f"DevInjection: Applied {override_type} override to response")
    
    @classmethod
    def clear_all_overrides(cls):
        """Clear all cached and file-based overrides."""
        if not settings.DEBUG:
            return False
        
        # Clear cache
        cache_keys = [f"{cls.CACHE_PREFIX}transient_view"]
        for key in cache_keys:
            cache.delete(key)
        
        # Clear files
        if os.path.exists(cls.DATA_DIR):
            try:
                for filename in os.listdir(cls.DATA_DIR):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(cls.DATA_DIR, filename))
                if settings.DEBUG:
                    logger.info("DevInjection: Cleared all overrides")
                return True
            except OSError as e:
                if settings.DEBUG:
                    logger.error(f"DevInjection: Error clearing overrides: {e}")
        
        return False
    
    @classmethod
    def list_active_overrides(cls):
        """List all currently active overrides for debugging."""
        if not settings.DEBUG:
            return {}
        
        active = {}
        
        # Check cache
        cache_key = f"{cls.CACHE_PREFIX}transient_view"
        if cache.get(cache_key):
            active['transient_view_cache'] = True
        
        # Check files
        file_path = cls._get_file_path('transient_view')
        if os.path.exists(file_path):
            active['transient_view_file'] = True
        
        return active