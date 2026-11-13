import os
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured

from hi.environment.settings_module import SETTINGS_MODULE_VAR, require_settings_module
from hi.testing.base_test_case import BaseTestCase


class RequireSettingsModuleTestCase(BaseTestCase):

    def test_passes_when_set(self):
        with patch.dict( os.environ, { SETTINGS_MODULE_VAR: 'hi.settings.local' } ):
            require_settings_module()
        return

    def test_raises_naming_the_variable_when_unset(self):
        with patch.dict( os.environ, {}, clear = True ):
            with self.assertRaises( ImproperlyConfigured ) as context:
                require_settings_module()
        self.assertIn( SETTINGS_MODULE_VAR, str( context.exception ) )
        self.assertIn( 'hi.settings.local', str( context.exception ) )
        return

    def test_raises_when_empty(self):
        with patch.dict( os.environ, { SETTINGS_MODULE_VAR: '' } ):
            with self.assertRaises( ImproperlyConfigured ):
                require_settings_module()
        return

    def test_does_not_set_a_default(self):
        with patch.dict( os.environ, {}, clear = True ):
            with self.assertRaises( ImproperlyConfigured ):
                require_settings_module()
            self.assertNotIn( SETTINGS_MODULE_VAR, os.environ )
        return
