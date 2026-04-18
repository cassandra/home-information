/*
  Entity SVG Edit

  Thin wrapper layer that initializes the shared SVG core modules
  (svg-icon-core, svg-path-core, svg-pan-zoom-core) with entity-specific
  configuration: edit mode guards, API persistence, cross-module selection
  clearing, and non-edit-mode status view fetching.

  Exposes the same public API as the original entity editing modules
  (Hi.edit.icon, Hi.edit.path, Hi.location) so that
  svg-entity-event-listeners.js requires minimal changes.
*/

(function() {

    window.Hi = window.Hi || {};
    window.Hi.edit = window.Hi.edit || {};

    var API_EDIT_LOCATION_ITEM_POSITION_URL = '/location/edit/item/position';

    /* ==================== */
    /* Icon Editing Wrapper  */
    /* ==================== */

    var HiEditIcon = {

        init: function() {
            Hi.SvgIconCore.init({
                identifyElement: function( event ) {
                    var target = event.target || event.srcElement;
                    var group = $( target ).closest( 'g' );
                    if ( group.length > 0 ) {
                        var svgDataType = group.attr( Hi.DATA_TYPE_ATTR );
                        if ( svgDataType === Hi.DATA_TYPE_ICON_VALUE ) {
                            return group[0];
                        }
                    }
                    return null;
                },
                onSelect: function( element ) {
                    var svgItemId = $( element ).attr( 'id' );
                    Hi.SvgPathCore.clearSelection();
                    AN.get( Hi.API_LOCATION_ITEM_EDIT_MODE_URL + '/' + svgItemId );
                },
                onDeselect: function() {},
                onSave: function( element, positionData ) {
                    var svgItemId = $( element ).attr( 'id' );
                    AN.post( API_EDIT_LOCATION_ITEM_POSITION_URL + '/' + svgItemId,
                             positionData );
                },
                baseSvgSelector: Hi.BASE_SVG_SELECTOR,
                areaSelector: Hi.LOCATION_VIEW_AREA_SELECTOR,
                highlightClass: Hi.HIGHLIGHTED_CLASS,
                enableMirror: false,
            });

        },

        handleSinglePointerEventStart: function( singlePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleSinglePointerEventStart( singlePointerEvent );
        },
        handleSinglePointerEventMove: function( singlePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleSinglePointerEventMove( singlePointerEvent );
        },
        handleSinglePointerEventEnd: function( singlePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleSinglePointerEventEnd( singlePointerEvent );
        },

        handleDoublePointerEventStart: function( doublePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleDoublePointerEventStart( doublePointerEvent );
        },
        handleDoublePointerEventMove: function( doublePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleDoublePointerEventMove( doublePointerEvent );
        },
        handleDoublePointerEventEnd: function( doublePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleDoublePointerEventEnd( doublePointerEvent );
        },

        handleLastPointerLocation: function( x, y ) {
            Hi.SvgIconCore.handleLastPointerLocation( x, y );
        },
        handleMouseWheel: function( event ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleMouseWheel( event );
        },
        handleClick: function( event ) {
            if ( Hi.isEditMode ) {
                return Hi.SvgIconCore.handleClick( event );
            }

            /* Non-edit mode: fetch status view on icon click. */
            var group = $( event.target ).closest( 'g' );
            if ( group.length > 0 ) {
                var svgDataType = group.attr( Hi.DATA_TYPE_ATTR );
                if ( svgDataType === Hi.DATA_TYPE_ICON_VALUE ) {
                    var svgItemId = group.attr( 'id' );
                    if ( svgItemId ) {
                        AN.get( Hi.API_LOCATION_ITEM_STATUS_URL + '/' + svgItemId );
                        return true;
                    }
                }
            }
            return false;
        },
        handleKeyDown: function( event ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgIconCore.handleKeyDown( event );
        },

        hasSelection: function() {
            return Hi.SvgIconCore.hasSelection();
        },

        deleteSelectedElement: function() {
            Hi.SvgIconCore.deleteSelectedElement();
        },

        mirrorSelected: function() {
            Hi.SvgIconCore.mirrorSelected();
        },
    };

    window.Hi.edit.icon = HiEditIcon;
    HiEditIcon.init();

    /* ==================== */
    /* Path Editing Wrapper  */
    /* ==================== */

    var API_EDIT_SVG_PATH_URL = '/location/edit/item/path';

    var HiEditPath = {

        init: function() {
            Hi.SvgPathCore.init({
                identifyElement: function( event ) {
                    var target = event.target || event.srcElement;
                    var group = $( target ).closest( 'g' );
                    if ( group.length > 0 ) {
                        var svgDataType = group.attr( Hi.DATA_TYPE_ATTR );
                        if ( svgDataType === Hi.DATA_TYPE_PATH_VALUE ) {
                            return group[0];
                        }
                    }
                    return null;
                },
                onSelect: function( element ) {
                    var svgItemId = $( element ).attr( 'id' );
                    Hi.SvgIconCore.clearSelection();
                    AN.get( Hi.API_LOCATION_ITEM_EDIT_MODE_URL + '/' + svgItemId );
                },
                onDeselect: function() {},
                onSave: function( element, svgPathString ) {
                    var svgItemId = $( element ).attr( 'id' );
                    AN.post( API_EDIT_SVG_PATH_URL + '/' + svgItemId,
                             { svg_path: svgPathString } );
                },
                allowDeleteAll: false,
                onDeleteAll: null,
                baseSvgSelector: Hi.BASE_SVG_SELECTOR,
                highlightClass: Hi.HIGHLIGHTED_CLASS,
            });

        },

        handleSinglePointerEventStart: function( singlePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgPathCore.handleSinglePointerEventStart( singlePointerEvent );
        },
        handleSinglePointerEventMove: function( singlePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgPathCore.handleSinglePointerEventMove( singlePointerEvent );
        },
        handleSinglePointerEventEnd: function( singlePointerEvent ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgPathCore.handleSinglePointerEventEnd( singlePointerEvent );
        },

        handleClick: function( event ) {
            if ( Hi.isEditMode ) {
                return Hi.SvgPathCore.handleClick( event );
            }

            /* Non-edit mode: fetch status view on path click. */
            var group = $( event.target ).closest( 'g' );
            if ( group.length > 0 ) {
                var svgDataType = group.attr( Hi.DATA_TYPE_ATTR );
                if ( svgDataType === Hi.DATA_TYPE_PATH_VALUE ) {
                    var svgItemId = group.attr( 'id' );
                    if ( svgItemId ) {
                        AN.get( Hi.API_LOCATION_ITEM_STATUS_URL + '/' + svgItemId );
                        return true;
                    }
                }
            }
            return false;
        },
        handleKeyDown: function( event ) {
            if ( ! Hi.isEditMode ) { return false; }
            return Hi.SvgPathCore.handleKeyDown( event );
        },

        hasSelection: function() {
            return Hi.SvgPathCore.hasSelection();
        },

        deleteSelectedElement: function() {
            Hi.SvgPathCore.deleteSelectedElement();
        },

        PROXY_PATH_CONTAINER_ID: Hi.SvgPathCore.PROXY_PATH_CONTAINER_ID,
    };

    window.Hi.edit.path = HiEditPath;
    HiEditPath.init();

    /* ==================== */
    /* Pan/Zoom Wrapper      */
    /* ==================== */

    var LOCATION_VIEW_EDIT_PANE_SELECTOR = '#hi-location-view-edit';
    var API_EDIT_LOCATION_VIEW_GEOMETRY_URL = '/location/edit/view/geometry';

    var HiSvgLocation = {

        init: function() {
            Hi.SvgPanZoomCore.init({
                baseSvgSelector: Hi.BASE_SVG_SELECTOR,
                areaSelector: Hi.LOCATION_VIEW_AREA_SELECTOR,
                enableCanvasRotation: true,
                onSave: function( saveData ) {
                    var svgElement = $( Hi.BASE_SVG_SELECTOR )[0];
                    if ( ! svgElement ) { return; }
                    var locationViewId = $( svgElement ).attr( 'location-view-id' );
                    if ( ! locationViewId ) { return; }
                    var data = {
                        svg_view_box_str: saveData.viewBoxStr,
                        svg_rotate: saveData.rotationAngle || 0,
                    };
                    AN.post( API_EDIT_LOCATION_VIEW_GEOMETRY_URL + '/' + locationViewId, data );
                },
                shouldSave: function() {
                    return ( Hi.isEditMode
                             && $( Hi.BASE_SVG_SELECTOR ).length > 0
                             && $( LOCATION_VIEW_EDIT_PANE_SELECTOR ).length > 0 );
                },
            });

        },

        handleSinglePointerEventStart: function( singlePointerEvent ) {
            return Hi.SvgPanZoomCore.handleSinglePointerEventStart(
                singlePointerEvent.start.event );
        },
        handleSinglePointerEventMove: function( singlePointerEvent ) {
            return Hi.SvgPanZoomCore.handleSinglePointerEventMove(
                singlePointerEvent.start.event, singlePointerEvent.last.event );
        },
        handleSinglePointerEventEnd: function( singlePointerEvent ) {
            return Hi.SvgPanZoomCore.handleSinglePointerEventEnd();
        },

        handleDoublePointerEventStart: function( doublePointerEvent ) {
            return Hi.SvgPanZoomCore.handleDoublePointerEventStart( doublePointerEvent );
        },
        handleDoublePointerEventMove: function( doublePointerEvent ) {
            return Hi.SvgPanZoomCore.handleDoublePointerEventMove( doublePointerEvent );
        },
        handleDoublePointerEventEnd: function( doublePointerEvent ) {
            return Hi.SvgPanZoomCore.handleDoublePointerEventEnd( doublePointerEvent );
        },

        handleLastPointerLocation: function( x, y ) {
            Hi.SvgPanZoomCore.handleLastPointerLocation( x, y );
        },
        handleMouseWheel: function( event ) {
            return Hi.SvgPanZoomCore.handleMouseWheel( event );
        },
        handleClick: function( event ) {
            /* Pan-zoom click suppression (after drag) must be checked first. */
            var suppressed = Hi.SvgPanZoomCore.handleClick( event );
            if ( suppressed ) { return true; }

            /* Select the location view SVG on background click — clear other selections. */
            if ( $( event.target ).closest( Hi.LOCATION_VIEW_BASE_SELECTOR ).length > 0 ) {
                var closest = $( event.target ).closest( Hi.LOCATION_VIEW_SVG_SELECTOR );
                if ( closest.length > 0 ) {
                    Hi.SvgIconCore.clearSelection();
                    Hi.SvgPathCore.clearSelection();
                    return true;
                }
            }
            return false;
        },
        handleKeyDown: function( event ) {
            return Hi.SvgPanZoomCore.handleKeyDown( event );
        },

    };

    window.Hi.location = HiSvgLocation;
    HiSvgLocation.init();

})();
