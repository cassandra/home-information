import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from hi.settings_check import SETTINGS_MODULE_ENV_VAR, require_settings_module
from hi.testing.base_test_case import BaseTestCase

SRC_DIR = Path( __file__ ).resolve().parents[2]


class TestRequireSettingsModule( BaseTestCase ):

    def test_returns_when_variable_is_set(self):
        with patch.dict( os.environ, { SETTINGS_MODULE_ENV_VAR: 'hi.settings.local' } ):
            self.assertIsNone( require_settings_module() )
        return

    def test_exits_with_clear_message_when_variable_is_unset(self):
        with patch.dict( os.environ ):
            os.environ.pop( SETTINGS_MODULE_ENV_VAR, None )
            with self.assertRaises( SystemExit ) as context:
                require_settings_module()

        message = str( context.exception )
        self.assertIn( SETTINGS_MODULE_ENV_VAR, message )
        self.assertIn( 'hi.settings.local', message )
        self.assertIn( 'hi.settings.production', message )
        return

    def test_exits_when_variable_is_empty(self):
        with patch.dict( os.environ, { SETTINGS_MODULE_ENV_VAR: '' } ):
            with self.assertRaises( SystemExit ):
                require_settings_module()
        return

    def test_does_not_modify_the_environment(self):
        with patch.dict( os.environ ):
            os.environ.pop( SETTINGS_MODULE_ENV_VAR, None )
            with self.assertRaises( SystemExit ):
                require_settings_module()
            self.assertNotIn( SETTINGS_MODULE_ENV_VAR, os.environ )
        return


class TestEntryPointsRequireSettingsModule( BaseTestCase ):
    """ Each entry point must fail fast, before Django is configured. """

    def _run_without_settings_module( self, *args ):
        env = { key: value for key, value in os.environ.items()
                if key != SETTINGS_MODULE_ENV_VAR }
        return subprocess.run(
            [ sys.executable, *args ],
            cwd = SRC_DIR,
            env = env,
            capture_output = True,
            text = True,
            timeout = 120,
        )

    def _assert_fails_fast( self, result ):
        self.assertNotEqual( result.returncode, 0 )
        self.assertIn( f'{SETTINGS_MODULE_ENV_VAR} is not set', result.stderr )
        self.assertNotIn( 'Traceback', result.stderr )
        return

    def test_manage_py(self):
        self._assert_fails_fast( self._run_without_settings_module( 'manage.py', 'check' ) )
        return

    def test_wsgi(self):
        self._assert_fails_fast( self._run_without_settings_module( '-c', 'import hi.wsgi' ) )
        return

    def test_asgi(self):
        self._assert_fails_fast( self._run_without_settings_module( '-c', 'import hi.asgi' ) )
        return
