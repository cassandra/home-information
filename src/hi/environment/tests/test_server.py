import io
import os
from contextlib import redirect_stderr
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured

from hi.environment.server import EnvironmentSettings
from hi.testing.base_test_case import BaseTestCase


def base_env():
    """A complete set of the env vars EnvironmentSettings.get() requires, so a
    test can copy it and tweak one thing at a time. (Required = a field whose
    default is None.)"""
    return {
        'DJANGO_SETTINGS_MODULE': 'hi.settings.local',
        'DJANGO_SECRET_KEY': 'test-secret-key',
        'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
        'DJANGO_SUPERUSER_PASSWORD': 'test-password',
        'HI_DB_PATH': '/data/database',
        'HI_MEDIA_PATH': '/data/media',
    }


class GetEnvVariableTestCase(BaseTestCase):

    def test_returns_value_when_set(self):
        with patch.dict(os.environ, {'HI_TEST_VAR': 'value'}, clear=True):
            self.assertEqual(EnvironmentSettings.get_env_variable('HI_TEST_VAR'), 'value')

    def test_returns_default_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                EnvironmentSettings.get_env_variable('HI_MISSING', 'fallback'), 'fallback')

    def test_empty_string_default_is_returned_not_treated_as_required(self):
        # '' is a valid (optional) default; only None means "required".
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(EnvironmentSettings.get_env_variable('HI_MISSING', ''), '')

    def test_raises_when_unset_and_no_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                EnvironmentSettings.get_env_variable('HI_REQUIRED')


class ToBoolTestCase(BaseTestCase):

    def test_bool_passthrough(self):
        self.assertIs(EnvironmentSettings.to_bool(True), True)
        self.assertIs(EnvironmentSettings.to_bool(False), False)

    def test_truthy_strings(self):
        for value in ['true', 'TRUE', '1', 'on', 'yes', 'y', 't', 'enabled', '  Yes  ']:
            self.assertTrue(EnvironmentSettings.to_bool(value), value)

    def test_falsey_strings(self):
        for value in ['false', '0', 'no', 'off', '', 'random']:
            self.assertFalse(EnvironmentSettings.to_bool(value), value)

    def test_non_string_non_bool_uses_bool_builtin(self):
        self.assertTrue(EnvironmentSettings.to_bool(1))
        self.assertFalse(EnvironmentSettings.to_bool(0))
        self.assertFalse(EnvironmentSettings.to_bool(None))


class ParseUrlTestCase(BaseTestCase):

    def test_valid_url_returns_parse_result(self):
        result = EnvironmentSettings.parse_url('http://myhost:9411')
        self.assertEqual(result.scheme, 'http')
        self.assertEqual(result.hostname, 'myhost')
        self.assertEqual(result.port, 9411)

    def test_non_http_scheme_is_accepted(self):
        # parse_url only requires scheme + netloc, not a specific scheme.
        result = EnvironmentSettings.parse_url('https://myhost')
        self.assertEqual(result.scheme, 'https')

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            EnvironmentSettings.parse_url('')

    def test_none_raises_valueerror(self):
        with self.assertRaises(ValueError):
            EnvironmentSettings.parse_url(None)

    def test_missing_scheme_raises(self):
        with self.assertRaises(ValueError):
            EnvironmentSettings.parse_url('myhost:9411')

    def test_missing_netloc_raises(self):
        with self.assertRaises(ValueError):
            EnvironmentSettings.parse_url('http://')


class EnvironmentNameTestCase(BaseTestCase):

    def test_dotted_module_returns_last_segment(self):
        env = EnvironmentSettings(DJANGO_SETTINGS_MODULE='hi.settings.local')
        self.assertEqual(env.environment_name, 'local')

    def test_none_module_returns_unknown(self):
        env = EnvironmentSettings(DJANGO_SETTINGS_MODULE=None)
        self.assertEqual(env.environment_name, 'unknown')

    def test_single_segment_module_returns_unknown(self):
        env = EnvironmentSettings(DJANGO_SETTINGS_MODULE='local')
        self.assertEqual(env.environment_name, 'unknown')


class ParseUrlListStrTestCase(BaseTestCase):
    """parse_url_list_str feeds ALLOWED_HOSTS and CORS/CSP origins from
    HI_EXTRA_HOST_URLS / HI_EXTRA_CSP_URLS. Entries must be full URLs; a value
    that isn't a parseable URL (e.g. a bare hostname, which is what Django's
    DisallowedHost error misleadingly tells users to add) is dropped, but with
    a loud stderr warning instead of silently."""

    def test_full_url_parsed_to_host_and_normalized_url(self):
        result = EnvironmentSettings.parse_url_list_str('http://myhost:9411')
        self.assertEqual(result, [('myhost', 'http://myhost:9411')])

    def test_url_without_port_normalized_without_port(self):
        result = EnvironmentSettings.parse_url_list_str('http://myhost')
        self.assertEqual(result, [('myhost', 'http://myhost')])

    def test_multiple_urls_split_on_space_comma_semicolon(self):
        result = EnvironmentSettings.parse_url_list_str(
            'http://a:9411, http://b:9411; http://c:9411')
        self.assertEqual(
            result,
            [('a', 'http://a:9411'), ('b', 'http://b:9411'), ('c', 'http://c:9411')],
        )

    def test_bare_hostname_ignored_with_actionable_stderr_warning(self):
        err = io.StringIO()
        with redirect_stderr(err):
            result = EnvironmentSettings.parse_url_list_str(
                'cassandra', source_var='HI_EXTRA_HOST_URLS')
        self.assertEqual(result, [])
        warning = err.getvalue()
        self.assertIn('HI_EXTRA_HOST_URLS', warning)   # names the source variable
        self.assertIn("'cassandra'", warning)          # names the ignored value
        self.assertIn('http://myhost:9411', warning)   # fixed, valid example

    def test_warning_example_is_fixed_not_built_from_bad_input(self):
        # A token with a port but no scheme is invalid; the suggestion must not
        # be assembled from it (which would yield 'http://cassandra:9411:9411').
        err = io.StringIO()
        with redirect_stderr(err):
            EnvironmentSettings.parse_url_list_str('cassandra:9411')
        warning = err.getvalue()
        self.assertIn('http://myhost:9411', warning)
        self.assertNotIn('http://cassandra:9411:9411', warning)

    def test_mixed_input_keeps_valid_and_warns_only_invalid(self):
        err = io.StringIO()
        with redirect_stderr(err):
            result = EnvironmentSettings.parse_url_list_str(
                'cassandra http://good:9411', source_var='HI_EXTRA_CSP_URLS')
        self.assertEqual(result, [('good', 'http://good:9411')])
        warning = err.getvalue()
        self.assertIn("'cassandra'", warning)
        self.assertIn('HI_EXTRA_CSP_URLS', warning)
        self.assertNotIn("'good'", warning)

    def test_empty_or_whitespace_yields_nothing_without_warning(self):
        err = io.StringIO()
        with redirect_stderr(err):
            result = EnvironmentSettings.parse_url_list_str('   ;,  ')
        self.assertEqual(result, [])
        self.assertEqual(err.getvalue(), '')


class EnvironmentSettingsGetTestCase(BaseTestCase):
    """End-to-end construction of EnvironmentSettings from the process
    environment via get()."""

    def _get_with(self, **overrides):
        env = base_env()
        env.update({k: v for k, v in overrides.items() if v is not None})
        for k, v in overrides.items():
            if v is None:
                env.pop(k, None)
        with patch.dict(os.environ, env, clear=True):
            return EnvironmentSettings.get()

    def test_minimal_valid_environment_populates_core_fields(self):
        env = self._get_with()
        self.assertEqual(env.DJANGO_SETTINGS_MODULE, 'hi.settings.local')
        self.assertEqual(env.SECRET_KEY, 'test-secret-key')
        self.assertEqual(env.DATABASES_NAME_PATH, '/data/database')
        self.assertEqual(env.MEDIA_ROOT, '/data/media')
        # VERSION is read from the HI_VERSION file (not the 'unknown' default).
        self.assertTrue(env.VERSION)
        self.assertNotEqual(env.VERSION, 'unknown')

    def test_missing_required_var_raises(self):
        for required in ['DJANGO_SETTINGS_MODULE', 'DJANGO_SECRET_KEY',
                         'DJANGO_SUPERUSER_EMAIL', 'HI_DB_PATH', 'HI_MEDIA_PATH']:
            with self.assertRaises(ImproperlyConfigured, msg=required):
                self._get_with(**{required: None})

    def test_loopback_host_and_cors_defaults_always_present(self):
        env = self._get_with()
        self.assertEqual(env.ALLOWED_HOSTS, ('127.0.0.1', 'localhost'))
        self.assertEqual(
            env.CORS_ALLOWED_ORIGINS,
            ('http://127.0.0.1:8000', 'http://localhost:8000'),
        )
        self.assertEqual(env.SITE_DOMAIN, 'localhost')

    def test_server_port_overrides_cors_default_port(self):
        env = self._get_with(DJANGO_SERVER_PORT='9999')
        self.assertEqual(env.DJANGO_SERVER_PORT, 9999)
        self.assertIn('http://localhost:9999', env.CORS_ALLOWED_ORIGINS)

    def test_invalid_server_port_falls_back_to_default(self):
        env = self._get_with(DJANGO_SERVER_PORT='not-a-number')
        self.assertEqual(env.DJANGO_SERVER_PORT, 8000)

    def test_redis_port_defaults_when_unset(self):
        # HI_REDIS_PORT is optional: absent -> the 6379 field default.
        env = self._get_with()
        self.assertEqual(env.REDIS_PORT, 6379)

    def test_redis_port_from_environment(self):
        env = self._get_with(HI_REDIS_PORT='6400')
        self.assertEqual(env.REDIS_PORT, 6400)

    def test_invalid_redis_port_falls_back_to_default(self):
        env = self._get_with(HI_REDIS_PORT='not-a-number')
        self.assertEqual(env.REDIS_PORT, 6379)

    def test_extra_host_urls_extend_allowed_hosts_cors_and_site_domain(self):
        env = self._get_with(HI_EXTRA_HOST_URLS='http://myhost:9411 http://other:9411')
        self.assertIn('myhost', env.ALLOWED_HOSTS)
        self.assertIn('other', env.ALLOWED_HOSTS)
        self.assertIn('http://myhost:9411', env.CORS_ALLOWED_ORIGINS)
        # First extra host becomes SITE_DOMAIN.
        self.assertEqual(env.SITE_DOMAIN, 'myhost')

    def test_extra_csp_urls_extend_cors_but_not_allowed_hosts(self):
        env = self._get_with(HI_EXTRA_CSP_URLS='http://csponly:9411')
        self.assertIn('http://csponly:9411', env.CORS_ALLOWED_ORIGINS)
        self.assertNotIn('csponly', env.ALLOWED_HOSTS)

    def test_email_use_tls_forces_ssl_off(self):
        env = self._get_with(HI_EMAIL_USE_TLS='true', HI_EMAIL_USE_SSL='true')
        self.assertTrue(env.EMAIL_USE_TLS)
        self.assertFalse(env.EMAIL_USE_SSL)

    def test_email_use_ssl_honored_when_tls_off(self):
        env = self._get_with(HI_EMAIL_USE_TLS='false', HI_EMAIL_USE_SSL='true')
        self.assertFalse(env.EMAIL_USE_TLS)
        self.assertTrue(env.EMAIL_USE_SSL)

    def test_suppress_authentication_parsed_as_bool(self):
        self.assertFalse(self._get_with(HI_SUPPRESS_AUTHENTICATION='false').SUPPRESS_AUTHENTICATION)
        self.assertTrue(self._get_with(HI_SUPPRESS_AUTHENTICATION='yes').SUPPRESS_AUTHENTICATION)
