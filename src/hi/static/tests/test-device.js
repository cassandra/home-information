/**
 * Unit Tests for device.js
 *
 * Tests capability gating of actions marked with Hi.DEVICE_REQUIRES_ATTR:
 * - which required capabilities count as missing
 * - the capture-phase click listener blocks only when one is missing
 */

(function() {
    'use strict';

    QUnit.module('Hi.device', function(hooks) {
        let originalCapabilities;
        let originalAnGet;
        let requestedUrls;

        hooks.beforeEach(function() {
            originalCapabilities = Hi.deviceCapabilities;
            originalAnGet = window.AN.get;
            requestedUrls = [];
            window.AN.get = function( url ) { requestedUrls.push( url ); };
            Hi.deviceCapabilities = {
                keyboard: true,
                browser_nav: false,
                local_files: false
            };
        });

        hooks.afterEach(function() {
            Hi.deviceCapabilities = originalCapabilities;
            if ( originalAnGet === undefined ) {
                delete window.AN.get;
            } else {
                window.AN.get = originalAnGet;
            }
        });

        function clickRequiring( requiresValue, eventType = 'click', mouseButton = 0 ) {
            const fixture = document.getElementById( 'qunit-fixture' );
            const button = document.createElement( 'button' );
            const inner = document.createElement( 'span' );
            button.setAttribute( Hi.DEVICE_REQUIRES_ATTR, requiresValue );
            button.appendChild( inner );
            fixture.appendChild( button );

            let actionRan = false;
            button.addEventListener( eventType, function() { actionRan = true; } );
            const notCanceled = inner.dispatchEvent(
                new MouseEvent( eventType, { bubbles: true, cancelable: true, button: mouseButton } )
            );
            return { actionRan: actionRan, defaultPrevented: ! notCanceled };
        }

        QUnit.test('getMissingCapabilities returns only unavailable names', function(assert) {
            assert.deepEqual( Hi.device.getMissingCapabilities( 'keyboard' ), [] );
            assert.deepEqual( Hi.device.getMissingCapabilities( ' keyboard  local_files browser_nav ' ),
                              [ 'local_files', 'browser_nav' ] );
            assert.deepEqual( Hi.device.getMissingCapabilities( '' ), [] );
        });

        QUnit.test('names not declared by the server are available', function(assert) {
            Hi.deviceCapabilities = {};
            assert.ok( Hi.device.isAvailable( 'local_files' ) );
            assert.deepEqual( Hi.device.getMissingCapabilities( 'local_files browser_nav' ), [] );
        });

        QUnit.test('click is blocked and modal requested when a capability is missing', function(assert) {
            const result = clickRequiring( 'keyboard local_files' );
            assert.notOk( result.actionRan, 'element click handler did not run' );
            assert.ok( result.defaultPrevented, 'default action prevented' );
            assert.equal( requestedUrls.length, 1, 'one modal request' );
            assert.equal( requestedUrls[0],
                          Hi.DEVICE_CAPABILITY_UNAVAILABLE_URL
                          + '?' + Hi.DEVICE_REQUIRES_FIELD + '=local_files' );
        });

        QUnit.test('middle-click is blocked but right-click is not', function(assert) {
            const middle = clickRequiring( 'local_files', 'auxclick', 1 );
            assert.notOk( middle.actionRan, 'middle-click blocked' );
            assert.equal( requestedUrls.length, 1, 'modal requested for middle-click' );

            const right = clickRequiring( 'local_files', 'auxclick', 2 );
            assert.ok( right.actionRan, 'right-click not blocked' );
            assert.equal( requestedUrls.length, 1, 'no modal for right-click' );
        });

        QUnit.test('click proceeds when all required capabilities are present', function(assert) {
            const result = clickRequiring( 'keyboard' );
            assert.ok( result.actionRan, 'element click handler ran' );
            assert.notOk( result.defaultPrevented, 'default action not prevented' );
            assert.equal( requestedUrls.length, 0, 'no modal request' );
        });
    });

})();
