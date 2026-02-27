import requests
import datetime
from .helpers.base import Base
from .helpers import globals as g
from .helpers.items import HbItems


class HBApi(Base):
    def __init__(self, options={}):
        '''
        Options is a dict with the following keys:

            - apiurl - the full API URL (example https://server/hb/api)
            - portalurl - the full portal URL (example https://server/hb). Only needed if you are downloading events/images
            - user - username (don't specify if no auth)
            - password - password (don't specify if no auth)
        '''

        self.api_url = options.get('apiurl').rstrip('/')
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

        self.Items = None

        self.session = requests.Session()
     
        self._login()

    def get_session(self):
        return self.session
    
    def _login(self):
        """This is called by the constructor. You are not expected to call this directly.
        
        Raises:
            err: reason for failure
        """
        try:
            url = f"{self.api_url}/v1/users/login"

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

                self.session.headers.update({'Authorization': self.access_token})

                if (rj.get('expiresAt')):
                    expires_at = rj.get('expiresAt')
                    
                    if isinstance(expires_at, str):
                        expires_at = expires_at.replace('Z', '+00:00')
                        expires_at = datetime.datetime.fromisoformat(expires_at)

                    if isinstance(expires_at, datetime.datetime) and expires_at.tzinfo is not None:
                        expires_at = expires_at.astimezone(datetime.timezone.utc).replace(tzinfo=None)

                    self.access_token_datetime = expires_at
                    g.logger.Debug(1, 'Access token expires on: {}'.format(self.access_token_datetime))

            self.authenticated = True

        except requests.exceptions.HTTPError as err:
            g.logger.Error('Got API login error: {}'.format(err))
            self.authenticated = False
            raise err
        
    # called in _make_request to avoid 401s if possible
    def _ensure_auth(self):
        if not self.auth_enabled:
            return

        if not self.access_token_datetime:
            if not self.access_token:
                self._login()
            return

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

    def _make_request( self, 
                       url=None, 
                       query={}, 
                       payload={}, 
                       type='get', 
                       reauth=True, 
                       timeout=25.0, 
                       return_raw_response=False ):
        query = dict(query or {})
        payload = payload or {}

        self._ensure_auth()

        type = type.lower()
        
        try:
            g.logger.Debug(3, 'make_request called with url={} payload={} type={} query={}'.format(url, payload, type, query))
            
            if type == 'get':
                r = self.session.get(url, params=query, timeout=timeout)
            elif type == 'post':
                r = self.session.post(url, data=payload, params=query, timeout=timeout)
            elif type == 'patch':
                r = self.session.patch(url, data=payload, params=query, timeout=timeout)
            elif type == 'put':
                r = self.session.put(url, data=payload, params=query, timeout=timeout)
            elif type == 'delete':
                r = self.session.delete(url, data=payload, params=query, timeout=timeout)
            else:
                g.logger.Error('Unsupported request type:{}'.format(type))
                raise ValueError('Unsupported request type:{}'.format(type))

            r.raise_for_status()

            if return_raw_response:
                return r

            content_type = r.headers.get('content-type', '')
            if content_type.startswith("application/json") and r.text:
                return r.json()
            elif content_type.startswith('image/'):
                return r
            elif type == 'delete':
                return None
        except requests.exceptions.HTTPError as err:
            g.logger.Debug(1, 'HTTP error: {}'.format(err))

            if err.response.status_code == 401 and reauth:
                g.logger.Debug(1, 'Got 401 (Unauthorized) - retrying login once')
                self._login()
                g.logger.Debug(1, 'Retrying failed request again...')
                return self._make_request(
                    url,
                    query,
                    payload,
                    type,
                    reauth=False,
                    timeout=timeout,
                    return_raw_response=return_raw_response,
                )

            raise err
        except ValueError as err:

            if reauth:
                g.logger.Debug(1, 'Got ValueError access error: {}'.format(err))
                g.logger.Debug(1, 'Retrying login once')
                self._login()
                g.logger.Debug(1, 'Retrying failed request again...')
                return self._make_request(
                    url=url,
                    query=query,
                    payload=payload,
                    type=type,
                    reauth=False,
                    return_raw_response=return_raw_response,
                )
            else:
                raise err
            
    def items(self):
        """
        Returns list of items.
            
        Returns:
            list of :class:`hb_client.helpers.HbItem`: list of items 
        """
        return HbItems(api=self)
