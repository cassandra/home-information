/**
 * Unit Tests for keypad-entry.js
 *
 * Drives the keypad through taps and physical keys on markup shaped like
 * panes/keypad_entry.html:
 * - filling fields in order, backspace across fields, clear
 * - masked and unmasked slots
 * - physical keys: alphabet filtering, exact or case-insensitive matching,
 *   modifiers, and editable elements keeping their keys
 * - paste: separators ignored, invalid text rejected whole, active field only
 * - auto-submit when the last field is full, and no input afterwards
 * - clearing a server-rendered error on the next edit
 * - a server-rendered disabled countdown refusing input, then re-enabling
 * - recovering from a failed submit the server never re-rendered
 * - resetting a submitting entry on a page restored from the back/forward cache
 * - announcing progress to screen readers
 * - keys and paste going only to an entry in an open modal
 */

(function() {
    'use strict';

    // Must exceed SUBMIT_DELAY_MS in keypad-entry.js.
    const AFTER_SUBMIT_DELAY_MS = 350;

    QUnit.module('Hi keypad entry', function() {

        function wait( ms ) {
            return new Promise( resolve => setTimeout( resolve, ms ));
        }

        // Polls rather than sleeping a fixed time: background tabs slow timers.
        async function waitFor( condition, timeoutMs = 3000 ) {
            const startMs = Date.now();
            while ( ! condition() && (( Date.now() - startMs ) < timeoutMs )) {
                await wait( 50 );
            }
            return condition();
        }

        function addEntry({ alphabet = '1234567890', length = 4, fieldNames = [ 'pin' ],
                            masked = true, autoSubmit = true, errorMessage = '',
                            disabledSecs = 0, caseSensitive = true,
                            container = document.getElementById( 'qunit-fixture' ) } = {}) {
            const form = document.createElement( 'form' );
            form.setAttribute( 'action', '/test/keypad' );
            form.submitCount = 0;
            // Stands in for antinode's jQuery submit handler.
            $( form ).on( 'submit', function( event ) {
                event.preventDefault();
                form.submitCount += 1;
            });

            const fieldsHtml = fieldNames.map( name => `
                <div class="hi-keypad-field" data-keypad-field>
                  <div class="hi-keypad-slots">
                    ${ '<div class="hi-keypad-slot"></div>'.repeat( length ) }
                  </div>
                  <input type="hidden" name="${name}" value="">
                </div>` ).join( '' );
            const keysHtml = alphabet.split( '' ).map(
                c => `<button type="button" data-keypad-key="${c}">${c}</button>` ).join( '' );

            const disabledAttr = disabledSecs ? `data-disabled-secs="${disabledSecs}"` : '';
            const messageHtml = disabledSecs
                  ? `<div class="hi-keypad-message is-wait" data-keypad-message>Wait
                       <span data-keypad-countdown>${disabledSecs}</span>s</div>`
                  : `<div class="hi-keypad-message ${ errorMessage ? 'is-error' : '' }"
                       data-keypad-message>${errorMessage}</div>`;
            form.innerHTML = `
                <div class="hi-keypad-entry ${ errorMessage ? 'is-error' : '' } ${ disabledSecs ? 'is-disabled' : '' }"
                     data-keypad-entry ${disabledAttr} data-failure-message="Failed"
                     data-paste-error-message="Bad paste" data-case-sensitive="${caseSensitive}"
                     data-alphabet="${alphabet}" data-length="${length}"
                     data-masked="${masked}" data-auto-submit="${autoSubmit}">
                  ${fieldsHtml}
                  <div data-keypad-progress></div>
                  ${messageHtml}
                  <div class="hi-keypad">
                    ${keysHtml}
                    <button type="button" data-keypad-action="clear">Clear</button>
                    <button type="button" data-keypad-action="backspace">Bksp</button>
                  </div>
                </div>`;
            container.appendChild( form );
            return form;
        }

        function addOpenModal() {
            const modal = document.createElement( 'div' );
            modal.className = 'modal show';
            document.getElementById( 'qunit-fixture' ).appendChild( modal );
            return modal;
        }

        function tap( form, key ) {
            form.querySelector( `[data-keypad-key="${key}"]` ).click();
        }

        function tapAction( form, action ) {
            form.querySelector( `[data-keypad-action="${action}"]` ).click();
        }

        function press( key, options = {} ) {
            const event = new KeyboardEvent( 'keydown', Object.assign(
                { key: key, bubbles: true, cancelable: true }, options ));
            document.dispatchEvent( event );
            return event;
        }

        function paste( text ) {
            const clipboardData = new DataTransfer();
            clipboardData.setData( 'text/plain', text );
            const event = new ClipboardEvent( 'paste', {
                clipboardData: clipboardData, bubbles: true, cancelable: true });
            document.dispatchEvent( event );
            return event;
        }

        function messageText( form ) {
            return form.querySelector( '[data-keypad-message]' ).textContent;
        }

        function values( form ) {
            return Array.from( form.querySelectorAll( 'input[type="hidden"]' )).map( i => i.value );
        }

        QUnit.test( 'taps fill the field in order', function( assert ) {
            const form = addEntry();
            tap( form, '4' );
            tap( form, '2' );
            assert.deepEqual( values( form ), [ '42' ] );
            const slots = form.querySelectorAll( '.hi-keypad-slot' );
            assert.ok( slots[0].classList.contains( 'is-filled' ));
            assert.ok( slots[1].classList.contains( 'is-filled' ));
            assert.ok( slots[2].classList.contains( 'is-next' ));
        });

        QUnit.test( 'masked slots hide characters; unmasked show them', function( assert ) {
            const masked = addEntry();
            tap( masked, '7' );
            assert.equal( masked.querySelector( '.hi-keypad-slot' ).textContent, '' );

            masked.remove();
            const unmasked = addEntry({ alphabet: 'abc', length: 3, masked: false });
            tap( unmasked, 'b' );
            assert.equal( unmasked.querySelector( '.hi-keypad-slot' ).textContent, 'b' );
        });

        QUnit.test( 'a full field advances to the next one', function( assert ) {
            const form = addEntry({ length: 2, fieldNames: [ 'pin', 'pin_confirm' ] });
            [ '1', '2', '3' ].forEach( k => tap( form, k ));
            assert.deepEqual( values( form ), [ '12', '3' ] );
            const fields = form.querySelectorAll( '[data-keypad-field]' );
            assert.notOk( fields[0].classList.contains( 'is-active' ));
            assert.ok( fields[1].classList.contains( 'is-active' ));
        });

        QUnit.test( 'backspace steps back across fields; clear empties all', function( assert ) {
            const form = addEntry({ length: 2, fieldNames: [ 'pin', 'pin_confirm' ] });
            [ '1', '2', '3' ].forEach( k => tap( form, k ));
            tapAction( form, 'backspace' );
            tapAction( form, 'backspace' );
            assert.deepEqual( values( form ), [ '1', '' ] );

            tap( form, '5' );
            tapAction( form, 'clear' );
            assert.deepEqual( values( form ), [ '', '' ] );
            assert.ok( form.querySelector( '[data-keypad-field]' ).classList.contains( 'is-active' ));
        });

        QUnit.test( 'physical keys: alphabet only, exact match', function( assert ) {
            const form = addEntry({ alphabet: 'abc', length: 3, masked: false, autoSubmit: false });
            const handled = press( 'a' );
            const ignored = press( 'z' );
            const wrongCase = press( 'B' );
            assert.deepEqual( values( form ), [ 'a' ] );
            assert.ok( handled.defaultPrevented, 'handled keys are consumed' );
            assert.notOk( ignored.defaultPrevented, 'other keys pass through' );
            assert.notOk( wrongCase.defaultPrevented, 'no case folding' );
        });

        QUnit.test( 'case-insensitive physical keys enter the alphabet character', function( assert ) {
            const form = addEntry({ alphabet: 'abc', length: 3, masked: false, autoSubmit: false,
                                    caseSensitive: false });
            const upper = press( 'B' );
            press( 'c' );
            const outside = press( 'Z' );
            assert.deepEqual( values( form ), [ 'bc' ] );
            assert.ok( upper.defaultPrevented );
            assert.notOk( outside.defaultPrevented );
        });

        QUnit.test( 'paste ignores separators and auto-submits a complete code', async function( assert ) {
            const form = addEntry({ alphabet: 'abcd', length: 4, masked: false, caseSensitive: false });
            const event = paste( ' AB-c d ' );
            assert.ok( event.defaultPrevented );
            assert.deepEqual( values( form ), [ 'abcd' ] );
            assert.ok( await waitFor( () => form.submitCount === 1 ));
        });

        QUnit.test( 'paste replaces a partial entry', function( assert ) {
            const form = addEntry({ autoSubmit: false });
            tap( form, '9' );
            paste( '12' );
            assert.deepEqual( values( form ), [ '12' ] );
        });

        QUnit.test( 'invalid or over-long paste is rejected whole', function( assert ) {
            const form = addEntry({ autoSubmit: false });
            tap( form, '7' );
            paste( '12a4' );
            assert.deepEqual( values( form ), [ '7' ], 'invalid character' );
            assert.equal( messageText( form ), 'Bad paste' );

            paste( '12345' );
            assert.deepEqual( values( form ), [ '7' ], 'too long' );

            paste( ' - ' );
            assert.deepEqual( values( form ), [ '7' ], 'only separators' );

            tap( form, '8' );
            assert.equal( messageText( form ), '', 'next edit clears the paste error' );
        });

        QUnit.test( 'paste fills only the active field', function( assert ) {
            const form = addEntry({ length: 2, fieldNames: [ 'pin', 'pin_confirm' ], autoSubmit: false });
            paste( '12' );
            assert.deepEqual( values( form ), [ '12', '' ] );
            paste( '34' );
            assert.deepEqual( values( form ), [ '12', '34' ] );
            paste( '123' );
            assert.deepEqual( values( form ), [ '12', '34' ], 'longer than one field is rejected' );
        });

        QUnit.test( 'paste is left alone while an editable element has focus', function( assert ) {
            const form = addEntry();
            const text = document.createElement( 'input' );
            text.type = 'text';
            document.getElementById( 'qunit-fixture' ).appendChild( text );
            text.focus();
            const event = paste( '12' );
            text.blur();
            assert.notOk( event.defaultPrevented );
            assert.deepEqual( values( form ), [ '' ] );
        });

        QUnit.test( 'physical Backspace and Delete edit', function( assert ) {
            const form = addEntry({ autoSubmit: false });
            [ '1', '2', '3' ].forEach( k => press( k ));
            press( 'Backspace' );
            assert.deepEqual( values( form ), [ '12' ] );
            press( 'Delete' );
            assert.deepEqual( values( form ), [ '' ] );
        });

        QUnit.test( 'modifier keys and editable focus are left alone', function( assert ) {
            const form = addEntry();
            const withCtrl = press( '1', { ctrlKey: true });
            assert.notOk( withCtrl.defaultPrevented );

            const text = document.createElement( 'input' );
            text.type = 'text';
            document.getElementById( 'qunit-fixture' ).appendChild( text );
            text.focus();
            const whileTyping = press( '2' );
            text.blur();

            assert.notOk( whileTyping.defaultPrevented );
            assert.deepEqual( values( form ), [ '' ] );
        });

        QUnit.test( 'auto-submits once the last field is full, then ignores input', async function( assert ) {
            const form = addEntry({ length: 2, fieldNames: [ 'pin', 'pin_confirm' ] });
            [ '1', '2', '1' ].forEach( k => tap( form, k ));
            await wait( AFTER_SUBMIT_DELAY_MS );
            assert.equal( form.submitCount, 0, 'not before the last field is full' );

            tap( form, '2' );
            tapAction( form, 'clear' );
            assert.ok( await waitFor( () => form.submitCount === 1 ));
            assert.deepEqual( values( form ), [ '12', '12' ], 'clear refused while submitting' );
        });

        QUnit.test( 'no submit without auto-submit', async function( assert ) {
            const form = addEntry({ autoSubmit: false });
            [ '1', '2', '3', '4' ].forEach( k => tap( form, k ));
            await wait( AFTER_SUBMIT_DELAY_MS );
            assert.equal( form.submitCount, 0 );
        });

        QUnit.test( 'next edit clears a server-rendered error', function( assert ) {
            const form = addEntry({ errorMessage: 'Incorrect PIN' });
            tap( form, '1' );
            const entry = form.querySelector( '[data-keypad-entry]' );
            const message = form.querySelector( '[data-keypad-message]' );
            assert.notOk( entry.classList.contains( 'is-error' ));
            assert.notOk( message.classList.contains( 'is-error' ));
            assert.equal( message.textContent, '' );
        });

        QUnit.test( 'disabled entry refuses input until its countdown ends', async function( assert ) {
            const form = addEntry({ disabledSecs: 1 });
            const entry = form.querySelector( '[data-keypad-entry]' );
            Hi.keypadEntry.startCountdowns();

            tap( form, '1' );
            press( '2' );
            assert.deepEqual( values( form ), [ '' ], 'taps and keys refused' );

            assert.ok( await waitFor( () => ! entry.hasAttribute( 'data-disabled-secs' )));
            assert.notOk( entry.classList.contains( 'is-disabled' ));
            assert.equal( form.querySelector( '[data-keypad-message]' ).textContent, '' );

            tap( form, '3' );
            assert.deepEqual( values( form ), [ '3' ], 'accepts input again' );
        });

        QUnit.test( 'a failed submit the server never re-rendered resets the keypad', async function( assert ) {
            const form = addEntry();
            [ '1', '2', '3', '4' ].forEach( k => tap( form, k ));
            assert.ok( await waitFor( () => form.submitCount === 1 ));

            $( document ).trigger( 'ajaxError', [ {}, { url: '/test/other' } ] );
            tap( form, '5' );
            assert.deepEqual( values( form ), [ '1234' ], 'other requests do not reset it' );

            $( document ).trigger( 'ajaxError', [ {}, { url: '/test/keypad' } ] );
            const message = form.querySelector( '[data-keypad-message]' );
            assert.equal( message.textContent, 'Failed' );
            assert.deepEqual( values( form ), [ '' ] );

            tap( form, '5' );
            assert.deepEqual( values( form ), [ '5' ], 'accepts input again' );
            assert.equal( message.textContent, '', 'next edit clears the failure message' );
        });

        QUnit.test( 'progress is announced as characters are entered', function( assert ) {
            const form = addEntry({ autoSubmit: false });
            const progress = form.querySelector( '[data-keypad-progress]' );
            tap( form, '1' );
            tap( form, '2' );
            assert.equal( progress.textContent, '2 of 4 entered' );
            tapAction( form, 'clear' );
            assert.equal( progress.textContent, '0 of 4 entered' );
        });

        QUnit.test( 'with a modal open, keys and paste skip an entry behind it', function( assert ) {
            const pageForm = addEntry({ autoSubmit: false });
            const modal = addOpenModal();
            const ignored = press( '1' );
            paste( '23' );
            assert.notOk( ignored.defaultPrevented );
            assert.deepEqual( values( pageForm ), [ '' ], 'page entry untouched' );

            const modalForm = addEntry({ autoSubmit: false, container: modal });
            press( '4' );
            paste( '56' );
            assert.deepEqual( values( modalForm ), [ '56' ], 'modal entry gets them' );
            assert.deepEqual( values( pageForm ), [ '' ] );
        });

        QUnit.test( 'a page restored from the back/forward cache resets a submitting entry', async function( assert ) {
            const form = addEntry();
            [ '1', '2', '3', '4' ].forEach( k => tap( form, k ));
            assert.ok( await waitFor( () => form.submitCount === 1 ));

            window.dispatchEvent( new PageTransitionEvent( 'pageshow', { persisted: false }));
            tap( form, '5' );
            assert.deepEqual( values( form ), [ '1234' ], 'a normal page load does not reset it' );

            window.dispatchEvent( new PageTransitionEvent( 'pageshow', { persisted: true }));
            assert.deepEqual( values( form ), [ '' ] );
            assert.equal( messageText( form ), '', 'no error shown' );
            tap( form, '5' );
            assert.deepEqual( values( form ), [ '5' ], 'accepts input again' );
        });
    });

})();
