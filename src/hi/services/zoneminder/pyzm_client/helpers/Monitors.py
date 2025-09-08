"""
Monitors
=========
Holds a list of Monitors for a ZM configuration
Given monitors are fairly static, maintains a cache of monitors
which can be overriden 
"""


from .Monitor import Monitor
from .Base import Base
from . import globals as g


class Monitors(Base):
    def __init__(self, api=None):
        self.api = api
        self._load()

    def _load(self, options={}):
        g.logger.Debug(2, 'Retrieving monitors via API')
        url = self.api.api_url + '/monitors.json'
        r = self.api._make_request(url=url)
        ms = r.get('monitors')
        self.monitors = []
        for m in ms:
            self.monitors.append(Monitor(monitor=m, api=self.api))

    def list(self):
        return self.monitors

    def add(self, options={}):
        """Adds a new monitor
        
        Args:
            options (dict): Set of attributes that define the monitor::

                {
                    'function': string # function of monitor
                    'name': string # name of monitor
                    'enabled': boolean
                    'protocol': string
                    'host': string
                    'port': int
                    'path': string
                    'width': int
                    'height': int
                    'raw': {
                        # Any other monitor value that is not exposed above. Example:
                        'Monitor[Colours]': '4',
                        'Monitor[Method]': 'simple'
                    }

                }
        
        Returns:
            json: json response of API request
        """
        url = self.api.api_url + '/monitors.json'
        payload = {}
        if options.get('function'):
            payload['Monitor[Function]'] = options.get('function')
        if options.get('name'):
            payload['Monitor[Name]'] = options.get('name')
        if options.get('enabled'):
            enabled = '1' if options.get('enabled') else '0'
            payload['Monitor[Enabled]'] = enabled
        if options.get('protocol'):
            payload['Monitor[Protocol]'] = options.get('protocol')
        if options.get('host'):
            payload['Monitor[Host]'] = options.get('host')
        if options.get('port'):
            payload['Monitor[Port]'] = str(options.get('port'))
        if options.get('path'):
            payload['Monitor[Path]'] = options.get('path')
        if options.get('width'):
            payload['Monitor[Width]'] = str(options.get('width'))
        if options.get('height'):
            payload['Monitor[Height]'] = str(options.get('height'))

        if options.get('raw'):
            for k in options.get('raw'):
                payload[k] = options.get('raw')[k]
               
        if payload:
            return self.api._make_request(url=url, payload=payload, type='post')
    
    def find(self, id=None, name=None):
        """Given an id or name, returns matching monitor object
        
        Args:
            id (int, optional): MonitorId of monitor. Defaults to None.
            name (string, optional): Monitor name of monitor. Defaults to None.
        
        Returns:
            :class:`pyzm.helpers.Monitor`: Matching monitor object
        """
        if not id and not name:
            return None
        match = None
        for mon in self.monitors:
            if id and mon.id() == id:
                match = mon
                break
            if name and mon.name().lower() == name.lower():
                match = mon
                break
        return match
