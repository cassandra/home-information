/*
  SVG Pan/Zoom Core

  Provides viewBox-based pan and zoom for an SVG element. Initialized with
  a configuration object that specifies the target SVG, container area,
  and optional save callback.

  Usage:
    Hi.SvgPanZoomCore.init({
        baseSvgSelector: '#my-svg',
        areaSelector: '#my-container',
        onSave: function(viewBoxStr) { ... },
        shouldSave: function() { return true; },
    });
*/

(function() {

    window.Hi = window.Hi || {};
    window.Hi.svgUtils = window.Hi.svgUtils || {};

    const MODULE_NAME = 'svg-pan-zoom-core';

    const KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const ZOOM_SAVE_DEBOUNCE_MS = 400;

    let gConfig = null;
    let gSvgElement = null;
    let gTransformData = null;
    let gIgnoreClick = false;
    let gLastPointerPosition = { x: 0, y: 0 };

    let saveDebounceTimer = null;
    let lastSaveTime = 0;

    const HiSvgPanZoomCore = {

        init: function( config ) {
            gConfig = config;
            gSvgElement = $( config.baseSvgSelector )[0] || null;
        },

        refresh: function() {
            gSvgElement = gConfig ? $( gConfig.baseSvgSelector )[0] || null : null;
        },

        handleSinglePointerEventStart: function( event ) {
            if ( ! gSvgElement ) { return false; }

            var svgViewBox = Hi.svgUtils.getSvgViewBox( gSvgElement );
            gTransformData = {
                isDragging: false,
                start: {
                    x: event.clientX,
                    y: event.clientY,
                    viewBox: svgViewBox,
                },
                last: {
                    x: event.clientX,
                    y: event.clientY,
                },
            };
            return true;
        },

        handleSinglePointerEventMove: function( startEvent, lastEvent ) {
            if ( ! gTransformData ) { return false; }

            gTransformData.isDragging = true;
            updatePan( startEvent, lastEvent );
            gTransformData.last = { x: lastEvent.clientX, y: lastEvent.clientY };
            return true;
        },

        handleSinglePointerEventEnd: function() {
            if ( ! gTransformData ) { return false; }

            var wasDragging = gTransformData.isDragging;
            gTransformData = null;

            if ( wasDragging ) {
                debouncedSave();
                gIgnoreClick = true;
                return true;
            }
            return false;
        },

        handleMouseWheel: function( event ) {
            if ( ! gSvgElement ) { return false; }
            if ( ! isEventInArea( event ) ) { return false; }

            var e = event.originalEvent || event;
            var scaleFactor = 1.0 - ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
            if ( e.deltaY > 0 ) {
                scaleFactor = 1.0 + ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
            }
            zoom( scaleFactor );
            debouncedSave();

            event.preventDefault();
            event.stopImmediatePropagation();
            return true;
        },

        handleKeyDown: function( event ) {
            if ( ! gSvgElement ) { return false; }
            if ( $( event.target ).is( 'input, textarea' ) ) { return false; }
            if ( $( event.target ).closest( '.modal' ).length > 0 ) { return false; }
            if ( ! isEventInArea( event ) ) { return false; }

            if ( event.key === '+' || event.key === '=' ) {
                zoomIn();
                event.preventDefault();
                event.stopImmediatePropagation();
                return true;

            } else if ( event.key === '-' ) {
                zoomOut();
                event.preventDefault();
                event.stopImmediatePropagation();
                return true;
            }
            return false;
        },

        handleClick: function( event ) {
            if ( gIgnoreClick ) {
                gIgnoreClick = false;
                return true;
            }
            return false;
        },

        handleLastPointerLocation: function( x, y ) {
            gLastPointerPosition.x = x;
            gLastPointerPosition.y = y;
        },

        /* Allow other modules to check if a pan drag is in progress. */
        isDragging: function() {
            return gTransformData && gTransformData.isDragging;
        },
    };

    window.Hi.SvgPanZoomCore = HiSvgPanZoomCore;

    /* ==================== */
    /* Pan                  */
    /* ==================== */

    function updatePan( startEvent, lastEvent ) {
        if ( ! gSvgElement || ! gTransformData ) {
            return;
        }

        var pixelsPerSvgUnit = Hi.svgUtils.getPixelsPerSvgUnit( gSvgElement );
        var deltaSvgUnits = {
            x: ( lastEvent.clientX - startEvent.clientX ) / pixelsPerSvgUnit.scaleX,
            y: ( lastEvent.clientY - startEvent.clientY ) / pixelsPerSvgUnit.scaleX,
        };

        var newX = gTransformData.start.viewBox.x - deltaSvgUnits.x;
        var newY = gTransformData.start.viewBox.y - deltaSvgUnits.y;

        adjustViewBox(
            gTransformData.start.viewBox,
            gTransformData.start.viewBox.width,
            gTransformData.start.viewBox.height,
            newX,
            newY
        );
    }

    /* ==================== */
    /* Zoom                 */
    /* ==================== */

    function zoom( scaleFactor ) {
        var currentViewBox = Hi.svgUtils.getSvgViewBox( gSvgElement );
        var newWidth = scaleFactor * currentViewBox.width;
        var newHeight = scaleFactor * currentViewBox.height;
        adjustViewBox( currentViewBox, newWidth, newHeight );
    }

    function zoomIn() {
        var scaleFactor = 1.0 / ( 1.0 + ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 ) );
        zoom( scaleFactor );
        debouncedSave();
    }

    function zoomOut() {
        var scaleFactor = 1.0 + ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
        zoom( scaleFactor );
        debouncedSave();
    }

    /* ==================== */
    /* ViewBox Adjustment   */
    /* ==================== */

    function adjustViewBox( initialViewBox, newWidth, newHeight, newX, newY ) {
        if ( ! gSvgElement ) { return; }

        /* Adjust aspect ratio to match container. */
        var areaElement = $( gConfig.areaSelector )[0];
        if ( areaElement ) {
            var containerRect = areaElement.getBoundingClientRect();
            var containerAspectRatio = containerRect.width / containerRect.height;
            var newAspectRatio = newWidth / newHeight;

            if ( newAspectRatio > containerAspectRatio ) {
                newHeight = newWidth / containerAspectRatio;
            } else if ( newAspectRatio < containerAspectRatio ) {
                newWidth = newHeight * containerAspectRatio;
            }
        }

        /* Clamp within extents. */
        var extents = Hi.svgUtils.getExtentsSvgViewBox( gSvgElement );
        if ( extents && extents.width ) {
            newWidth = Math.min( newWidth, extents.width );
            newHeight = Math.min( newHeight, extents.height );

            /* Center if no explicit position. */
            if ( newX === undefined || newX === null ) {
                newX = initialViewBox.x + ( initialViewBox.width - newWidth ) / 2.0;
            }
            if ( newY === undefined || newY === null ) {
                newY = initialViewBox.y + ( initialViewBox.height - newHeight ) / 2.0;
            }

            /* Clamp position within extents. */
            if ( newX < extents.x ) {
                newX = extents.x;
            }
            if ( newY < extents.y ) {
                newY = extents.y;
            }
            if ( ( newX + newWidth ) > ( extents.x + extents.width ) ) {
                newX = extents.x + extents.width - newWidth;
            }
            if ( ( newY + newHeight ) > ( extents.y + extents.height ) ) {
                newY = extents.y + extents.height - newHeight;
            }
        } else {
            if ( newX === undefined || newX === null ) {
                newX = initialViewBox.x + ( initialViewBox.width - newWidth ) / 2.0;
            }
            if ( newY === undefined || newY === null ) {
                newY = initialViewBox.y + ( initialViewBox.height - newHeight ) / 2.0;
            }
        }

        Hi.svgUtils.setSvgViewBox( gSvgElement, newX, newY, newWidth, newHeight );
    }

    /* ==================== */
    /* Utilities            */
    /* ==================== */

    function isEventInArea( event ) {
        if ( ! gConfig || ! gConfig.areaSelector ) {
            return true;
        }
        /* For keyboard events, check if last pointer position is within the area. */
        if ( event.type === 'keydown' || event.type === 'keyup' ) {
            var $area = $( gConfig.areaSelector );
            if ( $area.length === 0 ) { return false; }
            var offset = $area.offset();
            var width = $area.outerWidth();
            var height = $area.outerHeight();
            return ( gLastPointerPosition.x >= offset.left
                     && gLastPointerPosition.x <= ( offset.left + width )
                     && gLastPointerPosition.y >= offset.top
                     && gLastPointerPosition.y <= ( offset.top + height ) );
        }
        return $( event.target ).closest( gConfig.areaSelector ).length > 0;
    }

    function debouncedSave() {
        if ( ! gConfig || ! gConfig.onSave ) {
            return;
        }
        if ( gConfig.shouldSave && ! gConfig.shouldSave() ) {
            return;
        }
        clearTimeout( saveDebounceTimer );
        saveDebounceTimer = setTimeout(function() {
            if ( gSvgElement ) {
                var viewBoxStr = $( gSvgElement ).attr( 'viewBox' );
                gConfig.onSave( viewBoxStr );
            }
            lastSaveTime = Date.now();
        }, ZOOM_SAVE_DEBOUNCE_MS );
    }

})();
