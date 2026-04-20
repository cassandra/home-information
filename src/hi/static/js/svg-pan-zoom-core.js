/*
  SVG Pan/Zoom Core

  Provides viewBox-based pan and zoom for an SVG element, with optional
  canvas rotation and scale-mode support.
  Initialized with a configuration object. See DEFAULT_CONFIG for all
  available options and their defaults.
*/

(function() {

    window.Hi = window.Hi || {};
    window.Hi.svgUtils = window.Hi.svgUtils || {};

    var MODULE_NAME = 'svg-pan-zoom-core';

    var KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    var KEYPRESS_ROTATE_DEGREES = 10.0;
    var MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    var MOUSE_WHEEL_ROTATE_ANGLE = 3.0;
    var SINGLE_POINTER_SCALE_FACTOR = 250.0;
    var SINGLE_POINTER_ROTATE_FACTOR = 0.5;
    var DOUBLE_POINTER_SCALE_FACTOR = 250.0;
    var DOUBLE_POINTER_ROTATE_FACTOR = 0.5;
    var ZOOM_SAVE_DEBOUNCE_MS = 400;

    var SCALE_KEY = 's';
    var ROTATE_KEY = 'r';

    var SvgTransformType = {
        MOVE: 'move',
        SCALE: 'scale',
        ROTATE: 'rotate',
    };

    var DEFAULT_CONFIG = {
        baseSvgSelector: null,          /* CSS selector for the target SVG element */
        areaSelector: null,             /* CSS selector for the container area */
        onSave: null,                   /* function(saveData) — called after changes */
        shouldSave: null,               /* function() — return true to enable saving */
        enableCanvasRotation: false,    /* enable S/R key modes for scale and rotation */
    };

    var gConfig = null;
    var gSvgElement = null;
    var gTransformType = SvgTransformType.MOVE;
    var gTransformData = null;
    var gIgnoreClick = false;
    var gLastPointerPosition = { x: 0, y: 0 };

    var saveDebounceTimer = null;
    var lastSaveTime = 0;

    var HiSvgPanZoomCore = {

        init: function( config ) {
            gConfig = $.extend( {}, DEFAULT_CONFIG, config );
            gSvgElement = $( gConfig.baseSvgSelector )[0] || null;
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

            if ( gConfig.enableCanvasRotation && gTransformType === SvgTransformType.SCALE ) {
                updateScaleFromPointerMove( lastEvent );
            } else if ( gConfig.enableCanvasRotation && gTransformType === SvgTransformType.ROTATE ) {
                updateRotateFromPointerMove( startEvent, lastEvent );
            } else {
                updatePan( startEvent, lastEvent );
            }

            gTransformData.last = { x: lastEvent.clientX, y: lastEvent.clientY };
            return true;
        },

        handleSinglePointerEventEnd: function() {
            if ( ! gTransformData ) { return false; }

            var wasDragging = gTransformData.isDragging;

            if ( wasDragging ) {
                if ( gConfig.enableCanvasRotation && gTransformType === SvgTransformType.SCALE ) {
                    endScale();
                } else if ( gConfig.enableCanvasRotation && gTransformType === SvgTransformType.ROTATE ) {
                    endRotation();
                } else {
                    debouncedSave();
                }
                gIgnoreClick = true;
            }

            gTransformData = null;

            if ( wasDragging ) {
                return true;
            }
            return false;
        },

        handleDoublePointerEventStart: function( doublePointerEvent ) {
            if ( ! gSvgElement ) { return false; }

            var svgViewBox = Hi.svgUtils.getSvgViewBox( gSvgElement );
            gTransformData = {
                isDragging: false,
                start: {
                    x: doublePointerEvent.start.event.clientX,
                    y: doublePointerEvent.start.event.clientY,
                    viewBox: svgViewBox,
                },
                last: {
                    x: doublePointerEvent.start.event.clientX,
                    y: doublePointerEvent.start.event.clientY,
                },
            };
            return true;
        },

        handleDoublePointerEventMove: function( doublePointerEvent ) {
            if ( ! gTransformData ) { return false; }

            var scaleFactor = 1.0 - ( doublePointerEvent.deltaDistancePrevious
                                      / DOUBLE_POINTER_SCALE_FACTOR );
            zoom( scaleFactor );

            if ( gConfig.enableCanvasRotation ) {
                var deltaAngle = doublePointerEvent.deltaAnglePrevious * DOUBLE_POINTER_ROTATE_FACTOR;
                rotateCanvas( deltaAngle );
            }
            return true;
        },

        handleDoublePointerEventEnd: function( doublePointerEvent ) {
            if ( ! gTransformData ) { return false; }
            debouncedSave();
            if ( gConfig.enableCanvasRotation ) {
                abortScale();
                abortRotation();
            }
            gTransformData = null;
            return true;
        },

        handleMouseWheel: function( event ) {
            if ( ! gSvgElement ) { return false; }
            if ( ! isEventInArea( event ) ) { return false; }

            if ( gConfig.enableCanvasRotation && gTransformType === SvgTransformType.ROTATE ) {
                rotateFromMouseWheel( event );
            } else {
                if ( gConfig.enableCanvasRotation ) {
                    abortScale();
                    abortRotation();
                }
                var e = event.originalEvent || event;
                var scaleFactor = 1.0 - ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
                if ( e.deltaY > 0 ) {
                    scaleFactor = 1.0 + ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
                }
                zoom( scaleFactor );
            }
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

            if ( gConfig.enableCanvasRotation && event.key === SCALE_KEY ) {
                abortRotation();
                startScale();
                event.preventDefault();
                event.stopImmediatePropagation();
                return true;

            } else if ( gConfig.enableCanvasRotation && event.key === ROTATE_KEY ) {
                abortScale();
                startRotation();
                event.preventDefault();
                event.stopImmediatePropagation();
                return true;

            } else if ( event.key === '+' || event.key === '=' ) {
                if ( gConfig.enableCanvasRotation && gTransformType === SvgTransformType.ROTATE ) {
                    rotateRightFromKeypress();
                } else {
                    zoomIn();
                }
                event.preventDefault();
                event.stopImmediatePropagation();
                return true;

            } else if ( event.key === '-' ) {
                if ( gConfig.enableCanvasRotation && gTransformType === SvgTransformType.ROTATE ) {
                    rotateLeftFromKeypress();
                } else {
                    zoomOut();
                }
                event.preventDefault();
                event.stopImmediatePropagation();
                return true;

            } else if ( gConfig.enableCanvasRotation && event.key === 'Escape' ) {
                abortScale();
                abortRotation();
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

        isDragging: function() {
            return gTransformData && gTransformData.isDragging;
        },

        getRotationAngle: function() {
            if ( ! gSvgElement ) { return 0; }
            var transform = $( gSvgElement ).attr( 'transform' ) || '';
            var parsed = Hi.svgUtils.getSvgTransformValues( transform );
            return parsed.rotate.angle;
        },
    };

    window.Hi.SvgPanZoomCore = HiSvgPanZoomCore;

    /* ==================== */
    /* Pan                  */
    /* ==================== */

    function updatePan( startEvent, lastEvent ) {
        if ( ! gSvgElement || ! gTransformData ) { return; }

        var pixelsPerSvgUnit = Hi.svgUtils.getPixelsPerSvgUnit( gSvgElement );
        var deltaSvgUnits = {
            x: ( lastEvent.clientX - startEvent.clientX ) / pixelsPerSvgUnit.scaleX,
            y: ( lastEvent.clientY - startEvent.clientY ) / pixelsPerSvgUnit.scaleX,
        };

        /* Account for canvas rotation when panning. */
        if ( gConfig.enableCanvasRotation ) {
            var transform = $( gSvgElement ).attr( 'transform' ) || '';
            var parsed = Hi.svgUtils.getSvgTransformValues( transform );
            deltaSvgUnits = rotateVector( deltaSvgUnits, -1.0 * parsed.rotate.angle );
        }

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
    /* Canvas Scale Mode    */
    /* ==================== */

    function startScale() {
        gTransformType = SvgTransformType.SCALE;
        $( gSvgElement ).attr( 'action-state', gTransformType );
    }

    function updateScaleFromPointerMove( event ) {
        if ( ! gTransformData ) { return; }

        var screenCenter = Hi.getScreenCenterPoint( gSvgElement );
        var startVector = {
            x: gTransformData.start.x - screenCenter.x,
            y: gTransformData.start.y - screenCenter.y,
        };
        var endVector = {
            x: event.clientX - screenCenter.x,
            y: event.clientY - screenCenter.y,
        };
        var startDistance = Math.sqrt( startVector.x * startVector.x + startVector.y * startVector.y );
        var endDistance = Math.sqrt( endVector.x * endVector.x + endVector.y * endVector.y );
        var delta = endDistance - startDistance;

        var scaleFactor = 1.0 - ( delta / SINGLE_POINTER_SCALE_FACTOR );
        var currentViewBox = gTransformData.start.viewBox;
        var newWidth = scaleFactor * currentViewBox.width;
        var newHeight = scaleFactor * currentViewBox.height;
        adjustViewBox( currentViewBox, newWidth, newHeight );
    }

    function endScale() {
        gTransformType = SvgTransformType.MOVE;
        $( gSvgElement ).attr( 'action-state', '' );
        debouncedSave();
    }

    function abortScale() {
        if ( gTransformType !== SvgTransformType.SCALE ) { return; }
        gTransformType = SvgTransformType.MOVE;
        gTransformData = null;
        $( gSvgElement ).attr( 'action-state', '' );
    }

    /* ==================== */
    /* Canvas Rotation      */
    /* ==================== */

    function startRotation() {
        gTransformType = SvgTransformType.ROTATE;
        $( gSvgElement ).attr( 'action-state', gTransformType );
    }

    function rotateCanvas( deltaAngle ) {
        var transform = $( gSvgElement ).attr( 'transform' ) || '';
        var parsed = Hi.svgUtils.getSvgTransformValues( transform );
        var newAngle = Hi.normalizeAngle( parsed.rotate.angle + deltaAngle );
        var newTransform = 'rotate(' + newAngle + ', ' + parsed.rotate.cx + ', ' + parsed.rotate.cy + ')';
        $( gSvgElement ).attr( 'transform', newTransform );

        /* CSS transform for browser rendering compatibility. */
        gSvgElement.style.transform = 'rotate(' + newAngle + 'deg)';
    }

    function updateRotateFromPointerMove( startEvent, lastEvent ) {
        var screenCenter = Hi.getScreenCenterPoint( gSvgElement );
        var deltaAngle = Hi.getRotationAngle(
            screenCenter.x, screenCenter.y,
            gTransformData.last.x, gTransformData.last.y,
            lastEvent.clientX, lastEvent.clientY
        );
        deltaAngle *= SINGLE_POINTER_ROTATE_FACTOR;
        rotateCanvas( deltaAngle );
    }

    function rotateFromMouseWheel( event ) {
        var e = event.originalEvent || event;
        var deltaAngle = MOUSE_WHEEL_ROTATE_ANGLE;
        if ( e.deltaY > 0 ) {
            deltaAngle *= -1.0;
        }
        rotateCanvas( deltaAngle );
    }

    function rotateRightFromKeypress() {
        rotateCanvas( KEYPRESS_ROTATE_DEGREES );
        debouncedSave();
    }

    function rotateLeftFromKeypress() {
        rotateCanvas( -1.0 * KEYPRESS_ROTATE_DEGREES );
        debouncedSave();
    }

    function endRotation() {
        gTransformType = SvgTransformType.MOVE;
        $( gSvgElement ).attr( 'action-state', '' );
        debouncedSave();
    }

    function abortRotation() {
        if ( gTransformType !== SvgTransformType.ROTATE ) { return; }
        gTransformType = SvgTransformType.MOVE;
        gTransformData = null;
        $( gSvgElement ).attr( 'action-state', '' );
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

        /* Clamp within extents, accounting for canvas rotation if enabled. */
        var extents = Hi.svgUtils.getExtentsSvgViewBox( gSvgElement );
        if ( extents && extents.width ) {
            if ( gConfig.enableCanvasRotation ) {
                var transform = $( gSvgElement ).attr( 'transform' ) || '';
                var parsed = Hi.svgUtils.getSvgTransformValues( transform );
                extents = calculateRotatedRectangle( extents, parsed.rotate.angle );
            }

            newWidth = Math.min( newWidth, extents.width );
            newHeight = Math.min( newHeight, extents.height );

            if ( newX === undefined || newX === null ) {
                newX = initialViewBox.x + ( initialViewBox.width - newWidth ) / 2.0;
            }
            if ( newY === undefined || newY === null ) {
                newY = initialViewBox.y + ( initialViewBox.height - newHeight ) / 2.0;
            }

            if ( newX < extents.x ) { newX = extents.x; }
            if ( newY < extents.y ) { newY = extents.y; }
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
    /* Rotation Geometry    */
    /* ==================== */

    function calculateRotatedRectangle( rect, rotationAngle ) {
        var corners = [
            { x: rect.x, y: rect.y },
            { x: rect.x + rect.width, y: rect.y },
            { x: rect.x, y: rect.y + rect.height },
            { x: rect.x + rect.width, y: rect.y + rect.height },
        ];

        var centerX = rect.x + ( rect.width / 2.0 );
        var centerY = rect.y + ( rect.height / 2.0 );
        var radians = ( Math.PI / 180 ) * rotationAngle;

        var rotatedCorners = corners.map( function( corner ) {
            var dx = corner.x - centerX;
            var dy = corner.y - centerY;
            return {
                x: centerX + ( dx * Math.cos( radians ) - dy * Math.sin( radians ) ),
                y: centerY + ( dx * Math.sin( radians ) + dy * Math.cos( radians ) ),
            };
        });

        var minX = Math.min.apply( null, rotatedCorners.map( function( c ) { return c.x; } ) );
        var minY = Math.min.apply( null, rotatedCorners.map( function( c ) { return c.y; } ) );
        var maxX = Math.max.apply( null, rotatedCorners.map( function( c ) { return c.x; } ) );
        var maxY = Math.max.apply( null, rotatedCorners.map( function( c ) { return c.y; } ) );

        return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
    }

    function rotateVector( point, rotationAngle ) {
        var radians = ( Math.PI / 180 ) * rotationAngle;
        return {
            x: point.x * Math.cos( radians ) - point.y * Math.sin( radians ),
            y: point.x * Math.sin( radians ) + point.y * Math.cos( radians ),
        };
    }

    /* ==================== */
    /* Utilities            */
    /* ==================== */

    function isEventInArea( event ) {
        if ( ! gConfig || ! gConfig.areaSelector ) {
            return true;
        }
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
        if ( ! gConfig || ! gConfig.onSave ) { return; }
        if ( gConfig.shouldSave && ! gConfig.shouldSave() ) { return; }

        clearTimeout( saveDebounceTimer );
        saveDebounceTimer = setTimeout( function() {
            if ( ! gSvgElement ) { return; }
            var viewBoxStr = $( gSvgElement ).attr( 'viewBox' );
            var saveData = { viewBoxStr: viewBoxStr };

            if ( gConfig.enableCanvasRotation ) {
                var transform = $( gSvgElement ).attr( 'transform' ) || '';
                var parsed = Hi.svgUtils.getSvgTransformValues( transform );
                saveData.rotationAngle = parsed.rotate.angle;
            }

            gConfig.onSave( saveData );
            lastSaveTime = Date.now();
        }, ZOOM_SAVE_DEBOUNCE_MS );
    }

})();
