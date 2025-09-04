import logging
import random

from django.conf import settings
from django.forms.utils import ErrorList

from hi.apps.attribute.transient_models import AttributeEditFormData

logger = logging.getLogger(__name__)


class DevOverrideManager:

    @classmethod
    def validate_forms( cls, edit_form_data: AttributeEditFormData ) -> bool:
        """
        For: AttributeEditFormHandler.validate()forms)

        Inject simulated errors for UI testing (DEBUG mode only).
        
        This method simulates all types of form errors to test UI error display:
        - Owner form field errors
        - Owner form non-field errors
        - Formset management errors (simulated by corrupting management form)
        - Formset non-form errors
        - Individual form field errors
        - Individual form non-field errors
        
        Returns:
            bool: Always False (simulating validation failure)
        """
        assert settings.DEBUG
        
        error_injection_rate = 1.0
        
        logger.warning("Injecting test errors for UI validation testing")
        
        # Inject owner form errors
        if edit_form_data.owner_form and random.random() <= error_injection_rate:
            owner_form = edit_form_data.owner_form
            
            # Inject field errors
            if random.random() <= error_injection_rate:
                for field_name in list(owner_form.fields.keys())[:2]:  # Limit to first 2 fields
                    if random.random() <= error_injection_rate:
                        if not hasattr(owner_form, '_errors') or not owner_form._errors:
                            owner_form._errors = {}
                        if field_name not in owner_form._errors:
                            owner_form._errors[field_name] = ErrorList()
                        owner_form._errors[field_name].append(f"TEST: {field_name} validation failed")
            
            # Inject non-field errors
            if random.random() <= error_injection_rate:
                if not hasattr(owner_form, '_errors') or not owner_form._errors:
                    owner_form._errors = {}
                if '__all__' not in owner_form._errors:
                    owner_form._errors['__all__'] = ErrorList()
                owner_form._errors['__all__'].append("TEST: Owner form validation failed")
        
        # Inject formset errors
        if edit_form_data.regular_attributes_formset and random.random() <= error_injection_rate:
            formset = edit_form_data.regular_attributes_formset
            
            # Inject formset non-form errors
            if random.random() <= error_injection_rate:
                if not hasattr(formset, '_non_form_errors') or not formset._non_form_errors:
                    formset._non_form_errors = ErrorList()
                formset._non_form_errors.append("TEST: Formset validation constraint failed")
            
            # Inject individual form errors (only for bound forms)
            for i, form in enumerate(formset.forms):
                # Skip non-bound forms (empty extra forms)
                if not form.is_bound:
                    continue
                    
                if random.random() <= error_injection_rate:
                    
                    # Inject field errors
                    if random.random() <= error_injection_rate:
                        field_names = list(form.fields.keys())[:2]  # Limit to first 2 fields
                        for field_name in field_names:
                            if random.random() <= error_injection_rate:
                                if not hasattr(form, '_errors') or not form._errors:
                                    form._errors = {}
                                if field_name not in form._errors:
                                    form._errors[field_name] = ErrorList()
                                form._errors[field_name].append(f"TEST: Form {i} {field_name} invalid")
                    
                    # Inject non-field errors
                    if random.random() <= error_injection_rate:
                        if not hasattr(form, '_errors') or not form._errors:
                            form._errors = {}
                        if '__all__' not in form._errors:
                            form._errors['__all__'] = ErrorList()
                        form._errors['__all__'].append(f"TEST: Form {i} validation failed")
        
        # Always return False to simulate validation failure
        return False
    
    
