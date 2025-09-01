(function() {
    
    window.Hi = window.Hi || {};
    window.Hi.edit = window.Hi.edit || {};
    window.Hi.svgUtils = window.Hi.svgUtils || {};

    const MODULE_NAME = 'svg-path';    
    let gCurrentSelectionModule = null;

    const HiEditSvgPath = {
        init: function() {
            Hi.edit.eventBus.subscribe( Hi.edit.SELECTION_MADE_EVENT_NAME,
                                        this.clearSelection.bind( this ) );
        },
        handleClick: function( event ) {
            return _handleClick( event );           
        },
        handleKeyDown: function( event ) {
            return _handleKeyDown( event );         
        },
        clearSelection: function( data ) {
            gCurrentSelectionModule = data.moduleName;
            if ( data.moduleName != MODULE_NAME ) {
                clearSelectedPathSvgGroup();
            }
        }
    };

    window.Hi.edit.path = HiEditSvgPath;
    HiEditSvgPath.init();
    
    /* 
      SVG PATH EDITING
      
      - When a path is selected, the original SVG element/group is hidden and proxy elements created.
      - Proxy elements are points and lines with points being way to move path endpoint location.
      - During editing, control proxy popionts can be moved, added and deleted.
      - Two types of paths: closed (with ending 'Z') and open.
      - The type is determined by the initial path and not changeable during editing.
      - An open path must have at least two proxy points (control points for manipulation).
      - A closed path must have at least 3 proxy points.
      - The behavior of adding to the path depends on its type.
      - Adding is relative to the last selected item.
      - You can select a line or a proxy point during editing.
      - An open path gets extended when adding (can also subdivide a line if it is selected).
      - A closed path has its lines subdivided when adding.
      - A entity's path can consist of multiple, disconnected segments.
      - Add a new proxy path adds a line or a rectangle for open and closed paths respectively.
      - A selected path aso shows the entity details in the side edit panel.
    */    

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
    
    const PATH_ACTION_DELETE_KEY_CODES = [
        88, // 'x'
        8,  // Backspace
        46  // Delete
    ];
    const PATH_ACTION_INSERT_KEY_CODES = [
        73, // 'i'
        45 // Insert
    ];
    const PATH_ACTION_ADD_KEY_CODES = [
        65, // 'a'
        61 // '+'
    ];
    const PATH_ACTION_END_KEY_CODES = [
        27 // Escape
    ];

    const CURSOR_MOVEMENT_THRESHOLD_PIXELS = 3; // Differentiate between move events and sloppy clicks
    const PATH_EDIT_PROXY_POINT_RADIUS_PIXELS = 8;
    const PATH_EDIT_PROXY_LINE_WIDTH_PIXELS = 5;
    const PATH_EDIT_NEW_PATH_RADIUS_PERCENT = 5; // Preferrable if this matches server new path sizing.
    const PATH_EDIT_PROXY_LINE_COLOR = 'red';
    const PATH_EDIT_PROXY_POINT_COLOR = 'red';

    const API_EDIT_SVG_PATH_URL = '/location/edit/item/path';
    
    const ProxyPathType = {
        OPEN: 'open',
        CLOSED: 'closed'
    };

    let gSelectedPathSvgGroup = null;
    let gSvgPathEditData = null;
    let gIgnoreCLick = false;  // Set by mouseup handling when no click handling should be done

    function _handleClick( event ) {
        if ( gSelectedPathSvgGroup && gIgnoreCLick ) {
            if ( Hi.DEBUG ) { console.log( `Ignoring click: [${MODULE_NAME}]`, event ); }
            gIgnoreCLick = false;
            return true;
        }
        gIgnoreCLick = false;

        const enclosingSvgGroup = $(event.target).closest('g');
        let handled = false;
        if ( enclosingSvgGroup.length > 0 ) {
            let svgDataType = $(enclosingSvgGroup).attr( Hi.DATA_TYPE_ATTR );
            const isSvgPath = ( svgDataType == Hi.DATA_TYPE_PATH_VALUE );
            const svgItemId = enclosingSvgGroup.attr('id');
            if ( isSvgPath && svgItemId ) {
                handleSvgPathClick( event, enclosingSvgGroup );
                handled = true;
            }
        }
        if ( ! handled && gSelectedPathSvgGroup ) {
            const enclosingSvg = $(event.target).closest('svg');
            if ( $(enclosingSvg).hasClass( Hi.LOCATION_VIEW_SVG_CLASS ) ) { 
                handleProxyPathClick( event );
                handled = true;
            }
        }

        if ( handled ) {
            if ( Hi.DEBUG ) { console.log( `Click handled: [${MODULE_NAME}]`, event ); }
        } else {
            if ( Hi.DEBUG ) { console.log( `Click skipped: [${MODULE_NAME}]` ); }
        }
        return handled;
    }

    function _handleKeyDown( event ) {
        if ( ! Hi.isEditMode ) { return false; }
        if ( $(event.target).is('input[type="text"], textarea') ) {
            return false;
        }
        if ($(event.target).closest('.modal').length > 0) {
            return false;
        }
        if ( ! gSvgPathEditData ) {
            if ( Hi.DEBUG ) { console.log( `Key down skipped [${MODULE_NAME}]` ); }
            return false;
        }
        if ( Hi.DEBUG ) { console.log( `Key Down [${MODULE_NAME}]`, event ); }
        
        if ( PATH_ACTION_ADD_KEY_CODES.includes( event.keyCode ) ) {
            addProxyPath();
            return true;
            
        } else if ( PATH_ACTION_END_KEY_CODES.includes( event.keyCode ) ) {
            clearSelectedPathSvgGroup();
            let data = { moduleName: null };
            Hi.edit.eventBus.emit( Hi.edit.SELECTION_MADE_EVENT_NAME, data );
            return true;

        } else {
            if ( ! gSvgPathEditData.selectedProxyElement ) {
                if ( Hi.DEBUG ) { console.log( `Key down skipped [${MODULE_NAME}]` ); }
                return false;
            }

            if ( PATH_ACTION_DELETE_KEY_CODES.includes( event.keyCode )) {
                if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_POINT_CLASS ) ) {
                    deleteProxyPoint( gSvgPathEditData.selectedProxyElement );
                    return true;
                    
                } else if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_LINE_CLASS ) ) {
                    deleteProxyLine( gSvgPathEditData.selectedProxyElement );
                    return true;
                }
                
            } else if ( PATH_ACTION_INSERT_KEY_CODES.includes( event.keyCode ) ) {
                if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_LINE_CLASS ) ) {
                    divideProxyLine( gSvgPathEditData.selectedProxyElement );
                    return true;
                    
                } else if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_POINT_CLASS ) ) {
                    let svgProxyLine = getPrecedingProxyLine( gSvgPathEditData.selectedProxyElement );
                    if ( svgProxyLine.length > 0 ) {
                        divideProxyLine( svgProxyLine );
                        return true;
                        
                    } else {
                        // Fallback for case of last proxy point selected.
                        let svgProxyLine = getFollowingProxyLine( gSvgPathEditData.selectedProxyElement );
                        if( svgProxyLine.length > 0 ) {
                            divideProxyLine( svgProxyLine );
                            return true;
                        }
                    }
                }
            }
        }
        if ( Hi.DEBUG ) { console.log( `Key down skipped [${MODULE_NAME}]` ); }
        return false;
    }

    function handleSvgPathClick( event, enclosingSvgGroup ) {
        const svgItemId = $(enclosingSvgGroup).attr('id');

        if ( Hi.isEditMode ) {
            clearSelectedPathSvgGroup();
            gSelectedPathSvgGroup = enclosingSvgGroup;
            expandSvgPath( enclosingSvgGroup );
            let data = {
                moduleName: MODULE_NAME,
            };
            Hi.edit.eventBus.emit( Hi.edit.SELECTION_MADE_EVENT_NAME, data );
            AN.get( `${Hi.API_LOCATION_ITEM_EDIT_MODE_URL}/${svgItemId}` );
        } else {
            AN.get( `${Hi.API_LOCATION_ITEM_STATUS_URL}/${svgItemId}` );
        }
    }

    function clearSelectedPathSvgGroup() {
        if ( gSelectedPathSvgGroup ) {
            console.log('Clearing svg path selection');
            collapseSvgPath( );
            gSelectedPathSvgGroup = null;
        }
    }
    
    function handleProxyPathClick( event ) {
        const isProxyElement = $(event.target).hasClass( PROXY_ITEM_CLASS );
        if ( isProxyElement ) {
            setSelectedProxyElement( event.target );
        }
        else {
            extendProxyPath( event );
        }
    }
    
    function setSelectedProxyElement( proxyElement ) {
        if ( ! gSvgPathEditData ) {
            return;
        }
        $(gSvgPathEditData.proxyPathContainer).find('.' + PROXY_ITEM_CLASS).removeClass( Hi.HIGHLIGHTED_CLASS );
        if ( proxyElement ) {
            $(proxyElement).addClass( Hi.HIGHLIGHTED_CLASS );
        }
        gSvgPathEditData.selectedProxyElement = proxyElement;
    }
    
    function expandSvgPath( pathSvgGroup ) {
        if ( Hi.DEBUG ) { console.log( 'Expand SVG Path', pathSvgGroup ); }

        pathSvgGroup.hide();

        const baseSvgElement = $(Hi.BASE_SVG_SELECTOR)[0];
        const proxyPathContainer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        proxyPathContainer.setAttribute('id', PROXY_PATH_CONTAINER_ID );
        baseSvgElement.appendChild( proxyPathContainer );
        
        gSvgPathEditData = {
            proxyPathContainer: proxyPathContainer,
            selectedProxyElement: null,
            dragProxyPoint: null,
        };
        
        let svgPathElement = $(pathSvgGroup).find('path');
        const pathData = svgPathElement.attr('d');
        const segments = pathData.match(/[ML][^MLZ]+|Z/g);
        if ( Hi.DEBUG ) { console.log('Path segments', segments ); }

        /* Algorithm Description:

           - We first create all the proxy points in the first loop.
           - This builds the data structures to handle possibly having multiple line segments.
           - We then iterate though all the line segments.
           - We'll create all the lines and handlers for "interior" lines/points.
           - Finally, we deal with the special cases of the first and last proxy points.
           - First and last proxy points have only one line unless it is a closed path.
           - If it is a closed path, we also need to add an extra line to close the figure.
           - We organize all the proxy item into SVG groups:
           - A SVG group excloses all with one child SVG group for each line segment (called a proxyPath)
           - Insert items in DOM in order since we rely on this ordering as a data structure.
           - Lines should be drawn before proxy points, so use a subgrouping for each type.
        */

        // - Create all proxy points.
        let currentProxyPathGroup = null;
        let currentProxyPointsGroup = null;
        for ( let i = 0; i < segments.length; i++ ) {
            
            let command = segments[i].charAt(0);  // M or L or Z
            let coords = segments[i].substring(1).trim().split(/[\s,]+/).map(Number);

            if (command === 'M') {
                currentProxyPathGroup = createProxyPathGroup( ProxyPathType.OPEN );
                $(proxyPathContainer).append( currentProxyPathGroup );
                
                let newProxyPoint = createProxyPathProxyPoint( coords[0], coords[1] );
                $(currentProxyPathGroup).find( PROXY_POINTS_GROUP_SELECTOR ).append( newProxyPoint );
                
            } else if (command === 'L' && currentProxyPathGroup ) {
                let newProxyPoint = createProxyPathProxyPoint( coords[0], coords[1] );
                $(currentProxyPathGroup).find( PROXY_POINTS_GROUP_SELECTOR ).append( newProxyPoint );

            } else if (command === 'Z' && currentProxyPathGroup ) {
                $(currentProxyPathGroup).attr( PROXY_PATH_TYPE_ATTR, ProxyPathType.CLOSED );
                currentProxyPathGroup = null;
            }
        }

        // Paths can have multiple segments
        $(proxyPathContainer).find( PROXY_PATH_GROUP_SELECTOR ).each(function( index, proxyPathGroup ) {

            if ( Hi.DEBUG ) { console.log( 'Proxy path group: ', proxyPathGroup ); }
            
            // Create interior lines and proxy point handlers with bookkeeping for first/last edge cases.
            let previousProxyPoint = null;
            let firstLine = null;
            let previousLine = null;

            let proxyLinesGroup = $(proxyPathGroup).find( PROXY_LINES_GROUP_SELECTOR );
            let proxyPoints = $(proxyPathGroup).find( PROXY_POINT_SELECTOR );
            
            $(proxyPoints).each(function( index, currentProxyPoint ) {

                if ( previousProxyPoint ) {
                    const x1 = parseFloat(previousProxyPoint.getAttribute('cx'));
                    const y1 = parseFloat(previousProxyPoint.getAttribute('cy'));
                    const x2 = parseFloat(currentProxyPoint.getAttribute('cx'));
                    const y2 = parseFloat(currentProxyPoint.getAttribute('cy'));
                    let currentLine = createProxyPathLine( previousProxyPoint, currentProxyPoint,
                                                           x1, y1, x2, y2 );
                    $(proxyLinesGroup).append( currentLine );
                    
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

            // Degerate cases of zero or one point and no lines.
            if ( proxyPoints.length < 2 ) {
                addProxyPointEventHandler( previousProxyPoint, null, null );
                return;
            }
            
            // Edge cases for first and last points.
            let firstProxyPoint = proxyPoints[0];
            let lastProxyPoint = proxyPoints[proxyPoints.length -1];
            
            if ( $(proxyPathGroup).attr( PROXY_PATH_TYPE_ATTR ) == ProxyPathType.OPEN ) {
                addProxyPointEventHandler( firstProxyPoint, null, firstLine );
                addProxyPointEventHandler( lastProxyPoint, previousLine, null );
            } else {
                const x1 = parseFloat(lastProxyPoint.getAttribute('cx'));
                const y1 = parseFloat(lastProxyPoint.getAttribute('cy'));
                const x2 = parseFloat(firstProxyPoint.getAttribute('cx'));
                const y2 = parseFloat(firstProxyPoint.getAttribute('cy'));
                let closureLine = createProxyPathLine( lastProxyPoint, firstProxyPoint,
                                                       x1, y1, x2, y2 );
                $(proxyLinesGroup).append( closureLine );
                addProxyPointEventHandler( firstProxyPoint, closureLine, firstLine );
                addProxyPointEventHandler( lastProxyPoint, previousLine, closureLine );
            }
        });
    }

    function extendProxyPath( event ) {
            
        console.log( 'Extending proxy path' );
        const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
        const svgViewBox = Hi.svgUtils.getSvgViewBox( baseSvgElement );
        let svgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement, event.clientX, event.clientY );

        // Do not allow creating points outside viewbox (else cannot manipulate them).
        if (( svgPoint.x < svgViewBox.x )
            || ( svgPoint.x > ( svgViewBox.x + svgViewBox.width ))
            || ( svgPoint.y < svgViewBox.y )
            || ( svgPoint.y > ( svgViewBox.y + svgViewBox.height )) ) {
            return;
        }

        let referenceElement = getReferenceElementForExtendingProxyPath();
        let proxyPathGroup = $(referenceElement).closest(PROXY_PATH_GROUP_SELECTOR);
        let newProxyPoint = null;
        
        if (  $(referenceElement).hasClass( PROXY_POINT_CLASS) ) {
            if ( $(proxyPathGroup).attr( PROXY_PATH_TYPE_ATTR ) == ProxyPathType.OPEN ) {
                if ( $(referenceElement).is(':first-of-type') ) {
                    newProxyPoint = prependNewProxyPoint( svgPoint, proxyPathGroup );

                } else {
                    newProxyPoint = appendNewProxyPoint( svgPoint, proxyPathGroup );
                }
            } else {
                let followingProxyLine = getFollowingProxyLine( referenceElement );
                newProxyPoint = insertNewProxyPoint( svgPoint, followingProxyLine );

            }
        } else if (  $(referenceElement).hasClass( PROXY_LINE_CLASS ) ) {
            newProxyPoint = insertNewProxyPoint( svgPoint, referenceElement );
        } else {
            console.log( 'Unrecognized reference proxy element.' );
            return;
        }
        
        if ( newProxyPoint ) {
            setSelectedProxyElement( newProxyPoint );
            saveSvgPath();
        }
    }
    
    function prependNewProxyPoint( newSvgPoint, proxyPathGroup ) {

        let firstProxyPoint = proxyPathGroup.find( PROXY_POINT_SELECTOR ).first();
        let firstLine = proxyPathGroup.find( PROXY_LINE_SELECTOR ).first();

        if ( Hi.DEBUG ) { console.log( 'Prepend: First point and line: ', firstProxyPoint, firstLine ); }
        
        const firstX = parseFloat( $(firstProxyPoint).attr('cx') );
        const firstY = parseFloat( $(firstProxyPoint).attr('cy') );

        let newProxyPoint = createProxyPathProxyPoint( newSvgPoint.x, newSvgPoint.y );
        let newLine = createProxyPathLine( newProxyPoint, firstProxyPoint,
                                           newSvgPoint.x, newSvgPoint.y, firstX, firstY );

        let proxyPointsGroup = $(proxyPathGroup).find( PROXY_POINTS_GROUP_SELECTOR );
        let proxyLinesGroup = $(proxyPathGroup).find( PROXY_LINES_GROUP_SELECTOR );
        $(proxyPointsGroup).prepend( newProxyPoint );
        $(proxyLinesGroup).prepend( newLine );
        
        $(firstProxyPoint).off();  // Removes event listeners
        addProxyPointEventHandler( firstProxyPoint, newLine, firstLine );
        addProxyPointEventHandler( newProxyPoint, null, newLine );

        return newProxyPoint;
    }

    function appendNewProxyPoint( newSvgPoint, proxyPathGroup ) {

        let lastProxyPoint = proxyPathGroup.find( PROXY_POINT_SELECTOR ).last();
        let lastLine = proxyPathGroup.find( PROXY_LINE_SELECTOR ).last();

        if ( Hi.DEBUG ) { console.log( 'Append: Last point and line: ', lastProxyPoint, lastLine ); }
        
        const lastX = parseFloat($(lastProxyPoint).attr('cx'));
        const lastY = parseFloat($(lastProxyPoint).attr('cy'));

        let newProxyPoint = createProxyPathProxyPoint( newSvgPoint.x, newSvgPoint.y );
        let newLine = createProxyPathLine( lastProxyPoint, newProxyPoint,
                                           lastX, lastY, newSvgPoint.x, newSvgPoint.y );

        let proxyPointsGroup = $(proxyPathGroup).find( PROXY_POINTS_GROUP_SELECTOR );
        let proxyLinesGroup = $(proxyPathGroup).find( PROXY_LINES_GROUP_SELECTOR );
        $(proxyPointsGroup).append( newProxyPoint );
        $(proxyLinesGroup).append( newLine );
        
        $(lastProxyPoint).off();  // Removes event listeners
        addProxyPointEventHandler( lastProxyPoint, lastLine, newLine );
        addProxyPointEventHandler( newProxyPoint, newLine, null );

        return newProxyPoint;   
    }

    function insertNewProxyPoint( newSvgPoint, referenceProxyLine ) {

        const beforeProxyPointId = $(referenceProxyLine).attr( BEFORE_PROXY_POINT_ID );
        const afterProxyPointId = $(referenceProxyLine).attr( AFTER_PROXY_POINT_ID );

        let beforeProxyPoint = $('#' + beforeProxyPointId );
        let afterProxyPoint = $('#' + afterProxyPointId );
        let followingProxyLine = getFollowingProxyLine( afterProxyPoint );
        
        if ( Hi.DEBUG ) { console.log( 'Insert: ', referenceProxyLine, beforeProxyPoint,
                                    afterProxyPoint, followingProxyLine ); }

        const beforeX = parseFloat($(beforeProxyPoint).attr('cx'));
        const beforeY = parseFloat($(beforeProxyPoint).attr('cy'));

        const afterX = parseFloat($(afterProxyPoint).attr('cx'));
        const afterY = parseFloat($(afterProxyPoint).attr('cy'));

        let newProxyPoint = createProxyPathProxyPoint( newSvgPoint.x, newSvgPoint.y );
        let newLine = createProxyPathLine( newProxyPoint, afterProxyPoint,
                                           newSvgPoint.x, newSvgPoint.y, afterX, afterY );

        $(referenceProxyLine).attr( AFTER_PROXY_POINT_ID, $(newProxyPoint).attr('id') );
        $(referenceProxyLine).attr( 'x2', newSvgPoint.x );
        $(referenceProxyLine).attr( 'y2', newSvgPoint.y );

        $(beforeProxyPoint).after( newProxyPoint );
        $(referenceProxyLine).after( newLine );
        
        $(afterProxyPoint).off();  // Removes event listeners
        addProxyPointEventHandler( afterProxyPoint, newLine, followingProxyLine );
        addProxyPointEventHandler( newProxyPoint, referenceProxyLine, newLine );

        return newProxyPoint;   
    }

    function deleteProxyPoint( svgProxyPoint ) {

        let proxyPathGroup = $(svgProxyPoint).closest( PROXY_PATH_GROUP_SELECTOR );
        let proxyPathType = $(proxyPathGroup).attr( PROXY_PATH_TYPE_ATTR );
        let proxyPointsGroup = $(svgProxyPoint).closest( PROXY_POINTS_GROUP_SELECTOR );
        let minPoints = 2;
        if ( proxyPathType == ProxyPathType.CLOSED ) {
            minPoints = 3;
        }
        if ( $(proxyPointsGroup).children().length <= minPoints ) {
            removeProxyPathIfAllowed( proxyPathGroup );
            return;
        }
        
        let svgProxyPointId = $(svgProxyPoint).attr('id');

        let beforeProxyLine = getPrecedingProxyLine( svgProxyPoint );
        let afterProxyLine = getFollowingProxyLine( svgProxyPoint );
        
        if (( beforeProxyLine.length > 0 ) && ( afterProxyLine.length > 0)) {

            let afterProxyPointId = $(afterProxyLine).attr( AFTER_PROXY_POINT_ID );
            let afterProxyPoint = $('#' + afterProxyPointId);
            let followingProxyLine = getFollowingProxyLine( afterProxyPoint );

            const afterX = parseFloat( $(afterProxyPoint).attr('cx') );
            const afterY = parseFloat( $(afterProxyPoint).attr('cy') );
            $(beforeProxyLine).attr( AFTER_PROXY_POINT_ID, $(afterProxyPoint).attr('id') );
            $(beforeProxyLine).attr( 'x2', afterX );
            $(beforeProxyLine).attr( 'y2', afterY );

            $(afterProxyPoint).off();  // Removes event listeners
            addProxyPointEventHandler( afterProxyPoint, beforeProxyLine, followingProxyLine );

            $(svgProxyPoint).remove();
            $(afterProxyLine).remove();

            setSelectedProxyElement( afterProxyPoint );
            
        } else if ( afterProxyLine.length > 0 ) {

            let afterProxyPointId = $(afterProxyLine).attr( AFTER_PROXY_POINT_ID );
            let afterProxyPoint = $('#' + afterProxyPointId);
            let followingProxyLine = getFollowingProxyLine( afterProxyPoint );

            $(afterProxyPoint).off();  // Removes event listeners
            addProxyPointEventHandler( afterProxyPoint, null, followingProxyLine );

            $(svgProxyPoint).remove();
            $(afterProxyLine).remove();

            setSelectedProxyElement( afterProxyPoint );     
            
        } else if ( beforeProxyLine.length > 0 ) {
            let beforeProxyPointId = $(beforeProxyLine).attr( BEFORE_PROXY_POINT_ID );
            let beforeProxyPoint = $('#' + beforeProxyPointId);
            let precedingProxyLine =getPrecedingProxyLine( beforeProxyPoint );

            $(beforeProxyPoint).off();  // Removes event listeners
            addProxyPointEventHandler( beforeProxyPoint, precedingProxyLine, null );

            $(svgProxyPoint).remove();
            $(beforeProxyLine).remove();

            setSelectedProxyElement( beforeProxyPoint );            
            
        } else {
            $(svgProxyPoint).remove();
            setSelectedProxyElement( null );        
        }

        saveSvgPath();
    }
    
    function deleteProxyLine( svgProxyLine ) {
        // Acts like a delete for 'before' proxy point.
        let beforeProxyPointId = $(svgProxyLine).attr( BEFORE_PROXY_POINT_ID );
        let beforeProxyPoint = $('#' + beforeProxyPointId);
        deleteProxyPoint( beforeProxyPoint );
    }
    
    function divideProxyLine( svgProxyLine ) {
        // Same as inserting via mouse click, but use midpoint as the insertion point.

        let beforeProxyPointId = $(svgProxyLine).attr( BEFORE_PROXY_POINT_ID );
        let afterProxyPointId = $(svgProxyLine).attr( AFTER_PROXY_POINT_ID );
        let beforeProxyPoint = $('#' + beforeProxyPointId);
        let afterProxyPoint = $('#' + afterProxyPointId);

        const beforeX = parseFloat($(beforeProxyPoint).attr('cx'));
        const beforeY = parseFloat($(beforeProxyPoint).attr('cy'));

        const afterX = parseFloat($(afterProxyPoint).attr('cx'));
        const afterY = parseFloat($(afterProxyPoint).attr('cy'));

        let midSvgPoint = {
            x: ( beforeX + afterX ) / 2,
            y: ( beforeY + afterY ) / 2
        };
        insertNewProxyPoint( midSvgPoint, svgProxyLine );
        saveSvgPath();
    }

    function addProxyPath( ) {

        let proxyPathContainer = $('#' + PROXY_PATH_CONTAINER_ID );
        let firstProxyPath = $(proxyPathContainer).find( PROXY_PATH_GROUP_SELECTOR ).first();
        let proxyPathType = $(firstProxyPath).attr( PROXY_PATH_TYPE_ATTR );
        let newProxyPathGroup = createProxyPathGroup( proxyPathType );
        $(proxyPathContainer).append( newProxyPathGroup );

        const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
        const svgViewBox = Hi.svgUtils.getSvgViewBox( baseSvgElement );
        let svgCenter = {
            x: svgViewBox.x + ( svgViewBox.width / 2 ),
            y: svgViewBox.y + ( svgViewBox.height / 2 )
        };
        let svgUnitRadius = {
            x: svgViewBox.width * ( PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 ),
            y: svgViewBox.height * ( PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 )
        };

        if ( Hi.DEBUG ) { console.log( 'Add proxy path.', svgViewBox, svgCenter ); }
                       
        let proxyPointsGroup = $(newProxyPathGroup).find( PROXY_POINTS_GROUP_SELECTOR );
        let proxyLinesGroup = $(newProxyPathGroup).find( PROXY_LINES_GROUP_SELECTOR );

        if ( proxyPathType == ProxyPathType.OPEN ) {

            const leftSvgPoint = {
                x: svgCenter.x - svgUnitRadius.x,
                y: svgCenter.y,
            };
            const rightSvgPoint = {
                x: svgCenter.x + svgUnitRadius.x,
                y: svgCenter.y,
            };
            
            let beforeProxyPoint = createProxyPathProxyPoint( leftSvgPoint.x, leftSvgPoint.y );
            let afterProxyPoint = createProxyPathProxyPoint( rightSvgPoint.x, rightSvgPoint.y );
            proxyPointsGroup.append( beforeProxyPoint );
            proxyPointsGroup.append( afterProxyPoint );
            
            let newProxyLine = createProxyPathLine( beforeProxyPoint, afterProxyPoint,
                                                    leftSvgPoint.x, leftSvgPoint.y,
                                                    rightSvgPoint.x, rightSvgPoint.y );
            $(proxyLinesGroup).append( newProxyLine );

            addProxyPointEventHandler( beforeProxyPoint, null, newProxyLine );
            addProxyPointEventHandler( afterProxyPoint, newProxyLine, null );
            
        } else if ( proxyPathType == ProxyPathType.CLOSED ) {

            const topLeftSvgPoint = {
                x: svgCenter.x - svgUnitRadius.x,
                y: svgCenter.y - svgUnitRadius.y,
            };
            const topRightSvgPoint = {
                x: svgCenter.x + svgUnitRadius.x,
                y: svgCenter.y - svgUnitRadius.y,
            };
            const bottomRightSvgPoint = {
                x: svgCenter.x + svgUnitRadius.x,
                y: svgCenter.y + svgUnitRadius.y,
            };
            const bottomLeftSvgPoint = {
                x: svgCenter.x - svgUnitRadius.x,
                y: svgCenter.y + svgUnitRadius.y,
            };

            let topLeftProxyPoint = createProxyPathProxyPoint( topLeftSvgPoint.x,
                                                                 topLeftSvgPoint.y );
            let topRightProxyPoint = createProxyPathProxyPoint( topRightSvgPoint.x,
                                                                  topRightSvgPoint.y );
            let bottomRightProxyPoint = createProxyPathProxyPoint( bottomRightSvgPoint.x,
                                                                     bottomRightSvgPoint.y );
            let bottomLeftProxyPoint = createProxyPathProxyPoint( bottomLeftSvgPoint.x,
                                                                    bottomLeftSvgPoint.y );
            proxyPointsGroup.append( topLeftProxyPoint );
            proxyPointsGroup.append( topRightProxyPoint );
            proxyPointsGroup.append( bottomRightProxyPoint );
            proxyPointsGroup.append( bottomLeftProxyPoint );

            let topProxyLine = createProxyPathLine( topLeftProxyPoint, topRightProxyPoint,
                                                    topLeftSvgPoint.x, topLeftSvgPoint.y,
                                                    topRightSvgPoint.x, topRightSvgPoint.y );
            let rightProxyLine = createProxyPathLine( topRightProxyPoint, bottomRightProxyPoint,
                                                      topRightSvgPoint.x, topRightSvgPoint.y,
                                                      bottomRightSvgPoint.x, bottomRightSvgPoint.y );
            let bottomProxyLine = createProxyPathLine( bottomRightProxyPoint, bottomLeftProxyPoint,
                                                       bottomRightSvgPoint.x, bottomRightSvgPoint.y,
                                                       bottomLeftSvgPoint.x, bottomLeftSvgPoint.y );
            let leftProxyLine = createProxyPathLine( bottomLeftProxyPoint, topLeftProxyPoint,
                                                     bottomLeftSvgPoint.x, bottomLeftSvgPoint.y,
                                                     topLeftSvgPoint.x, topLeftSvgPoint.y );
            $(proxyLinesGroup).append( topProxyLine );
            $(proxyLinesGroup).append( rightProxyLine );
            $(proxyLinesGroup).append( bottomProxyLine );
            $(proxyLinesGroup).append( leftProxyLine );

            addProxyPointEventHandler( topLeftProxyPoint, leftProxyLine, topProxyLine );
            addProxyPointEventHandler( topRightProxyPoint, topProxyLine, rightProxyLine );
            addProxyPointEventHandler( bottomRightProxyPoint, rightProxyLine, bottomProxyLine );
            addProxyPointEventHandler( bottomLeftProxyPoint, bottomProxyLine, leftProxyLine );

        } else {
            console.log( `Unknown proxy path type: ${proxyPathType}` );
        }
        saveSvgPath();  
    }

    function removeProxyPathIfAllowed( targetProxyPathGroup ) {
        let proxyPathContainer = $('#' + PROXY_PATH_CONTAINER_ID );
        let proxyPathGroups = $(proxyPathContainer).find( PROXY_PATH_GROUP_SELECTOR );
        if ( proxyPathGroups.length < 2 ) {
            return;
        }
        $(targetProxyPathGroup).remove();
        setSelectedProxyElement( null );            
        saveSvgPath();
    }
    
    function createProxyPathGroup( proxyPathType ) {
        let proxyPathGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        proxyPathGroup.setAttribute('id', Hi.generateUniqueId() );
        proxyPathGroup.setAttribute('class', PROXY_PATH_CLASS );
        proxyPathGroup.setAttribute( PROXY_PATH_TYPE_ATTR, proxyPathType );

        // Lines should come before points so mouse clicks land on points before lines.
        let proxyLinesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        proxyLinesGroup.setAttribute('class', PROXY_LINES_CLASS );
        proxyPathGroup.appendChild( proxyLinesGroup );

        let proxyPointsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        proxyPointsGroup.setAttribute('class', PROXY_POINTS_CLASS );
        proxyPathGroup.appendChild( proxyPointsGroup );

        return proxyPathGroup;
    }
    
    function createProxyPathProxyPoint( cx, cy ) {
        const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
        const pixelsPerSvgUnit = Hi.svgUtils.getPixelsPerSvgUnit( baseSvgElement );
        const svgRadius = PATH_EDIT_PROXY_POINT_RADIUS_PIXELS / pixelsPerSvgUnit.scaleX;
        
        const proxyPoint = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        proxyPoint.setAttribute('cx', cx);
        proxyPoint.setAttribute('cy', cy);
        proxyPoint.setAttribute('r', svgRadius);
        proxyPoint.setAttribute('id', Hi.generateUniqueId() );
        $(proxyPoint).addClass( 'draggable');
        $(proxyPoint).addClass( PROXY_ITEM_CLASS );
        $(proxyPoint).addClass( PROXY_POINT_CLASS );
        proxyPoint.setAttribute('fill', PATH_EDIT_PROXY_POINT_COLOR );
        proxyPoint.setAttribute('vector-effect', 'non-scaling-stroke');
        return proxyPoint;
    }

    function createProxyPathLine( beforeProxyPoint, afterProxyPoint, x1, y1, x2, y2, ) {
        const proxyLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        proxyLine.setAttribute('x1', x1);
        proxyLine.setAttribute('y1', y1);
        proxyLine.setAttribute('x2', x2);
        proxyLine.setAttribute('y2', y2);
        $(proxyLine).addClass( PROXY_ITEM_CLASS );
        $(proxyLine).addClass( PROXY_LINE_CLASS );
        proxyLine.setAttribute( BEFORE_PROXY_POINT_ID, $(beforeProxyPoint).attr('id') );
        proxyLine.setAttribute( AFTER_PROXY_POINT_ID, $(afterProxyPoint).attr('id'));
        proxyLine.setAttribute('stroke', PATH_EDIT_PROXY_LINE_COLOR );
        proxyLine.setAttribute('stroke-width', PATH_EDIT_PROXY_LINE_WIDTH_PIXELS );
        proxyLine.setAttribute('vector-effect', 'non-scaling-stroke');
        return proxyLine;
    }
    
    function addProxyPointEventHandler( proxyPoint, beforeProxyLine, afterProxyLine ) {
        // Drag logic for the proxy point
        $(proxyPoint).on('mousedown', function( event ) {
            event.preventDefault();
            event.stopImmediatePropagation();

            let startMousePosition = {
                x: event.clientX,
                y: event.clientY
            };

            const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);         
            const eventSvgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement, event.clientX, event.clientY );

            
            const offsetX = eventSvgPoint.x - parseFloat($(proxyPoint).attr('cx'));
            const offsetY = eventSvgPoint.y - parseFloat($(proxyPoint).attr('cy'));

            let isDragging = false;
            
            // Function to handle mouse movement
            function onMouseMove( event ) {
                if ( ! gSvgPathEditData ) {
                    return;
                }
                
                let currentMousePosition = {
                    x: event.clientX,
                    y: event.clientY
                };
                const distanceX = Math.abs( currentMousePosition.x - startMousePosition.x );
                const distanceY = Math.abs( currentMousePosition.y - startMousePosition.y );

                if ( isDragging
                     || ( distanceX > CURSOR_MOVEMENT_THRESHOLD_PIXELS )
                     || ( distanceY > CURSOR_MOVEMENT_THRESHOLD_PIXELS )) {
                    isDragging = true;
                    event.preventDefault();
                    event.stopImmediatePropagation();

                    const eventSvgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement,
                                                                  event.clientX,
                                                                  event.clientY );
                    
                    gSvgPathEditData.dragProxyPoint = event.target;
                    const newCx = eventSvgPoint.x - offsetX;
                    const newCy = eventSvgPoint.y - offsetY;
                    $(proxyPoint).attr('cx', newCx).attr('cy', newCy);

                    // Update the line endpoints to follow proxy point movement
                    if ( $(beforeProxyLine).length > 0 ) {
                        $(beforeProxyLine).attr('x2', newCx).attr('y2', newCy);
                    }
                    if ( $(afterProxyLine).length > 0 ) {
                        $(afterProxyLine).attr('x1', newCx).attr('y1', newCy);
                    }

                    setSelectedProxyElement(proxyPoint);
                }
            }

            // Function to handle mouse up (end of drag)
            function onMouseUp( event ) {
                if ( ! gSvgPathEditData ) {
                    return;
                }

                event.preventDefault();
                event.stopImmediatePropagation();
                saveSvgPath();
                gSvgPathEditData.dragProxyPoint = null;
                if ( isDragging ) {
                    gIgnoreCLick = true;
                }
                $(document).off('mousemove', onMouseMove);
                $(document).off('mouseup', onMouseUp);
            }

            // Bind the mousemove and mouseup handlers using jQuery
            $(document).on('mousemove', onMouseMove);
            $(document).on('mouseup', onMouseUp);
        });
    }
    
    function collapseSvgPath( ) {
        if ( Hi.DEBUG ) { console.log( 'Collapse SVG Path' ); }

        let newSvgPath = getSvgPathStringFromProxyPaths();
        $(gSelectedPathSvgGroup).find('path').attr( 'd', newSvgPath );

        const proxyPathContainer = $( '#' + PROXY_PATH_CONTAINER_ID );
        $(proxyPathContainer).remove();

        gSelectedPathSvgGroup.show();

        gSvgPathEditData = null;
    }

    function saveSvgPath() {
        if ( ! gSelectedPathSvgGroup ) {
            return;
        }

        let svgItemId = $(gSelectedPathSvgGroup).attr('id');
        let svgPathString = getSvgPathStringFromProxyPaths();
        let data = {
            svg_path: svgPathString
        };
        AN.post( `${API_EDIT_SVG_PATH_URL}/${svgItemId}`, data );
    }
    
    function getSvgPathStringFromProxyPaths() {
        const proxyPathContainer = $( '#' + PROXY_PATH_CONTAINER_ID );
        const proxyPathGroups = $(proxyPathContainer).find( PROXY_PATH_GROUP_SELECTOR );
        
        let pathString = '';
        $(proxyPathGroups).each(function( index, proxyPathGroup ) {

            let proxyPoints = $(proxyPathGroup).find( PROXY_POINT_SELECTOR );
            $(proxyPoints).each(function( index, proxyPoint ) {
                if ( index == 0 ) {
                    pathString += ' M ';
                } else {
                    pathString += ' L ';
                }
                pathString += proxyPoint.getAttribute('cx') + ',' + proxyPoint.getAttribute('cy');
            });
            if ( $(proxyPathGroup).attr( PROXY_PATH_TYPE_ATTR ) == ProxyPathType.CLOSED ) {
                pathString += ' Z';
            }

        });

        console.log( `PATH = ${pathString}` );
        return pathString;
    }
    
    function getReferenceElementForExtendingProxyPath( ) {
        if ( gSvgPathEditData.selectedProxyElement ) {
            return gSvgPathEditData.selectedProxyElement;
        }
        let lastProxyPath = $(gSvgPathEditData.proxyPathContainer).find( PROXY_PATH_GROUP_SELECTOR ).last();
        let lastProxyPoint = lastProxyPath.find( PROXY_POINT_SELECTOR ).last();
        return lastProxyPoint;
    }

    function getPrecedingProxyLine( proxyPoint ) {
        const proxyPointId = $(proxyPoint).attr('id');
        return $('line[' + AFTER_PROXY_POINT_ID + '="' + proxyPointId + '"]');
    }
    
    function getFollowingProxyLine( proxyPoint ) {
        const proxyPointId = $(proxyPoint).attr('id');
        return $('line[' + BEFORE_PROXY_POINT_ID + '="' + proxyPointId + '"]');
    }
    
})();
