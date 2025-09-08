"""
ZMApi
=============
Python API wrapper for ZM.
Exposes login, monitors, events, etc. API

Important: 

  Make sure you have the following settings in ZM:
  
  - ``AUTH_RELAY`` is set to hashed
  - A valid ``AUTH_HASH_SECRET`` is provided (not empty)
  - ``AUTH_HASH_IPS`` is disabled
  - ``OPT_USE_APIS`` is enabled
  - If you are using any version lower than ZM 1.34, ``OPT_USE_GOOG_RECAPTCHA`` is disabled
  - If you are NOT using authentication at all in ZM, that is ``OPT_USE_AUTH`` is disabled, then make sure you also disable authentication in zmNinja, otherwise it will keep waiting for auth keys.
  - I don't quite know why, but on some devices, connection issues are caused because ZoneMinder's CSRF code causes issues. See `this <https://forums.zoneminder.com/viewtopic.php?f=33&p=115422#p115422>`__ thread, for example. In this case, try turning off CSRF checks by going to  ``ZM->Options->System`` and disable "Enable CSRF magic".

"""

import requests
import datetime
from .helpers.Base import Base
from .helpers.Monitors import Monitors
from .helpers.Events import Events
from .helpers.States import States
# from .helpers.Configs import Configs  # Not needed for our use case
from .helpers import globals as g

class ZMApi (Base):
    def __init__(self,options={}):
        '''
        Options is a dict with the following keys:

            - apiurl - the full API URL (example https://server/zm/api)
            - portalurl - the full portal URL (example https://server/zm). Only needed if you are downloading events/images
            - user - username (don't specify if no auth)
            - password - password (don't specify if no auth)
            - disable_ssl_cert_check - if True will let you use self signed certs
            - basic_auth_user - basic auth username
            - basic_auth_password - basic auth password
            Note: you can connect your own customer logging class to the API in which case all modules will use your custom class. Your class will need to implement some methods for this to work. See :class:`pyzm.helpers.Base.SimpleLog` for method details.
        '''
        
        self.api_url = options.get('apiurl')
        self.portal_url = options.get('portalurl')
        if not self.portal_url and self.api_url.endswith('/api'):
            self.portal_url = self.api_url[:-len('/api')] 
            g.logger.Debug(2, 'Guessing portal URL is: {}'.format(self.portal_url))

        self.options = options
        
        self.authenticated = False
        self.auth_enabled = True
        self.access_token = ''
        self.refresh_token = ''
        self.access_token_expires = None
        self.refresh_token_expires = None
        self.refresh_token_datetime = None
        self.access_token_datetime = None

        self.legacy_credentials = None
        self.session = requests.Session()
        if (self.options.get('basic_auth_user')):
            g.logger.Debug(2, 'Basic auth requested, configuring')
            self.session.auth = (self.options.get('basic_auth_user'), self.options.get('basic_auth_password'))
        if options.get('disable_ssl_cert_check', True):
            self.session.verify = False
            g.logger.Debug(2, 'API SSL certificate check has been disbled')
            from urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        self.api_version = None
        self.zm_version = None
        self.zm_tz = None
     
        self._login()
     
        self.Monitors = None
        self.Events = None
        self.Configs = None
    def _versiontuple(self,v):
        #https://stackoverflow.com/a/11887825/1361529
        return tuple(map(int, (v.split("."))))

    def get_session(self):
        return self.session

    def version(self):
        """Returns version of API and ZM
        
        Returns:
            dict: Version of API and ZM::

            {
                status: string # if 'error' then will also have 'reason' 
                api_version: string # if status is 'ok'
                zm_version: string # if status is 'ok'
            }
        """
        if not self.authenticated:
            return {'status':'error', 'reason':'not authenticated'}
        return {
            'status': 'ok',
            'api_version': self.api_version,
            'zm_version': self.zm_version
        }

    def tz(self):
        """Returns timezone of ZoneMinder server
       
        Returns:
           string: timezone of ZoneMinder server (or None if API not supported)
        """
        if not self.zm_tz:
            url = self.api_url + '/host/gettimezone.json'
            
            try:
                r = self._make_request(url=url)
                self.zm_tz = r.get('tz')
            except requests.exceptions.HTTPError as err:
                g.logger.Error ('Timezone API not found, relative timezones will be local time')
        return self.zm_tz

    def authenticated(self):
        """True if login API worked
        
        Returns:
            boolean -- True if Login API worked
        """
        return self.authenticated

    # called in _make_request to avoid 401s if possible
    def _refresh_tokens_if_needed(self):
        if not (self.access_token_expires and self.refresh_token_expires):
            return
        tr = (self.access_token_datetime - datetime.datetime.now()).total_seconds()
        if (tr >= 60*5): # 5 mins grace 
            g.logger.Debug(3, 'No need to relogin as access token still has {} minutes remaining'.format(tr/60))
            return
        else:
            self._relogin()
              
    def _relogin(self):
        """ Used for 401. I could use _login too but decided to do a simpler fn
        """
        url = self.api_url+'/host/login.json'
        if self._versiontuple(self.api_version) >= self._versiontuple('2.0'):
            # use tokens
            tr = (self.refresh_token_datetime - datetime.datetime.now()).total_seconds()

            if (tr >= 60 * 5): # 5 mins grace
                g.logger.Debug(2, 'Going to use refresh token as it still has {} minutes remaining'.format(tr/60))
                self.options['token'] = self.refresh_token
            else:
                g.logger.Debug(1, 'Refresh token only has {}s of lifetime, going to use user/pass'.format(tr))
                self.options['token'] = None
        self._login()

    def _login(self):
        """This is called by the constructor. You are not expected to call this directly.
        
        Raises:
            err: reason for failure
        """
        try:
            url = self.api_url+'/host/login.json'
            if self.options.get('token'):
                g.logger.Debug(1,'Using token for login [{}]'.format(self.options.get('token')))
                data = {'token':self.options.get('token')}
                self.auth_enabled = True

            elif self.options.get('user') and self.options.get('password'):
                g.logger.Debug(1, 'using username/password for login')
                data={'user': self.options.get('user'), 'pass': self.options.get('password') }
                self.auth_enabled = True

            else:
                g.logger.Debug(1, 'Not using auth')
                self.auth_enabled = False
                data = {}
                url = self.api_url + '/host/getVersion.json'
                
            r = self.session.post(url, data=data)
            if r.status_code == 401 and self.options.get('token') and self.auth_enabled:
                g.logger.Debug(1, 'Token auth with refresh failed. Likely revoked, doing u/p login')
                self.options['token'] = None
                data={'user': self.options.get('user'), 'pass': self.options.get('password')}
                r = self.session.post(url, data=data)
                r.raise_for_status()
            else:
                r.raise_for_status()

            g.logger.Debug(1, r.text)
            rj = r.json()
            self.api_version = rj.get('apiversion')
            self.zm_version = rj.get('version')
            if self.auth_enabled:
                if (self._versiontuple(self.api_version) >= self._versiontuple('2.0')):
                    g.logger.Debug(2, 'Using new token API')
                    self.access_token = rj.get('access_token','')
                    if rj.get('refresh_token'):
                        self.refresh_token = rj.get('refresh_token')
                    if (rj.get('access_token_expires')):
                        self.access_token_expires = int(rj.get('access_token_expires'))
                        self.access_token_datetime = datetime.datetime.now() + datetime.timedelta(seconds = self.access_token_expires)
                        g.logger.Debug(1, 'Access token expires on:{} [{}s]'.format(self.access_token_datetime, self.access_token_expires))
                    if (rj.get('refresh_token_expires')):
                        self.refresh_token_expires = int(rj.get('refresh_token_expires'))
                        self.refresh_token_datetime = datetime.datetime.now() + datetime.timedelta(seconds = self.refresh_token_expires)
                        g.logger.Debug(1, 'Refresh token expires on:{} [{}s]'.format(self.refresh_token_datetime, self.refresh_token_expires))
                else:
                    g.logger.Info('Using old credentials API. Recommended you upgrade to token API')
                    self.legacy_credentials = rj.get('credentials')
                    if (rj.get('append_password') == '1'):
                        self.legacy_credentials = self.legacy_credentials + self.options.get('password')
            self.authenticated = True
            #print (vars(self.session))

        except requests.exceptions.HTTPError as err:
            g.logger.Error('Got API login error: {}'.format(err))
            self.authenticated = False
            raise err

    def get_apibase(self):
        return self.api_url

    def get_portalbase(self):
        return self.portal_url

    def get_auth(self):
        if not self.auth_enabled:
            return ''

        if self._versiontuple(self.api_version) >= self._versiontuple('2.0'):
            return 'token='+self.access_token
        else:
            return self.legacy_credentials


    def _make_request(self, url=None, query={}, payload={}, type='get', reauth=True):

        self._refresh_tokens_if_needed()
        type = type.lower()
        if self.auth_enabled:
            if self._versiontuple(self.api_version) >= self._versiontuple('2.0'):
                query['token'] = self.access_token
                # ZM 1.34 API bug, will be fixed soon
                # self.session = requests.Session()
        
            else:
                # credentials is already query formatted
                lurl = url.lower()
                if lurl.endswith('json') or lurl.endswith('/'):
                    qchar = '?'
                else:
                    qchar = '&'
                url += qchar + self.legacy_credentials
                
        try:
            g.logger.Debug(3, 'make_request called with url={} payload={} type={} query={}'.format(url,payload,type,query))
            if type=='get':
                r = self.session.get(url, params=query)

            elif type=='post':
                r = self.session.post(url, data=payload, params=query)
            elif type=='put':
                r = self.session.put(url, data=payload, params=query)
            elif type=='delete':
                r = self.session.delete(url, data=payload, params=query)
            else:
                g.logger.Error('Unsupported request type:{}'.format(type))
                raise ValueError ('Unsupported request type:{}'.format(type))
            #print (url, params)
            #r = requests.get(url, params=params)
            #print(r.request.headers)

            r.raise_for_status()

            # Empty response, e.g. to DELETE requests, can't be parsed to json
            # even if the content-type says it is application/json

            if r.headers.get('content-type').startswith("application/json") and r.text:
                return r.json()
            elif r.headers.get('content-type').startswith('image/'):
                return r
            elif type=='delete':
                return None
            else:
                # A non 0 byte response will usually mean its an image eid request that needs re-login
                if r.headers.get('content-length') != '0':
                    g.logger.Debug(2, 'Raising RELOGIN ValueError')
                    raise ValueError ("RELOGIN")
                else:
                    # ZM returns 0 byte body if index not found
                    g.logger.Debug(2, 'Raising BAD_IMAGE ValueError as Content-Length:0')
                    raise ValueError ("BAD_IMAGE")
                #return r.text

        except requests.exceptions.HTTPError as err:
            g.logger.Debug(1, 'HTTP error: {}'.format(err))
            if err.response.status_code == 401 and reauth:
                g.logger.Debug(1, 'Got 401 (Unauthorized) - retrying login once')
                self._relogin()
                g.logger.Debug(1, 'Retrying failed request again...')
                return self._make_request(url, query, payload, type, reauth=False)
            elif err.response.status_code == 404:
                # ZM returns 404 when an image cannot be decoded
                g.logger.Debug(3, 'Raising BAD_IMAGE ValueError for a 404')
                raise ValueError ("BAD_IMAGE")
        except ValueError as err:
            err_msg = '{}'.format(err)
            if err_msg == "RELOGIN":
                if reauth:
                    g.logger.Debug(1, 'Got ValueError access error: {}'.format(err))
                    g.logger.Debug(1, 'Retrying login once')
                    self._relogin()
                    g.logger.Debug(1, 'Retrying failed request again...')
                    return self._make_request(url, query, payload, type, reauth=False)
                else:
                    raise err
            elif err_msg == "BAD_IMAGE":
                raise ValueError ("BAD_IMAGE")
        
       


    def monitors(self, options={}):
        """Returns list of monitors. Given monitors are fairly static, maintains a cache and returns from cache on subsequent calls.
                
            Args:
                options (dict, optional): Available fields::
            
                    {
                        'force_reload': boolean # if True refreshes monitors 

                    }
            
        Returns:
            list of :class:`pyzm.helpers.Monitor`: list of monitors 
        """
        if options.get('force_reload') or not self.Monitors:
            self.Monitors = Monitors(api=self)
        return self.Monitors

    def events(self,options={}):
        """Returns list of events based on filter criteria. Note that each time you called events, a new HTTP call is made.
        
        Args:
            options (dict, optional): Various filters that will be applied to events. Defaults to {}. Available fields::
        
                {
                    'event_id': string # specific event ID to fetch
                    'tz': string # long form timezone (example America/New_York),
                    'from': string # string # minimum start time (including human readable
                                   # strings like '1 hour ago' or '10 minutes ago to 5 minutes ago' to create a range)
                    'to': string # string # maximum end time
                    'mid': int # monitor id
                    'min_alarmed_frames': int # minimum alarmed frames
                    'max_alarmed_frames': int # maximum alarmed frames
                    'object_only': boolean # if True will only pick events 
                                           # that have objects

                }
        
        Returns:
            list of :class:`pyzm.helpers.Event`: list of events that match criteria
        """
        self.Events = Events(api=self, options=options)
        return self.Events

    def states(self, options={}):
        """Returns configured states
        
        Args:
            options (dict, optional): Not used. Defaults to {}.
        
        Returns:
            list of  :class:`pyzm.helpers.State`: list of states
        """
        self.States = States(api=self)
        return self.States
    
    def restart(self):
        """Restarts ZoneMinder
        
        Returns:
            json: json value of restart command
        """
        return self.set_state(state='restart')
    
    def stop(self):
        """Stops ZoneMinder
        
        Returns:
            json: json value of stop command
        """
        return self.set_state(state='stop')
    
    def start(self):
        """Starts ZoneMinder
        
        Returns:
            json: json value of start command
        """
        return self.set_state(state='start')
    
    def set_state(self, state):
        """Sets Zoneminder state to specific state 
        
        Args:
            state (string): Name of state    
        
        Returns:
            json: value of state change command
        """
        if not state:
            return
        url = self.api_url +'/states/change/{}.json'.format(state)
        return self._make_request(url=url)

    def configs(self, options={}):
        """Returns config values of ZM
        
            Args:
                options (dict, optional): Defaults to {}.
                options::

                    {
                        'force_reload': boolean # if True, reloads  
                    }
        
        Returns:
            :class:`pyzm.helpers.Configs`: ZM configs
        """
        if options.get('force_reload') or not self.Configs:
            self.Configs = Configs(api=self)
        return self.Configs
