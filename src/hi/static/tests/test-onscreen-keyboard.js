/**
 * Unit Tests for onscreen-keyboard.js
 *
 * Drives the real keyboard through key taps on a keyboardless device:
 * - which fields it serves, and keeping focus in the field
 * - editing with and without selection support, maxlength
 * - Enter: cancelable keydown, change, newline, implicit form submission
 * - change on leave, layouts by field type, layout keys
 * - publishing its height for layouts while shown, and deferring the
 *   hide until a tap's click is handled
 * - a field removed from the page while served
 */

(function() {
    'use strict';

    // Must exceed DEFERRED_HIDE_FALLBACK_MS in onscreen-keyboard.js.
    const AFTER_HIDE_FALLBACK_MS = 400;

    QUnit.module('Hi onscreen keyboard', function(hooks) {
        let originalCapabilities;

        hooks.beforeEach(function() {
            originalCapabilities = Hi.deviceCapabilities;
            Hi.deviceCapabilities = { keyboard: false };
        });

        // End every test hidden, with no hide pending, since the module's
        // state and its root-element class outlive the fixture.
        hooks.afterEach(async function() {
            if ( document.activeElement ) {
                document.activeElement.blur();
            }
            await settled();
            Hi.deviceCapabilities = originalCapabilities;
        });

        function addField( html, parent = null ) {
            const holder = document.createElement( 'div' );
            holder.innerHTML = html;
            const field = holder.firstElementChild;
            field.setAttribute( Hi.DEVICE_REQUIRES_ATTR, 'keyboard' );
            field.setAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR, 'on-screen-keyboard' );
            ( parent || document.getElementById( 'qunit-fixture' )).appendChild( field );
            return field;
        }

        function addForm() {
            const form = document.createElement( 'form' );
            document.getElementById( 'qunit-fixture' ).appendChild( form );
            return form;
        }

        function addButton( html = '<button type="button"></button>', parent = null ) {
            const holder = document.createElement( 'div' );
            holder.innerHTML = html;
            const button = holder.firstElementChild;
            ( parent || document.getElementById( 'qunit-fixture' )).appendChild( button );
            return button;
        }

        function isShown() {
            const container = document.getElementById( 'hi-onscreen-keyboard' );
            return Boolean( container ) && ! container.hidden;
        }

        function findKey( button ) {
            return document.querySelector(
                '#hi-onscreen-keyboard .hg-button[data-skbtn=' + CSS.escape( button ) + ']'
            );
        }

        // The event sequence of a tap: pointerdown, pointerup, click.
        // Focus moves during the press for a mouse, but after pointerup
        // (on the compatibility mousedown) for touch. Pointer events are
        // sent only here, always paired, since the module tracks whether
        // a pointer is down.
        function tap( element, { focusDuringPress = null, focusAfterRelease = null } = {} ) {
            element.dispatchEvent( new PointerEvent( 'pointerdown', { bubbles: true, cancelable: true } ));
            if ( focusDuringPress ) {
                focusDuringPress.focus();
            }
            element.dispatchEvent( new PointerEvent( 'pointerup', { bubbles: true } ));
            if ( focusAfterRelease ) {
                focusAfterRelease.focus();
            }
            element.dispatchEvent( new MouseEvent( 'click', { bubbles: true, cancelable: true } ));
        }

        function press( button ) {
            tap( findKey( button ));
        }

        function delay( ms ) {
            return new Promise( function( resolve ) { setTimeout( resolve, ms ); } );
        }

        // Completes any hide still waiting for a click.
        function settled() {
            document.body.dispatchEvent( new MouseEvent( 'click', { bubbles: true } ));
            return delay( 0 );
        }

        function countEvents( target, eventType ) {
            const counter = { count: 0 };
            target.addEventListener( eventType, function() { counter.count += 1; } );
            return counter;
        }

        QUnit.test('serves only declared, editable text fields on a keyboardless device', async function(assert) {
            async function shownOnFocus( field ) {
                await settled();
                field.focus();
                const shown = isShown();
                field.blur();
                return shown;
            }
            assert.ok( await shownOnFocus( addField( '<input type="text">' )), 'text input' );
            assert.ok( await shownOnFocus( addField( '<textarea></textarea>' )), 'textarea' );
            assert.notOk( await shownOnFocus( addField( '<input type="text" readonly>' )), 'readonly' );
            assert.notOk( await shownOnFocus( addField( '<input type="number">' )), 'number input' );

            const undeclared = addField( '<input type="text">' );
            undeclared.removeAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR );
            assert.notOk( await shownOnFocus( undeclared ), 'handler not declared' );

            Hi.deviceCapabilities = { keyboard: true };
            assert.notOk( await shownOnFocus( addField( '<input type="text">' )), 'device has a keyboard' );
        });

        QUnit.test('pressing keys cannot take focus from the field', function(assert) {
            addField( '<input type="text">' ).focus();
            const key = findKey( 'a' );
            const pointerNotCanceled = key.dispatchEvent(
                new PointerEvent( 'pointerdown', { bubbles: true, cancelable: true } )
            );
            key.dispatchEvent( new PointerEvent( 'pointerup', { bubbles: true } ));
            const mouseNotCanceled = key.dispatchEvent(
                new MouseEvent( 'mousedown', { bubbles: true, cancelable: true } )
            );
            assert.notOk( pointerNotCanceled, 'pointerdown default prevented' );
            assert.notOk( mouseNotCanceled, 'mousedown default prevented' );
        });

        QUnit.test('typing inserts at the caret and fires input', function(assert) {
            const field = addField( '<input type="text" value="ac">' );
            const inputs = countEvents( field, 'input' );
            field.focus();
            field.setSelectionRange( 1, 1 );
            press( 'b' );
            assert.equal( field.value, 'abc' );
            assert.equal( field.selectionStart, 2, 'caret after inserted text' );
            assert.equal( inputs.count, 1 );
        });

        QUnit.test('backspace deletes the selection, else the previous character', function(assert) {
            const field = addField( '<input type="text" value="abcd">' );
            const inputs = countEvents( field, 'input' );
            field.focus();
            field.setSelectionRange( 1, 3 );
            press( '{bksp}' );
            assert.equal( field.value, 'ad' );
            press( '{bksp}' );
            assert.equal( field.value, 'd' );
            press( '{bksp}' );
            assert.equal( field.value, 'd', 'nothing before the caret' );
            assert.equal( inputs.count, 2, 'no input event when nothing changed' );
        });

        QUnit.test('fields without selection support edit at the end', function(assert) {
            const field = addField( '<input type="email" value="a@b">' );
            field.focus();
            press( '.com' );
            assert.equal( field.value, 'a@b.com' );
            press( '{bksp}' );
            assert.equal( field.value, 'a@b.co' );
        });

        QUnit.test('maxlength is enforced', function(assert) {
            const email = addField( '<input type="email" value="a@b" maxlength="4">' );
            email.focus();
            press( '.com' );
            assert.equal( email.value, 'a@b.', 'without selection support' );

            const text = addField( '<input type="text" value="ab" maxlength="2">' );
            text.focus();
            text.setSelectionRange( 2, 2 );
            press( 'c' );
            assert.equal( text.value, 'ab', 'with selection support, at the limit' );
            text.setSelectionRange( 0, 1 );
            press( 'c' );
            assert.equal( text.value, 'cb', 'replacing a selection frees its length' );
        });

        QUnit.test('fields get layouts for their type', function(assert) {
            addField( '<input type="email">' ).focus();
            assert.ok( findKey( '@' ), 'email layout has @' );
            assert.notOk( findKey( '{space}' ), 'email layout has no space' );

            addField( '<input type="text">' ).focus();
            assert.ok( findKey( '{space}' ), 'text layout has space' );
        });

        QUnit.test('layout keys switch layouts and shift applies to one character', function(assert) {
            const field = addField( '<input type="text">' );
            field.focus();
            press( '{shift}' );
            press( 'Q' );
            press( 'q' );
            press( '{shift}' );
            press( '{shift}' );
            press( 'a' );
            press( '{symbols}' );
            press( '!' );
            press( '{abc}' );
            press( 'b' );
            press( '{space}' );
            assert.equal( field.value, 'Qqa!b ' );
        });

        QUnit.test('Enter fires change, then clicks the default button unless keydown is canceled', function(assert) {
            const form = addForm();
            const field = addField( '<input type="text">', form );
            const button = addButton( '<button></button>', form );
            const events = [];
            field.addEventListener( 'change', function() { events.push( 'change' ); } );
            button.addEventListener( 'click', function( event ) {
                events.push( 'click' );
                event.preventDefault();
            });

            field.focus();
            press( 'a' );
            press( '{enter}' );
            assert.deepEqual( events, [ 'change', 'click' ], 'change before submission' );

            field.addEventListener( 'keydown', function( event ) {
                if ( event.key === 'Enter' ) {
                    event.preventDefault();
                }
            });
            press( '{enter}' );
            assert.deepEqual( events, [ 'change', 'click' ], 'canceled keydown stops submission' );
        });

        QUnit.test('Enter honors the default button kind and state', function(assert) {
            let submits = 0;
            function countSubmits( form ) {
                form.addEventListener( 'submit', function( event ) {
                    submits += 1;
                    event.preventDefault();
                });
            }

            const inputSubmitForm = addForm();
            countSubmits( inputSubmitForm );
            const first = addField( '<input type="text">', inputSubmitForm );
            addField( '<input type="text">', inputSubmitForm );
            addButton( '<input type="submit">', inputSubmitForm );
            first.focus();
            press( '{enter}' );
            assert.equal( submits, 1, 'input[type=submit] is a default button' );

            const disabledForm = addForm();
            countSubmits( disabledForm );
            const lone = addField( '<input type="text">', disabledForm );
            addButton( '<button disabled></button>', disabledForm );
            lone.focus();
            press( '{enter}' );
            assert.equal( submits, 1, 'disabled default button blocks submission' );
        });

        QUnit.test('Enter without a submit button submits only a lone field', function(assert) {
            let submits = 0;
            function countSubmits( form ) {
                form.addEventListener( 'submit', function( event ) {
                    submits += 1;
                    event.preventDefault();
                });
            }
            const loneForm = addForm();
            countSubmits( loneForm );
            const lone = addField( '<input type="email">', loneForm );
            lone.focus();
            press( '{enter}' );
            assert.equal( submits, 1, 'lone field submits' );

            const pairForm = addForm();
            countSubmits( pairForm );
            const first = addField( '<input type="text">', pairForm );
            addField( '<input type="text">', pairForm );
            first.focus();
            press( '{enter}' );
            assert.equal( submits, 1, 'two fields do not submit' );
        });

        QUnit.test('Enter in a textarea inserts a newline', function(assert) {
            const field = addField( '<textarea>ab</textarea>' );
            field.focus();
            field.setSelectionRange( 2, 2 );
            press( '{enter}' );
            assert.equal( field.value, 'ab\n' );
        });

        QUnit.test('leaving fires change only when the value changed', function(assert) {
            const unchanged = addField( '<input type="text" value="x">' );
            const unchangedEvents = countEvents( unchanged, 'change' );
            unchanged.focus();
            unchanged.blur();
            assert.equal( unchangedEvents.count, 0 );

            const changed = addField( '<input type="text">' );
            const changedEvents = countEvents( changed, 'change' );
            changed.focus();
            press( 'a' );
            changed.blur();
            assert.equal( changedEvents.count, 1 );
        });

        QUnit.test('publishes its height for layouts while shown, until a delay after leaving', async function(assert) {
            const root = document.documentElement;
            const field = addField( '<input type="text">' );
            field.focus();
            assert.ok( root.classList.contains( 'hi-onscreen-keyboard-shown' ));
            assert.equal( root.style.getPropertyValue( '--hi-onscreen-keyboard-inset' ),
                          document.getElementById( 'hi-onscreen-keyboard' ).offsetHeight + 'px' );

            field.blur();
            assert.ok( isShown(), 'still shown right after leaving' );
            await delay( AFTER_HIDE_FALLBACK_MS );
            assert.notOk( isShown() );
            assert.notOk( root.classList.contains( 'hi-onscreen-keyboard-shown' ));
            assert.equal( root.style.getPropertyValue( '--hi-onscreen-keyboard-inset' ), '' );
        });

        QUnit.test('the hide key releases the field', async function(assert) {
            const field = addField( '<input type="text">' );
            field.focus();
            press( '{hide}' );
            assert.notEqual( document.activeElement, field );
            await delay( 0 );
            assert.notOk( isShown() );
        });

        QUnit.test('a tap that takes focus keeps the layout until its click is handled', async function(assert) {
            const button = addButton();
            let shownAtClick = null;
            button.addEventListener( 'click', function() { shownAtClick = isShown(); } );

            for ( const [ label, focusTiming ] of [[ 'mouse', 'focusDuringPress' ],
                                                   [ 'touch', 'focusAfterRelease' ]] ) {
                const field = addField( '<input type="text">' );
                const changes = countEvents( field, 'change' );
                shownAtClick = null;
                field.focus();
                press( 'a' );
                tap( button, { [focusTiming]: button } );
                assert.equal( changes.count, 1, label + ': field released at once' );
                assert.ok( shownAtClick, label + ': keyboard shown when the click is handled' );
                await delay( 0 );
                assert.notOk( isShown(), label + ': hidden after the click' );
            }
        });

        QUnit.test('a press held past the fallback delay still keeps the layout', async function(assert) {
            const button = addButton();
            addField( '<input type="text">' ).focus();

            button.dispatchEvent( new PointerEvent( 'pointerdown', { bubbles: true, cancelable: true } ));
            button.focus();
            await delay( AFTER_HIDE_FALLBACK_MS );
            assert.ok( isShown(), 'shown while the press is held' );

            button.dispatchEvent( new PointerEvent( 'pointerup', { bubbles: true } ));
            button.dispatchEvent( new MouseEvent( 'click', { bubbles: true, cancelable: true } ));
            await delay( 0 );
            assert.notOk( isShown(), 'hidden after the click' );
        });

        // Whether removal fires focusout differs by browser; either way the
        // field must take no further edits and the keyboard must go away.
        QUnit.test('a field removed while served is released', async function(assert) {
            const field = addField( '<input type="text">' );
            field.focus();
            press( 'a' );
            field.remove();

            press( 'b' );
            addButton().focus();
            assert.equal( field.value, 'a', 'no edits after removal' );
            await settled();
            assert.notOk( isShown() );
        });
    });

})();
