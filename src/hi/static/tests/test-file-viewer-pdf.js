/**
 * Unit Tests for file-viewer-pdf.js
 *
 * Tests the logic behind PDF display that needs no document:
 * - canvas output scale: the device pixel ratio, reduced to keep a
 *   canvas within the pixel budget
 * - current page: the last page starting at or above an offset
 * - error classification before pdf.js has loaded
 */

(function() {
    'use strict';

    QUnit.module('Hi.fileViewerPdf', function() {

        QUnit.test('output scale is the pixel ratio when within budget', function(assert) {
            assert.strictEqual( Hi.fileViewerPdf.outputScale( 800, 1000, 2, 16000000 ), 2 );
            assert.strictEqual( Hi.fileViewerPdf.outputScale( 800, 1000, undefined, 16000000 ), 1,
                                'missing ratio counts as 1' );
        });

        QUnit.test('output scale is the pixel ratio for a page not yet laid out', function(assert) {
            assert.strictEqual( Hi.fileViewerPdf.outputScale( 0, 0, 2, 16000000 ), 2 );
        });

        QUnit.test('output scale shrinks to keep the canvas within budget', function(assert) {
            const scale = Hi.fileViewerPdf.outputScale( 4000, 5000, 2, 16000000 );
            assert.ok( scale < 1, 'below 1 for a very large page' );
            assert.ok( Math.abs( 4000 * 5000 * scale * scale - 16000000 ) < 1, 'fills the budget' );
        });

        QUnit.test('current page is the last page starting at or above the offset', function(assert) {
            const pageTops = [ 0, 1000, 2000, 3000 ];
            assert.strictEqual( Hi.fileViewerPdf.pageNumberAt( pageTops, 0 ), 1 );
            assert.strictEqual( Hi.fileViewerPdf.pageNumberAt( pageTops, 999 ), 1 );
            assert.strictEqual( Hi.fileViewerPdf.pageNumberAt( pageTops, 1000 ), 2 );
            assert.strictEqual( Hi.fileViewerPdf.pageNumberAt( pageTops, 2500 ), 3 );
            assert.strictEqual( Hi.fileViewerPdf.pageNumberAt( pageTops, 99999 ), 4 );
        });

        QUnit.test('errors before pdf.js loads are not document errors', function(assert) {
            // The suite never loads pdf.js, as when a browser cannot run it.
            assert.false( Hi.fileViewerPdf.isDocumentError( new Error( 'x' )));
        });

        QUnit.test('current page is the first before any page starts', function(assert) {
            assert.strictEqual( Hi.fileViewerPdf.pageNumberAt( [ 16, 1016 ], 0 ), 1 );
            assert.strictEqual( Hi.fileViewerPdf.pageNumberAt( [ 16 ], 500 ), 1 );
        });
    });

})();
