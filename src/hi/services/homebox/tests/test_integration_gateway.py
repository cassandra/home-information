"""
Smoke tests for HomeBox connector hooks the framework calls.

The substantive behavior of each connector method lives in the
collaborator it delegates to (HomeBoxExternalViewResolver, HomeBoxManager,
HomeBoxConnector); these tests pin the delegation contract.
"""
import logging
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from hi.services.homebox.connector.homebox_connector import HomeBoxConnector


logging.disable(logging.CRITICAL)


class HomeBoxConnectorExternalViewDataTests(SimpleTestCase):

    def test_delegates_to_homebox_external_view_resolver(self):
        connector = HomeBoxConnector()
        entity = Mock(name='entity')
        expected_result = Mock(name='external_view_data')

        with patch(
            'hi.services.homebox.connector.homebox_connector.HomeBoxExternalViewResolver'
        ) as resolver_cls:
            resolver_instance = resolver_cls.return_value
            resolver_instance.get_external_view_data.return_value = expected_result

            result = connector.get_external_view_data(entity)

        self.assertIs(result, expected_result)
        resolver_cls.assert_called_once_with()
        resolver_instance.get_external_view_data.assert_called_once_with(entity)
