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

    def __init__(self, api_options: Dict[str, str], timeout_secs: Optional[float] = None):
        self._api_url = api_options.get(self.API_URL)
        assert self._api_url is not None
        if self._api_url.endswith('/'):
            self._api_url = self._api_url[:-1]

        self._user = api_options.get(self.API_USER)
        assert self._user is not None
        self._password = api_options.get(self.API_PASSWORD)
        assert self._password is not None

        # Per-instance timeout. Defaults to DEFAULT_TIMEOUT when not
        # specified; the connection-test path passes a tighter bound for
        # interactive save-time validation.
        self._timeout_secs = timeout_secs if timeout_secs is not None else self.DEFAULT_TIMEOUT

        self._session = Session()
        self._login()

    def _login(self):
        url = f"{self._api_url}/{self.API_VERSION}/users/login"
        data = {
            'username': self._user,
            'password': self._password,
            'stayLoggedIn': True
        }
        try:
            response = self._session.post(url, json=data, timeout=self._timeout_secs)
        except Exception as e:
            raise ConnectionError(
                f'Cannot connect to HomeBox at {self._api_url}. '
                f'Verify the API URL is correct and the server is running.'
            ) from e

        response.raise_for_status()

        content_type = response.headers.get('content-type', '')
        if 'json' not in content_type:
            raise ValueError(
                f'HomeBox API URL may be incorrect. Expected JSON response but received '
                f'{content_type or "unknown content type"}. '
                f'Ensure the URL includes the API path (e.g., http://host:port/api).'
            )

        token = response.json().get('token')
        if token:
            self._session.headers.update({'Authorization': token})
        else:
            logger.warning("HomeBox login succeeded but response did not contain a token.")

    def _make_request(self, method: str, url: str, **kwargs) -> Union[dict, Response]:
        """Helper to make requests with simple re-authentication."""
        
        kwargs.setdefault('timeout', self._timeout_secs)
        
        response = self._session.request(method, url, **kwargs)
        
        if response.status_code == 401 and self._user:
            self._login()
            response = self._session.request(method, url, **kwargs)
            
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        if content_type.startswith('application/json'):
            return response.json()
        return response

    def get_items_summary(self) -> List[Dict[str, Any]]:
        """
        Fetches just the items summary list (one API call). Does not fetch
        per-item details. Suitable for lightweight reachability /
        health-check probes where only the count or IDs are needed.
        """
        url_list = f"{self._api_url}/{self.API_VERSION}/items"
        data = self._make_request('GET', url_list)
        return data.get('items', []) if isinstance(data, dict) else data

    def get_items(self) -> List[HbItem]:
        """
        Fetches the list of items and, for each one, fetches the full details.
        Returns a list of fully populated HbItem objects.
        """
        items_summary = self.get_items_summary()

        full_items = []
        for summary in items_summary:
            item_id = summary.get('id')
            if item_id:
                try:
                    url_detail = f"{self._api_url}/{self.API_VERSION}/items/{item_id}"
                    item_detail = self._make_request('GET', url_detail)
                    full_items.append(HbItem(api_dict=item_detail, client=self))
                except Exception as e:
                    logger.error(f"Error fetching details for item {item_id}: {e}")

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
