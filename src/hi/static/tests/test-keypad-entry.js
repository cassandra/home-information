/**
 * Unit Tests for keypad-entry.js
 *
 * Drives the keypad through taps and physical keys on markup shaped like
 * panes/keypad_entry.html:
 * - filling fields in order, backspace across fields, clear
 * - masked and unmasked slots
 * - physical keys: alphabet filtering, exact matching, modifiers, and
 *   editable elements keeping their keys
 * - auto-submit when the last field is full, and no input afterwards
 * - clearing a server-rendered error on the next edit
 * - a server-rendered disabled countdown refusing input, then re-enabling
 * - recovering from a failed submit the server never re-rendered
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
                            disabledSecs = 0 } = {}) {
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

                     data-alphabet="${alphabet}" data-length="${length}"
                     data-masked="${masked}" data-auto-submit="${autoSubmit}">
                  ${fieldsHtml}
                  ${messageHtml}
                  <div class="hi-keypad">
                    ${keysHtml}
                    <button type="button" data-keypad-action="clear">Clear</button>
                    <button type="button" data-keypad-action="backspace">Bksp</button>
                  </div>
                </div>`;
            document.getElementById( 'qunit-fixture' ).appendChild( form );
            return form;
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
    });

})();
