"""
Labels
=========
Holds a list of Labels for a HB configuration
"""


from .base import Base
from .label import Label
from . import globals as g


class Labels(Base):
    def __init__(self, api=None):
        self.api = api
        self._load()

    def _load(self, options={}):
        g.logger.Debug(2, 'Retrieving labels via API')

        url = f"{self.api.api_url}/v1/labels"
        labels = self.api._make_request(url=url)

        self.labels = []
        for label in labels:
            self.labels.append(Label(api=self.api, label=label))

    def list(self):
        return self.labels

    def add(self, options={}):
        """Adds a new label
        Args:
            options (dict): Set of attributes that define the label:
                {
                    "color": str,
                    "description": str,
                    "name": str
                }
        Returns:
            json: json response of API request
        """

        url = f"{self.api.api_url}/v1/labels"

        return self.api._make_request(url=url, payload=options, type="post")
