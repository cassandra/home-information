import logging
import random
from typing import Any, Optional

from django.conf import settings
from django.forms.utils import ErrorList

from hi.apps.attribute.transient_models import AttributeEditFormData

logger = logging.getLogger(__name__)
trace_logger = logging.getLogger('hi.state_trace')


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

    @classmethod
    def trace_state( cls,
                     label              : str,
                     ha_entity_id       : Optional[ str ] = None,
                     hi_entity_state_id : Optional[ int ] = None,
                     ha_value           : Any             = None,
                     hi_value           : Any             = None,
                     **kwargs           : Any ) -> None:
        if not StateTraceManager.is_traced(
                ha_entity_id = ha_entity_id,
                hi_entity_state_id = hi_entity_state_id ):
            return
        StateTraceManager.emit(
            label = label,
            ha_entity_id = ha_entity_id,
            hi_entity_state_id = hi_entity_state_id,
            ha_value = ha_value,
            hi_value = hi_value,
            **kwargs,
        )


class StateTraceManager:
    """
    Per-state tracing for debugging value flow across the HA
    integration and the simulator.

    Reached from main code only via ``DevOverrideManager.trace_state``;
    main-code sites short-circuit on
    ``settings.DEBUG and settings.DEBUG_TRACE_STATE`` so this class
    is only consulted when tracing is on.

    Granularity is set by ``DEBUG_TRACE_HA_ENTITY_IDS`` (HA
    entity_ids; the matcher strips any ``~suffix`` so a single
    entry like ``'cover.x'`` catches its substate variants) and
    ``DEBUG_TRACE_HI_ENTITY_STATE_IDS`` (HI EntityState PKs).
    Output goes to the dedicated ``hi.state_trace`` logger at
    INFO so verbosity can be scoped independently of other
    loggers.
    """

    @classmethod
    def is_traced( cls,
                   ha_entity_id       : Optional[ str ] = None,
                   hi_entity_state_id : Optional[ int ] = None ) -> bool:
        if ha_entity_id:
            target = ha_entity_id.split( '~', 1 )[ 0 ]
            if target in settings.DEBUG_TRACE_HA_ENTITY_IDS:
                return True
        if hi_entity_state_id is not None:
            if hi_entity_state_id in settings.DEBUG_TRACE_HI_ENTITY_STATE_IDS:
                return True
        return False

    # Tabular column widths. Generous so common values fit without
    # disrupting alignment; long values overflow the slot and
    # disrupt only their own row, not subsequent ones.
    LABEL_W   = 28
    HA_ID_W   = 32
    HA_VAL_W  = 14
    HI_ID_W   = 6
    HI_VAL_W  = 36

    @classmethod
    def emit( cls,
              label              : str,
              ha_entity_id       : Optional[ str ] = None,
              hi_entity_state_id : Optional[ int ] = None,
              ha_value           : Any             = None,
              hi_value           : Any             = None,
              **kwargs           : Any ) -> None:
        ha_id_str   = ha_entity_id or ''
        hi_id_str   = '' if hi_entity_state_id is None else str( hi_entity_state_id )
        ha_val_str  = '' if ha_value is None else str( ha_value )
        hi_val_str  = '' if hi_value is None else str( hi_value )
        extras_str  = ' '.join( f'{k}={v}' for k, v in kwargs.items() )
        line = (
            f'{label:<{cls.LABEL_W}} | '
            f'{ha_id_str:<{cls.HA_ID_W}} | '
            f'{ha_val_str:<{cls.HA_VAL_W}} | '
            f'{hi_id_str:<{cls.HI_ID_W}} | '
            f'{hi_val_str:<{cls.HI_VAL_W}} | '
            f'{extras_str}'
        )
        trace_logger.info( line.rstrip() )



