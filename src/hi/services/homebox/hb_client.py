import logging
from typing import Dict, List, Union, Any, Optional
from requests import Session, Response

from .hb_models import HbItem

logger = logging.getLogger(__name__)


class HbClient:
    API_URL = 'apiurl'
    API_USER = 'user'
    API_PASSWORD = 'password'
    
    DEFAULT_TIMEOUT = 25.0
    API_VERSION = 'v1'

    def __init__(self, api_options: Dict[str, str]):
        self._api_url = api_options.get(self.API_URL)
        if self._api_url and self._api_url.endswith('/'):
            self._api_url = self._api_url[:-1]
            
        self._user = api_options.get(self.API_USER)
        self._password = api_options.get(self.API_PASSWORD)
        
        self._session = Session()
        
        if self._user and self._password:
            self._login()
        else:
            logger.warning("HomeBox API user or password is missing.")

    def _login(self):
        url = f"{self._api_url}/{self.API_VERSION}/users/login"
        data = {
            'username': self._user, 
            'password': self._password, 
            'stayLoggedIn': True
        }
        response = self._session.post(url, json=data, timeout=self.DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        token = response.json().get('token')
        if token:
            self._session.headers.update({'Authorization': token})

    def _make_request(self, method: str, url: str, **kwargs) -> Union[dict, Response]:
        """Helper to make requests with simple re-authentication."""
        
        kwargs.setdefault('timeout', self.DEFAULT_TIMEOUT)
        
        response = self._session.request(method, url, **kwargs)
        
        if response.status_code == 401 and self._user:
            self._login()
            response = self._session.request(method, url, **kwargs)
            
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        if content_type.startswith('application/json'):
            return response.json()
        return response

    def get_items(self) -> List[HbItem]:
        """
        Fetches the list of items and, for each one, fetches the full details.
        Returns a list of fully populated HbItem objects.
        """
        url_list = f"{self._api_url}/{self.API_VERSION}/items"
        data = self._make_request('GET', url_list)
        items_summary = data.get('items', []) if isinstance(data, dict) else data
        
        full_items = []
        for summary in items_summary:
            item_id = summary.get('id')
            if item_id:
                try:
                    url_detail = f"{self._api_url}/{self.API_VERSION}/items/{item_id}"
                    item_detail = self._make_request('GET', url_detail)
                    full_items.append(HbItem(api_dict=item_detail, client=self))
                except Exception as e:
                    logger.error(f"Erro ao buscar detalhes do item {item_id}: {e}")
                    
        return full_items

    def download_attachment(self, item_id: str, attachment_id: str) -> Optional[Dict[str, Any]]:
        """Downloads an attachment """
        url = f"{self._api_url}/{self.API_VERSION}/items/{item_id}/attachments/{attachment_id}"
        response = self._make_request('GET', url)

        if not isinstance(response, Response):
            logger.warning(f"Expected a Response object for attachment download, got {type(response)}")
            return None
        
        return {
            'content': response.content,
            'mime_type': response.headers.get('content-type'),
        }
