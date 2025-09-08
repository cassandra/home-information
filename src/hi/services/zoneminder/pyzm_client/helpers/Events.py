"""
Events
=======
Holds a list of Events for a ZM configuration
You can pass different conditions to filter the events
Each invocation results in a new API call as events are very dynamic

You are not expected to use this module directly. It is instantiated when you use the :meth:`pyzm.api.ZMApi.events` method of :class:`pyzm.api`
"""

from .Base import Base
from .Event import Event
#import requests  # Unused 
import dateparser
from . import globals as g


class Events(Base):
    def __init__(self, api=None, options=None):
       
        self.api = api
        self.events = []
        self.pagination = {}
        self._load(options)
    
    def list(self):
        """Returns list of event
        
        Returns:
            list -- events of :class:`.Event`
        """
        return self.events

    def count(self):
        """Returns number of events retrieved in previous invocation
        
        Returns:
            int -- number of events
        """
        return int(self.pagination.get('count'))

    def _load(self, options={}):
        g.logger.Debug(2,'Retrieving events via API')
        url_filter=''
       
        tz = {}

        if options.get('event_id'):
            url_filter += '/Id=:' + str(options.get('event_id'))
        if options.get('tz'):
            tz = {'TIMEZONE': options.get('tz')}
            #print ('USING ',tz)
        if options.get('from'):
            from_list = options.get('from').split(" to ", 1)
            if len(from_list) == 2:
                from_start = dateparser.parse(from_list[0], settings=tz)
                from_end = dateparser.parse(from_list[1], settings=tz)
                if from_start > from_end:
                    from_start, from_end = from_end, from_start

                url_filter += '/StartTime >=:'+from_start.strftime('%Y-%m-%d %H:%M:%S')
                url_filter += '/StartTime <=:' + from_end.strftime('%Y-%m-%d %H:%M:%S')
            else:
                url_filter += '/StartTime >=:' + dateparser.parse(from_list[0], settings=tz).strftime('%Y-%m-%d %H:%M:%S')
        if options.get('to'):
            to_list = options.get('to').split(" to ", 1)
            if len(to_list) == 2:
                to_start = dateparser.parse(to_list[0], settings=tz)
                to_end = dateparser.parse(to_list[1], settings=tz)
                if to_start > to_end:
                    to_start, to_end = to_end, to_start
                url_filter += '/EndTime <=:'+to_end.strftime('%Y-%m-%d %H:%M:%S')
                url_filter += '/EndTime >=:' + to_start.strftime('%Y-%m-%d %H:%M:%S')
            else:
                url_filter += '/EndTime <=:' + dateparser.parse(to_list[0], settings=tz).strftime('%Y-%m-%d %H:%M:%S')
        if options.get('mid'):
            url_filter += '/MonitorId =:'+str(options.get('mid'))
        if options.get('min_alarmed_frames'):
            url_filter += '/AlarmFrames >=:'+str(options.get('min_alarmed_frames'))
        if options.get('max_alarmed_frames'):
            url_filter += '/AlarmFrames <=:'+str(options.get('max_alarmed_frames'))
        if options.get('object_only'):
            url_filter += '/Notes REGEXP:detected:'

        # catch all
        if options.get('raw_filter'):
             url_filter+=options.get('raw_filter')


        #print ('URL filter: ',url_filter)
        # tbd - no need for url_prefix in options
    
        url_prefix = options.get('url_prefix',self.api.api_url + '/events/index' )
       
        url = url_prefix + url_filter +'.json'
        params = {
            'sort':'StartTime',
            'direction': 'desc',
            'page': 1
        }
        for k in options:
            if k in params:
                params[k] = options[k]

        numevents = 100
        if options.get('max_events'): numevents = options.get('max_events')
        if options.get('limit'): numevents = options.get('limit')
      
        params['limit'] = numevents
        currevents = 0
        self.events = []
        events= []
        while True:
            r = self.api._make_request(url=url, query=params)
            events.extend(r.get('events'))
            pagination = r.get('pagination')
            self.pagination = pagination
            if not pagination:
                break
            if  not pagination.get('nextPage'):
                break
            currevents += int(pagination.get('current'))
            if currevents >= numevents:
                break
            params['page'] +=1 
        
        for event in events:
            self.events.append(Event(event=event,api=self.api))
    
    def get(self, options={}):
        """Returns the full list of events. Typically useful if you need access to data for which you don't have an easy getter
        
        Keyword Arguments:
        
        - options: dict with same parameters as the one you pass in :meth:`pyzm.api.ZMApi.events`. This is really a convenience instead of re-creating the instance.
        
        Returns:
            list -- of :class:`pyzm.helpers.Events`
        """
        self._load(options)
        return self.events

  
        
