/*
  SVG Icon Core

  Provides drag/scale/rotate editing for positioned SVG icon elements.
  Initialized with a configuration object that specifies how to identify
  icon elements, what to do on selection, and how to persist changes.

  Usage:
    Hi.SvgIconCore.init({
        identifyElement: function(event) { ... },
        onSelect: function(element) { ... },
        onDeselect: function() { ... },
        onSave: function(element, positionData) { ... },
        baseSvgSelector: '#my-svg',
        areaSelector: '#my-container',
        highlightClass: 'highlighted',
    });
*/

(function() {

    window.Hi = window.Hi || {};
    window.Hi.svgUtils = window.Hi.svgUtils || {};

    const MODULE_NAME = 'svg-icon-core';

    const ICON_ACTION_SCALE_KEY = 's';
    const ICON_ACTION_ROTATE_KEY = 'r';
    const ICON_ACTION_ZOOM_IN_KEY = '+';
    const ICON_ACTION_ZOOM_OUT_KEY = '-';

    const POINTER_EVENTS_SCALE_FACTOR = 250.0;
    const POINTER_EVENTS_ROTATE_FACTOR = 0.1;
    const POINTER_MOVE_ZOOM_SCALE_FACTOR = 175.0;
    const KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const MOUSE_WHEEL_ROTATE_DEGREES = 10.0;
    const KEYPRESS_ROTATE_DEGREES = 10.0;
    const SAVE_DEBOUNCE_MS = 400;

    const SvgActionStateType = {
        MOVE: 'move',
        SCALE: 'scale',
        ROTATE: 'rotate',
    };

    let gConfig = null;
    let gActionState = SvgActionStateType.MOVE;
    let gSelectedGroup = null;
    let gDragData = null;
    let gActionEditData = null;
    let gLastPointerPosition = { x: 0, y: 0 };
    let gIgnoreClick = false;

    let saveDebounceTimer = null;

    const HiSvgIconCore = {

        init: function( config ) {
            gConfig = config;
        },

        handleSinglePointerEventStart: function( singlePointerEvent ) {
            if ( gActionEditData ) {
                if ( gActionState === SvgActionStateType.SCALE ) {
                    gActionEditData.isScaling = true;
                } else if ( gActionState === SvgActionStateType.ROTATE ) {
                    gActionEditData.isRotating = true;
                }
                return true;
            }

            var element = gConfig.identifyElement( singlePointerEvent.start.event );
            if ( element ) {
                var $element = $( element );
                if ( ! gSelectedGroup || $element.attr('id') !== $( gSelectedGroup ).attr('id') ) {
                    clearSelection();
                    gSelectedGroup = element;
                }
                startDrag( singlePointerEvent, $element );
                return true;
            }
            return false;
        },

        handleSinglePointerEventMove: function( singlePointerEvent ) {
            var handled = false;

            if ( gActionEditData ) {
                if ( gActionEditData.isScaling ) {
                    updateScaleFromPointerMove( singlePointerEvent );
                    handled = true;
                } else if ( gActionEditData.isRotating ) {
                    updateRotateFromPointerMove( singlePointerEvent );
                    handled = true;
                }
            }

            if ( gDragData ) {
                gDragData.isDragging = true;
                setActionStateAttr( SvgActionStateType.MOVE );
                updateDrag( singlePointerEvent );
                handled = true;
            }
            return handled;
        },

        handleSinglePointerEventEnd: function( singlePointerEvent ) {
            return endSinglePointerEvent();
        },

        handleDoublePointerEventStart: function( doublePointerEvent ) {
            if ( ! gSelectedGroup ) { return false; }
            endSinglePointerEvent();
            return true;
        },

        handleDoublePointerEventMove: function( doublePointerEvent ) {
            if ( ! gSelectedGroup ) { return false; }

            var scaleMultiplier = 1.0 + ( doublePointerEvent.deltaDistancePrevious
                                          / POINTER_EVENTS_SCALE_FACTOR );
            var deltaAngle = doublePointerEvent.deltaAngleStart * POINTER_EVENTS_ROTATE_FACTOR;

            updateScale( gSelectedGroup, scaleMultiplier );
            updateRotate( gSelectedGroup, deltaAngle );
            return true;
        },

        handleDoublePointerEventEnd: function( doublePointerEvent ) {
            if ( ! gSelectedGroup ) { return false; }
            debouncedSave( gSelectedGroup );
            return true;
        },

        handleLastPointerLocation: function( x, y ) {
            gLastPointerPosition.x = x;
            gLastPointerPosition.y = y;
        },

        handleMouseWheel: function( event ) {
            if ( gDragData ) { return false; }

            if ( gActionEditData ) {
                if ( gActionState === SvgActionStateType.SCALE ) {
                    updateScaleFromMouseWheel( event );
                    return true;
                } else if ( gActionState === SvgActionStateType.ROTATE ) {
                    updateRotateFromMouseWheel( event );
                    return true;
                }
            }
            return false;
        },

        handleClick: function( event ) {
            if ( gIgnoreClick ) {
                gIgnoreClick = false;
                return true;
            }
            gIgnoreClick = false;

            var element = gConfig.identifyElement( event );
            if ( element ) {
                handleIconClick( event, element );
                return true;
            }
            return false;
        },

        handleKeyDown: function( event ) {
            if ( $( event.target ).is( 'input, textarea' ) ) { return false; }
            if ( $( event.target ).closest( '.modal' ).length > 0 ) { return false; }

            if ( ! gSelectedGroup ) { return false; }
            if ( ! isPointerInArea() ) { return false; }

            if ( event.key === ICON_ACTION_SCALE_KEY ) {
                rotateAbort();
                startScale();

            } else if ( event.key === ICON_ACTION_ROTATE_KEY ) {
                scaleAbort();
                startRotate();

            } else if ( event.key === ICON_ACTION_ZOOM_IN_KEY || event.key === '=' ) {
                if ( gActionState === SvgActionStateType.SCALE ) {
                    scaleUpFromKeypress();
                } else if ( gActionState === SvgActionStateType.ROTATE ) {
                    rotateRightFromKeypress();
                }

            } else if ( event.key === ICON_ACTION_ZOOM_OUT_KEY ) {
                if ( gActionState === SvgActionStateType.SCALE ) {
                    scaleDownFromKeypress();
                } else if ( gActionState === SvgActionStateType.ROTATE ) {
                    rotateLeftFromKeypress();
                }

            } else if ( event.key === 'Escape' ) {
                scaleAbort();
                rotateAbort();
                gActionState = SvgActionStateType.MOVE;
                setActionStateAttr( '' );
                clearSelection();
            } else {
                return false;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
            return true;
        },

        clearSelection: function() {
            clearSelection();
        },

        hasSelection: function() {
            return gSelectedGroup !== null;
        },
    };

    window.Hi.SvgIconCore = HiSvgIconCore;

    /* ==================== */
    /* Selection            */
    /* ==================== */

    function handleIconClick( event, element ) {
        clearSelection();
        gSelectedGroup = element;
        $( element ).addClass( gConfig.highlightClass || 'highlighted' );
        gActionState = SvgActionStateType.MOVE;
        if ( gConfig.onSelect ) {
            gConfig.onSelect( element );
        }
    }

    function clearSelection() {
        if ( gSelectedGroup ) {
            $( gSelectedGroup ).removeClass( gConfig.highlightClass || 'highlighted' );
            gSelectedGroup = null;
            if ( gConfig.onDeselect ) {
                gConfig.onDeselect();
            }
        }
    }

    /* ==================== */
    /* Drag                 */
    /* ==================== */

    function startDrag( singlePointerEvent, $element ) {
        var baseSvgElement = $( gConfig.baseSvgSelector );

        var transform = $element.attr( 'transform' ) || '';
        var parsed = Hi.svgUtils.getSvgTransformValues( transform );
        var cursorSvgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement,
                                                      singlePointerEvent.last.x,
                                                      singlePointerEvent.last.y );

        var cursorSvgOffset = {
            x: ( cursorSvgPoint.x / parsed.scale.x ) - parsed.translate.x,
            y: ( cursorSvgPoint.y / parsed.scale.y ) - parsed.translate.y,
        };

        gDragData = {
            element: $element,
            baseSvgElement: baseSvgElement,
            cursorSvgOffset: cursorSvgOffset,
            originalSvgScale: parsed.scale,
            originalSvgRotate: parsed.rotate,
            isDragging: false,
        };
    }

    function updateDrag( singlePointerEvent ) {
        if ( ! gDragData ) { return; }

        var cursorSvgPoint = Hi.svgUtils.toSvgPoint( gDragData.baseSvgElement,
                                                      singlePointerEvent.last.x,
                                                      singlePointerEvent.last.y );

        var scale = gDragData.originalSvgScale;
        var rotate = gDragData.originalSvgRotate;
        var translate = {
            x: ( cursorSvgPoint.x / scale.x ) - gDragData.cursorSvgOffset.x,
            y: ( cursorSvgPoint.y / scale.y ) - gDragData.cursorSvgOffset.y,
        };

        setSvgTransformAttr( gDragData.element, scale, translate, rotate );
    }

    function endDrag() {
        if ( ! gDragData ) { return; }
        debouncedSave( gDragData.element );
        gDragData = null;
    }

    /* ==================== */
    /* Pointer Event End    */
    /* ==================== */

    function endSinglePointerEvent() {
        if ( gActionEditData ) {
            if ( gActionState === SvgActionStateType.SCALE ) {
                gActionEditData.isScaling = false;
                endScale();
            } else if ( gActionState === SvgActionStateType.ROTATE ) {
                gActionEditData.isRotating = false;
                endRotate();
            }
            gActionState = SvgActionStateType.MOVE;
            setActionStateAttr( '' );
            gActionEditData = null;
            gIgnoreClick = true;
            return true;
        }

        if ( gDragData ) {
            if ( gDragData.isDragging ) {
                endDrag();
                gIgnoreClick = true;
                setActionStateAttr( '' );
            }
            gDragData = null;
            return true;
        }
        return false;
    }

    /* ==================== */
    /* Scale                */
    /* ==================== */

    function startScale() {
        startIconAction( SvgActionStateType.SCALE );
    }

    function updateScaleFromMouseWheel( event ) {
        var e = event.originalEvent || event;
        var scaleMultiplier = 1.0 + ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
        if ( e.deltaY > 0 ) {
            scaleMultiplier = 1.0 - ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
        }
        updateScale( gActionEditData.element, scaleMultiplier );
        debouncedSave( gSelectedGroup );
    }

    function scaleUpFromKeypress() {
        if ( gSelectedGroup ) {
            var scaleMultiplier = 1.0 + ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
            updateScale( gSelectedGroup, scaleMultiplier );
            debouncedSave( gSelectedGroup );
        }
    }

    function scaleDownFromKeypress() {
        if ( gSelectedGroup ) {
            var scaleMultiplier = 1.0 - ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
            updateScale( gSelectedGroup, scaleMultiplier );
            debouncedSave( gSelectedGroup );
        }
    }

    function updateScaleFromPointerMove( singlePointerEvent ) {
        var center = Hi.getScreenCenterPoint( gActionEditData.element );
        var startX = singlePointerEvent.previous.x;
        var startY = singlePointerEvent.previous.y;
        var endX = singlePointerEvent.last.x;
        var endY = singlePointerEvent.last.y;
        var startDistance = Math.sqrt( Math.pow( startX - center.x, 2 ) + Math.pow( startY - center.y, 2 ) );
        var endDistance = Math.sqrt( Math.pow( endX - center.x, 2 ) + Math.pow( endY - center.y, 2 ) );
        var moveDistance = Math.abs( endDistance - startDistance );

        var scaleMultiplier = 1.0;
        if ( endDistance > startDistance ) {
            scaleMultiplier = Math.pow( 2, moveDistance / POINTER_MOVE_ZOOM_SCALE_FACTOR );
        } else {
            scaleMultiplier = Math.pow( 2, -1.0 * moveDistance / POINTER_MOVE_ZOOM_SCALE_FACTOR );
        }

        updateScale( gActionEditData.element, scaleMultiplier );
    }

    function updateScale( svgElement, scaleMultiplier ) {
        var transformStr = $( svgElement ).attr( 'transform' );
        var oldTransform = Hi.svgUtils.getSvgTransformValues( transformStr );
        var newScale = {
            x: oldTransform.scale.x * scaleMultiplier,
            y: oldTransform.scale.y * scaleMultiplier,
        };
        var newTranslate = {
            x: oldTransform.translate.x * oldTransform.scale.x / newScale.x,
            y: oldTransform.translate.y * oldTransform.scale.y / newScale.y,
        };

        setSvgTransformAttr( svgElement, newScale, newTranslate, oldTransform.rotate );
    }

    function endScale() {
        savePosition( gActionEditData.element );
    }

    function scaleAbort() {
        if ( gActionState !== SvgActionStateType.SCALE ) { return; }
        endIconAction();
    }

    /* ==================== */
    /* Rotate               */
    /* ==================== */

    function startRotate() {
        startIconAction( SvgActionStateType.ROTATE );
    }

    function updateRotateFromPointerMove( singlePointerEvent ) {
        var center = Hi.getScreenCenterPoint( gActionEditData.element );
        var deltaAngle = Hi.getRotationAngle( center.x, center.y,
                                               singlePointerEvent.previous.x, singlePointerEvent.previous.y,
                                               singlePointerEvent.last.x, singlePointerEvent.last.y );

        var transformStr = $( gActionEditData.element ).attr( 'transform' );
        var oldTransform = Hi.svgUtils.getSvgTransformValues( transformStr );

        var newRotate = { angle: oldTransform.rotate.angle + deltaAngle,
                          cx: oldTransform.rotate.cx,
                          cy: oldTransform.rotate.cy };
        newRotate.angle = Hi.normalizeAngle( newRotate.angle );

        setSvgTransformAttr( gActionEditData.element,
                             oldTransform.scale, oldTransform.translate, newRotate );
    }

    function updateRotateFromMouseWheel( event ) {
        var e = event.originalEvent || event;
        var deltaAngle = MOUSE_WHEEL_ROTATE_DEGREES;
        if ( e.deltaY > 0 ) {
            deltaAngle = -1.0 * MOUSE_WHEEL_ROTATE_DEGREES;
        }
        updateRotate( gActionEditData.element, deltaAngle );
        debouncedSave( gSelectedGroup );
    }

    function rotateRightFromKeypress() {
        updateRotate( gSelectedGroup, KEYPRESS_ROTATE_DEGREES );
        debouncedSave( gSelectedGroup );
    }

    function rotateLeftFromKeypress() {
        updateRotate( gSelectedGroup, -1.0 * KEYPRESS_ROTATE_DEGREES );
        debouncedSave( gSelectedGroup );
    }

    function updateRotate( svgElement, deltaAngle ) {
        var transformStr = $( svgElement ).attr( 'transform' );
        var oldTransform = Hi.svgUtils.getSvgTransformValues( transformStr );

        var newRotate = { angle: oldTransform.rotate.angle + deltaAngle,
                          cx: oldTransform.rotate.cx,
                          cy: oldTransform.rotate.cy };
        newRotate.angle = Hi.normalizeAngle( newRotate.angle );

        setSvgTransformAttr( svgElement,
                             oldTransform.scale, oldTransform.translate, newRotate );
    }

    function endRotate() {
        savePosition( gActionEditData.element );
    }

    function rotateAbort() {
        if ( gActionState !== SvgActionStateType.ROTATE ) { return; }
        endIconAction();
    }

    /* ==================== */
    /* Action Helpers       */
    /* ==================== */

    function startIconAction( actionState ) {
        if ( ! gSelectedGroup ) { return; }

        var transform = $( gSelectedGroup ).attr( 'transform' );
        var parsed = Hi.svgUtils.getSvgTransformValues( transform );

        gActionEditData = {
            element: gSelectedGroup,
            scaleStart: parsed.scale,
            translateStart: parsed.translate,
            rotateStart: parsed.rotate,
            isScaling: false,
            isRotating: false,
        };

        gActionState = actionState;
        setActionStateAttr( actionState );
    }

    function endIconAction() {
        gActionEditData = null;
    }

    function setActionStateAttr( actionState ) {
        if ( gConfig && gConfig.baseSvgSelector ) {
            $( gConfig.baseSvgSelector ).attr( 'action-state', actionState || '' );
        }
    }

    /* ==================== */
    /* Transform            */
    /* ==================== */

    function setSvgTransformAttr( element, scale, translate, rotate ) {
        var newTransform = 'scale(' + scale.x + ' ' + scale.y + ') '
                         + 'translate(' + translate.x + ', ' + translate.y + ') '
                         + 'rotate(' + rotate.angle + ', ' + rotate.cx + ', ' + rotate.cy + ')';
        $( element ).attr( 'transform', newTransform );
    }

    /* ==================== */
    /* Save                 */
    /* ==================== */

    function savePosition( element ) {
        if ( ! gConfig || ! gConfig.onSave ) { return; }

        var transform = $( element ).attr( 'transform' );
        var parsed = Hi.svgUtils.getSvgTransformValues( transform );
        var baseSvgElement = $( gConfig.baseSvgSelector );
        var center = Hi.svgUtils.getSvgCenterPoint( element, baseSvgElement );

        var positionData = {
            svg_x: center.x,
            svg_y: center.y,
            svg_scale: parsed.scale.x,
            svg_rotate: parsed.rotate.angle,
        };
        gConfig.onSave( element, positionData );
    }

    function debouncedSave( element ) {
        clearTimeout( saveDebounceTimer );
        saveDebounceTimer = setTimeout( function() {
            savePosition( element );
        }, SAVE_DEBOUNCE_MS );
    }

    /* ==================== */
    /* Utilities            */
    /* ==================== */

    function isPointerInArea() {
        if ( ! gConfig || ! gConfig.areaSelector ) { return true; }
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

})();
