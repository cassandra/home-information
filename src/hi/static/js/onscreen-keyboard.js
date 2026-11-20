(function() {

    window.Hi = window.Hi || {};

    /*
      ON-SCREEN KEYBOARD

      - The requirement handler for a missing "keyboard" capability (see
        device.js). It serves a text field only when device.js says the
        handler is active for it: the field declares the requirement and
        this handler, and the device has no keyboard.
      - simple-keyboard only renders keys. This module owns all editing,
        so the field's value is the single source of truth.
      - Edits fire "input"; leaving a field whose value changed fires
        "change", since programmatic edits never trigger it natively.
      - Enter first dispatches a cancelable keydown, as existing handlers
        may suppress it. Otherwise: newline in a textarea, or the
        browser's implicit form submission.
      - Taps on the keyboard must not take focus from the field, so
        pointerdown/mousedown defaults are prevented on its container.
      - input[type=number] is not served: its value sanitizes partial
        entries such as "-" or "1." to empty, so it cannot be built up
        key by key through .value.
    */

    // External names, as in DeviceCapabilitiesCodec.
    const CAPABILITY_NAME = 'keyboard';
    const HANDLER_NAME = 'on-screen-keyboard';

    const CONTAINER_ID = 'hi-onscreen-keyboard';
    const KEYS_CLASS = 'hi-onscreen-keyboard-keys';

    const SERVED_INPUT_TYPES = new Set([ 'text', 'email', 'password', 'search', 'url', 'tel' ]);

    // Input types that block implicit submission when no submit button exists (HTML spec).
    const IMPLICIT_SUBMISSION_BLOCKING_TYPES = new Set([
        'text', 'search', 'url', 'tel', 'email', 'password', 'date', 'month',
        'week', 'time', 'datetime-local', 'number'
    ]);

    const BUTTON = {
        BACKSPACE : '{bksp}',
        ENTER     : '{enter}',
        SHIFT     : '{shift}',
        SPACE     : '{space}',
        SYMBOLS   : '{symbols}',
        LETTERS   : '{abc}',
        HIDE      : '{hide}'
    };

    const BUTTON_DISPLAY = {
        '{bksp}'    : '&#9003;',
        '{enter}'   : 'Enter',
        '{shift}'   : '&#8679;',
        '{space}'   : '&nbsp;',
        '{symbols}' : '?123',
        '{abc}'     : 'ABC',
        '{hide}'    : 'Hide'
    };

    const LAYOUT_NAME = {
        DEFAULT : 'default',
        SHIFT   : 'shift',
        SYMBOLS : 'symbols'
    };

    const SYMBOL_ROWS = [
        '1 2 3 4 5 6 7 8 9 0 {bksp}',
        '! @ # $ % ^ & * ( ) _',
        '- + = / \\ | : ; {enter}',
        '\' " , . ? < > [ ] { }'
    ];

    const LAYOUTS = {
        text: {
            [LAYOUT_NAME.DEFAULT]: [
                '1 2 3 4 5 6 7 8 9 0 {bksp}',
                'q w e r t y u i o p',
                'a s d f g h j k l {enter}',
                '{shift} z x c v b n m , . {shift}',
                '{symbols} {space} {hide}'
            ],
            [LAYOUT_NAME.SHIFT]: [
                '1 2 3 4 5 6 7 8 9 0 {bksp}',
                'Q W E R T Y U I O P',
                'A S D F G H J K L {enter}',
                '{shift} Z X C V B N M , . {shift}',
                '{symbols} {space} {hide}'
            ],
            [LAYOUT_NAME.SYMBOLS]: SYMBOL_ROWS.concat([ '{abc} {space} {hide}' ])
        },
        email: {
            [LAYOUT_NAME.DEFAULT]: [
                '1 2 3 4 5 6 7 8 9 0 {bksp}',
                'q w e r t y u i o p',
                'a s d f g h j k l {enter}',
                '{shift} z x c v b n m - _ {shift}',
                '{symbols} @ . .com {hide}'
            ],
            [LAYOUT_NAME.SHIFT]: [
                '1 2 3 4 5 6 7 8 9 0 {bksp}',
                'Q W E R T Y U I O P',
                'A S D F G H J K L {enter}',
                '{shift} Z X C V B N M - _ {shift}',
                '{symbols} @ . .com {hide}'
            ],
            [LAYOUT_NAME.SYMBOLS]: SYMBOL_ROWS.concat([ '{abc} @ . .com {hide}' ])
        }
    };

    let _keyboard = null;        // simple-keyboard instance, created on first use
    let _containerElement = null;
    let _field = null;           // the field being served
    let _valueAtEngage = null;
    let _layoutName = LAYOUT_NAME.DEFAULT;

    function _isServed( element ) {
        if ( element instanceof HTMLInputElement ) {
            if ( ! SERVED_INPUT_TYPES.has( element.type )) {
                return false;
            }
        } else if ( ! ( element instanceof HTMLTextAreaElement )) {
            return false;
        }
        return ! element.disabled
            && ! element.readOnly
            && Hi.device.isHandlerActiveFor( HANDLER_NAME, element );
    }

    function _layoutsFor( field ) {
        return ( field.type === 'email' ) ? LAYOUTS.email : LAYOUTS.text;
    }

    /* Engagement */

    function _engage( field ) {
        if ( _field === field ) {
            return;
        }
        _disengage();
        _field = field;
        _valueAtEngage = field.value;
        _showKeyboard( _layoutsFor( field ));
    }

    function _disengage() {
        if ( ! _field ) {
            return;
        }
        const field = _field;
        _field = null;
        _hideKeyboard();
        if ( field.isConnected && ( field.value !== _valueAtEngage )) {
            field.dispatchEvent( new Event( 'change', { bubbles: true } ));
        }
    }

    /* Keyboard display */

    function _ensureKeyboard() {
        if ( _keyboard ) {
            return;
        }
        _containerElement = document.createElement( 'div' );
        _containerElement.id = CONTAINER_ID;
        _containerElement.hidden = true;
        const keysElement = document.createElement( 'div' );
        keysElement.className = KEYS_CLASS;
        _containerElement.appendChild( keysElement );

        _containerElement.addEventListener( 'pointerdown', _preventFocusChange );
        _containerElement.addEventListener( 'mousedown', _preventFocusChange );
        document.body.appendChild( _containerElement );

        _keyboard = new SimpleKeyboard.default( keysElement, {
            display: BUTTON_DISPLAY,
            preventMouseDownDefault: true,
            disableCaretPositioning: true,
            onKeyPress: _handleButton
        });
    }

    function _preventFocusChange( event ) {
        event.preventDefault();
    }

    function _showKeyboard( layouts ) {
        _ensureKeyboard();
        _layoutName = LAYOUT_NAME.DEFAULT;
        _keyboard.setOptions({ layout: layouts, layoutName: _layoutName });
        _containerElement.hidden = false;
    }

    function _hideKeyboard() {
        if ( _containerElement ) {
            _containerElement.hidden = true;
        }
    }

    function _setLayoutName( layoutName ) {
        _layoutName = layoutName;
        _keyboard.setOptions({ layoutName: layoutName });
    }

    function _handleButton( button ) {
        const field = _field;
        if ( ! field ) {
            return;
        }
        if ( ! field.isConnected ) {
            _disengage();
            return;
        }
        switch ( button ) {
        case BUTTON.BACKSPACE:
            _deleteBackward( field );
            break;
        case BUTTON.ENTER:
            _pressEnter( field );
            break;
        case BUTTON.SHIFT:
            _setLayoutName( _layoutName === LAYOUT_NAME.SHIFT ? LAYOUT_NAME.DEFAULT : LAYOUT_NAME.SHIFT );
            break;
        case BUTTON.SYMBOLS:
            _setLayoutName( LAYOUT_NAME.SYMBOLS );
            break;
        case BUTTON.LETTERS:
            _setLayoutName( LAYOUT_NAME.DEFAULT );
            break;
        case BUTTON.HIDE:
            field.blur();
            break;
        case BUTTON.SPACE:
            _typeText( field, ' ' );
            break;
        default:
            _typeText( field, button );
            break;
        }
    }

    // Shift applies to one character, as on touch keyboards.
    function _typeText( field, text ) {
        _insertText( field, text );
        if ( _layoutName === LAYOUT_NAME.SHIFT ) {
            _setLayoutName( LAYOUT_NAME.DEFAULT );
        }
    }

    /* Field editing */

    // Inputs such as email expose no selection: selectionStart is null.
    function _supportsSelection( field ) {
        return typeof field.selectionStart === 'number';
    }

    function _insertText( field, text ) {
        if ( _supportsSelection( field )) {
            const start = field.selectionStart;
            const end = field.selectionEnd;
            const fitted = _fitToMaxLength( field, text, field.value.length - ( end - start ));
            field.setRangeText( fitted, start, end, 'end' );
        } else {
            field.value += _fitToMaxLength( field, text, field.value.length );
        }
        _notifyInput( field );
    }

    // Programmatic edits bypass maxlength, which typing would enforce.
    function _fitToMaxLength( field, text, keptLength ) {
        if ( field.maxLength < 0 ) {
            return text;
        }
        return text.slice( 0, Math.max( 0, field.maxLength - keptLength ));
    }

    function _deleteBackward( field ) {
        if ( _supportsSelection( field )) {
            const start = field.selectionStart;
            const end = field.selectionEnd;
            if ( start !== end ) {
                field.setRangeText( '', start, end, 'end' );
            } else if ( start > 0 ) {
                field.setRangeText( '', start - 1, start, 'end' );
            } else {
                return;
            }
        } else if ( field.value.length > 0 ) {
            field.value = field.value.slice( 0, -1 );
        } else {
            return;
        }
        _notifyInput( field );
    }

    function _notifyInput( field ) {
        field.dispatchEvent( new Event( 'input', { bubbles: true } ));
    }

    function _pressEnter( field ) {
        const notCanceled = field.dispatchEvent( new KeyboardEvent( 'keydown', {
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true,
            cancelable: true
        }));
        if ( ! notCanceled ) {
            return;
        }
        if ( field instanceof HTMLTextAreaElement ) {
            _insertText( field, '\n' );
            return;
        }
        _submitImplicitly( field.form );
    }

    // Mirrors the browser: click the default button if there is one;
    // with none, submit only when a single field blocks implicit submission.
    function _submitImplicitly( form ) {
        if ( ! form ) {
            return;
        }
        const controls = Array.from( form.elements );
        const defaultButton = controls.find( _isSubmitButton );
        if ( defaultButton ) {
            if ( ! defaultButton.disabled ) {
                defaultButton.click();
            }
            return;
        }
        const blockingFields = controls.filter( function( control ) {
            return ( control instanceof HTMLInputElement )
                && IMPLICIT_SUBMISSION_BLOCKING_TYPES.has( control.type );
        });
        if ( blockingFields.length === 1 ) {
            form.requestSubmit();
        }
    }

    function _isSubmitButton( control ) {
        if ( control instanceof HTMLButtonElement ) {
            return control.type === 'submit';
        }
        return ( control instanceof HTMLInputElement )
            && (( control.type === 'submit' ) || ( control.type === 'image' ));
    }

    /* Wiring */

    Hi.device.registerHandler( HANDLER_NAME, CAPABILITY_NAME );

    document.addEventListener( 'focusin', function( event ) {
        if ( _isServed( event.target )) {
            _engage( event.target );
        }
    });

    document.addEventListener( 'focusout', function( event ) {
        if ( event.target === _field ) {
            _disengage();
        }
    });

    // A field may already have focus (e.g. autofocus) before this loads.
    if ( document.activeElement && _isServed( document.activeElement )) {
        _engage( document.activeElement );
    }

})();
