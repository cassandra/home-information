"""
SECRET attribute encryption integration tests.

Tests SECRET attribute encryption during form save, decryption during form
load, and end-to-end round-trip.
"""
import logging

from cryptography.fernet import Fernet

from django.http import QueryDict

from hi.apps.attribute.crypto import encrypt_value, decrypt_value
from hi.apps.attribute.enums import AttributeType, AttributeValueType

from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler

from hi.apps.entity.forms import EntityAttributeForm
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.entity.tests.synthetic_data import EntityAttributeSyntheticData
from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext

from hi.testing.base_test_case import BaseTestCase, MockRequest, MockSession

logging.disable(logging.CRITICAL)

TEST_ENCRYPTION_KEY = Fernet.generate_key().decode('utf-8')


class TestSecretAttributeEncryption(BaseTestCase):
    """Tests for SECRET attributes encryption and decryption."""

    def test_save_new_secret_attribute_stores_ciphertext_not_plaintext(self):
        """Test that new SECRET attributes are encrypted before saving."""

        plain = 'my_api_key_12345'
        entity = self._create_entity()

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            form = self._build_bound_form(entity, value=plain, secret=True)
            self.assertTrue(form.is_valid(), form.errors)
            saved_attr = form.save()

        saved_attr.refresh_from_db()

        self.assertEqual(saved_attr.value_type, AttributeValueType.SECRET)
        self.assertNotEqual(
            saved_attr.value, plain,
            'The plain-text value must not be stored directly in the database.',
        )

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            decrypted = decrypt_value(saved_attr.value)
            self.assertEqual(decrypted, plain)

    def test_save_new_non_secret_attribute_stores_plaintext(self):
        """Test that non-secret attributes are stored as plain text."""

        plain = 'ordinary_value'
        entity = self._create_entity()

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            form = self._build_bound_form(entity, value=plain, secret=False)
            self.assertTrue(form.is_valid(), form.errors)
            saved_attr = form.save()

        saved_attr.refresh_from_db()

        self.assertEqual(saved_attr.value_type, AttributeValueType.TEXT)
        self.assertEqual(saved_attr.value, plain)

    def test_form_initial_value_is_decrypted_plain_text(self):
        """Test that SECRET attributes are decrypted when the form is loaded."""

        plain = 'secret_token_xyz'
        attr = self._create_encrypted_attribute(plain)

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            form = EntityAttributeForm(instance=attr)

        self.assertEqual(
            form.initial.get('value'), plain,
            'form.initial["value"] must be the decrypted plain text, not the ciphertext.',
        )

    def test_handler_save_then_load_round_trip(self):
        """Test round-trip encryption."""

        plain = 'my_secret'
        entity = self._create_entity()
        context = self._make_context(entity)
        handler = AttributeEditFormHandler()
        post_data = self._create_secret_post_data(entity, context, plain)

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            form_data = handler.create_edit_form_data(
                attr_item_context=context,
                form_data=post_data,
            )
            self.assertTrue(
                handler.validate_forms(edit_form_data=form_data),
                f'Form validation failed: {form_data.regular_attributes_formset.errors}',
            )
            handler.save_forms(
                attr_item_context=context,
                edit_form_data=form_data,
                request=self._make_request(post_data),
            )

            saved_attr = EntityAttribute.objects.get(
                entity=entity,
                name='my_secret_attr',
            )
            self.assertNotEqual(
                saved_attr.value, plain,
                'Ciphertext must differ from the plain-text submission.',
            )
            self.assertEqual(saved_attr.value_type, AttributeValueType.SECRET)

            load_form_data = handler.create_edit_form_data(
                attr_item_context=context,
            )
            
            formset = load_form_data.regular_attributes_formset
            secret_form = next(
                (f for f in formset.forms if f.instance.pk == saved_attr.pk),
                None,
            )
            
        self.assertIsNotNone(
            secret_form,
            'Expected to find the saved SECRET attribute in the formset.',
        )
        self.assertEqual(
            secret_form.initial.get('value'), plain,
            'The form initial value must be the decrypted plain text, ready for the frontend.',
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_entity(self, name: str = 'Test Entity') -> Entity:
        return EntityAttributeSyntheticData.create_test_entity(name=name)

    def _build_bound_form( self, 
                           entity: Entity, 
                           value: str, 
                           secret: bool = True ) -> EntityAttributeForm:
        
        new_instance = EntityAttribute(entity=entity)
        data = {
            'name': 'api_key',
            'value': value,
            'secret': str(secret),
            'order_id': '0',
        }
        return EntityAttributeForm(data, instance=new_instance)

    def _create_encrypted_attribute( self, plain: str, entity: Entity = None ) -> EntityAttribute:
        if entity is None:
            entity = self._create_entity()

        with self.settings(MASTER_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY):
            ciphertext = encrypt_value(plain)

        return EntityAttribute.objects.create(
            entity=entity,
            name='stored_secret',
            value=ciphertext,
            attribute_type_str=str(AttributeType.CUSTOM),
            value_type_str=str(AttributeValueType.SECRET),
        )

    def _make_request(self, post_data: dict) -> MockRequest:
        qd = QueryDict(mutable=True)
        for key, value in post_data.items():
            qd[key] = value
        request = MockRequest()
        request.POST = qd
        request.session = MockSession()
        return request

    def _make_context(self, entity: Entity) -> EntityAttributeItemEditContext:
        return EntityAttributeItemEditContext(entity=entity)

    def _create_secret_post_data( self, 
                                  entity: Entity, 
                                  context: EntityAttributeItemEditContext, 
                                  plain_value: str ) -> dict:

        prefix = context.formset_prefix
        return {
            'name': entity.name,
            'entity_type_str': entity.entity_type_str,
            f'{prefix}-TOTAL_FORMS': '1',
            f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '100',
            f'{prefix}-0-id': '',
            f'{prefix}-0-name': 'my_secret_attr',
            f'{prefix}-0-value': plain_value,
            f'{prefix}-0-secret': 'on',
            f'{prefix}-0-order_id': '0',
        }
