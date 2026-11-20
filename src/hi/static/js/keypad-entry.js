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
      - Character matching is exact unless data-case-sensitive="false";
        then case is ignored, but the alphabet's own character is entered.
      - Paste (under the same focus rules as physical keys) fills the
        active field, ignoring spaces and dashes; text that is not a valid
        code is rejected whole with the paste error message.
      - Pointer presses never focus a key, so a later Enter or Space cannot
        re-press the last tapped key. (Tab can still focus keys.)
      - Submission goes through jQuery so antinode's submit handler runs.
        If that request fails without the server re-rendering the entry
        (network loss, an HTML error page), the entry is still in the page
        and still submitting: it is reset with the server-rendered failure
        message so the keypad is never left dead. Likewise, an entry still
        submitting on a page restored from the back/forward cache is reset.
      - The server renders any error state; the next edit clears it.
      - The server can render the entry disabled for some seconds (e.g.
        too many wrong attempts). It refuses input while a countdown runs,
        then re-enables. Countdowns start when content is rendered: page
        load and antinode's post-render hooks. The server still enforces
        the limit; this only reflects it.
    */

    const ENTRY_SELECTOR = '[data-keypad-entry]';
    const FIELD_INPUT_SELECTOR = '[data-keypad-field] input';
    const FIELD_SELECTOR = '[data-keypad-field]';
    const FIELD_LABEL_SELECTOR = '.hi-keypad-field-label';
    const PROGRESS_SELECTOR = '[data-keypad-progress]';
    const OPEN_MODAL_SELECTOR = '.modal.show';
    const SLOT_SELECTOR = '.hi-keypad-slot';
    const MESSAGE_SELECTOR = '[data-keypad-message]';
    const KEY_ATTR = 'data-keypad-key';
    const ACTION_ATTR = 'data-keypad-action';
    const SUBMITTING_ATTR = 'data-keypad-submitting';
    const DISABLED_SECS_ATTR = 'data-disabled-secs';
    const COUNTDOWN_STARTED_ATTR = 'data-keypad-countdown-started';
    const COUNTDOWN_SELECTOR = '[data-keypad-countdown]';
    const FAILURE_MESSAGE_ATTR = 'data-failure-message';
    const PASTE_ERROR_MESSAGE_ATTR = 'data-paste-error-message';
    // As the server does: codes may be copied with spaces or dashes.
    const PASTE_SEPARATORS_REGEX = /[\s-]/g;

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
        ERROR    : 'is-error',
        WAIT     : 'is-wait',
        DISABLED : 'is-disabled',
        PRESSED  : 'is-pressed'
    };

    const SUBMIT_DELAY_MS = 250;
    const PRESSED_FLASH_MS = 120;
    const COUNTDOWN_TICK_MS = 250;

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
        return ! ( entry.hasAttribute( SUBMITTING_ATTR ) || entry.hasAttribute( DISABLED_SECS_ATTR ));
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
        _renderProgress( entry, activeIndex );
    }

    // Slots are hidden from screen readers; this announces how far along the active field is.
    function _renderProgress( entry, activeIndex ) {
        const progress = entry.querySelector( PROGRESS_SELECTOR );
        if ( ! progress ) {
            return;
        }
        const field = entry.querySelectorAll( FIELD_SELECTOR )[ activeIndex ];
        const label = field.querySelector( FIELD_LABEL_SELECTOR );
        const prefix = label ? `${label.textContent.trim()}: ` : '';
        const count = field.querySelector( 'input' ).value.length;
        progress.textContent = `${prefix}${count} of ${_length( entry )} entered`;
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
            $( form ).trigger( 'submit' );
        }, SUBMIT_DELAY_MS );
    }

    function _showError( entry, text ) {
        entry.classList.add( CSS_CLASS.ERROR );
        const message = entry.querySelector( MESSAGE_SELECTOR );
        if ( message ) {
            message.classList.add( CSS_CLASS.ERROR );
            message.textContent = text || '';
        }
    }

    function _resetSubmitting( entry ) {
        entry.removeAttribute( SUBMITTING_ATTR );
        _inputs( entry ).forEach( function( input ) {
            input.value = '';
        });
        _render( entry );
    }

    function _recoverFromFailedSubmit( entry ) {
        _resetSubmitting( entry );
        _showError( entry, entry.getAttribute( FAILURE_MESSAGE_ATTR ));
    }

    // A page restored from the back/forward cache keeps the DOM as it was
    // when the browser left it, including an entry mid-submit.
    function _onPageShow( event ) {
        if ( ! event.persisted ) {
            return;
        }
        document.querySelectorAll( `${ENTRY_SELECTOR}[${SUBMITTING_ATTR}]` ).forEach( _resetSubmitting );
    }

    // Antinode's own error callback runs first, so an entry the server
    // re-rendered is already detached and not matched here.
    function _onAjaxError( event, jqXHR, ajaxSettings ) {
        document.querySelectorAll( `${ENTRY_SELECTOR}[${SUBMITTING_ATTR}]` ).forEach( function( entry ) {
            const form = entry.closest( 'form' );
            if ( form && ( form.getAttribute( 'action' ) === ajaxSettings.url )) {
                _recoverFromFailedSubmit( entry );
            }
        });
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

    // The alphabet character a typed or pasted character enters, or null.
    // Case-insensitive entries still enter the alphabet's own character.
    function _resolveChar( entry, char ) {
        if ( char.length !== 1 ) {
            return null;
        }
        const alphabet = entry.dataset.alphabet;
        if ( alphabet.indexOf( char ) >= 0 ) {
            return char;
        }
        if ( entry.dataset.caseSensitive !== 'false' ) {
            return null;
        }
        const folded = char.toLowerCase();
        return Array.from( alphabet ).find( c => c.toLowerCase() === folded ) || null;
    }

    // Fills only the active field, replacing what it holds. All or nothing:
    // separators are ignored, any other character outside the alphabet
    // rejects the whole paste.
    function _paste( entry, text ) {
        if ( ! _isAcceptingInput( entry )) {
            return;
        }
        const chars = Array.from( text.replace( PASTE_SEPARATORS_REGEX, '' ));
        const resolved = chars.map( c => _resolveChar( entry, c ));
        if (( chars.length === 0 )
            || ( chars.length > _length( entry ))
            || resolved.includes( null )) {
            _showError( entry, entry.getAttribute( PASTE_ERROR_MESSAGE_ATTR ));
            return;
        }
        _inputs( entry )[ _activeIndex( entry ) ].value = '';
        resolved.forEach( c => _appendChar( entry, c ));
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

    // The entry physical keys and paste go to: the last one rendered and
    // visible, within the topmost open modal if there is one (never one in
    // the page behind it).
    function _keyboardEntry() {
        const openModals = document.querySelectorAll( OPEN_MODAL_SELECTOR );
        const scope = openModals.length ? openModals[openModals.length - 1] : document;
        const visible = Array.from( scope.querySelectorAll( ENTRY_SELECTOR ))
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

    function _enable( entry ) {
        entry.removeAttribute( DISABLED_SECS_ATTR );
        entry.classList.remove( CSS_CLASS.DISABLED );
        const message = entry.querySelector( MESSAGE_SELECTOR );
        if ( message && message.classList.contains( CSS_CLASS.WAIT )) {
            message.classList.remove( CSS_CLASS.WAIT );
            message.textContent = '';
        }
    }

    function _startCountdown( entry ) {
        entry.setAttribute( COUNTDOWN_STARTED_ATTR, 'true' );
        const disabledSecs = parseInt( entry.getAttribute( DISABLED_SECS_ATTR ), 10 );
        const deadlineMs = Date.now() + ( disabledSecs * 1000 );
        const countdown = entry.querySelector( COUNTDOWN_SELECTOR );

        const timer = setInterval( function() {
            if ( ! entry.isConnected ) {
                clearInterval( timer );
                return;
            }
            const remainingSecs = Math.ceil(( deadlineMs - Date.now() ) / 1000 );
            if ( remainingSecs > 0 ) {
                if ( countdown ) {
                    countdown.textContent = remainingSecs;
                }
                return;
            }
            clearInterval( timer );
            _enable( entry );
        }, COUNTDOWN_TICK_MS );
    }

    function startCountdowns() {
        const selector = `${ENTRY_SELECTOR}[${DISABLED_SECS_ATTR}]:not([${COUNTDOWN_STARTED_ATTR}])`;
        document.querySelectorAll( selector ).forEach( _startCountdown );
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
            // Explicit feedback: iOS Safari may not apply :active on tap.
            _flashKey( entry, key.getAttribute( KEY_ATTR ));
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
        } else {
            const char = _resolveChar( entry, event.key );
            if ( char ) {
                event.preventDefault();
                _flashKey( entry, char );
                _appendChar( entry, char );
            }
        }
    });

    document.addEventListener( 'paste', function( event ) {
        if ( event.defaultPrevented || _isEditable( document.activeElement )) {
            return;
        }
        const entry = _keyboardEntry();
        if ( ! entry || ! event.clipboardData ) {
            return;
        }
        event.preventDefault();
        _paste( entry, event.clipboardData.getData( 'text' ));
    });

    window.addEventListener( 'pageshow', _onPageShow );

    if ( document.readyState === 'loading' ) {
        document.addEventListener( 'DOMContentLoaded', startCountdowns );
    } else {
        startCountdowns();
    }
    $( document ).on( 'ajaxError', _onAjaxError );

    if ( window.AN && window.AN.addAfterAsyncRenderFunction ) {
        window.AN.addAfterAsyncRenderFunction( startCountdowns );
        window.AN.addAfterModalRenderFunction( startCountdowns );
    }

    Hi.keypadEntry = {
        startCountdowns: startCountdowns
    };

})();
