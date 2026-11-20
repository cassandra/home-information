(function() {
    'use strict';

    window.Hi = window.Hi || {};

    /*
      KEYPAD ENTRY

      - Behavior for the panes/keypad_entry.html include: fixed-length
        codes over a fixed alphabet (e.g. lock PIN, magic code). Knows
        nothing about any particular alphabet; all of it comes from the
        data- attributes the server renders from a KeypadSpec.
      - Stateless: the hidden inputs hold the entered values, so content
        swapped in by antinode (modals re-rendered on error) needs no
        binding. All handlers are delegated from the document.
      - Fields fill in DOM order; the active field is the first one not
        full. With auto-submit, the enclosing form submits once the last
        field is full, after a short pause so the last slot is seen.
      - Physical keys: characters in the alphabet append, Backspace
        removes, Delete clears. They go to the visible entry, and are
        left alone while an editable element has focus or a modifier is
        held, so normal typing and browser shortcuts still work.
      - Character matching is exact; no case folding.
      - Keys never take focus, so a later Enter or Space cannot re-press
        the last tapped key.
      - The server renders any error state; the next edit clears it.
    */

    const ENTRY_SELECTOR = '[data-keypad-entry]';
    const FIELD_INPUT_SELECTOR = '[data-keypad-field] input';
    const FIELD_SELECTOR = '[data-keypad-field]';
    const SLOT_SELECTOR = '.hi-keypad-slot';
    const MESSAGE_SELECTOR = '[data-keypad-message]';
    const KEY_ATTR = 'data-keypad-key';
    const ACTION_ATTR = 'data-keypad-action';
    const SUBMITTING_ATTR = 'data-keypad-submitting';

    // External names, as in KeypadAction.
    const ACTION = {
        CLEAR     : 'clear',
        BACKSPACE : 'backspace'
    };

    const PHYSICAL_KEY = {
        BACKSPACE : 'Backspace',
        DELETE    : 'Delete'
    };

    const CSS_CLASS = {
        ACTIVE  : 'is-active',
        FILLED  : 'is-filled',
        NEXT    : 'is-next',
        ERROR   : 'is-error',
        PRESSED : 'is-pressed'
    };

    const SUBMIT_DELAY_MS = 250;
    const PRESSED_FLASH_MS = 120;

    function _length( entry ) {
        return parseInt( entry.dataset.length, 10 );
    }

    function _inputs( entry ) {
        return Array.from( entry.querySelectorAll( FIELD_INPUT_SELECTOR ));
    }

    function _activeIndex( entry ) {
        const inputs = _inputs( entry );
        const length = _length( entry );
        const index = inputs.findIndex( input => input.value.length < length );
        return ( index < 0 ) ? inputs.length - 1 : index;
    }

    function _isAcceptingInput( entry ) {
        return ! entry.hasAttribute( SUBMITTING_ATTR );
    }

    function _render( entry ) {
        const isMasked = ( entry.dataset.masked === 'true' );
        const activeIndex = _activeIndex( entry );
        entry.querySelectorAll( FIELD_SELECTOR ).forEach( function( field, fieldIndex ) {
            const isActive = ( fieldIndex === activeIndex );
            const value = field.querySelector( 'input' ).value;
            field.classList.toggle( CSS_CLASS.ACTIVE, isActive );
            field.querySelectorAll( SLOT_SELECTOR ).forEach( function( slot, slotIndex ) {
                const isFilled = ( slotIndex < value.length );
                slot.classList.toggle( CSS_CLASS.FILLED, isFilled );
                slot.classList.toggle( CSS_CLASS.NEXT, isActive && ( slotIndex === value.length ));
                slot.textContent = ( isFilled && ! isMasked ) ? value[slotIndex] : '';
            });
        });
    }

    function _clearError( entry ) {
        entry.classList.remove( CSS_CLASS.ERROR );
        const message = entry.querySelector( MESSAGE_SELECTOR );
        if ( message && message.classList.contains( CSS_CLASS.ERROR )) {
            message.classList.remove( CSS_CLASS.ERROR );
            message.textContent = '';
        }
    }

    function _submit( entry ) {
        const form = entry.closest( 'form' );
        if ( ! form ) {
            console.warn( 'Keypad entry is not inside a form; cannot submit.' );
            return;
        }
        entry.setAttribute( SUBMITTING_ATTR, 'true' );
        setTimeout( function() {
            form.requestSubmit();
        }, SUBMIT_DELAY_MS );
    }

    function _appendChar( entry, char ) {
        if ( ! _isAcceptingInput( entry )) {
            return;
        }
        const length = _length( entry );
        const inputs = _inputs( entry );
        const target = inputs.find( input => input.value.length < length );
        if ( ! target ) {
            return;
        }
        _clearError( entry );
        target.value += char;
        _render( entry );

        const isComplete = inputs.every( input => input.value.length === length );
        if ( isComplete && ( entry.dataset.autoSubmit === 'true' )) {
            _submit( entry );
        }
    }

    function _backspace( entry ) {
        if ( ! _isAcceptingInput( entry )) {
            return;
        }
        _clearError( entry );
        const target = _inputs( entry ).reverse().find( input => input.value.length > 0 );
        if ( target ) {
            target.value = target.value.slice( 0, -1 );
        }
        _render( entry );
    }

    function _clear( entry ) {
        if ( ! _isAcceptingInput( entry )) {
            return;
        }
        _clearError( entry );
        _inputs( entry ).forEach( function( input ) {
            input.value = '';
        });
        _render( entry );
    }

    function _isInAlphabet( entry, char ) {
        return ( char.length === 1 ) && ( entry.dataset.alphabet.indexOf( char ) >= 0 );
    }

    function _isEditable( element ) {
        if ( ! element ) {
            return false;
        }
        if ( element.isContentEditable ) {
            return true;
        }
        return [ 'INPUT', 'TEXTAREA', 'SELECT' ].includes( element.tagName );
    }

    // The entry physical keys go to: the last one rendered and visible.
    function _keyboardEntry() {
        const visible = Array.from( document.querySelectorAll( ENTRY_SELECTOR ))
              .filter( entry => entry.getClientRects().length > 0 );
        return visible.length ? visible[visible.length - 1] : null;
    }

    function _flashKey( entry, char ) {
        const key = Array.from( entry.querySelectorAll( `[${KEY_ATTR}]` ))
              .find( element => element.getAttribute( KEY_ATTR ) === char );
        if ( ! key ) {
            return;
        }
        key.classList.add( CSS_CLASS.PRESSED );
        setTimeout( function() {
            key.classList.remove( CSS_CLASS.PRESSED );
        }, PRESSED_FLASH_MS );
    }

    document.addEventListener( 'mousedown', function( event ) {
        if ( event.target.closest( `${ENTRY_SELECTOR} [${KEY_ATTR}], ${ENTRY_SELECTOR} [${ACTION_ATTR}]` )) {
            event.preventDefault();
        }
    });

    document.addEventListener( 'click', function( event ) {
        const key = event.target.closest( `[${KEY_ATTR}]` );
        const action = event.target.closest( `[${ACTION_ATTR}]` );
        const control = key || action;
        const entry = control ? control.closest( ENTRY_SELECTOR ) : null;
        if ( ! entry ) {
            return;
        }
        if ( key ) {
            _appendChar( entry, key.getAttribute( KEY_ATTR ));
        } else if ( action.getAttribute( ACTION_ATTR ) === ACTION.CLEAR ) {
            _clear( entry );
        } else if ( action.getAttribute( ACTION_ATTR ) === ACTION.BACKSPACE ) {
            _backspace( entry );
        }
    });

    document.addEventListener( 'keydown', function( event ) {
        if ( event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey ) {
            return;
        }
        if ( _isEditable( document.activeElement )) {
            return;
        }
        const entry = _keyboardEntry();
        if ( ! entry ) {
            return;
        }
        if ( event.key === PHYSICAL_KEY.BACKSPACE ) {
            event.preventDefault();
            _backspace( entry );
        } else if ( event.key === PHYSICAL_KEY.DELETE ) {
            event.preventDefault();
            _clear( entry );
        } else if ( _isInAlphabet( entry, event.key )) {
            event.preventDefault();
            _flashKey( entry, event.key );
            _appendChar( entry, event.key );
        }
    });

})();
