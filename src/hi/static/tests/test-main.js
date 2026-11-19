/**
 * Unit Tests for main.js
 * 
 * Tests the core utility functions including:
 * - generateUniqueId - ID generation algorithm
 * - setCookie/getCookie - Cookie string parsing and formatting
 */

(function() {
    'use strict';
    
    // ===== UNIQUE ID GENERATION TESTS =====
    QUnit.module('Hi.generateUniqueId', function(hooks) {
        let originalDateNow;
        let mockTime;
        let originalMathRandom;
        
        hooks.beforeEach(function() {
            originalDateNow = Date.now;
            originalMathRandom = Math.random;
            mockTime = 1234567890000; // Fixed timestamp for testing
        });
        
        hooks.afterEach(function() {
            Date.now = originalDateNow;
            Math.random = originalMathRandom;
        });
        
        QUnit.test('generates ID with correct format', function(assert) {
            Date.now = function() { return mockTime; };
            Math.random = function() { return 0.123; }; // Fixed random for testing
            
            const id = Hi.generateUniqueId();
            const expectedPattern = /^id-\d+-\d+$/;
            
            assert.ok(expectedPattern.test(id), 'ID matches expected pattern');
            assert.equal(id, 'id-1234567890000-123', 'ID has expected exact value with mocked inputs');
        });
        
        QUnit.test('generates different IDs on different calls', function(assert) {
            let timeCounter = mockTime;
            Date.now = function() { return timeCounter++; };
            
            const id1 = Hi.generateUniqueId();
            const id2 = Hi.generateUniqueId();
            
            assert.notEqual(id1, id2, 'Sequential calls generate different IDs');
        });
        
        QUnit.test('includes timestamp component', function(assert) {
            Date.now = function() { return mockTime; };
            
            const id = Hi.generateUniqueId();
            
            assert.ok(id.includes('1234567890000'), 'ID includes timestamp');
            assert.ok(id.startsWith('id-1234567890000-'), 'Timestamp in correct position');
        });
        
        QUnit.test('includes random component', function(assert) {
            Date.now = function() { return mockTime; };
            Math.random = function() { return 0.999; };
            
            const id = Hi.generateUniqueId();
            
            assert.ok(id.includes('999'), 'ID includes random component');
            assert.ok(id.endsWith('-999'), 'Random component in correct position');
        });
    });
    
    // ===== COOKIE FUNCTIONS TESTS =====
    QUnit.module('Hi Cookie Functions', function(hooks) {
        let originalDocumentCookie;
        let mockCookie = '';
        
        hooks.beforeEach(function() {
            // Mock document.cookie
            originalDocumentCookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
            Object.defineProperty(document, 'cookie', {
                get: function() { return mockCookie; },
                set: function(value) { 
                    // Simulate browser cookie setting behavior
                    const [nameValue] = value.split(';');
                    const [name, val] = nameValue.split('=');
                    
                    // Simple mock - just store the name=value part
                    if (mockCookie) {
                        const cookies = mockCookie.split('; ');
                        const index = cookies.findIndex(cookie => cookie.startsWith(name + '='));
                        if (index >= 0) {
                            cookies[index] = nameValue;
                        } else {
                            cookies.push(nameValue);
                        }
                        mockCookie = cookies.join('; ');
                    } else {
                        mockCookie = nameValue;
                    }
                },
                configurable: true
            });
        });
        
        hooks.afterEach(function() {
            // Restore original document.cookie
            if (originalDocumentCookie) {
                Object.defineProperty(Document.prototype, 'cookie', originalDocumentCookie);
            }
            mockCookie = '';
        });
        
        QUnit.test('setCookie sets cookie with correct format', function(assert) {
            const result = Hi.setCookie('testName', 'testValue', 7);
            
            assert.true(result, 'setCookie returns true on success');
            assert.ok(mockCookie.includes('testName=testValue'), 'Cookie contains name=value pair');
        });
        
        QUnit.test('setCookie handles URL encoding', function(assert) {
            Hi.setCookie('test', 'value with spaces & symbols');
            
            assert.ok(mockCookie.includes('test=value%20with%20spaces%20%26%20symbols'), 
                     'Cookie value is URL encoded');
        });
        
        QUnit.test('getCookie retrieves set cookie', function(assert) {
            Hi.setCookie('retrieveTest', 'retrieveValue');
            
            const value = Hi.getCookie('retrieveTest');
            
            assert.equal(value, 'retrieveValue', 'Retrieved cookie matches set value');
        });
        
        QUnit.test('getCookie handles URL decoding', function(assert) {
            // Manually set encoded cookie
            mockCookie = 'encoded=value%20with%20spaces%20%26%20symbols';
            
            const value = Hi.getCookie('encoded');
            
            assert.equal(value, 'value with spaces & symbols', 'Cookie value is URL decoded');
        });
        
        QUnit.test('getCookie returns null for non-existent cookie', function(assert) {
            const value = Hi.getCookie('nonExistent');
            
            assert.strictEqual(value, null, 'Non-existent cookie returns null');
        });
        
        QUnit.test('getCookie handles multiple cookies', function(assert) {
            mockCookie = 'first=value1; second=value2; third=value3';
            
            assert.equal(Hi.getCookie('first'), 'value1', 'Gets first cookie');
            assert.equal(Hi.getCookie('second'), 'value2', 'Gets middle cookie');
            assert.equal(Hi.getCookie('third'), 'value3', 'Gets last cookie');
            assert.strictEqual(Hi.getCookie('fourth'), null, 'Non-existent returns null');
        });
        
        QUnit.test('getCookie handles partial name matches correctly', function(assert) {
            mockCookie = 'test=value1; testLonger=value2; pretest=value3';
            
            assert.equal(Hi.getCookie('test'), 'value1', 'Exact match returns correct value');
            assert.equal(Hi.getCookie('testLonger'), 'value2', 'Longer name with same prefix works');
            assert.equal(Hi.getCookie('pretest'), 'value3', 'Name as suffix works');
        });
        
        QUnit.test('cookie functions handle edge cases', function(assert) {
            // Empty value
            Hi.setCookie('empty', '');
            assert.equal(Hi.getCookie('empty'), '', 'Empty cookie value handled');
            
            // Special characters in name (encoded)
            Hi.setCookie('special-name_123', 'specialValue');
            assert.equal(Hi.getCookie('special-name_123'), 'specialValue', 'Special chars in name handled');
            
            // Cookie with equals in value
            mockCookie = 'equation=a%3Db%2Bc';
            assert.equal(Hi.getCookie('equation'), 'a=b+c', 'Equals signs in value handled');
        });
    });

    // ===== TAP SLOP TESTS =====
    QUnit.module('Hi.exceedsTapSlop', function(hooks) {
        const start = { x: 100, y: 200 };

        function offset( dx, dy ) {
            return { x: start.x + dx, y: start.y + dy };
        }

        QUnit.test('touch and pen allow 10px of wobble', function(assert) {
            ['touch', 'pen'].forEach(function(pointerType) {
                assert.false(Hi.exceedsTapSlop(start, offset(10, 0), pointerType),
                             `${pointerType}: at slop is still a tap`);
                assert.true(Hi.exceedsTapSlop(start, offset(11, 0), pointerType),
                            `${pointerType}: beyond slop is a drag`);
            });
        });

        QUnit.test('mouse allows only 3px', function(assert) {
            assert.false(Hi.exceedsTapSlop(start, offset(3, 0), 'mouse'), 'At slop is still a tap');
            assert.true(Hi.exceedsTapSlop(start, offset(4, 0), 'mouse'), 'Beyond slop is a drag');
        });

        QUnit.test('unknown pointer type uses the forgiving default', function(assert) {
            assert.false(Hi.exceedsTapSlop(start, offset(10, 0), ''), 'Empty type within default slop');
            assert.false(Hi.exceedsTapSlop(start, offset(10, 0), undefined), 'Undefined type within default slop');
            assert.true(Hi.exceedsTapSlop(start, offset(11, 0), undefined), 'Beyond default slop is a drag');
        });

        QUnit.test('measures each axis independently, in either direction', function(assert) {
            assert.true(Hi.exceedsTapSlop(start, offset(0, 11), 'touch'), 'Vertical movement counts');
            assert.true(Hi.exceedsTapSlop(start, offset(-11, 0), 'touch'), 'Negative X counts');
            assert.true(Hi.exceedsTapSlop(start, offset(0, -11), 'touch'), 'Negative Y counts');
            assert.false(Hi.exceedsTapSlop(start, offset(10, 10), 'touch'),
                         'Diagonal within slop on both axes is still a tap');
        });
    });

})();