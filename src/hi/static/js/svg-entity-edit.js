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
    window.Hi.SvgEdit = window.Hi.SvgEdit || {};

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
        handleLongPress: function( event ) {
            /* Long-press on an entity icon is the gesture-based escape
               hatch out of a view-type-specific tap behavior (e.g.,
               AUTOMATION's one-click control). The server decides what
               to surface; we just signal that the gesture happened. */
            if ( Hi.isEditMode ) { return false; }
            var group = $( event.target ).closest( 'g' );
            if ( group.length === 0 ) { return false; }
            if ( group.attr( Hi.DATA_TYPE_ATTR ) !== Hi.DATA_TYPE_ICON_VALUE ) {
                return false;
            }
            var svgItemId = group.attr( 'id' );
            if ( ! svgItemId ) { return false; }
            AN.get( Hi.API_LOCATION_ITEM_STATUS_URL + '/' + svgItemId
                    + '?long_press=1' );
            return true;
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
        handleLongPress: function( event ) {
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
                        // Context, not instruction: signals the LocationView
                        // properties editor is open. The server decides what
                        // to do with it (persist to the LocationView vs. only
                        // track the session pan/zoom).
                        view_edit_active: ( $( LOCATION_VIEW_EDIT_PANE_SELECTOR ).length > 0 ),
                    };
                    AN.post( API_EDIT_LOCATION_VIEW_GEOMETRY_URL + '/' + locationViewId, data,
                             { suppressLoader: true } );

                    // Keep this page's URL query params in sync with the latest
                    // pan/zoom so any reload of the current view (e.g. antinode's
                    // refresh_response after an edit) restores the geometry
                    // instead of snapping to the stored viewbox. A deliberate
                    // navigation to another view replaces the URL (no params)
                    // and correctly resets to stored.
                    try {
                        var url = new URL( window.location.href );
                        url.searchParams.set( 'svg_view_box', saveData.viewBoxStr );
                        url.searchParams.set( 'svg_rotate', saveData.rotationAngle || 0 );
                        window.history.replaceState( window.history.state, '', url.toString() );
                    } catch ( e ) { /* URL/History unavailable; non-critical */ }
                },
                shouldSave: function() {
                    // Send pan/zoom to the server throughout edit mode so the
                    // session always holds the latest geometry. Whether it
                    // overwrites the stored LocationView geometry is the
                    // server's call (see view_edit_active above).
                    return ( Hi.isEditMode
                             && $( Hi.BASE_SVG_SELECTOR ).length > 0 );
                },
            });

            // Fit the server-rendered viewBox to the container once the
            // page has laid out. Deferred to a frame after ready so the
            // container has its final size (reading it at ready can yield
            // 0). Without this the view paints letterboxed until the first
            // pan/zoom. A resize re-fits for the same reason; this only
            // rewrites the viewBox locally and never triggers a save.
            function fitToContainer() {
                window.requestAnimationFrame( function() {
                    Hi.SvgPanZoomCore.fitViewBoxToContainer();
                });
            }
            $(document).ready( fitToContainer );

            var resizeFitTimer = null;
            $(window).on( 'resize', function() {
                clearTimeout( resizeFitTimer );
                resizeFitTimer = setTimeout( fitToContainer, 150 );
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
            /* Location only suppresses the trailing click after a pan/scale/
               rotate drag. A click on empty canvas is deliberately NOT
               consumed here: it falls through to the path module so that,
               while a path is being edited, clicking extends it (open or
               closed paths alike). Deselecting is done with Escape -- a stray
               background click no longer clears the icon/path selection or
               exits path editing. */
            return Hi.SvgPanZoomCore.handleClick( event );
        },
        handleLongPress: function( event ) {
            return false;
        },
        handleKeyDown: function( event ) {
            return Hi.SvgPanZoomCore.handleKeyDown( event );
        },

    };

    window.Hi.location = HiSvgLocation;
    HiSvgLocation.init();

})();
