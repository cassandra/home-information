/*
  SVG Path Core

  Provides proxy-point-based path editing for open and closed SVG paths.
  Initialized with a configuration object that specifies how to identify
  path elements, what to do on selection, and how to persist changes.

  Usage:
    Hi.SvgPathCore.init({
        identifyElement: function(event) { ... },
        onSelect: function(element) { ... },
        onDeselect: function() { ... },
        onSave: function(element, svgPathString) { ... },
        baseSvgSelector: '#my-svg',
        highlightClass: 'highlighted',
    });
*/

(function() {

    window.Hi = window.Hi || {};
    window.Hi.svgUtils = window.Hi.svgUtils || {};

    const MODULE_NAME = 'svg-path-core';

    const PROXY_PATH_CONTAINER_ID = 'hi-proxy-path-container';
    const PROXY_PATH_CLASS = 'hi-proxy-path';
    const PROXY_PATH_GROUP_SELECTOR = 'g.' + PROXY_PATH_CLASS;
    const PROXY_POINTS_CLASS = 'hi-proxy-points';
    const PROXY_POINTS_GROUP_SELECTOR = 'g.' + PROXY_POINTS_CLASS;
    const PROXY_LINES_CLASS = 'hi-proxy-lines';
    const PROXY_LINES_GROUP_SELECTOR = 'g.' + PROXY_LINES_CLASS;
    const PROXY_ITEM_CLASS = 'proxy';
    const PROXY_POINT_CLASS = 'proxy-point';
    const PROXY_LINE_CLASS = 'proxy-line';
    const PROXY_POINT_SELECTOR = 'circle.' + PROXY_POINT_CLASS;
    const PROXY_LINE_SELECTOR = 'line.' + PROXY_LINE_CLASS;
    const PROXY_PATH_TYPE_ATTR = 'hi-proxy-path-type';
    const BEFORE_PROXY_POINT_ID = 'before-proxy-point-id';
    const AFTER_PROXY_POINT_ID = 'after-proxy-point-id';

    const PATH_ACTION_DELETE_KEY_CODES = [ 88, 8, 46 ];   // x, Backspace, Delete
    const PATH_ACTION_INSERT_KEY_CODES = [ 73, 45 ];       // i, Insert
    const PATH_ACTION_ADD_KEY_CODES = [ 65, 61 ];          // a, +
    const PATH_ACTION_END_KEY_CODES = [ 27 ];              // Escape

    const CURSOR_MOVEMENT_THRESHOLD_PIXELS = 3;
    const PATH_EDIT_PROXY_POINT_RADIUS_PIXELS = 8;
    const PATH_EDIT_PROXY_LINE_WIDTH_PIXELS = 5;
    const PATH_EDIT_NEW_PATH_RADIUS_PERCENT = 5;
    const PATH_EDIT_PROXY_LINE_COLOR = 'red';
    const PATH_EDIT_PROXY_POINT_COLOR = 'red';

    const ProxyPathType = {
        OPEN: 'open',
        CLOSED: 'closed',
    };

    let gConfig = null;
    let gSelectedPathSvgGroup = null;
    let gSvgPathEditData = null;
    let gIgnoreClick = false;

    let uniqueIdCounter = 0;

    function generateUniqueId() {
        uniqueIdCounter += 1;
        return 'svg-path-core-' + uniqueIdCounter + '-' + Date.now();
    }

    const HiSvgPathCore = {

        init: function( config ) {
            gConfig = config;
        },

        handleClick: function( event ) {
            return _handleClick( event );
        },

        handleKeyDown: function( event ) {
            return _handleKeyDown( event );
        },

        clearSelection: function() {
            clearSelectedPathSvgGroup();
        },

        hasSelection: function() {
            return gSelectedPathSvgGroup !== null;
        },
    };

    window.Hi.SvgPathCore = HiSvgPathCore;

    /* ==================== */
    /* Click Handling       */
    /* ==================== */

    function _handleClick( event ) {
        if ( gSelectedPathSvgGroup && gIgnoreClick ) {
            gIgnoreClick = false;
            return true;
        }
        gIgnoreClick = false;

        /* Check if clicked on a path element. */
        var element = gConfig.identifyElement( event );
        var handled = false;
        if ( element ) {
            handleSvgPathClick( event, element );
            handled = true;
        }

        /* If a path is being edited, check for proxy element clicks or extension clicks. */
        if ( ! handled && gSelectedPathSvgGroup ) {
            var baseSvg = $( gConfig.baseSvgSelector );
            if ( $( event.target ).closest( baseSvg ).length > 0 ) {
                handleProxyPathClick( event );
                handled = true;
            }
        }

        return handled;
    }

    /* ==================== */
    /* KeyDown Handling     */
    /* ==================== */

    function _handleKeyDown( event ) {
        if ( $( event.target ).is( 'input[type="text"], textarea' ) ) { return false; }
        if ( $( event.target ).closest( '.modal' ).length > 0 ) { return false; }
        if ( ! gSvgPathEditData ) { return false; }

        if ( PATH_ACTION_ADD_KEY_CODES.indexOf( event.keyCode ) >= 0 ) {
            addProxyPath();
            return true;

        } else if ( PATH_ACTION_END_KEY_CODES.indexOf( event.keyCode ) >= 0 ) {
            clearSelectedPathSvgGroup();
            return true;

        } else {
            if ( ! gSvgPathEditData.selectedProxyElement ) { return false; }

            if ( PATH_ACTION_DELETE_KEY_CODES.indexOf( event.keyCode ) >= 0 ) {
                if ( $( gSvgPathEditData.selectedProxyElement ).hasClass( PROXY_POINT_CLASS ) ) {
                    deleteProxyPoint( gSvgPathEditData.selectedProxyElement );
                    return true;
                } else if ( $( gSvgPathEditData.selectedProxyElement ).hasClass( PROXY_LINE_CLASS ) ) {
                    deleteProxyLine( gSvgPathEditData.selectedProxyElement );
                    return true;
                }

            } else if ( PATH_ACTION_INSERT_KEY_CODES.indexOf( event.keyCode ) >= 0 ) {
                if ( $( gSvgPathEditData.selectedProxyElement ).hasClass( PROXY_LINE_CLASS ) ) {
                    divideProxyLine( gSvgPathEditData.selectedProxyElement );
                    return true;
                } else if ( $( gSvgPathEditData.selectedProxyElement ).hasClass( PROXY_POINT_CLASS ) ) {
                    var svgProxyLine = getPrecedingProxyLine( gSvgPathEditData.selectedProxyElement );
                    if ( svgProxyLine.length > 0 ) {
                        divideProxyLine( svgProxyLine );
                        return true;
                    } else {
                        svgProxyLine = getFollowingProxyLine( gSvgPathEditData.selectedProxyElement );
                        if ( svgProxyLine.length > 0 ) {
                            divideProxyLine( svgProxyLine );
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    /* ==================== */
    /* Selection            */
    /* ==================== */

    function handleSvgPathClick( event, element ) {
        clearSelectedPathSvgGroup();
        gSelectedPathSvgGroup = $( element );
        expandSvgPath( gSelectedPathSvgGroup );
        if ( gConfig.onSelect ) {
            gConfig.onSelect( element );
        }
    }

    function clearSelectedPathSvgGroup() {
        if ( gSelectedPathSvgGroup ) {
            collapseSvgPath();
            gSelectedPathSvgGroup = null;
            if ( gConfig.onDeselect ) {
                gConfig.onDeselect();
            }
        }
    }

    function handleProxyPathClick( event ) {
        var isProxyElement = $( event.target ).hasClass( PROXY_ITEM_CLASS );
        if ( isProxyElement ) {
            setSelectedProxyElement( event.target );
        } else {
            extendProxyPath( event );
        }
    }

    function setSelectedProxyElement( proxyElement ) {
        if ( ! gSvgPathEditData ) { return; }
        $( gSvgPathEditData.proxyPathContainer ).find( '.' + PROXY_ITEM_CLASS )
            .removeClass( gConfig.highlightClass || 'highlighted' );
        if ( proxyElement ) {
            $( proxyElement ).addClass( gConfig.highlightClass || 'highlighted' );
        }
        gSvgPathEditData.selectedProxyElement = proxyElement;
    }

    /* ==================== */
    /* Expand / Collapse    */
    /* ==================== */

    function expandSvgPath( pathSvgGroup ) {
        pathSvgGroup.hide();

        var baseSvgElement = $( gConfig.baseSvgSelector )[0];
        var proxyPathContainer = document.createElementNS( 'http://www.w3.org/2000/svg', 'g' );
        proxyPathContainer.setAttribute( 'id', PROXY_PATH_CONTAINER_ID );
        baseSvgElement.appendChild( proxyPathContainer );

        gSvgPathEditData = {
            proxyPathContainer: proxyPathContainer,
            selectedProxyElement: null,
            dragProxyPoint: null,
        };

        var svgPathElement = $( pathSvgGroup ).find( 'path' ).not( '.hi-bg-hit-area' );
        var pathData = svgPathElement.attr( 'd' );
        var segments = pathData.match( /[ML][^MLZ]+|Z/g );

        /* Create all proxy points. */
        var currentProxyPathGroup = null;
        for ( var i = 0; i < segments.length; i++ ) {
            var command = segments[i].charAt(0);
            var coords = segments[i].substring(1).trim().split( /[\s,]+/ ).map( Number );

            if ( command === 'M' ) {
                currentProxyPathGroup = createProxyPathGroup( ProxyPathType.OPEN );
                $( proxyPathContainer ).append( currentProxyPathGroup );
                var newProxyPoint = createProxyPathProxyPoint( coords[0], coords[1] );
                $( currentProxyPathGroup ).find( PROXY_POINTS_GROUP_SELECTOR ).append( newProxyPoint );

            } else if ( command === 'L' && currentProxyPathGroup ) {
                var newProxyPoint = createProxyPathProxyPoint( coords[0], coords[1] );
                $( currentProxyPathGroup ).find( PROXY_POINTS_GROUP_SELECTOR ).append( newProxyPoint );

            } else if ( command === 'Z' && currentProxyPathGroup ) {
                $( currentProxyPathGroup ).attr( PROXY_PATH_TYPE_ATTR, ProxyPathType.CLOSED );
                currentProxyPathGroup = null;
            }
        }

        /* Create lines and event handlers. */
        $( proxyPathContainer ).find( PROXY_PATH_GROUP_SELECTOR ).each( function( index, proxyPathGroup ) {
            var previousProxyPoint = null;
            var firstLine = null;
            var previousLine = null;

            var proxyLinesGroup = $( proxyPathGroup ).find( PROXY_LINES_GROUP_SELECTOR );
            var proxyPoints = $( proxyPathGroup ).find( PROXY_POINT_SELECTOR );

            $( proxyPoints ).each( function( index, currentProxyPoint ) {
                if ( previousProxyPoint ) {
                    var x1 = parseFloat( previousProxyPoint.getAttribute( 'cx' ) );
                    var y1 = parseFloat( previousProxyPoint.getAttribute( 'cy' ) );
                    var x2 = parseFloat( currentProxyPoint.getAttribute( 'cx' ) );
                    var y2 = parseFloat( currentProxyPoint.getAttribute( 'cy' ) );
                    var currentLine = createProxyPathLine( previousProxyPoint, currentProxyPoint,
                                                           x1, y1, x2, y2 );
                    $( proxyLinesGroup ).append( currentLine );

                    if ( previousLine ) {
                        addProxyPointEventHandler( previousProxyPoint, previousLine, currentLine );
                    }
                    if ( ! firstLine ) {
                        firstLine = currentLine;
                    }
                    previousLine = currentLine;
                }
                previousProxyPoint = currentProxyPoint;
            });

            if ( proxyPoints.length < 2 ) {
                addProxyPointEventHandler( previousProxyPoint, null, null );
                return;
            }

            var firstProxyPoint = proxyPoints[0];
            var lastProxyPoint = proxyPoints[ proxyPoints.length - 1 ];

            if ( $( proxyPathGroup ).attr( PROXY_PATH_TYPE_ATTR ) === ProxyPathType.OPEN ) {
                addProxyPointEventHandler( firstProxyPoint, null, firstLine );
                addProxyPointEventHandler( lastProxyPoint, previousLine, null );
            } else {
                var x1 = parseFloat( lastProxyPoint.getAttribute( 'cx' ) );
                var y1 = parseFloat( lastProxyPoint.getAttribute( 'cy' ) );
                var x2 = parseFloat( firstProxyPoint.getAttribute( 'cx' ) );
                var y2 = parseFloat( firstProxyPoint.getAttribute( 'cy' ) );
                var closureLine = createProxyPathLine( lastProxyPoint, firstProxyPoint,
                                                       x1, y1, x2, y2 );
                $( proxyLinesGroup ).append( closureLine );
                addProxyPointEventHandler( firstProxyPoint, closureLine, firstLine );
                addProxyPointEventHandler( lastProxyPoint, previousLine, closureLine );
            }
        });
    }

    function collapseSvgPath() {
        var newSvgPath = getSvgPathStringFromProxyPaths();
        $( gSelectedPathSvgGroup ).find( 'path' ).not( '.hi-bg-hit-area' ).attr( 'd', newSvgPath );

        /* Also update the hit-area path if present. */
        var hitAreaPath = $( gSelectedPathSvgGroup ).find( 'path.hi-bg-hit-area' );
        if ( hitAreaPath.length > 0 ) {
            hitAreaPath.attr( 'd', newSvgPath );
        }

        var proxyPathContainer = $( '#' + PROXY_PATH_CONTAINER_ID );
        $( proxyPathContainer ).remove();

        gSelectedPathSvgGroup.show();
        gSvgPathEditData = null;
    }

    /* ==================== */
    /* Extend Path          */
    /* ==================== */

    function extendProxyPath( event ) {
        var baseSvgElement = $( gConfig.baseSvgSelector );
        var svgViewBox = Hi.svgUtils.getSvgViewBox( baseSvgElement );
        var svgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement, event.clientX, event.clientY );

        if ( svgPoint.x < svgViewBox.x
             || svgPoint.x > ( svgViewBox.x + svgViewBox.width )
             || svgPoint.y < svgViewBox.y
             || svgPoint.y > ( svgViewBox.y + svgViewBox.height ) ) {
            return;
        }

        var referenceElement = getReferenceElementForExtendingProxyPath();
        var proxyPathGroup = $( referenceElement ).closest( PROXY_PATH_GROUP_SELECTOR );
        var newProxyPoint = null;

        if ( $( referenceElement ).hasClass( PROXY_POINT_CLASS ) ) {
            if ( $( proxyPathGroup ).attr( PROXY_PATH_TYPE_ATTR ) === ProxyPathType.OPEN ) {
                if ( $( referenceElement ).is( ':first-of-type' ) ) {
                    newProxyPoint = prependNewProxyPoint( svgPoint, proxyPathGroup );
                } else {
                    newProxyPoint = appendNewProxyPoint( svgPoint, proxyPathGroup );
                }
            } else {
                var followingProxyLine = getFollowingProxyLine( referenceElement );
                newProxyPoint = insertNewProxyPoint( svgPoint, followingProxyLine );
            }
        } else if ( $( referenceElement ).hasClass( PROXY_LINE_CLASS ) ) {
            newProxyPoint = insertNewProxyPoint( svgPoint, referenceElement );
        }

        if ( newProxyPoint ) {
            setSelectedProxyElement( newProxyPoint );
            saveSvgPath();
        }
    }

    /* ==================== */
    /* Add / Insert Points  */
    /* ==================== */

    function prependNewProxyPoint( newSvgPoint, proxyPathGroup ) {
        var firstProxyPoint = proxyPathGroup.find( PROXY_POINT_SELECTOR ).first();
        var firstLine = proxyPathGroup.find( PROXY_LINE_SELECTOR ).first();

        var firstX = parseFloat( $( firstProxyPoint ).attr( 'cx' ) );
        var firstY = parseFloat( $( firstProxyPoint ).attr( 'cy' ) );

        var newProxyPoint = createProxyPathProxyPoint( newSvgPoint.x, newSvgPoint.y );
        var newLine = createProxyPathLine( newProxyPoint, firstProxyPoint,
                                           newSvgPoint.x, newSvgPoint.y, firstX, firstY );

        var proxyPointsGroup = $( proxyPathGroup ).find( PROXY_POINTS_GROUP_SELECTOR );
        var proxyLinesGroup = $( proxyPathGroup ).find( PROXY_LINES_GROUP_SELECTOR );
        $( proxyPointsGroup ).prepend( newProxyPoint );
        $( proxyLinesGroup ).prepend( newLine );

        $( firstProxyPoint ).off();
        addProxyPointEventHandler( firstProxyPoint, newLine, firstLine );
        addProxyPointEventHandler( newProxyPoint, null, newLine );

        return newProxyPoint;
    }

    function appendNewProxyPoint( newSvgPoint, proxyPathGroup ) {
        var lastProxyPoint = proxyPathGroup.find( PROXY_POINT_SELECTOR ).last();
        var lastLine = proxyPathGroup.find( PROXY_LINE_SELECTOR ).last();

        var lastX = parseFloat( $( lastProxyPoint ).attr( 'cx' ) );
        var lastY = parseFloat( $( lastProxyPoint ).attr( 'cy' ) );

        var newProxyPoint = createProxyPathProxyPoint( newSvgPoint.x, newSvgPoint.y );
        var newLine = createProxyPathLine( lastProxyPoint, newProxyPoint,
                                           lastX, lastY, newSvgPoint.x, newSvgPoint.y );

        var proxyPointsGroup = $( proxyPathGroup ).find( PROXY_POINTS_GROUP_SELECTOR );
        var proxyLinesGroup = $( proxyPathGroup ).find( PROXY_LINES_GROUP_SELECTOR );
        $( proxyPointsGroup ).append( newProxyPoint );
        $( proxyLinesGroup ).append( newLine );

        $( lastProxyPoint ).off();
        addProxyPointEventHandler( lastProxyPoint, lastLine, newLine );
        addProxyPointEventHandler( newProxyPoint, newLine, null );

        return newProxyPoint;
    }

    function insertNewProxyPoint( newSvgPoint, referenceProxyLine ) {
        var beforeProxyPointId = $( referenceProxyLine ).attr( BEFORE_PROXY_POINT_ID );
        var afterProxyPointId = $( referenceProxyLine ).attr( AFTER_PROXY_POINT_ID );

        var beforeProxyPoint = $( '#' + beforeProxyPointId );
        var afterProxyPoint = $( '#' + afterProxyPointId );
        var followingProxyLine = getFollowingProxyLine( afterProxyPoint );

        var afterX = parseFloat( $( afterProxyPoint ).attr( 'cx' ) );
        var afterY = parseFloat( $( afterProxyPoint ).attr( 'cy' ) );

        var newProxyPoint = createProxyPathProxyPoint( newSvgPoint.x, newSvgPoint.y );
        var newLine = createProxyPathLine( newProxyPoint, afterProxyPoint,
                                           newSvgPoint.x, newSvgPoint.y, afterX, afterY );

        $( referenceProxyLine ).attr( AFTER_PROXY_POINT_ID, $( newProxyPoint ).attr( 'id' ) );
        $( referenceProxyLine ).attr( 'x2', newSvgPoint.x );
        $( referenceProxyLine ).attr( 'y2', newSvgPoint.y );

        $( beforeProxyPoint ).after( newProxyPoint );
        $( referenceProxyLine ).after( newLine );

        $( afterProxyPoint ).off();
        addProxyPointEventHandler( afterProxyPoint, newLine, followingProxyLine );
        addProxyPointEventHandler( newProxyPoint, referenceProxyLine, newLine );

        return newProxyPoint;
    }

    /* ==================== */
    /* Delete Points        */
    /* ==================== */

    function deleteProxyPoint( svgProxyPoint ) {
        var proxyPathGroup = $( svgProxyPoint ).closest( PROXY_PATH_GROUP_SELECTOR );
        var proxyPathType = $( proxyPathGroup ).attr( PROXY_PATH_TYPE_ATTR );
        var proxyPointsGroup = $( svgProxyPoint ).closest( PROXY_POINTS_GROUP_SELECTOR );
        var minPoints = ( proxyPathType === ProxyPathType.CLOSED ) ? 3 : 2;

        if ( $( proxyPointsGroup ).children().length <= minPoints ) {
            removeProxyPathIfAllowed( proxyPathGroup );
            return;
        }

        var beforeProxyLine = getPrecedingProxyLine( svgProxyPoint );
        var afterProxyLine = getFollowingProxyLine( svgProxyPoint );

        if ( beforeProxyLine.length > 0 && afterProxyLine.length > 0 ) {
            var afterProxyPointId = $( afterProxyLine ).attr( AFTER_PROXY_POINT_ID );
            var afterProxyPoint = $( '#' + afterProxyPointId );
            var followingProxyLine = getFollowingProxyLine( afterProxyPoint );

            var afterX = parseFloat( $( afterProxyPoint ).attr( 'cx' ) );
            var afterY = parseFloat( $( afterProxyPoint ).attr( 'cy' ) );
            $( beforeProxyLine ).attr( AFTER_PROXY_POINT_ID, $( afterProxyPoint ).attr( 'id' ) );
            $( beforeProxyLine ).attr( 'x2', afterX );
            $( beforeProxyLine ).attr( 'y2', afterY );

            $( afterProxyPoint ).off();
            addProxyPointEventHandler( afterProxyPoint, beforeProxyLine, followingProxyLine );

            $( svgProxyPoint ).remove();
            $( afterProxyLine ).remove();
            setSelectedProxyElement( afterProxyPoint );

        } else if ( afterProxyLine.length > 0 ) {
            var afterProxyPointId = $( afterProxyLine ).attr( AFTER_PROXY_POINT_ID );
            var afterProxyPoint = $( '#' + afterProxyPointId );
            var followingProxyLine = getFollowingProxyLine( afterProxyPoint );

            $( afterProxyPoint ).off();
            addProxyPointEventHandler( afterProxyPoint, null, followingProxyLine );

            $( svgProxyPoint ).remove();
            $( afterProxyLine ).remove();
            setSelectedProxyElement( afterProxyPoint );

        } else if ( beforeProxyLine.length > 0 ) {
            var beforeProxyPointId = $( beforeProxyLine ).attr( BEFORE_PROXY_POINT_ID );
            var beforeProxyPoint = $( '#' + beforeProxyPointId );
            var precedingProxyLine = getPrecedingProxyLine( beforeProxyPoint );

            $( beforeProxyPoint ).off();
            addProxyPointEventHandler( beforeProxyPoint, precedingProxyLine, null );

            $( svgProxyPoint ).remove();
            $( beforeProxyLine ).remove();
            setSelectedProxyElement( beforeProxyPoint );

        } else {
            $( svgProxyPoint ).remove();
            setSelectedProxyElement( null );
        }

        saveSvgPath();
    }

    function deleteProxyLine( svgProxyLine ) {
        var beforeProxyPointId = $( svgProxyLine ).attr( BEFORE_PROXY_POINT_ID );
        var beforeProxyPoint = $( '#' + beforeProxyPointId );
        deleteProxyPoint( beforeProxyPoint );
    }

    function divideProxyLine( svgProxyLine ) {
        var beforeProxyPointId = $( svgProxyLine ).attr( BEFORE_PROXY_POINT_ID );
        var afterProxyPointId = $( svgProxyLine ).attr( AFTER_PROXY_POINT_ID );
        var beforeProxyPoint = $( '#' + beforeProxyPointId );
        var afterProxyPoint = $( '#' + afterProxyPointId );

        var beforeX = parseFloat( $( beforeProxyPoint ).attr( 'cx' ) );
        var beforeY = parseFloat( $( beforeProxyPoint ).attr( 'cy' ) );
        var afterX = parseFloat( $( afterProxyPoint ).attr( 'cx' ) );
        var afterY = parseFloat( $( afterProxyPoint ).attr( 'cy' ) );

        var midSvgPoint = {
            x: ( beforeX + afterX ) / 2,
            y: ( beforeY + afterY ) / 2,
        };
        insertNewProxyPoint( midSvgPoint, svgProxyLine );
        saveSvgPath();
    }

    /* ==================== */
    /* Add Path Segment     */
    /* ==================== */

    function addProxyPath() {
        var proxyPathContainer = $( '#' + PROXY_PATH_CONTAINER_ID );
        var firstProxyPath = $( proxyPathContainer ).find( PROXY_PATH_GROUP_SELECTOR ).first();
        var proxyPathType = $( firstProxyPath ).attr( PROXY_PATH_TYPE_ATTR );
        var newProxyPathGroup = createProxyPathGroup( proxyPathType );
        $( proxyPathContainer ).append( newProxyPathGroup );

        var baseSvgElement = $( gConfig.baseSvgSelector );
        var svgViewBox = Hi.svgUtils.getSvgViewBox( baseSvgElement );
        var svgCenter = {
            x: svgViewBox.x + ( svgViewBox.width / 2 ),
            y: svgViewBox.y + ( svgViewBox.height / 2 ),
        };
        var svgUnitRadius = {
            x: svgViewBox.width * ( PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 ),
            y: svgViewBox.height * ( PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 ),
        };

        var proxyPointsGroup = $( newProxyPathGroup ).find( PROXY_POINTS_GROUP_SELECTOR );
        var proxyLinesGroup = $( newProxyPathGroup ).find( PROXY_LINES_GROUP_SELECTOR );

        if ( proxyPathType === ProxyPathType.OPEN ) {
            var leftPoint = { x: svgCenter.x - svgUnitRadius.x, y: svgCenter.y };
            var rightPoint = { x: svgCenter.x + svgUnitRadius.x, y: svgCenter.y };

            var beforePP = createProxyPathProxyPoint( leftPoint.x, leftPoint.y );
            var afterPP = createProxyPathProxyPoint( rightPoint.x, rightPoint.y );
            proxyPointsGroup.append( beforePP );
            proxyPointsGroup.append( afterPP );

            var newLine = createProxyPathLine( beforePP, afterPP,
                                               leftPoint.x, leftPoint.y, rightPoint.x, rightPoint.y );
            $( proxyLinesGroup ).append( newLine );

            addProxyPointEventHandler( beforePP, null, newLine );
            addProxyPointEventHandler( afterPP, newLine, null );

        } else if ( proxyPathType === ProxyPathType.CLOSED ) {
            var tl = { x: svgCenter.x - svgUnitRadius.x, y: svgCenter.y - svgUnitRadius.y };
            var tr = { x: svgCenter.x + svgUnitRadius.x, y: svgCenter.y - svgUnitRadius.y };
            var br = { x: svgCenter.x + svgUnitRadius.x, y: svgCenter.y + svgUnitRadius.y };
            var bl = { x: svgCenter.x - svgUnitRadius.x, y: svgCenter.y + svgUnitRadius.y };

            var tlPP = createProxyPathProxyPoint( tl.x, tl.y );
            var trPP = createProxyPathProxyPoint( tr.x, tr.y );
            var brPP = createProxyPathProxyPoint( br.x, br.y );
            var blPP = createProxyPathProxyPoint( bl.x, bl.y );
            proxyPointsGroup.append( tlPP );
            proxyPointsGroup.append( trPP );
            proxyPointsGroup.append( brPP );
            proxyPointsGroup.append( blPP );

            var topLine = createProxyPathLine( tlPP, trPP, tl.x, tl.y, tr.x, tr.y );
            var rightLine = createProxyPathLine( trPP, brPP, tr.x, tr.y, br.x, br.y );
            var bottomLine = createProxyPathLine( brPP, blPP, br.x, br.y, bl.x, bl.y );
            var leftLine = createProxyPathLine( blPP, tlPP, bl.x, bl.y, tl.x, tl.y );
            $( proxyLinesGroup ).append( topLine );
            $( proxyLinesGroup ).append( rightLine );
            $( proxyLinesGroup ).append( bottomLine );
            $( proxyLinesGroup ).append( leftLine );

            addProxyPointEventHandler( tlPP, leftLine, topLine );
            addProxyPointEventHandler( trPP, topLine, rightLine );
            addProxyPointEventHandler( brPP, rightLine, bottomLine );
            addProxyPointEventHandler( blPP, bottomLine, leftLine );
        }
        saveSvgPath();
    }

    function removeProxyPathIfAllowed( targetProxyPathGroup ) {
        var proxyPathContainer = $( '#' + PROXY_PATH_CONTAINER_ID );
        var proxyPathGroups = $( proxyPathContainer ).find( PROXY_PATH_GROUP_SELECTOR );
        if ( proxyPathGroups.length < 2 ) { return; }
        $( targetProxyPathGroup ).remove();
        setSelectedProxyElement( null );
        saveSvgPath();
    }

    /* ==================== */
    /* Create Proxy Items   */
    /* ==================== */

    function createProxyPathGroup( proxyPathType ) {
        var group = document.createElementNS( 'http://www.w3.org/2000/svg', 'g' );
        group.setAttribute( 'id', generateUniqueId() );
        group.setAttribute( 'class', PROXY_PATH_CLASS );
        group.setAttribute( PROXY_PATH_TYPE_ATTR, proxyPathType );

        var linesGroup = document.createElementNS( 'http://www.w3.org/2000/svg', 'g' );
        linesGroup.setAttribute( 'class', PROXY_LINES_CLASS );
        group.appendChild( linesGroup );

        var pointsGroup = document.createElementNS( 'http://www.w3.org/2000/svg', 'g' );
        pointsGroup.setAttribute( 'class', PROXY_POINTS_CLASS );
        group.appendChild( pointsGroup );

        return group;
    }

    function createProxyPathProxyPoint( cx, cy ) {
        var baseSvgElement = $( gConfig.baseSvgSelector );
        var pixelsPerSvgUnit = Hi.svgUtils.getPixelsPerSvgUnit( baseSvgElement );
        var svgRadius = PATH_EDIT_PROXY_POINT_RADIUS_PIXELS / pixelsPerSvgUnit.scaleX;

        var point = document.createElementNS( 'http://www.w3.org/2000/svg', 'circle' );
        point.setAttribute( 'cx', cx );
        point.setAttribute( 'cy', cy );
        point.setAttribute( 'r', svgRadius );
        point.setAttribute( 'id', generateUniqueId() );
        $( point ).addClass( 'draggable' );
        $( point ).addClass( PROXY_ITEM_CLASS );
        $( point ).addClass( PROXY_POINT_CLASS );
        point.setAttribute( 'fill', PATH_EDIT_PROXY_POINT_COLOR );
        point.setAttribute( 'vector-effect', 'non-scaling-stroke' );
        return point;
    }

    function createProxyPathLine( beforeProxyPoint, afterProxyPoint, x1, y1, x2, y2 ) {
        var line = document.createElementNS( 'http://www.w3.org/2000/svg', 'line' );
        line.setAttribute( 'x1', x1 );
        line.setAttribute( 'y1', y1 );
        line.setAttribute( 'x2', x2 );
        line.setAttribute( 'y2', y2 );
        $( line ).addClass( PROXY_ITEM_CLASS );
        $( line ).addClass( PROXY_LINE_CLASS );
        line.setAttribute( BEFORE_PROXY_POINT_ID, $( beforeProxyPoint ).attr( 'id' ) );
        line.setAttribute( AFTER_PROXY_POINT_ID, $( afterProxyPoint ).attr( 'id' ) );
        line.setAttribute( 'stroke', PATH_EDIT_PROXY_LINE_COLOR );
        line.setAttribute( 'stroke-width', PATH_EDIT_PROXY_LINE_WIDTH_PIXELS );
        line.setAttribute( 'vector-effect', 'non-scaling-stroke' );
        return line;
    }

    /* ==================== */
    /* Proxy Point Drag     */
    /* ==================== */

    function addProxyPointEventHandler( proxyPoint, beforeProxyLine, afterProxyLine ) {
        $( proxyPoint ).on( 'mousedown', function( event ) {
            event.preventDefault();
            event.stopImmediatePropagation();

            var startMousePosition = { x: event.clientX, y: event.clientY };
            var baseSvgElement = $( gConfig.baseSvgSelector );
            var eventSvgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement, event.clientX, event.clientY );

            var offsetX = eventSvgPoint.x - parseFloat( $( proxyPoint ).attr( 'cx' ) );
            var offsetY = eventSvgPoint.y - parseFloat( $( proxyPoint ).attr( 'cy' ) );

            var isDragging = false;

            function onMouseMove( event ) {
                if ( ! gSvgPathEditData ) { return; }

                var currentMousePosition = { x: event.clientX, y: event.clientY };
                var distanceX = Math.abs( currentMousePosition.x - startMousePosition.x );
                var distanceY = Math.abs( currentMousePosition.y - startMousePosition.y );

                if ( isDragging
                     || distanceX > CURSOR_MOVEMENT_THRESHOLD_PIXELS
                     || distanceY > CURSOR_MOVEMENT_THRESHOLD_PIXELS ) {
                    isDragging = true;
                    event.preventDefault();
                    event.stopImmediatePropagation();

                    var eventSvgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement,
                                                                 event.clientX, event.clientY );

                    gSvgPathEditData.dragProxyPoint = event.target;
                    var newCx = eventSvgPoint.x - offsetX;
                    var newCy = eventSvgPoint.y - offsetY;
                    $( proxyPoint ).attr( 'cx', newCx ).attr( 'cy', newCy );

                    if ( $( beforeProxyLine ).length > 0 ) {
                        $( beforeProxyLine ).attr( 'x2', newCx ).attr( 'y2', newCy );
                    }
                    if ( $( afterProxyLine ).length > 0 ) {
                        $( afterProxyLine ).attr( 'x1', newCx ).attr( 'y1', newCy );
                    }

                    setSelectedProxyElement( proxyPoint );
                }
            }

            function onMouseUp( event ) {
                if ( ! gSvgPathEditData ) { return; }

                event.preventDefault();
                event.stopImmediatePropagation();
                saveSvgPath();
                gSvgPathEditData.dragProxyPoint = null;
                if ( isDragging ) {
                    gIgnoreClick = true;
                }
                $( document ).off( 'mousemove', onMouseMove );
                $( document ).off( 'mouseup', onMouseUp );
            }

            $( document ).on( 'mousemove', onMouseMove );
            $( document ).on( 'mouseup', onMouseUp );
        });
    }

    /* ==================== */
    /* Path Serialization   */
    /* ==================== */

    function getSvgPathStringFromProxyPaths() {
        var proxyPathContainer = $( '#' + PROXY_PATH_CONTAINER_ID );
        var proxyPathGroups = $( proxyPathContainer ).find( PROXY_PATH_GROUP_SELECTOR );

        var pathString = '';
        $( proxyPathGroups ).each( function( index, proxyPathGroup ) {
            var proxyPoints = $( proxyPathGroup ).find( PROXY_POINT_SELECTOR );
            $( proxyPoints ).each( function( index, proxyPoint ) {
                if ( index === 0 ) {
                    pathString += ' M ';
                } else {
                    pathString += ' L ';
                }
                pathString += proxyPoint.getAttribute( 'cx' ) + ',' + proxyPoint.getAttribute( 'cy' );
            });
            if ( $( proxyPathGroup ).attr( PROXY_PATH_TYPE_ATTR ) === ProxyPathType.CLOSED ) {
                pathString += ' Z';
            }
        });

        return pathString;
    }

    /* ==================== */
    /* Save                 */
    /* ==================== */

    function saveSvgPath() {
        if ( ! gSelectedPathSvgGroup || ! gConfig || ! gConfig.onSave ) { return; }

        var svgPathString = getSvgPathStringFromProxyPaths();
        gConfig.onSave( gSelectedPathSvgGroup[0], svgPathString );
    }

    /* ==================== */
    /* Utilities            */
    /* ==================== */

    function getReferenceElementForExtendingProxyPath() {
        if ( gSvgPathEditData.selectedProxyElement ) {
            return gSvgPathEditData.selectedProxyElement;
        }
        var lastProxyPath = $( gSvgPathEditData.proxyPathContainer ).find( PROXY_PATH_GROUP_SELECTOR ).last();
        var lastProxyPoint = lastProxyPath.find( PROXY_POINT_SELECTOR ).last();
        return lastProxyPoint;
    }

    function getPrecedingProxyLine( proxyPoint ) {
        var proxyPointId = $( proxyPoint ).attr( 'id' );
        return $( 'line[' + AFTER_PROXY_POINT_ID + '="' + proxyPointId + '"]' );
    }

    function getFollowingProxyLine( proxyPoint ) {
        var proxyPointId = $( proxyPoint ).attr( 'id' );
        return $( 'line[' + BEFORE_PROXY_POINT_ID + '="' + proxyPointId + '"]' );
    }

})();
