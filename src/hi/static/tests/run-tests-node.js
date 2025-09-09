#!/usr/bin/env node

/**
 * Node.js runner for QUnit tests
 * This allows running the JavaScript tests from the command line
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Create a mock browser environment
const mockWindow = {
    addEventListener: function(event, handler, options) {
        // Mock implementation
    },
    removeEventListener: function(event, handler, options) {
        // Mock implementation
    },
    location: {
        href: 'http://localhost:8000/test'
    },
    history: {
        back: function() {},
        replaceState: function() {},
        pushState: function() {}
    },
    Hi: {
        DEBUG: false,
        MAIN_AREA_SELECTOR: '#main-content',
        autoView: null
    },
    // Add AN mock for antinode dependency
    AN: {
        loadAsyncContent: function(options) {
            console.log('Mock: loadAsyncContent called with', options.url);
        }
    }
};

// Create mock jQuery
const $ = function(selector) {
    return {
        html: function(content) { 
            if (arguments.length === 0) return '<div>Mock content</div>';
            return this;
        },
        addClass: function() { return this; },
        removeClass: function() { return this; },
        remove: function() { return this; },
        append: function() { return this; },
        on: function() { return this; },
        off: function() { return this; },
        css: function() { return this; },
        length: 1,
        0: { getBoundingClientRect: function() { return { bottom: 100, right: 100 }; } }
    };
};

// Mock document
const mockDocument = {
    addEventListener: function(event, handler, options) {
        // Mock implementation
    },
    removeEventListener: function(event, handler, options) {
        // Mock implementation
    }
};

// Create global context for the tests
const sandbox = {
    window: mockWindow,
    document: mockDocument,
    $: $,
    jQuery: $,
    console: console,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    Date: Date,
    Hi: mockWindow.Hi
};

// Make window properties available globally in sandbox
Object.keys(mockWindow).forEach(key => {
    if (!(key in sandbox)) {
        sandbox[key] = mockWindow[key];
    }
});

console.log('Loading auto-view.js...');

// Load and execute auto-view.js
const autoViewPath = path.join(__dirname, '../js/auto-view.js');
const autoViewCode = fs.readFileSync(autoViewPath, 'utf8');

try {
    vm.runInNewContext(autoViewCode, sandbox);
    console.log('✓ auto-view.js loaded successfully');
} catch (error) {
    console.error('✗ Error loading auto-view.js:', error.message);
    process.exit(1);
}

// Simple test runner without QUnit
console.log('\n=== Running Tests ===\n');

let passCount = 0;
let failCount = 0;

function assert(condition, message) {
    if (condition) {
        console.log('✓', message);
        passCount++;
    } else {
        console.log('✗', message);
        failCount++;
    }
}

function test(name, fn) {
    console.log('\nTest:', name);
    try {
        fn();
    } catch (error) {
        console.log('✗ Test threw error:', error.message);
        failCount++;
    }
}

// Run basic tests to verify the module loaded correctly
test('AutoView module exists', () => {
    assert(sandbox.Hi.autoView !== null, 'AutoView module is defined');
    assert(typeof sandbox.Hi.autoView === 'object', 'AutoView is an object');
});

test('Core functions exist', () => {
    const autoView = sandbox.Hi.autoView;
    assert(typeof autoView.throttle === 'function', 'throttle function exists');
    assert(typeof autoView.shouldAutoSwitch === 'function', 'shouldAutoSwitch function exists');
    assert(typeof autoView.isPassiveEventSupported === 'function', 'isPassiveEventSupported function exists');
    assert(typeof autoView.recordInteraction === 'function', 'recordInteraction function exists');
    assert(typeof autoView.clearRevertTimer === 'function', 'clearRevertTimer function exists');
    assert(typeof autoView.resetTransientState === 'function', 'resetTransientState function exists');
});

test('Throttle function basic behavior', () => {
    const autoView = sandbox.Hi.autoView;
    let callCount = 0;
    const throttled = autoView.throttle(() => callCount++, 100);
    
    throttled();
    assert(callCount === 1, 'First call executes immediately');
    
    throttled();
    throttled();
    assert(callCount === 1, 'Subsequent rapid calls are throttled');
});

test('shouldAutoSwitch with recent activity', () => {
    const autoView = sandbox.Hi.autoView;
    const now = Date.now();
    
    // Set recent interaction (30 seconds ago)
    autoView.lastInteractionTime = now - 30000;
    
    const result = autoView.shouldAutoSwitch({});
    assert(result === false, 'Returns false for recent activity (< 60s)');
});

test('shouldAutoSwitch with old activity', () => {
    const autoView = sandbox.Hi.autoView;
    const now = Date.now();
    
    // Set old interaction (61 seconds ago)
    autoView.lastInteractionTime = now - 61000;
    
    const result = autoView.shouldAutoSwitch({});
    assert(result === true, 'Returns true for old activity (> 60s)');
});

test('isPassiveEventSupported returns boolean', () => {
    const autoView = sandbox.Hi.autoView;
    const result = autoView.isPassiveEventSupported();
    assert(typeof result === 'boolean', 'Returns a boolean value');
});

test('recordInteraction updates lastInteractionTime', () => {
    const autoView = sandbox.Hi.autoView;
    const beforeTime = Date.now();
    
    autoView.recordInteraction();
    
    const afterTime = Date.now();
    assert(autoView.lastInteractionTime >= beforeTime, 'Updates interaction time');
    assert(autoView.lastInteractionTime <= afterTime, 'Interaction time is current');
});

test('clearRevertTimer handles null timer', () => {
    const autoView = sandbox.Hi.autoView;
    autoView.revertTimer = null;
    
    // Should not throw error
    autoView.clearRevertTimer();
    assert(autoView.revertTimer === null, 'Handles null timer gracefully');
});

test('resetTransientState clears all state', () => {
    const autoView = sandbox.Hi.autoView;
    
    // Set up state
    autoView.isTransientView = true;
    autoView.originalContent = 'test';
    autoView.originalUrl = 'http://test';
    autoView.transientUrls = ['url1', 'url2'];
    
    // Reset
    autoView.resetTransientState();
    
    assert(autoView.isTransientView === false, 'Clears isTransientView');
    assert(autoView.originalContent === null, 'Clears originalContent');
    assert(autoView.originalUrl === null, 'Clears originalUrl');
    assert(autoView.transientUrls.length === 0, 'Clears transientUrls');
});

// Print summary
console.log('\n=== Test Summary ===');
console.log(`Passed: ${passCount}`);
console.log(`Failed: ${failCount}`);
console.log(`Total:  ${passCount + failCount}`);

// Exit with appropriate code
process.exit(failCount > 0 ? 1 : 0);