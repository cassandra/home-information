import logging
from unittest.mock import patch

from django.contrib.auth import get_user, get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse

from hi.apps.notify.email_sender import EmailSender
from hi.apps.user.constants import UserConstants
from hi.apps.user.magic_code_generator import MagicCodeGenerator
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)

User = get_user_model()


class SigninFlowTestMixin:
    """ Drives the real sign-in flow, mocking only the outbound email boundary. """

    MAGIC_CODE_TEMPLATE = 'user/pages/magic_code_signin.html'
    CODE_ENTRY_MARKUP = 'name="magic_code"'

    def code_page_url(self):
        return reverse('user_signin_magic_code')

    def request_signin_code(self, email_address):
        with patch.object(EmailSender, 'send') as mock_send:
            response = self.client.post(reverse('user_signin'), {'email': email_address})
        self.assertRedirects(response, self.code_page_url(), fetch_redirect_response=False)
        return mock_send, self.client.session.get(MagicCodeGenerator.MAGIC_CODE)

    def get_code_page(self):
        response = self.client.get(self.code_page_url())
        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, self.MAGIC_CODE_TEMPLATE)
        return response

    def submit_signin_code(self, email_address, magic_code):
        return self.client.post(reverse('user_signin_magic_code'), {
            'email_address': email_address,
            'magic_code': magic_code,
        })

    def assertSignedInAs(self, user):
        self.assertEqual(get_user(self.client), user)

    def assertNotSignedIn(self):
        self.assertFalse(get_user(self.client).is_authenticated)

    def assertRejectedWithoutSignin(self, response):
        """ Rejected with no sign-in in progress: the code page has nothing to show. """
        self.assertRedirects(response, self.code_page_url(), fetch_redirect_response=False)
        self.assertNotSignedIn()
        self.assertRedirects(self.client.get(self.code_page_url()), reverse('user_signin'),
                             fetch_redirect_response=False)

    def assertCodeRejected(self, response, message='Invalid access code.'):
        """ A rejected code redirects to the code page, which then shows why. """
        self.assertRedirects(response, self.code_page_url(), fetch_redirect_response=False)
        self.assertNotSignedIn()
        page = self.get_code_page()
        self.assertContains(page, message)
        return page


class TestUserSigninView(SigninFlowTestMixin, SyncViewTestCase):

    @patch.object(EmailSender, 'is_email_configured', return_value=False)
    def test_get_signin_page_flags_email_not_configured(self, mock_is_configured):
        response = self.client.get(reverse('user_signin'))

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'user/pages/signin.html')
        self.assertTrue(response.context['email_not_configured'])

    def test_post_signin_already_authenticated(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('user_signin'), {'email': self.user.email})

        self.assertEqual(response.status_code, 400)

    def test_post_signin_no_email(self):
        response = self.client.post(reverse('user_signin'), {})

        self.assertEqual(response.status_code, 400)

    def test_post_signin_invalid_email(self):
        response = self.client.post(reverse('user_signin'), {'email': 'not-an-email'})

        self.assertEqual(response.status_code, 400)

    def test_existing_account_is_sent_code(self):
        mock_send, magic_code = self.request_signin_code(self.user.email)

        mock_send.assert_called_once()
        self.assertIsNotNone(magic_code)

    def test_nonexistent_account_gets_unsent_code_bound_to_email(self):
        """ Session must change exactly as for a real account, so a prior code cannot be used as an oracle. """
        mock_send, magic_code = self.request_signin_code('nobody@example.com')

        mock_send.assert_not_called()
        self.assertIsNotNone(magic_code)
        self.assertEqual(self.client.session[MagicCodeGenerator.MAGIC_CODE_EMAIL], 'nobody@example.com')

    def test_new_signin_replaces_pending_code_for_any_email(self):
        _, first_code = self.request_signin_code(self.user.email)
        self.request_signin_code('nobody@example.com')

        response = self.submit_signin_code(self.user.email, first_code)

        self.assertCodeRejected(response)


class TestSigninMagicCodeView(SigninFlowTestMixin, SyncViewTestCase):

    def test_invalid_form(self):
        self.request_signin_code(self.user.email)

        response = self.client.post(self.code_page_url(), {})

        self.assertCodeRejected(response)

    def test_get_shows_code_entry_for_pending_code(self):
        self.request_signin_code(self.user.email)

        page = self.get_code_page()

        self.assertContains(page, self.user.email)
        self.assertContains(page, self.CODE_ENTRY_MARKUP)
        self.assertNotContains(page, 'Invalid access code.')

    def test_code_entry_keypad_renders_magic_code_spec(self):
        spec = UserConstants.MAGIC_CODE_KEYPAD
        self.request_signin_code(self.user.email)

        page = self.get_code_page()

        self.assertContains(page, f'data-alphabet="{spec.alphabet}"')
        self.assertContains(page, f'data-length="{spec.length}"')
        self.assertContains(page, 'data-case-sensitive="false"')

    def test_get_while_signed_in_redirects_home(self):
        self.client.force_login(self.user)

        response = self.client.get(self.code_page_url())

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_get_without_signin_in_progress_redirects_to_signin(self):
        response = self.client.get(self.code_page_url())

        self.assertRedirects(response, reverse('user_signin'), fetch_redirect_response=False)

    def test_reload_after_wrong_code_drops_error_and_keeps_code_usable(self):
        _, magic_code = self.request_signin_code(self.user.email)
        self.assertCodeRejected(self.submit_signin_code(self.user.email, 'wxyzwx'))

        page = self.get_code_page()

        self.assertNotContains(page, 'Invalid access code.')
        self.submit_signin_code(self.user.email, magic_code)
        self.assertSignedInAs(self.user)

    def test_unusable_code_hides_code_entry_and_stays_unusable_on_reload(self):
        self.request_signin_code(self.user.email)
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS):
            response = self.submit_signin_code(self.user.email, 'wxyzwx')

        page = self.assertCodeRejected(response, message='Too many incorrect attempts.')
        self.assertNotContains(page, self.CODE_ENTRY_MARKUP)
        self.assertContains(page, self.user.email, msg_prefix='email kept for sending a new code')

        reloaded = self.get_code_page()
        self.assertContains(reloaded, 'This access code is no longer valid.')
        self.assertNotContains(reloaded, self.CODE_ENTRY_MARKUP)

    def test_correct_code_signs_in_and_verifies_email(self):
        _, magic_code = self.request_signin_code(self.user.email)

        response = self.submit_signin_code(self.user.email, magic_code)

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertSignedInAs(self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_code_cannot_be_reused(self):
        _, magic_code = self.request_signin_code(self.user.email)
        self.submit_signin_code(self.user.email, magic_code)
        self.client.logout()

        response = self.submit_signin_code(self.user.email, magic_code)

        self.assertRejectedWithoutSignin(response)

    def test_wrong_code_rejected(self):
        self.request_signin_code(self.user.email)

        response = self.submit_signin_code(self.user.email, 'wxyzwx')

        page = self.assertCodeRejected(response)
        self.assertContains(page, 'hi-keypad-entry is-error', msg_prefix='keypad shown in error state')

    def test_nonexistent_account_rejected_even_with_matching_code(self):
        _, magic_code = self.request_signin_code('nobody@example.com')

        response = self.submit_signin_code('nobody@example.com', magic_code)

        self.assertCodeRejected(response)

    def test_no_code_in_session_rejected(self):
        response = self.submit_signin_code(self.user.email, 'abcdef')

        self.assertRejectedWithoutSignin(response)

    def test_code_issued_for_other_account_rejected(self):
        other_user = User.objects.create_user(email='other@example.com', password='x')
        _, magic_code = self.request_signin_code(other_user.email)

        response = self.submit_signin_code(self.user.email, magic_code)

        self.assertCodeRejected(response)

    def test_expired_code_rejected_with_expired_message(self):
        _, magic_code = self.request_signin_code(self.user.email)
        expired_now = (MagicCodeGenerator.get_elapsed_seconds()
                       + MagicCodeGenerator.MAGIC_CODE_TIMEOUT_SECS + 1)

        with patch.object(MagicCodeGenerator, 'get_elapsed_seconds', return_value=expired_now):
            response = self.submit_signin_code(self.user.email, magic_code)

        self.assertCodeRejected(response, message='Access code has expired.')

    def test_too_many_attempts_then_new_code_for_same_email_signs_in(self):
        _, first_code = self.request_signin_code(self.user.email)
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS):
            response = self.submit_signin_code(self.user.email, 'wxyzwx')
        self.assertCodeRejected(response, message='Too many incorrect attempts.')

        _, new_code = self.request_signin_code(self.user.email)
        response = self.submit_signin_code(self.user.email, new_code)

        self.assertSignedInAs(self.user)


class TestSigninMagicLinkView(SigninFlowTestMixin, SyncViewTestCase):

    BAD_LINK_TEMPLATE = 'user/pages/signin_magic_bad_link.html'

    def get_link(self, email_address, token):
        return self.client.get(reverse('user_signin_magic_link', kwargs={
            'email': email_address,
            'token': token,
        }))

    def test_valid_token_signs_in(self):
        token = PasswordResetTokenGenerator().make_token(user=self.user)

        response = self.get_link(self.user.email, token)

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertSignedInAs(self.user)

    def test_invalid_token_shows_bad_link_page(self):
        response = self.get_link(self.user.email, 'invalid-token')

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, self.BAD_LINK_TEMPLATE)
        self.assertNotSignedIn()

    def test_nonexistent_account_matches_invalid_token_response(self):
        response = self.get_link('nobody@example.com', 'invalid-token')

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, self.BAD_LINK_TEMPLATE)
        self.assertNotSignedIn()
