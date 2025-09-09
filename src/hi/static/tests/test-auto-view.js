/**
 * Unit Tests for auto-view.js
 * 
 * Tests the core logic functions of the AutoView module including:
 * - Throttle function timing behavior
 * - Idle timeout decision logic
 * - Feature detection and caching
 * - State management functions
 */

(function() {
    'use strict';
    
    // Helper to save and restore original values
    const TestHelpers = {
        savedValues: {},
        
        save: function(obj, prop) {
            this.savedValues[prop] = obj[prop];
        },
        
        restore: function(obj, prop) {
            if (this.savedValues.hasOwnProperty(prop)) {
                obj[prop] = this.savedValues[prop];
                delete this.savedValues[prop];
            }
        },
        
        restoreAll: function() {
            // Restore Date.now if it was mocked
            if (this.savedValues.dateNow) {
                Date.now = this.savedValues.dateNow;
            }
        }
    };
    
    // ===== THROTTLE FUNCTION TESTS =====
    QUnit.module('AutoView.throttle', function(hooks) {
        
        hooks.afterEach(function() {
            TestHelpers.restoreAll();
        });
        
        QUnit.test('executes immediately on first call', function(assert) {
            let callCount = 0;
            const throttled = Hi.autoView.throttle(function() {
                callCount++;
            }, 100);
            
            throttled();
            assert.equal(callCount, 1, 'Function executed immediately on first call');
        });
        
        QUnit.test('prevents multiple executions within delay period', function(assert) {
            let callCount = 0;
            const throttled = Hi.autoView.throttle(function() {
                callCount++;
            }, 100);
            
            throttled();
            throttled();
            throttled();
            
            assert.equal(callCount, 1, 'Function executed only once within delay period');
        });
        
        QUnit.test('schedules delayed execution after throttle period', function(assert) {
            const done = assert.async();
            let callCount = 0;
            const throttled = Hi.autoView.throttle(function() {
                callCount++;
            }, 50);
            
            throttled(); // immediate execution
            assert.equal(callCount, 1, 'First call executed immediately');
            
            throttled(); // should be delayed
            assert.equal(callCount, 1, 'Second call not executed immediately');
            
            setTimeout(function() {
                assert.equal(callCount, 2, 'Delayed execution occurred after throttle period');
                done();
            }, 60);
        });
        
        QUnit.test('clears previous timeout on rapid calls', function(assert) {
            const done = assert.async();
            let callCount = 0;
            let callValues = [];
            const throttled = Hi.autoView.throttle(function(value) {
                callCount++;
                callValues.push(value);
            }, 100);
            
            throttled(1); // immediate
            assert.equal(callCount, 1, 'First call executed immediately');
            
            setTimeout(function() {
                throttled(2); // sets timeout
            }, 10);
            
            setTimeout(function() {
                throttled(3); // should clear previous timeout and set new one
            }, 20);
            
            setTimeout(function() {
                assert.equal(callCount, 2, 'Only two executions total');
                assert.deepEqual(callValues, [1, 3], 'First immediate call and last delayed call executed');
                done();
            }, 130);
        });
        
        QUnit.test('handles arguments correctly', function(assert) {
            const done = assert.async();
            let receivedArgs = [];
            const throttled = Hi.autoView.throttle(function(a, b, c) {
                receivedArgs.push([a, b, c]);
            }, 50);
            
            throttled(1, 2, 3);
            throttled(4, 5, 6);
            
            setTimeout(function() {
                assert.equal(receivedArgs.length, 2, 'Function called twice');
                assert.deepEqual(receivedArgs[0], [1, 2, 3], 'First call received correct arguments');
                assert.deepEqual(receivedArgs[1], [4, 5, 6], 'Second call received correct arguments');
                done();
            }, 60);
        });
        
        QUnit.test('preserves context (this) binding', function(assert) {
            const done = assert.async();
            const contextObj = { value: 42 };
            let capturedContext = null;
            
            const throttled = Hi.autoView.throttle(function() {
                capturedContext = this;
            }, 50);
            
            throttled.call(contextObj);
            
            setTimeout(function() {
                assert.strictEqual(capturedContext, contextObj, 'Context preserved in throttled function');
                done();
            }, 10);
        });
    });
    
    // ===== SHOULD AUTO SWITCH TESTS =====
    QUnit.module('AutoView.shouldAutoSwitch', function(hooks) {
        let originalDateNow;
        let mockTime;
        
        hooks.beforeEach(function() {
            // Save original Date.now
            originalDateNow = Date.now;
            mockTime = 1000000; // Base time for testing
            
            // Mock Date.now for consistent testing
            Date.now = function() {
                return mockTime;
            };
        });
        
        hooks.afterEach(function() {
            // Restore original Date.now
            Date.now = originalDateNow;
        });
        
        QUnit.test('returns false for recent activity (< 60s)', function(assert) {
            // Set recent interaction (30 seconds ago)
            Hi.autoView.lastInteractionTime = mockTime - 30000;
            
            const result = Hi.autoView.shouldAutoSwitch({});
            
            assert.false(result, 'Should not auto-switch when user active within 60 seconds');
        });
        
        QUnit.test('returns true at exact threshold (60s)', function(assert) {
            // Set interaction exactly 60 seconds ago
            Hi.autoView.lastInteractionTime = mockTime - 60000;
            
            const result = Hi.autoView.shouldAutoSwitch({});
            
            assert.true(result, 'Should auto-switch at exactly 60 seconds (threshold is inclusive)');
        });
        
        QUnit.test('returns true after idle timeout (> 60s)', function(assert) {
            // Set old interaction (61 seconds ago)
            Hi.autoView.lastInteractionTime = mockTime - 61000;
            
            const result = Hi.autoView.shouldAutoSwitch({});
            
            assert.true(result, 'Should auto-switch after idle timeout exceeded');
        });
        
        QUnit.test('returns true for very old activity', function(assert) {
            // Set very old interaction (5 minutes ago)
            Hi.autoView.lastInteractionTime = mockTime - 300000;
            
            const result = Hi.autoView.shouldAutoSwitch({});
            
            assert.true(result, 'Should auto-switch for very old activity');
        });
        
        QUnit.test('handles zero lastInteractionTime', function(assert) {
            // Set lastInteractionTime to 0 (very old)
            Hi.autoView.lastInteractionTime = 0;
            
            const result = Hi.autoView.shouldAutoSwitch({});
            
            assert.true(result, 'Should auto-switch when lastInteractionTime is 0');
        });
        
        QUnit.test('handles future lastInteractionTime', function(assert) {
            // Set interaction time in the future (edge case)
            Hi.autoView.lastInteractionTime = mockTime + 10000;
            
            const result = Hi.autoView.shouldAutoSwitch({});
            
            assert.false(result, 'Should not auto-switch when lastInteractionTime is in the future');
        });
    });
    
    // ===== IS PASSIVE EVENT SUPPORTED TESTS =====
    QUnit.module('AutoView.isPassiveEventSupported', function(hooks) {
        
        hooks.beforeEach(function() {
            // Clear cached value before each test
            delete Hi.autoView._passiveSupported;
        });
        
        QUnit.test('detects passive event support', function(assert) {
            // First call should perform detection
            const result1 = Hi.autoView.isPassiveEventSupported();
            
            assert.strictEqual(typeof result1, 'boolean', 'Returns a boolean value');
            
            // For testing purposes, we can't easily mock the browser's passive support,
            // but we can verify the function works without errors
            assert.ok(true, 'Feature detection completed without errors');
        });
        
        QUnit.test('caches result after first call', function(assert) {
            // First call
            const result1 = Hi.autoView.isPassiveEventSupported();
            
            // Manually set the cached value to verify caching
            Hi.autoView._passiveSupported = !result1;
            
            // Second call should return cached value
            const result2 = Hi.autoView.isPassiveEventSupported();
            
            assert.strictEqual(result2, !result1, 'Returns cached value on subsequent calls');
        });
        
        QUnit.test('handles browsers without passive support gracefully', function(assert) {
            // Clear cache
            delete Hi.autoView._passiveSupported;
            
            // Mock addEventListener to throw an error
            const originalAddEventListener = window.addEventListener;
            const originalRemoveEventListener = window.removeEventListener;
            
            window.addEventListener = function() {
                throw new Error('Passive not supported');
            };
            
            window.removeEventListener = function() {
                // No-op
            };
            
            const result = Hi.autoView.isPassiveEventSupported();
            
            assert.strictEqual(result, false, 'Returns false when passive events not supported');
            
            // Restore original methods
            window.addEventListener = originalAddEventListener;
            window.removeEventListener = originalRemoveEventListener;
        });
    });
    
    // ===== STATE MANAGEMENT TESTS =====
    QUnit.module('AutoView State Management', function(hooks) {
        let originalDateNow;
        let mockTime;
        
        hooks.beforeEach(function() {
            // Save original Date.now and state
            originalDateNow = Date.now;
            mockTime = 1000000;
            Date.now = function() {
                return mockTime;
            };
            
            // Reset AutoView state
            Hi.autoView.isTransientView = false;
            Hi.autoView.revertTimer = null;
            Hi.autoView.originalContent = null;
            Hi.autoView.originalUrl = null;
            Hi.autoView.transientUrls = [];
        });
        
        hooks.afterEach(function() {
            // Restore Date.now
            Date.now = originalDateNow;
            
            // Clear any timers
            if (Hi.autoView.revertTimer) {
                clearTimeout(Hi.autoView.revertTimer);
                Hi.autoView.revertTimer = null;
            }
        });
        
        QUnit.test('recordInteraction updates lastInteractionTime', function(assert) {
            const beforeTime = mockTime;
            Hi.autoView.lastInteractionTime = beforeTime - 1000;
            
            Hi.autoView.recordInteraction();
            
            assert.equal(Hi.autoView.lastInteractionTime, mockTime, 'Interaction time updated to current time');
        });
        
        QUnit.test('recordInteraction makes transient view permanent when active', function(assert) {
            // Set up transient view state
            Hi.autoView.isTransientView = true;
            Hi.autoView.revertTimer = setTimeout(function() {}, 1000);
            Hi.autoView.originalContent = '<div>Original</div>';
            Hi.autoView.originalUrl = 'http://example.com/original';
            
            // Mock makeTransientViewPermanent to verify it's called
            let permanentCalled = false;
            const originalMakePermament = Hi.autoView.makeTransientViewPermanent;
            Hi.autoView.makeTransientViewPermanent = function() {
                permanentCalled = true;
                originalMakePermament.call(this);
            };
            
            Hi.autoView.recordInteraction();
            
            assert.true(permanentCalled, 'makeTransientViewPermanent called when in transient view');
            assert.false(Hi.autoView.isTransientView, 'Transient view state cleared');
            
            // Restore original method
            Hi.autoView.makeTransientViewPermanent = originalMakePermament;
        });
        
        QUnit.test('clearRevertTimer clears timeout', function(assert) {
            // Set a timer
            let timerExecuted = false;
            Hi.autoView.revertTimer = setTimeout(function() {
                timerExecuted = true;
            }, 50);
            
            // Clear it
            Hi.autoView.clearRevertTimer();
            
            assert.strictEqual(Hi.autoView.revertTimer, null, 'Timer reference cleared');
            
            // Wait to ensure timer doesn't execute
            const done = assert.async();
            setTimeout(function() {
                assert.false(timerExecuted, 'Timer callback not executed after clearing');
                done();
            }, 60);
        });
        
        QUnit.test('clearRevertTimer handles null timer gracefully', function(assert) {
            Hi.autoView.revertTimer = null;
            
            // Should not throw error
            Hi.autoView.clearRevertTimer();
            
            assert.strictEqual(Hi.autoView.revertTimer, null, 'Null timer handled gracefully');
        });
        
        QUnit.test('resetTransientState clears all transient state', function(assert) {
            // Set up transient state
            Hi.autoView.isTransientView = true;
            Hi.autoView.revertTimer = setTimeout(function() {}, 1000);
            Hi.autoView.originalContent = '<div>Original</div>';
            Hi.autoView.originalUrl = 'http://example.com/original';
            Hi.autoView.transientUrls = ['url1', 'url2'];
            
            // Mock hideTransientViewIndicator to verify it's called
            let indicatorHidden = false;
            const originalHide = Hi.autoView.hideTransientViewIndicator;
            Hi.autoView.hideTransientViewIndicator = function() {
                indicatorHidden = true;
            };
            
            Hi.autoView.resetTransientState();
            
            assert.false(Hi.autoView.isTransientView, 'isTransientView reset to false');
            assert.strictEqual(Hi.autoView.revertTimer, null, 'revertTimer cleared');
            assert.strictEqual(Hi.autoView.originalContent, null, 'originalContent cleared');
            assert.strictEqual(Hi.autoView.originalUrl, null, 'originalUrl cleared');
            assert.deepEqual(Hi.autoView.transientUrls, [], 'transientUrls cleared');
            assert.true(indicatorHidden, 'hideTransientViewIndicator called');
            
            // Restore original method
            Hi.autoView.hideTransientViewIndicator = originalHide;
        });
        
        QUnit.test('makeTransientViewPermanent resets state', function(assert) {
            // Set up transient state
            Hi.autoView.isTransientView = true;
            Hi.autoView.revertTimer = setTimeout(function() {}, 1000);
            Hi.autoView.originalContent = '<div>Original</div>';
            
            Hi.autoView.makeTransientViewPermanent();
            
            assert.false(Hi.autoView.isTransientView, 'Transient view state cleared');
            assert.strictEqual(Hi.autoView.revertTimer, null, 'Timer cleared');
            assert.strictEqual(Hi.autoView.originalContent, null, 'Original content cleared');
        });
    });
    
    // ===== INTEGRATION TESTS =====
    QUnit.module('AutoView Integration', function(hooks) {
        
        QUnit.test('init attaches interaction listeners', function(assert) {
            // Mock addEventListener to track calls
            const eventListeners = [];
            const originalAddEventListener = document.addEventListener;
            
            document.addEventListener = function(event, handler, options) {
                eventListeners.push({ event, handler, options });
            };
            
            // Re-initialize
            Hi.autoView.init();
            
            // Verify expected events are listened to
            const expectedEvents = ['mousedown', 'keydown', 'touchstart', 'click'];
            const attachedEvents = eventListeners.map(function(listener) {
                return listener.event;
            });
            
            expectedEvents.forEach(function(event) {
                assert.ok(
                    attachedEvents.includes(event),
                    'Listener attached for ' + event + ' event'
                );
            });
            
            // Restore original
            document.addEventListener = originalAddEventListener;
        });
        
        QUnit.test('throttled interaction recording', function(assert) {
            const done = assert.async();
            let recordCount = 0;
            
            // Mock recordInteraction to count calls
            const originalRecord = Hi.autoView.recordInteraction;
            Hi.autoView.recordInteraction = function() {
                recordCount++;
            };
            
            // Get the throttled function that would be attached to events
            const throttledRecord = Hi.autoView.throttle(function() {
                Hi.autoView.recordInteraction();
            }, 100);
            
            // Simulate rapid events
            throttledRecord();
            throttledRecord();
            throttledRecord();
            
            assert.equal(recordCount, 1, 'Only one immediate recording for rapid events');
            
            setTimeout(function() {
                assert.equal(recordCount, 2, 'Delayed recording executed after throttle period');
                
                // Restore original
                Hi.autoView.recordInteraction = originalRecord;
                done();
            }, 110);
        });
    });
    
})();