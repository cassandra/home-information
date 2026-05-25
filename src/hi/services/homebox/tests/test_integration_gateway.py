"""
Smoke tests for HomeBoxGateway hooks the framework calls.

The substantive behavior of each gateway method lives in the
collaborator it delegates to (HomeBoxExternalViewResolver, HomeBoxManager,
HomeBoxConnector); these tests pin the delegation contract.
"""
import logging
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from hi.services.homebox.integration import HomeBoxGateway


logging.disable(logging.CRITICAL)


class HomeBoxGatewayExternalViewDataTests(SimpleTestCase):

    def test_delegates_to_homebox_external_view_resolver(self):
        gateway = HomeBoxGateway()
        entity = Mock(name='entity')
        expected_result = Mock(name='external_view_data')

        with patch(
            'hi.services.homebox.integration.HomeBoxExternalViewResolver'
        ) as resolver_cls:
            resolver_instance = resolver_cls.return_value
            resolver_instance.get_external_view_data.return_value = expected_result

            result = gateway.get_external_view_data(entity)

        self.assertIs(result, expected_result)
        resolver_cls.assert_called_once_with()
        resolver_instance.get_external_view_data.assert_called_once_with(entity)
