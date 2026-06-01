(function() {
    
    const Hi = {

        // HiClientConfig comes from server-side template injection. This module
        // (main.css) should be the only Javaacript that knows about
        // HiClientConfig and the coordination mechanism with those
        // server-delivered config settings.  All other JS modules should
        // look to this module to relay any needed config settings (via
        // variable below).
        //
        DEBUG: window.HiClientConfig?.DEBUG ?? false,
        isEditMode: window.HiClientConfig?.IS_EDIT_MODE ?? false,

        // Server-provided URLs (via ClientConfig context processor)
        API_STATUS_URL: window.HiClientConfig?.API_STATUS_URL ?? '/api/status',
        CONSOLE_UNLOCK_URL: window.HiClientConfig?.CONSOLE_UNLOCK_URL ?? '/console/unlock',

        MAIN_AREA_SELECTOR: '#hi-main-content',
        LOCATION_VIEW_AREA_SELECTOR: '#hi-location-view-main',
        LOCATION_VIEW_SVG_CLASS: 'hi-location-view-svg',
        LOCATION_VIEW_SVG_SELECTOR: '.hi-location-view-svg',
        LOCATION_VIEW_BASE_SELECTOR: '.hi-location-view-base',
        BASE_SVG_SELECTOR: '#hi-location-view-main > svg',
        SVG_ICON_CLASS: 'hi-svg-icon',
        SVG_PATH_CLASS: 'hi-svg-path',
        HIGHLIGHTED_CLASS: 'highlighted',
        ATTRIBUTE_CONTAINER_SELECTOR: '.hi-attribute',
        FORM_FIELD_CONTAINER_SELECTOR: '.input-group',
        AUDIO_PERMISSION_GUIDANCE_SELECTOR: '#hi-audio-permission-guidance',
        SVG_ACTION_STATE_ATTR_NAME: 'action-state',

        DATA_TYPE_ATTR: 'data-type',
        DATA_TYPE_ICON_VALUE: 'svg-icon',
        DATA_TYPE_PATH_VALUE: 'svg-path',
        
        API_LOCATION_ITEM_EDIT_MODE_URL: '/location/edit/item/edit-mode',
        API_LOCATION_ITEM_STATUS_URL: '/location/item/status',
        ENTITY_STATE_VALUE_CHOICES_URL_PREFIX: '/edit/entity/state/values',
        
        generateUniqueId: function() {
            return _generateUniqueId();
        },
        setCookie: function( name, value, days = 365, sameSite = 'Lax' ) {
            return _setCookie( name, value, days, sameSite );
        },
        getCookie: function( name ) {
            return _getCookie( name );
        },
        submitForm: function( formElement ) {
            return _submitForm( formElement );
        },
        updateFormDirtyState: function( formElement ) {
            return _updateFormDirtyState( formElement );
        },
        togglePasswordField: function( toggleCheckbox ) {
            return _togglePasswordField( toggleCheckbox );
        },
        toggleDetails: function( elementId ) {
            return _toggleDetails( elementId );
        },
        setEntityStateValueSelect: function( valueFieldId, instanceName, instanceId ) {
            return _setEntityStateValueSelect( valueFieldId, instanceName, instanceId );
        },
        setEventClauseValueOperatorWidget: function( operatorFieldId, valueFieldId ) {
            return _setEventClauseValueOperatorWidget( operatorFieldId, valueFieldId );
        },
        getScreenCenterPoint: function( element ) {
            return _getScreenCenterPoint( element );
        },
        getRotationAngle: function( centerX, centerY, startX, startY, endX, endY ) {
            return _getRotationAngle( centerX, centerY, startX, startY, endX, endY );
        },
        normalizeAngle: function(angle) {
            return _normalizeAngle(angle);
        },
        displayEventInfo: function ( label, event ) {
            return _displayEventInfo( label, event );
        },
        displayElementInfo: function( label, element ) {
            return _displayElementInfo( label, element );
        },
        
        // Entity Attribute Editing V2 - IDs and Classes
        ATTR_V2_CONTENT_CLASS: 'attr-v2-content',
        ATTR_V2_UPLOAD_FORM_CONTAINER_ID: 'attr-v2-upload-form-container',
        ATTR_V2_FILE_INPUT_ID: 'attr-v2-file-input',
        ATTR_V2_FILE_TITLE_INPUT_CLASS: 'attr-v2-file-title-input',
        ATTR_V2_DIRTY_MESSAGE_CLASS: 'attr-v2-dirty-message',
        ATTR_V2_STATUS_MESSAGE_CLASS: 'attr-v2-status-message',
        ATTR_V2_UPDATE_BTN_CLASS: 'attr-v2-update-btn',

        ATTR_V2_ATTRIBUTE_NAME_CLASS: 'attr-v2-attribute-name',
        // Ready-to-use jQuery selectors
        ATTR_V2_FORM_CLASS_SELECTOR: '.attr-v2-form',        // Form class
        ATTR_V2_CONTAINER_SELECTOR: '.attr-v2-container',
        ATTR_V2_FILE_INPUT_SELECTOR: '.attr-v2-file-input',
        ATTR_V2_STATUS_MESSAGE_SELECTOR: '.attr-v2-status-message',
        ATTR_V2_DIRTY_MESSAGE_SELECTOR: '.attr-v2-dirty-message',
        ATTR_V2_HISTORY_LINK_SELECTOR: '.attr-v2-history-link',
        ATTR_V2_RESTORE_LINK_SELECTOR: '.attr-v2-restore-link',
        ATTR_V2_ATTRIBUTE_CARD_SELECTOR: '.attr-v2-attribute-card',
        ATTR_V2_NEW_ATTRIBUTE_SELECTOR: '.attr-v2-new-attribute',
        ATTR_V2_FILE_TITLE_INPUT_SELECTOR: '.attr-v2-file-title-input',
        ATTR_V2_FILE_INFO_SELECTOR: '.attr-v2-file-info',
        ATTR_V2_ATTRIBUTE_NAME_SELECTOR: '.attr-v2-attribute-name',
        ATTR_V2_DELETE_BTN_SELECTOR: '.attr-v2-delete-btn',
        ATTR_V2_UNDO_BTN_SELECTOR: '.attr-v2-undo-btn',
        ATTR_V2_FILE_CARD_SELECTOR: '.attr-v2-file-card',
        ATTR_V2_SECRET_INPUT_WRAPPER_SELECTOR: '.attr-v2-secret-input-wrapper',
        ATTR_V2_FORM_DISPLAY_LABEL_SELECTOR: '.attr-v2-form-display-label',
        ATTR_V2_SECRET_INPUT_SELECTOR: '.attr-v2-secret-input',
        ATTR_V2_ICON_SHOW_SELECTOR: '.attr-v2-icon-show',
        ATTR_V2_ICON_HIDE_SELECTOR: '.attr-v2-icon-hide',
        ATTR_V2_TEXTAREA_SELECTOR: '.attr-v2-textarea',
        ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR: '.attr-v2-text-value-wrapper',
        ATTR_V2_EXPAND_CONTROLS_SELECTOR: '.attr-v2-expand-controls',
        ATTR_V2_AUTO_DISMISS_SELECTOR: '.attr-v2-auto-dismiss',
        ATTR_V2_UPDATE_BTN_SELECTOR: '.attr-v2-update-btn',
        ATTR_V2_DISPLAY_FIELD_SELECTOR: '.display-field',
        ATTR_V2_TEXT_READ_MODE_SELECTOR: '.attr-v2-text-read-mode',
        ATTR_V2_TEXT_READ_CONTENT_SELECTOR: '.attr-v2-text-read-content',
        ATTR_V2_TEXT_EDIT_MODE_SELECTOR: '.attr-v2-text-edit-mode',
        ATTR_V2_TEXT_EDIT_FIELD_SELECTOR: '.attr-v2-text-edit-field',
        ATTR_V2_SHOW_MORE_TEXT_SELECTOR: '.show-more-text',
        ATTR_V2_SHOW_LESS_TEXT_SELECTOR: '.show-less-text',
        
        // Data attributes set by server, read by JS
        DATA_ATTRIBUTE_ID_ATTR: 'data-attribute-id',
        DATA_HIDDEN_FIELD_ATTR: 'data-hidden-field',
        DATA_OVERFLOW_ATTR: 'data-overflow',
        DATA_LINE_COUNT_ATTR: 'data-line-count',
        DATA_ORIGINAL_VALUE_ATTR: 'data-original-value',
        ATTR_V2_DELETE_FILE_ATTR: 'delete_file_attribute',

        // Controller widgets - Class names and data attributes
        // shared between controller templates (server-emitted)
        // and controllers.js (client-side display sync, preset
        // buttons). Mirror of DIVID entries in src/hi/constants.py.
        CONTROLLER_DISPLAY_TARGET_ATTR: 'data-display-target',
        CONTROLLER_DISPLAY_FORMAT_ATTR: 'data-display-format',
        CONTROLLER_SLIDER_CLASS: 'hi-continuous-slider',
        CONTROLLER_SLIDER_CONTROL_CLASS: 'hi-continuous-slider-control',
        CONTROLLER_PRESET_BTN_CLASS: 'hi-continuous-slider-preset-btn',
        DATA_VALUE_ATTR: 'data-value',

        // Entity Picker - selectors for JavaScript dependencies
        ENTITY_PICKER_FILTERABLE_ITEM_SELECTOR: '.filterable-item',
        ENTITY_PICKER_GROUP_SECTION_SELECTOR: '.entity-group-section',
        ENTITY_PICKER_SEARCH_INPUT_SELECTOR: '#entity-search-input',
        ENTITY_PICKER_SEARCH_CLEAR_SELECTOR: '.entity-search-clear',
        ENTITY_PICKER_FILTER_BTN_SELECTOR: '.entity-filter-btn',

        // Entity Picker - Data attributes
        ENTITY_PICKER_DATA_NAME_ATTR: 'data-entity-name',
        ENTITY_PICKER_DATA_TYPE_ATTR: 'data-entity-type',
        ENTITY_PICKER_DATA_STATUS_ATTR: 'data-status',
        ENTITY_PICKER_DATA_FILTER_ATTR: 'data-filter',

        // Entity Picker - Status values
        ENTITY_PICKER_STATUS_IN_VIEW: 'in-view',
        ENTITY_PICKER_STATUS_NOT_IN_VIEW: 'not-in-view',
        ENTITY_PICKER_STATUS_UNUSED: 'unused',

        // Entity Picker - Filter values
        ENTITY_PICKER_FILTER_ALL: 'all',

        // EXTERNAL_REFERENCE picker — DOM classes / data attributes
        // / wire-format field names shared with the server. Mirror
        // of the ``REF_PICKER_*`` entries in
        // ``src/hi/constants.py:DIVID``.
        REF_PICKER_ROOT_CLASS:              'hi-ref-picker',
        REF_PICKER_CHIPS_CLASS:             'hi-ref-picker-chips',
        REF_PICKER_CHIPS_EMPTY_CLASS:       'hi-ref-picker-chips-empty',
        REF_PICKER_CHIP_REMOVE_CLASS:       'hi-ref-picker-chip-remove',
        REF_PICKER_RESULTS_CLASS:           'hi-ref-picker-results',
        REF_PICKER_SEARCH_FORM_CLASS:       'hi-ref-picker-search-form',
        REF_PICKER_ATTACH_FORM_CLASS:       'hi-ref-picker-attach-form',
        REF_PICKER_ATTACH_BTN_CLASS:        'hi-ref-picker-attach-btn',
        REF_PICKER_ATTACH_LABEL_CLASS:      'hi-ref-picker-attach-label',
        REF_PICKER_RESULT_CHECKBOX_CLASS:   'hi-ref-picker-result-checkbox',
        REF_PICKER_SEARCH_URL_ATTR:         'data-ref-picker-search-url',
        REF_PICKER_TITLE_ATTR:              'data-ref-picker-title',
        REF_PICKER_SOURCE_URL_ATTR:         'data-ref-picker-source-url',
        REF_PICKER_INTEGRATION_NAME_ATTR:   'data-ref-picker-integration-name',
        REF_PICKER_MIME_TYPE_ATTR:          'data-ref-picker-mime-type',
        REF_PICKER_QUERY_FIELD:             'query',
        REF_PICKER_LIMIT_FIELD:             'limit',
        REF_PICKER_ITEM_TYPE_FIELD:         'item_type',
        REF_PICKER_ITEM_ID_FIELD:           'item_id',
        REF_PICKER_INTEGRATION_ID_FIELD:    'integration_id',
        REF_PICKER_SELECTIONS_JSON_FIELD:   'selections_json',
        REF_PICKER_SELECTION_TITLE_KEY:     'title',
        REF_PICKER_SELECTION_URL_KEY:       'source_url',
        REF_PICKER_SELECTION_INTEGRATION_NAME_KEY: 'integration_name',
        REF_PICKER_SELECTION_MIME_TYPE_KEY: 'mime_type',
        REF_PICKER_SOURCE_BANNER_CLASS:     'hi-ref-picker-source-banner',
        REF_PICKER_SOURCE_BANNER_LOGO_CLASS: 'hi-ref-picker-source-banner-logo',
        REF_PICKER_SOURCE_BANNER_LABEL_CLASS: 'hi-ref-picker-source-banner-label',
        REF_PICKER_SOURCE_OPTION_CLASS:     'hi-ref-picker-source-option',
        REF_PICKER_SOURCE_ID_ATTR:          'data-ref-picker-source-id',
        REF_PICKER_SOURCE_LOGO_ATTR:        'data-ref-picker-source-logo',
        REF_PICKER_SOURCE_LABEL_ATTR:       'data-ref-picker-source-label',

        // External-reference card grid -- mirrors EXT_REF_* keys in
        // hi.constants.DIVID.
        EXT_REF_GRID_CLASS:                  'hi-ext-ref-grid',
        EXT_REF_CARD_CLASS:                  'hi-ext-ref-card',
        EXT_REF_TITLE_INPUT_CLASS:           'hi-ext-ref-title-input',
        EXT_REF_DELETE_BTN_CLASS:            'hi-ext-ref-delete-btn',
        EXT_REF_REORDER_LEFT_CLASS:          'hi-ext-ref-reorder-left',
        EXT_REF_REORDER_RIGHT_CLASS:         'hi-ext-ref-reorder-right',
        EXT_REF_REFERENCE_ID_ATTR:           'data-ext-ref-id',
        EXT_REF_OWNER_TYPE_ATTR:             'data-ext-ref-owner-type',
        EXT_REF_SOURCE_URL_ATTR:             'data-ext-ref-source-url',
        EXT_REF_TITLE_FIELD:                 'title',
        EXT_REF_DIRECTION_FIELD:             'direction',
        EXT_REF_DIRECTION_LEFT:              'left',
        EXT_REF_DIRECTION_RIGHT:             'right'
    };
    
    window.Hi = Hi;

    function _generateUniqueId() {
        return 'id-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
    }

    function _setCookie( name, value, days, sameSite ) {
        const expires = new Date();
        expires.setTime( expires.getTime() + days * 24 * 60 * 60 * 1000 );
        const secureFlag = sameSite === 'None' ? '; Secure' : '';
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires.toUTCString()}; path=/; SameSite=${sameSite}${secureFlag}`;
        return true;
    }

    function _getCookie( name ) {
        const nameEQ = `${encodeURIComponent(name)}=`;
        const cookies = document.cookie.split(';'); // SPlit into key-pairs
        for ( let i = 0; i < cookies.length; i++ ) {
            let cookie = cookies[i].trim();
            if (cookie.startsWith( nameEQ )) {
                return decodeURIComponent( cookie.substring( nameEQ.length ));
            }
        }
        return null;    
    }
    
    function _submitForm( formElement ) {
        let form = $(formElement).closest('form');
        if ( Hi.DEBUG ) { console.debug( 'Submitting form:', formElement, form ); }
        $(form).submit();
    }

    function _updateFormDirtyState( formElement ) {
        // Compares each field's current value to its server-rendered
        // initial (``defaultValue`` / ``defaultChecked`` /
        // ``defaultSelected``), toggles ``.dirty`` on the field's
        // label, and enables/disables the form's submit button(s).
        // ``defaultValue`` etc. survive value mutations but are reset
        // by any re-render of the form HTML, so a successful save's
        // returned markup naturally re-baselines without explicit
        // state-reset code.
        let anyDirty = false;
        const fields = formElement.querySelectorAll( 'input, select, textarea' );
        fields.forEach( function( field ) {
            // Skip hidden CSRF tokens, submit buttons, and unnamed
            // controls that aren't part of the form's data payload.
            if ( ! field.name ) { return; }
            if ( field.type === 'hidden' ) { return; }
            if ( field.type === 'submit' || field.type === 'button' ) { return; }
            let fieldDirty = false;
            if ( field.type === 'checkbox' || field.type === 'radio' ) {
                fieldDirty = ( field.checked !== field.defaultChecked );
            } else if ( field.tagName === 'SELECT' ) {
                for ( const option of field.options ) {
                    if ( option.selected !== option.defaultSelected ) {
                        fieldDirty = true;
                        break;
                    }
                }
            } else {
                fieldDirty = ( field.value !== field.defaultValue );
            }
            if ( field.id ) {
                const label = formElement.querySelector(
                    'label[for="' + field.id + '"]'
                );
                if ( label ) {
                    label.classList.toggle( 'dirty', fieldDirty );
                }
            }
            if ( fieldDirty ) { anyDirty = true; }
        });
        const submitButtons = formElement.querySelectorAll( 'button[type="submit"]' );
        submitButtons.forEach( function( button ) {
            button.disabled = ! anyDirty;
        });
    }

    function _togglePasswordField( toggleCheckbox ) {

        let passwordField = $(toggleCheckbox).closest(Hi.FORM_FIELD_CONTAINER_SELECTOR).find('input[type="password"], input[type="text"]');
        if ( toggleCheckbox.checked ) {
            passwordField.attr('type', 'text');
            $('label[for="' +  $(toggleCheckbox).attr('id') + '"]').text('Hide');
        } else {
            passwordField.attr('type', 'password');
            $('label[for="' +  $(toggleCheckbox).attr('id') + '"]').text('Show');
        }
    }

    function _toggleDetails( elementId ) {
        if (!elementId || elementId.trim() === '') {
            console.warn('_toggleDetails called with empty elementId');
            return;
        }
        const el = document.getElementById(elementId);
        if (el) {
            $(el).toggle();
        } else {
            console.warn('_toggleDetails: Element not found with ID:', elementId);
        }
    }
    
    function _setEventClauseValueOperatorWidget( operatorFieldId, valueFieldId ) {
        // EventClause operator change handler. Four cases:
        //   numeric ops → number input; IN → multi-select; EQ/NEQ →
        //   leave widget alone (collapsing a prior IN multi-select if
        //   needed). The numeric-ops list comes from the operator
        //   field's ``data-numeric-ops`` attribute so the enum stays
        //   the single source of truth.
        const operatorElement = $(`#${operatorFieldId}`);
        const op = operatorElement.val().toLowerCase();
        const numericOps = JSON.parse(
            operatorElement.attr( 'data-numeric-ops' ) || '[]'
        );
        const valueElement = $(`#${valueFieldId}`);
        const isSelect = ( valueElement.prop( 'tagName' ).toLowerCase() === 'select' );

        if ( numericOps.includes( op )) {
            const currentValue = isSelect ? '' : valueElement.val();
            const numericInput = $('<input>')
                .attr( 'type', 'number' )
                .attr( 'step', 'any' )
                .attr( 'id', valueElement.attr('id') )
                .attr( 'name', valueElement.attr('name') )
                .val( currentValue );
            valueElement.replaceWith( numericInput );
            return;
        }

        if ( op === 'in' ) {
            if ( isSelect ) {
                valueElement.attr( 'multiple', 'multiple' );
            }
            return;
        }

        if ( isSelect && valueElement.attr( 'multiple' )) {
            valueElement.removeAttr( 'multiple' );
            const selected = valueElement.find( 'option:selected' );
            if ( selected.length > 1 ) {
                selected.slice( 1 ).prop( 'selected', false );
            }
        }
    }

    function _setEntityStateValueSelect( valueFieldId, instanceName, instanceId ) {
        $.ajax({
            type: 'GET',
            url: `${Hi.ENTITY_STATE_VALUE_CHOICES_URL_PREFIX}/${instanceName}/${instanceId}`,

            success: function( data, status, xhr ) {
                const choices_list = data;
                const valueElement = $(`#${valueFieldId}`);
                const valueElementId = $(valueElement).attr('id');
                const valueElementName = $(valueElement).attr('name');

                if (choices_list.length > 0) {
                    const selectElement = $('<select>')
                          .attr( 'id', valueElementId )
                          .attr( 'name', valueElementName );

                    selectElement.append( $('<option>').val('').text('------'));
                    choices_list.forEach( choice => {
                        const [value, label] = choice;
                        selectElement.append( $('<option>').val(value).text(label) );
                    });
                    valueElement.replaceWith(selectElement);
                } else {
                    const inputElement = $('<input>')
                          .attr( 'type', 'text' )
                          .attr( 'id', valueElementId )
                          .attr( 'name', valueElementName );
                    valueElement.replaceWith(inputElement);
                }
                return false;
            },
            error: function (xhr, ajaxOptions, thrownError) {
                console.error( `Fetch entity state choices error [${xhr.status}] : ${thrownError}` );
                return false;
            } 
        });
    }
    
    function _getScreenCenterPoint( element ) {
        try {
            let rect = $(element)[0].getBoundingClientRect();
            if ( rect ) {
                const screenCenterX = rect.left + ( rect.width / 2.0 );
                const screenCenterY = rect.top + ( rect.height / 2.0 );
                return {
                    x: rect.left + ( rect.width / 2.0 ),
                    y: rect.top + ( rect.height / 2.0 )
                };
            }
        } catch (e) {
            console.debug( `Problem getting bounding box: ${e}` );
        }
        return null;
    }
    
    function _getRotationAngle( centerX, centerY, startX, startY, endX, endY ) {

        const startVectorX = startX - centerX;
        const startVectorY = startY - centerY;

        const endVectorX = endX - centerX;
        const endVectorY = endY - centerY;

        const startAngle = Math.atan2( startVectorY, startVectorX );
        const endAngle = Math.atan2( endVectorY, endVectorX );

        let angleDifference = endAngle - startAngle;

        // Normalize the angle to be between -π and π
        if ( angleDifference > Math.PI ) {
            angleDifference -= 2 * Math.PI;
        } else if ( angleDifference < -Math.PI ) {
            angleDifference += 2 * Math.PI;
        }

        const angleDifferenceDegrees = angleDifference * ( 180 / Math.PI );

        return angleDifferenceDegrees;
    }

    function _normalizeAngle(angle) {
        return (angle % 360 + 360) % 360;
    }

    function _displayEventInfo ( label, event ) {
        if ( ! Hi.DEBUG ) { return; }
        if ( ! event ) {
            console.log( 'No element to display info for.' );
            return;
        }
        console.log( `${label} Event: 
    Type: ${event.type}, 
    Key: ${event.key},
    KeyCode: ${event.keyCode},
    Pos: ( ${event.clientX}, ${event.clientY} )` );
    }

    function _displayElementInfo( label, element ) {
        if ( ! Hi.DEBUG ) { return; }
        if ( ! element ) {
            console.log( 'No element to display info for.' );
            return;
        }
        const elementTag = $(element).prop('tagName');
        const elementId = $(element).attr('id') || 'No ID';
        const elementClasses = $(element).attr('class') || 'No Classes';
        
        let rectStr = 'No Bounding Rect';
        try {
            let rect = $(element)[0].getBoundingClientRect();
            if ( rect ) {
                rectStr = `Dim: ${rect.width}px x ${rect.height}px,
    Pos: left=${rect.left}px, top=${rect.top}px`;
            }
        } catch (e) {
        }
        
        let offsetStr = 'No Offset';
        const offset = $(element).offset();
        if ( offset ) {
            offsetStr = `Offset: ( ${offset.left}px,  ${offset.top}px )`;
        }
        
        let svgStr = 'Not an SVG';
        if ( elementTag == 'svg' ) {
            let viewBox = $(element).attr( 'viewBox' );
            if ( viewBox != null ) {
                svgStr = `Viewbox: ${viewBox}`;
            } else {
                svgStr = 'No viewbox attribute';
            }
        }
        
        console.log( `${label}: 
    Name: ${elementTag}, 
    Id: ${elementId},
    Classes: ${elementClasses},
    ${svgStr},
    ${offsetStr},
    ${rectStr}`) ;
        
    }
    
})();    
