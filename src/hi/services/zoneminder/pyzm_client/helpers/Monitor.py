"""
Monitor
=======
Each Monitor will hold a single ZoneMinder Monitor.
It is basically a bunch of getters for each access to event data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from .Base import Base


class Monitor(Base):
    def __init__(self, api=None, monitor=None):
        self.monitor = monitor
        self.api = api
    
    def get(self):
        """Returns monitor object
        
        Returns:
            :class:`pyzm.helpers.Monitor`: Monitor object
        """
        return self.monitor['Monitor']

    def enabled(self):
        """True if monitor is enabled
        
        Returns:
            bool: Enabled or not
        """
        return self.monitor['Monitor']['Enabled'] == '1'

    def function(self):
        """returns monitor function
        
        Returns:
            string: monitor function
        """
        return self.monitor['Monitor']['Function']
    
    def name(self):
        """Returns monitor name
        
        Returns:
            string: monitor name
        """
        return self.monitor['Monitor']['Name']
    
    def id(self):
        """Returns monitor Id
        
        Returns:
            int: Monitor Id
        """
        return int(self.monitor['Monitor']['Id'])

    def type(self):
        """Returns monitor type
        
        Returns:
            string: Monitor type
        """
        return self.monitor['Monitor']['Type']
    
    def dimensions(self):
        """Returns width and height of monitor
        
        Returns:
            dict: as below::

            {
                'width': int,
                'height': int
            }
        """
        return {'width': int(self.monitor['Monitor']['Width']),
                'height': int(self.monitor['Monitor']['Height'])}
    
    def events(self, options={}):
        """Returns events associated to the monitor, subject to filters in options
        
        Args:
            options (dict, optional): Same as options for :class:`pyzm.helpers.Event`. Defaults to {}.
        
        Returns:
           :class:`pyzm.helpers.Events`
        """
        options['mid'] = self.id()
        return self.api.events(options=options)

    def eventcount(self, options={}):
        """Returns count of events for monitor
        
        Args:
            options (dict, optional): Same as options for :class:`pyzm.helpers.Event`. Defaults to {}.
        
        Returns:
            int: count
        """
        # regular events API is more powerful than
        # console events as it allows us flexible timings
        # making limit=1 keeps the processing limited
        options['mid'] = self.id()
        options['max_events'] = 1
        return self.api.events(options=options).count()
        # print (s)
    
    def delete(self):
        """Deletes monitor
        
        Returns:
            json: API response
        """
        url = self.api.api_url + '/monitors/{}.json'.format(self.id())
        return self.api._make_request(url=url, type='delete')

    def set_parameter(self, options={}):
        """Changes monitor parameters
        
        Args:
            options (dict, optional): As below. Defaults to {}::

                {
                    'function': string # function of monitor
                    'name': string # name of monitor
                    'enabled': boolean
                    'raw': {
                        # Any other monitor value that is not exposed above. Example:
                        'Monitor[Colours]': '4',
                        'Monitor[Method]': 'simple'
                    }

                }
    
        
        Returns:
            json: API Response
        """
        url = self.api.api_url + '/monitors/{}.json'.format(self.id())
        payload = {}
        if options.get('function'):
            payload['Monitor[Function]'] = options.get('function')
        if options.get('name'):
            payload['Monitor[Name]'] = options.get('name')
        if options.get('enabled') is not None:
            enabled = '1' if options.get('enabled') else '0'
            payload['Monitor[Enabled]'] = enabled

        if options.get('raw'):
            for k in options.get('raw'):
                payload[k] = options.get('raw')[k]
               
        if payload:
            return self.api._make_request(url=url, payload=payload, type='post')

    def arm(self):
        """Arms monitor (forces alarm)
        
        Returns:
            json: API response
        """
        return self._set_alarm(type='on')

    def disarm(self):
        """Disarm monito (removes alarm)
        
        Returns:
            json: API response
        """
        return self._set_alarm(type='off')

    def _set_alarm(self, type='on'):
        url = self.api.api_url + '/monitors/alarm/id:{}/command:{}.json'.format(self.id(), type)
        return self.api._make_request(url=url)

    def status(self):
        """Returns status of monitor, as reported by zmdc
            TBD: crappy return, need to normalize
        
        Returns:
            json: API response
        """
        url = self.api.api_url + '/monitors/daemonStatus/id:{}/daemon:zmc.json'.format(self.id())
        return self.api._make_request(url=url)
