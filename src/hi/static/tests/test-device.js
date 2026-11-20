/**
 * Unit Tests for device.js
 *
 * Tests capability gating of actions marked with Hi.DEVICE_REQUIRES_ATTR:
 * - which required capabilities count as unmet, including handlers
 *   declared via Hi.DEVICE_REQUIRES_HANDLER_ATTR standing in for them
 * - the capture-phase click listener blocks only when one is unmet
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

        // Handler registrations persist for the page, so tests use their
        // own handler names rather than real ones.
        Hi.device.registerHandler( 'test-files-handler', 'local_files' );
        Hi.device.registerHandler( 'test-keyboard-handler', 'keyboard' );

        function clickRequiring( requiresValue, eventType = 'click', mouseButton = 0, handlersValue = null ) {
            const fixture = document.getElementById( 'qunit-fixture' );
            const button = document.createElement( 'button' );
            const inner = document.createElement( 'span' );
            button.setAttribute( Hi.DEVICE_REQUIRES_ATTR, requiresValue );
            if ( handlersValue !== null ) {
                button.setAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR, handlersValue );
            }
            button.appendChild( inner );
            fixture.appendChild( button );

            let actionRan = false;
            button.addEventListener( eventType, function() { actionRan = true; } );
            const notCanceled = inner.dispatchEvent(
                new MouseEvent( eventType, { bubbles: true, cancelable: true, button: mouseButton } )
            );
            return { actionRan: actionRan, defaultPrevented: ! notCanceled };
        }

        QUnit.test('getUnmetRequirements returns only unavailable names', function(assert) {
            assert.deepEqual( Hi.device.getUnmetRequirements( 'keyboard' ), [] );
            assert.deepEqual( Hi.device.getUnmetRequirements( ' keyboard  local_files browser_nav ' ),
                              [ 'local_files', 'browser_nav' ] );
            assert.deepEqual( Hi.device.getUnmetRequirements( '' ), [] );
        });

        QUnit.test('a declared, registered handler meets only the capability it stands in for', function(assert) {
            assert.deepEqual( Hi.device.getUnmetRequirements( 'local_files', 'test-files-handler' ), [] );
            assert.deepEqual( Hi.device.getUnmetRequirements( 'local_files browser_nav', 'test-files-handler' ),
                              [ 'browser_nav' ] );
        });

        QUnit.test('a handler meets nothing unless both declared and registered', function(assert) {
            assert.deepEqual( Hi.device.getUnmetRequirements( 'local_files', 'test-unregistered-handler' ),
                              [ 'local_files' ], 'declared but never registered' );
            assert.deepEqual( Hi.device.getUnmetRequirements( 'local_files', 'test-keyboard-handler' ),
                              [ 'local_files' ], 'registered for a different capability' );
            assert.deepEqual( Hi.device.getUnmetRequirements( 'local_files' ),
                              [ 'local_files' ], 'registered but not declared on the element' );
        });

        QUnit.test('names not declared by the server are available', function(assert) {
            Hi.deviceCapabilities = {};
            assert.ok( Hi.device.isAvailable( 'local_files' ) );
            assert.deepEqual( Hi.device.getUnmetRequirements( 'local_files browser_nav' ), [] );
        });

        QUnit.test('isHandlerActiveFor needs the declaration, the requirement and the missing capability', function(assert) {
            function element( requiresValue, handlersValue ) {
                const el = document.createElement( 'input' );
                el.setAttribute( Hi.DEVICE_REQUIRES_ATTR, requiresValue );
                el.setAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR, handlersValue );
                return el;
            }
            assert.ok( Hi.device.isHandlerActiveFor( 'test-files-handler',
                                                     element( 'local_files', 'test-files-handler' )));
            assert.notOk( Hi.device.isHandlerActiveFor( 'test-files-handler',
                                                        element( 'local_files', 'other-handler' )),
                          'handler not declared' );
            assert.notOk( Hi.device.isHandlerActiveFor( 'test-files-handler',
                                                        element( 'browser_nav', 'test-files-handler' )),
                          'its capability not required' );
            assert.notOk( Hi.device.isHandlerActiveFor( 'test-keyboard-handler',
                                                        element( 'keyboard', 'test-keyboard-handler' )),
                          'capability present' );
            assert.notOk( Hi.device.isHandlerActiveFor( 'test-unregistered-handler',
                                                        element( 'local_files', 'test-unregistered-handler' )),
                          'handler not registered' );
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

        QUnit.test('click proceeds when a declared handler stands in for the missing capability', function(assert) {
            const result = clickRequiring( 'local_files', 'click', 0, 'test-files-handler' );
            assert.ok( result.actionRan, 'element click handler ran' );
            assert.notOk( result.defaultPrevented, 'default action not prevented' );
            assert.equal( requestedUrls.length, 0, 'no modal request' );
        });

        QUnit.test('click proceeds when all required capabilities are present', function(assert) {
            const result = clickRequiring( 'keyboard' );
            assert.ok( result.actionRan, 'element click handler ran' );
            assert.notOk( result.defaultPrevented, 'default action not prevented' );
            assert.equal( requestedUrls.length, 0, 'no modal request' );
        });
    });

})();
