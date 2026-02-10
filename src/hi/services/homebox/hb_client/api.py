import requests
import datetime
from .helpers.base import Base
from .helpers import globals as g


class HBApi(Base):
    def __init__(self, options={}):
        '''
        Options is a dict with the following keys:

            - apiurl - the full API URL (example https://server/hb/api)
            - portalurl - the full portal URL (example https://server/hb). Only needed if you are downloading events/images
            - user - username (don't specify if no auth)
            - password - password (don't specify if no auth)
            - disable_ssl_cert_check - if True will let you use self signed certs
            - basic_auth_user - basic auth username
            - basic_auth_password - basic auth password
            Note: you can connect your own customer logging class to the API in which case all modules will use your custom class. Your class will need to implement some methods for this to work. See :class:`pyzm.helpers.Base.ConsoleLog` for method details.
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
        self.access_token_expires = None
        self.access_token_datetime: datetime.datetime = None

        self.session = requests.Session()
        if (self.options.get('basic_auth_user')):
            g.logger.Debug(2, 'Basic auth requested, configuring')
            self.session.auth = (self.options.get('basic_auth_user'), self.options.get('basic_auth_password'))
        if options.get('disable_ssl_cert_check', True):
            self.session.verify = False
            g.logger.Debug(2, 'API SSL certificate check has been disbled')
            from urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
     
        self._login()

    def get_session(self):
        return self.session
    
    def version(self):
        """Returns version of API and HB
        
        Returns:
            dict: Version of API and HB:

                {
                status: string # if 'error' then will also have 'reason' 
                api_version: string # if status is 'ok'
                hb_version: string # if status is 'ok'
            }
        """
        if not self.authenticated:
            return {'status':'error', 'reason':'not authenticated'}
        
        return {
            'status': 'ok',
            'api_version': self.api_version,
            'hb_version': self.hb_version
        }
    
    def _login(self):
        """This is called by the constructor. You are not expected to call this directly.
        
        Raises:
            err: reason for failure
        """
        try:
            url = self.api_url + '/v1/users/login'

            if self.options.get('user') and self.options.get('password'):
                g.logger.Debug(1, 'using username/password for login')
                data = {'username': self.options.get('user'), 'password': self.options.get('password'), 'stayLoggedIn': True}
                self.auth_enabled = True

            else:
                g.logger.Debug(1, 'Not using auth')
                data = {}
                self.auth_enabled = False
                
            r = self.session.post(url, data=data, timeout=25.0)
            r.raise_for_status()

            g.logger.Debug(1, r.text)
            rj = r.json()

            if self.auth_enabled:
                self.access_token = rj.get('token', '')

                if (rj.get('expiresAt')):
                    self.access_token_datetime = rj.get('expiresAt')
                    g.logger.Debug(1, 'Access token expires on: {}'.format(self.access_token_datetime))

            self.authenticated = True

        except requests.exceptions.HTTPError as err:
            g.logger.Error('Got API login error: {}'.format(err))
            self.authenticated = False
            raise err
        
    # called in _make_request to avoid 401s if possible
    def _ensure_auth(self):
        tr = (self.access_token_datetime - datetime.datetime.now()).total_seconds()

        if (tr >= 60 * 5):  # 5 mins grace
            g.logger.Debug(3, 'No need to relogin as access token still has {} minutes remaining'.format(tr / 60))
            return
        
        self._login()

    def get_apibase(self):
        return self.api_url

    def get_portalbase(self):
        return self.portal_url
    
    def get_auth(self):
        if not self.auth_enabled:
            return ''
        return 'token=' + self.access_token

    def _make_request(self, url=None, query={}, payload={}, type='get', reauth=True):
       
        self._ensure_auth()

        type = type.lower()
        if self.auth_enabled:
            query['token'] = self.access_token
            self.session = requests.Session()
        
        try:
            g.logger.Debug(3, 'make_request called with url={} payload={} type={} query={}'.format(url, payload, type, query))
            if type == 'get':
                r = self.session.get(url, params=query, timeout=25.0)
            elif type == 'post':
                r = self.session.post(url, data=payload, params=query, timeout=25.0)
            elif type == 'put':
                r = self.session.put(url, data=payload, params=query, timeout=25.0)
            elif type == 'delete':
                r = self.session.delete(url, data=payload, params=query, timeout=25.0)
            else:
                g.logger.Error('Unsupported request type:{}'.format(type))
                raise ValueError('Unsupported request type:{}'.format(type))

            r.raise_for_status()

            if r.headers.get('content-type').startswith("application/json") and r.text:
                return r.json()
            elif r.headers.get('content-type').startswith('image/'):
                return r
            elif type == 'delete':
                return None
            else:
                # A non 0 byte response will usually mean its an image eid request that needs re-login
                if r.headers.get('content-length') != '0':
                    g.logger.Debug(2, 'Raising RELOGIN ValueError')
                    raise ValueError("RELOGIN")
                else:
                    # ZM returns 0 byte body if index not found
                    g.logger.Debug(2, 'Raising BAD_IMAGE ValueError as Content-Length:0')
                    raise ValueError("BAD_IMAGE")
                # return r.text

        except requests.exceptions.HTTPError as err:
            g.logger.Debug(1, 'HTTP error: {}'.format(err))
            if err.response.status_code == 401 and reauth:
                g.logger.Debug(1, 'Got 401 (Unauthorized) - retrying login once')
                self._login()
                g.logger.Debug(1, 'Retrying failed request again...')
                return self._make_request(url, query, payload, type, reauth=False)
            elif err.response.status_code == 404:
                # ZM returns 404 when an image cannot be decoded
                g.logger.Debug(3, 'Raising BAD_IMAGE ValueError for a 404')
                raise ValueError("BAD_IMAGE")
        except ValueError as err:
            err_msg = '{}'.format(err)
            if err_msg == "RELOGIN":
                if reauth:
                    g.logger.Debug(1, 'Got ValueError access error: {}'.format(err))
                    g.logger.Debug(1, 'Retrying login once')
                    self._login()
                    g.logger.Debug(1, 'Retrying failed request again...')
                    return self._make_request(url, query, payload, type, reauth=False)
                else:
                    raise err
            elif err_msg == "BAD_IMAGE":
                raise ValueError("BAD_IMAGE")