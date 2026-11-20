/**
 * Unit Tests for onscreen-keyboard.js
 *
 * Drives the real keyboard through key taps on a keyboardless device:
 * - which fields it serves
 * - editing with and without selection support, maxlength
 * - Enter: cancelable keydown, newline, implicit form submission
 * - change on leave, layouts by field type, one-shot shift
 */

(function() {
    'use strict';

    QUnit.module('Hi onscreen keyboard', function(hooks) {
        let originalCapabilities;

        hooks.beforeEach(function() {
            originalCapabilities = Hi.deviceCapabilities;
            Hi.deviceCapabilities = { keyboard: false };
        });

        hooks.afterEach(function() {
            if ( document.activeElement ) {
                document.activeElement.blur();
            }
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

        function isShown() {
            const container = document.getElementById( 'hi-onscreen-keyboard' );
            return Boolean( container ) && ! container.hidden;
        }

        function findKey( button ) {
            return document.querySelector(
                '#hi-onscreen-keyboard .hg-button[data-skbtn=' + CSS.escape( button ) + ']'
            );
        }

        function press( button ) {
            findKey( button ).dispatchEvent(
                new PointerEvent( 'pointerdown', { bubbles: true, cancelable: true } )
            );
            document.dispatchEvent( new PointerEvent( 'pointerup', { bubbles: true } ));
        }

        function countEvents( field, eventType ) {
            const counter = { count: 0 };
            field.addEventListener( eventType, function() { counter.count += 1; } );
            return counter;
        }

        QUnit.test('serves only declared, editable text fields on a keyboardless device', function(assert) {
            function shownOnFocus( field ) {
                field.focus();
                const shown = isShown();
                field.blur();
                return shown;
            }
            assert.ok( shownOnFocus( addField( '<input type="text">' )), 'text input' );
            assert.ok( shownOnFocus( addField( '<textarea></textarea>' )), 'textarea' );
            assert.notOk( shownOnFocus( addField( '<input type="text" readonly>' )), 'readonly' );
            assert.notOk( shownOnFocus( addField( '<input type="number">' )), 'number input' );

            const undeclared = addField( '<input type="text">' );
            undeclared.removeAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR );
            assert.notOk( shownOnFocus( undeclared ), 'handler not declared' );

            Hi.deviceCapabilities = { keyboard: true };
            assert.notOk( shownOnFocus( addField( '<input type="text">' )), 'device has a keyboard' );
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
            press( 'c' );
            assert.equal( text.value, 'ab', 'with selection support' );
        });

        QUnit.test('fields get layouts for their type', function(assert) {
            addField( '<input type="email">' ).focus();
            assert.ok( findKey( '@' ), 'email layout has @' );
            assert.notOk( findKey( '{space}' ), 'email layout has no space' );

            addField( '<input type="text">' ).focus();
            assert.ok( findKey( '{space}' ), 'text layout has space' );
        });

        QUnit.test('shift applies to one character', function(assert) {
            const field = addField( '<input type="text">' );
            field.focus();
            press( '{shift}' );
            press( 'Q' );
            press( 'q' );
            assert.equal( field.value, 'Qq' );
        });

        QUnit.test('Enter clicks the default button unless keydown is canceled', function(assert) {
            const form = addForm();
            const field = addField( '<input type="text">', form );
            const button = document.createElement( 'button' );
            form.appendChild( button );
            let clicks = 0;
            button.addEventListener( 'click', function( event ) {
                clicks += 1;
                event.preventDefault();
            });

            field.focus();
            press( '{enter}' );
            assert.equal( clicks, 1, 'default button clicked' );

            field.addEventListener( 'keydown', function( event ) {
                if ( event.key === 'Enter' ) {
                    event.preventDefault();
                }
            });
            press( '{enter}' );
            assert.equal( clicks, 1, 'canceled keydown stops submission' );
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
            assert.notOk( isShown(), 'keyboard hidden on leave' );
        });

        QUnit.test('the hide key releases the field', function(assert) {
            const field = addField( '<input type="text">' );
            field.focus();
            press( '{hide}' );
            assert.notOk( isShown() );
            assert.notEqual( document.activeElement, field );
        });
    });

})();
