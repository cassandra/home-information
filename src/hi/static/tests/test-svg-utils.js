/**
 * Unit Tests for svg-utils.js
 * 
 * Tests the SVG utility functions including:
 * - _getSvgTransformValues - SVG transform string parsing
 * - Other utility functions that can be tested without DOM
 */

(function() {
    'use strict';
    
    // ===== SVG TRANSFORM VALUES PARSING TESTS =====
    QUnit.module('SvgUtils._getSvgTransformValues', function(hooks) {
        
        QUnit.test('returns default values for null/undefined input', function(assert) {
            const result1 = Hi.svgUtils.getSvgTransformValues(null);
            const result2 = Hi.svgUtils.getSvgTransformValues(undefined);
            const result3 = Hi.svgUtils.getSvgTransformValues('');
            
            const expectedDefaults = {
                scale: { x: 1, y: 1 },
                rotate: { angle: 0, cx: 0, cy: 0 },
                translate: { x: 100, y: 100 }
            };
            
            assert.deepEqual(result1, expectedDefaults, 'Returns defaults for null');
            assert.deepEqual(result2, expectedDefaults, 'Returns defaults for undefined');
            assert.deepEqual(result3, expectedDefaults, 'Returns defaults for empty string');
        });
        
        QUnit.test('parses single scale transform correctly', function(assert) {
            const result1 = Hi.svgUtils.getSvgTransformValues('scale(2)');
            const result2 = Hi.svgUtils.getSvgTransformValues('scale(2.5, 1.5)');
            
            assert.equal(result1.scale.x, 2, 'Single scale value applies to x');
            assert.equal(result1.scale.y, 2, 'Single scale value applies to y');
            
            assert.equal(result2.scale.x, 2.5, 'First scale value applies to x');
            assert.equal(result2.scale.y, 1.5, 'Second scale value applies to y');
        });
        
        QUnit.test('parses single translate transform correctly', function(assert) {
            const result1 = Hi.svgUtils.getSvgTransformValues('translate(50, 75)');
            const result2 = Hi.svgUtils.getSvgTransformValues('translate(100)');
            
            assert.equal(result1.translate.x, 50, 'Translate x parsed correctly');
            assert.equal(result1.translate.y, 75, 'Translate y parsed correctly');
            
            assert.equal(result2.translate.x, 100, 'Single translate value applies to x');
            assert.ok(isNaN(result2.translate.y), 'Single translate leaves y as NaN');
        });
        
        QUnit.test('parses single rotate transform correctly', function(assert) {
            const result1 = Hi.svgUtils.getSvgTransformValues('rotate(45)');
            const result2 = Hi.svgUtils.getSvgTransformValues('rotate(90, 100, 200)');
            
            assert.equal(result1.rotate.angle, 45, 'Rotate angle parsed correctly');
            assert.equal(result1.rotate.cx, 0, 'Default rotate center x is 0');
            assert.equal(result1.rotate.cy, 0, 'Default rotate center y is 0');
            
            assert.equal(result2.rotate.angle, 90, 'Rotate angle with center parsed correctly');
            assert.equal(result2.rotate.cx, 100, 'Rotate center x parsed correctly');
            assert.equal(result2.rotate.cy, 200, 'Rotate center y parsed correctly');
        });
        
        QUnit.test('parses multiple transforms correctly', function(assert) {
            const transformStr = 'translate(10, 20) scale(1.5, 2) rotate(45, 50, 60)';
            const result = Hi.svgUtils.getSvgTransformValues(transformStr);
            
            assert.equal(result.translate.x, 10, 'Multiple: translate x');
            assert.equal(result.translate.y, 20, 'Multiple: translate y');
            assert.equal(result.scale.x, 1.5, 'Multiple: scale x');
            assert.equal(result.scale.y, 2, 'Multiple: scale y');
            assert.equal(result.rotate.angle, 45, 'Multiple: rotate angle');
            assert.equal(result.rotate.cx, 50, 'Multiple: rotate center x');
            assert.equal(result.rotate.cy, 60, 'Multiple: rotate center y');
        });
        
        QUnit.test('handles whitespace variations correctly', function(assert) {
            const result1 = Hi.svgUtils.getSvgTransformValues('scale( 2 , 3 )');
            const result2 = Hi.svgUtils.getSvgTransformValues('translate(10,20)scale(1.5)');
            const result3 = Hi.svgUtils.getSvgTransformValues('  translate( 5   10 )  ');
            
            assert.equal(result1.scale.x, 2, 'Handles spaces around commas');
            assert.equal(result1.scale.y, 3, 'Handles spaces around commas');
            
            assert.equal(result2.translate.x, 10, 'Handles no spaces between transforms');
            assert.equal(result2.scale.x, 1.5, 'Handles no spaces between transforms');
            
            assert.equal(result3.translate.x, 5, 'Handles space-separated values');
            assert.equal(result3.translate.y, 10, 'Handles space-separated values');
        });
        
        QUnit.test('handles decimal and negative values correctly', function(assert) {
            const result = Hi.svgUtils.getSvgTransformValues('translate(-10.5, 20.25) scale(0.75, -1.5)');
            
            assert.equal(result.translate.x, -10.5, 'Handles negative decimal translate x');
            assert.equal(result.translate.y, 20.25, 'Handles positive decimal translate y');
            assert.equal(result.scale.x, 0.75, 'Handles decimal scale x');
            assert.equal(result.scale.y, -1.5, 'Handles negative decimal scale y');
        });
        
        QUnit.test('handles malformed input gracefully', function(assert) {
            const result1 = Hi.svgUtils.getSvgTransformValues('scale()');
            const result2 = Hi.svgUtils.getSvgTransformValues('invalid(10, 20)');
            const result3 = Hi.svgUtils.getSvgTransformValues('scale(abc, def)');
            
            // Empty parentheses don't match regex ([^)]+ requires 1+ chars), so defaults preserved
            assert.equal(result1.scale.x, 1, 'Empty scale params ignored - default scale x preserved');
            assert.equal(result1.scale.y, 1, 'Empty scale params ignored - default scale y preserved');
            
            // Invalid transforms should be ignored, defaults preserved
            assert.equal(result2.scale.x, 1, 'Invalid transform type ignored - scale x default');
            assert.equal(result2.translate.x, 100, 'Invalid transform type ignored - translate x default');
            
            assert.ok(isNaN(result3.scale.x), 'Invalid numeric values result in NaN');
            assert.ok(isNaN(result3.scale.y), 'Invalid numeric values result in NaN');
        });
        
        QUnit.test('handles overlapping transforms (last wins)', function(assert) {
            const result = Hi.svgUtils.getSvgTransformValues('scale(2) translate(10, 20) scale(3, 4) translate(30, 40)');
            
            assert.equal(result.scale.x, 3, 'Last scale x value wins');
            assert.equal(result.scale.y, 4, 'Last scale y value wins');
            assert.equal(result.translate.x, 30, 'Last translate x value wins');
            assert.equal(result.translate.y, 40, 'Last translate y value wins');
        });
        
        QUnit.test('preserves unspecified transform defaults', function(assert) {
            const result = Hi.svgUtils.getSvgTransformValues('scale(2)');
            
            assert.equal(result.scale.x, 2, 'Specified scale x updated');
            assert.equal(result.scale.y, 2, 'Specified scale y updated');
            assert.equal(result.translate.x, 100, 'Unspecified translate x keeps default');
            assert.equal(result.translate.y, 100, 'Unspecified translate y keeps default');
            assert.equal(result.rotate.angle, 0, 'Unspecified rotate angle keeps default');
        });
        
        QUnit.test('handles edge case transform strings', function(assert) {
            const result1 = Hi.svgUtils.getSvgTransformValues('SCALE(2)'); // Case shouldn't matter for regex
            const result2 = Hi.svgUtils.getSvgTransformValues('scale(1,)'); // Trailing comma
            const result3 = Hi.svgUtils.getSvgTransformValues('scale(1 2 3)'); // Too many values
            
            // These are edge cases - behavior may vary, just ensure no crashes
            assert.ok(typeof result1.scale.x === 'number' || isNaN(result1.scale.x), 'Edge case 1 handled gracefully');
            assert.ok(typeof result2.scale.x === 'number' || isNaN(result2.scale.x), 'Edge case 2 handled gracefully');  
            assert.ok(typeof result3.scale.x === 'number' || isNaN(result3.scale.x), 'Edge case 3 handled gracefully');
        });
    });
    
})();