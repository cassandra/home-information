/**
 * Unit Tests for file-viewer.js
 *
 * - Zoom stepping: in and out move one step and stop at the ends, and
 *   fit always returns to the first (fitted) step.
 * - Reading text within a size limit: the declared and the streamed
 *   size are both checked, and an HTTP error rejects.
 */

(function() {
    'use strict';

    QUnit.module('Hi.fileViewer zoom', function() {

        function lastZoomIndex() {
            let zoomIndex = 0;
            while ( Hi.fileViewer.nextZoomIndex( zoomIndex, 'zoom-in' ) !== zoomIndex ) {
                zoomIndex = Hi.fileViewer.nextZoomIndex( zoomIndex, 'zoom-in' );
            }
            return zoomIndex;
        }

        QUnit.test('zoom in and out move one step within the ends', function(assert) {
            const last = lastZoomIndex();
            assert.ok( last > 0, 'there is more than one step' );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( 0, 'zoom-in' ), 1 );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( last, 'zoom-out' ), last - 1 );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( 0, 'zoom-out' ), 0, 'stays at fit' );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( last, 'zoom-in' ), last, 'stays at the largest step' );
        });

        QUnit.test('fit returns to the first step from anywhere', function(assert) {
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( lastZoomIndex(), 'zoom-fit' ), 0 );
            assert.strictEqual( Hi.fileViewer.nextZoomIndex( 0, 'zoom-fit' ), 0 );
        });
    });

    QUnit.module('Hi.fileViewer text within limit', function() {

        const MAX_BYTES = 8;

        QUnit.test('text at the limit is read in full', async function(assert) {
            const text = await Hi.fileViewer.readTextWithinLimit( new Response( '12345678' ), MAX_BYTES );
            assert.strictEqual( text, '12345678' );
        });

        QUnit.test('text over the limit is refused while streaming', async function(assert) {
            const text = await Hi.fileViewer.readTextWithinLimit( new Response( '123456789' ), MAX_BYTES );
            assert.strictEqual( text, null );
        });

        QUnit.test('a declared length over the limit is refused before reading', async function(assert) {
            const response = new Response( 'short', { headers: { 'Content-Length': String( MAX_BYTES + 1 ) } });
            const text = await Hi.fileViewer.readTextWithinLimit( response, MAX_BYTES );
            assert.strictEqual( text, null );
        });

        QUnit.test('an HTTP error rejects', async function(assert) {
            await assert.rejects( Hi.fileViewer.readTextWithinLimit( new Response( 'x', { status: 404 } ), MAX_BYTES ));
        });
    });

})();
