"""
Item
=======
Each Item will hold a single HomeBox Item.
It is basically a bunch of getters for each access to event data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""


from .base import Base
from . import globals as g


class HbItem(Base):
    def __init__(self, api, item):
        self.api = api
        self._load(item)

    def _load(self, item):
        item_id = item.get('id')
        if not item_id:
            g.logger.Error('Item ID is required to initialize Item object')
            raise ValueError('Item ID is required to initialize Item object')

        url = f"{self.api.api_url}/v1/items/{item_id}"
        self.item = self.api._make_request(url=url, type='get')
    
    @property
    def id(self):
        """Returns item Id
        
        Returns:
            string: Item Id
        """
        return self.item['id']
    
    @property
    def name(self):
        """Returns item name
        
        Returns:
            string: item name
        """
        return self.item['name']
    
    @property
    def description(self):
        """Returns item description
        
        Returns:
            string: item description
        """
        return self.item['description']
    
    @property
    def serial_number(self):
        """Returns item serial number
        
        Returns:
            string: item serial number
        """
        return self.item['serialNumber']
    
    @property
    def model_number(self):
        """Returns item model number
        
        Returns:
            string: item model number
        """
        return self.item['modelNumber']
    
    @property
    def manufacturer(self):
        """Returns item manufacturer
        
        Returns:
            string: item manufacturer
        """
        return self.item['manufacturer']

    @property
    def notes(self):
        """Returns item notes
        
        Returns:
            string: item notes
        """
        return self.item['notes']

    @property
    def attachments(self):
        """Returns item attachments
        
        Returns:
            list: item attachments
        """
        return self.item['attachments']

    def download_attachment(self, attachment=None):
        if not isinstance(attachment, dict):
            g.logger.Error(f'Invalid attachment provided for download: expected dict, got {type(attachment)}')
            return None
        
        attachment_id = str(attachment.get('id', '')).strip()

        if not attachment_id:
            g.logger.Debug(1, f'Cannot download attachment for item {self.id}: missing attachment id')
            return None

        content_type_hint = str(attachment.get('mimeType', '')).strip()
        filename_hint = str(attachment.get('title', '')).strip()
        url = f"{self.api.api_url}/v1/items/{self.id}/attachments/{attachment_id}"

        response = self.api._make_request(url=url, return_raw_response=True)

        if not response.content:
            g.logger.Debug(2, f'Attachment download returned empty payload: {url}')
            return None

        content_type = response.headers.get('content-type', '') or content_type_hint

        return {
            'content': response.content,
            'mime_type': content_type,
            'filename': filename_hint,
            'source_url': url,
        }
    
    @property
    def fields(self):
        """Returns item custom fields
        
        Returns:
            list: item custom fields
        """
        return self.item['fields']
    
    def get(self):
        """Returns item object
        
        Returns:
            :class:`hb_client.helpers.Item`: Item object
        """
        return self.item
    