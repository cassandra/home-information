import logging
from unittest.mock import patch

from django.contrib.auth import get_user
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse

from hi.apps.notify.email_sender import EmailSender
from hi.apps.user.constants import UserConstants
from hi.apps.user.magic_code_generator import MagicCodeGenerator, MagicCodeStatus
from hi.apps.user.views import SigninMagicCodeView
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class SigninFlowTestMixin:
    """ Drives the real sign-in flow, mocking only the outbound email boundary and the clock. """

    MAGIC_CODE_TEMPLATE = 'user/pages/magic_code_signin.html'
    MESSAGES = SigninMagicCodeView.MESSAGES

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

    def submit_signin_code(self, magic_code):
        return self.client.post(self.code_page_url(), {'magic_code': magic_code})

    def expired_now(self):
        return MagicCodeGenerator.get_elapsed_seconds() + MagicCodeGenerator.MAGIC_CODE_TIMEOUT_SECS + 1

    def assertSignedInAs(self, user):
        self.assertEqual(get_user(self.client), user)

    def assertNotSignedIn(self):
        self.assertFalse(get_user(self.client).is_authenticated)

    def assertCodeEntry(self, page, error_status=None):
        keypad_entry = page.context.get('keypad_entry')
        self.assertIsNotNone(keypad_entry, 'code entry shown')
        if error_status is None:
            self.assertIsNone(keypad_entry.error_message)
        else:
            self.assertTrue(keypad_entry.error_message.startswith(self.MESSAGES[error_status]))

    def assertCodeUnusable(self, page, status):
        self.assertNotIn('keypad_entry', page.context)
        self.assertEqual(page.context['unusable_code_message'], self.MESSAGES[status])

    def assertRejectedWithoutSignin(self, response):
        """ Rejected with no sign-in in progress: the code page has nothing to show. """
        self.assertRedirects(response, self.code_page_url(), fetch_redirect_response=False)
        self.assertNotSignedIn()
        self.assertRedirects(self.client.get(self.code_page_url()), reverse('user_signin'),
                             fetch_redirect_response=False)

    def assertCodeRejected(self, response, status=MagicCodeStatus.INVALID):
        """ A rejected code redirects to the code page, which then shows why. """
        self.assertRedirects(response, self.code_page_url(), fetch_redirect_response=False)
        self.assertNotSignedIn()
        page = self.get_code_page()
        if status == MagicCodeStatus.INVALID:
            self.assertCodeEntry(page, error_status=status)
        else:
            self.assertCodeUnusable(page, status)
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

        response = self.submit_signin_code(first_code)

        self.assertCodeRejected(response)


class TestSigninMagicCodeView(SigninFlowTestMixin, SyncViewTestCase):

    def test_get_shows_code_entry_with_email_and_magic_code_keypad(self):
        self.request_signin_code(self.user.email)

        page = self.get_code_page()

        self.assertCodeEntry(page)
        self.assertEqual(page.context['email_address'], self.user.email)
        self.assertIs(page.context['keypad_entry'].spec, UserConstants.MAGIC_CODE_KEYPAD)

    def test_get_while_signed_in_redirects_home(self):
        self.client.force_login(self.user)

        response = self.client.get(self.code_page_url())

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_get_without_signin_in_progress_redirects_to_signin(self):
        response = self.client.get(self.code_page_url())

        self.assertRedirects(response, reverse('user_signin'), fetch_redirect_response=False)

    def test_correct_code_signs_in_and_verifies_email(self):
        _, magic_code = self.request_signin_code(self.user.email)

        response = self.submit_signin_code(magic_code)

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertSignedInAs(self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_wrong_code_rejected(self):
        self.request_signin_code(self.user.email)

        response = self.submit_signin_code('wxyzwx')

        self.assertCodeRejected(response)

    def test_wrong_code_says_how_many_attempts_remain(self):
        self.request_signin_code(self.user.email)

        first = self.assertCodeRejected(self.submit_signin_code('wxyzwx'))
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS - 3):
            self.submit_signin_code('wxyzwx')
        last = self.assertCodeRejected(self.submit_signin_code('wxyzwx'))

        remaining = MagicCodeGenerator.MAX_FAILED_ATTEMPTS - 1
        self.assertIn(f'{remaining} attempts left.', first.context['keypad_entry'].error_message)
        self.assertIn('1 attempt left.', last.context['keypad_entry'].error_message)

    def test_malformed_submit_rejected_without_using_an_attempt(self):
        _, magic_code = self.request_signin_code(self.user.email)
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS):
            self.assertCodeRejected(self.client.post(self.code_page_url(), {}))

        self.submit_signin_code(magic_code)

        self.assertSignedInAs(self.user)

    def test_reload_after_wrong_code_drops_error_and_keeps_code_usable(self):
        _, magic_code = self.request_signin_code(self.user.email)
        self.assertCodeRejected(self.submit_signin_code('wxyzwx'))

        self.assertCodeEntry(self.get_code_page())
        self.submit_signin_code(magic_code)
        self.assertSignedInAs(self.user)

    def test_too_many_attempts_keeps_email_and_stays_unusable_on_reload(self):
        self.request_signin_code(self.user.email)
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS):
            response = self.submit_signin_code('wxyzwx')

        page = self.assertCodeRejected(response, status=MagicCodeStatus.TOO_MANY_ATTEMPTS)
        self.assertEqual(page.context['email_address'], self.user.email)
        self.assertCodeUnusable(self.get_code_page(), MagicCodeStatus.NO_CODE)

    def test_too_many_attempts_then_new_code_signs_in(self):
        self.request_signin_code(self.user.email)
        for _ in range(MagicCodeGenerator.MAX_FAILED_ATTEMPTS):
            self.submit_signin_code('wxyzwx')

        _, new_code = self.request_signin_code(self.user.email)
        self.submit_signin_code(new_code)

        self.assertSignedInAs(self.user)

    def test_expired_code_shown_unusable_before_any_submit(self):
        self.request_signin_code(self.user.email)

        with patch.object(MagicCodeGenerator, 'get_elapsed_seconds', return_value=self.expired_now()):
            page = self.get_code_page()

        self.assertCodeUnusable(page, MagicCodeStatus.EXPIRED)

    def test_expired_code_rejected_as_expired_even_when_wrong(self):
        self.request_signin_code(self.user.email)

        with patch.object(MagicCodeGenerator, 'get_elapsed_seconds', return_value=self.expired_now()):
            response = self.submit_signin_code('wxyzwx')

        self.assertCodeRejected(response, status=MagicCodeStatus.EXPIRED)

    def test_nonexistent_account_matching_code_leaves_no_usable_code(self):
        _, magic_code = self.request_signin_code('nobody@example.com')

        response = self.submit_signin_code(magic_code)

        self.assertCodeRejected(response, status=MagicCodeStatus.NO_CODE)

    def test_code_cannot_be_reused(self):
        _, magic_code = self.request_signin_code(self.user.email)
        self.submit_signin_code(magic_code)
        self.client.logout()

        response = self.submit_signin_code(magic_code)

        self.assertRejectedWithoutSignin(response)

    def test_rejection_without_signin_does_not_carry_into_next_signin(self):
        self.assertRejectedWithoutSignin(self.submit_signin_code('abcdef'))

        self.request_signin_code(self.user.email)

        self.assertCodeEntry(self.get_code_page())

    def test_post_while_signed_in_redirects_home_without_redeeming(self):
        _, magic_code = self.request_signin_code(self.user.email)
        self.client.force_login(self.user)

        response = self.submit_signin_code(magic_code)

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertEqual(self.client.session.get(MagicCodeGenerator.MAGIC_CODE), magic_code)


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

    def test_signing_in_by_link_spends_the_pending_code(self):
        self.request_signin_code(self.user.email)
        token = PasswordResetTokenGenerator().make_token(user=self.user)

        self.get_link(self.user.email, token)

        self.assertIsNone(self.client.session.get(MagicCodeGenerator.MAGIC_CODE))

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
