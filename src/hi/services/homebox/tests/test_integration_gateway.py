"""
Smoke tests for HomeBoxGateway hooks the framework calls.

The substantive behavior of each gateway method lives in the
collaborator it delegates to (HomeBoxConnector, HomeBoxManager,
HomeBoxSynchronizer); these tests pin the delegation contract.
"""
import logging
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from hi.services.homebox.integration import HomeBoxGateway


logging.disable(logging.CRITICAL)


class HomeBoxGatewayExternalViewDataTests(SimpleTestCase):

    def test_delegates_to_homebox_connector(self):
        gateway = HomeBoxGateway()
        entity = Mock(name='entity')
        expected_result = Mock(name='external_view_data')

        with patch(
            'hi.services.homebox.connector.hb_connector.HomeBoxConnector'
        ) as connector_cls:
            connector_instance = connector_cls.return_value
            connector_instance.get_external_view_data.return_value = expected_result

            result = gateway.get_external_view_data(entity)

        self.assertIs(result, expected_result)
        connector_cls.assert_called_once_with()
        connector_instance.get_external_view_data.assert_called_once_with(entity)
