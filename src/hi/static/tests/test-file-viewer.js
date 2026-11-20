/**
 * Unit Tests for file-viewer.js
 *
 * Tests zoom stepping: in and out move one step and stop at the ends,
 * and fit always returns to the first (fitted) step.
 */

(function() {
    'use strict';

    // Must match ZOOM_STEPS in file-viewer.js.
    const LAST_ZOOM_INDEX = 4;

    QUnit.module('Hi.fileViewer zoom', function() {

        QUnit.test('zoom in and out move one step within the ends', function(assert) {
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( 0, 'zoom-in' ), 1 );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( 2, 'zoom-out' ), 1 );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( 0, 'zoom-out' ), 0, 'stays at fit' );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( LAST_ZOOM_INDEX, 'zoom-in' ),
                                LAST_ZOOM_INDEX, 'stays at the largest step' );
        });

        QUnit.test('fit returns to the first step from anywhere', function(assert) {
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( LAST_ZOOM_INDEX, 'zoom-fit' ), 0 );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( 0, 'zoom-fit' ), 0 );
        });
    });

})();
