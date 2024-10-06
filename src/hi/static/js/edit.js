(function() {
    const DEBUG = true;

    window.Hi = window.Hi || {};

    const HiEdit = {
	editThing: function() {
            return true;
	}
    };
    
    window.Hi.edit = HiEdit;

    const LOCATION_VIEW_AREA_SELECTOR = '#hi-location-view-main';
    const BASE_SVG_SELECTOR = '#hi-location-view-main > svg';
    const HIGHLIGHTED_CLASS = 'highlighted';

    const DRAGGABLE_CONTAINER_CLASS = 'draggable-container';
    const DRAGGABLE_CONTAINER_SELECTOR = '.' + DRAGGABLE_CONTAINER_CLASS;
    const DRAGGABLE_CLASS = 'draggable';
    const DRAGGABLE_SELECTOR = '.' + DRAGGABLE_CLASS;
    const DRAG_OVER_CLASS = 'drag-over';
    const DATA_ID_ATTR = 'data-id';
    const DATA_TYPE_ATTR = 'data-type';
    const DATA_TYPE_ICON_VALUE = 'svg-icon';
    const DATA_TYPE_PATH_VALUE = 'svg-path';
    const SELECTABLE_CLASS = 'selectable';
    const SELECTABLE_SELECTOR = '.' + SELECTABLE_CLASS;
    
    const API_REORDER_ITEMS_URL = '/edit/reorder-items';
    const API_EDIT_DETAILS_URL = '/edit/details';
    const API_EDIT_SVG_POSITION_URL = '/edit/svg/position';
    const API_EDIT_SVG_PATH_URL = '/edit/svg/path';
    
    const ICON_ACTION_STATE_ATTR_NAME = 'action-state';
    const ICON_ACTION_SCALE_KEY = 's';
    const ICON_ACTION_ROTATE_KEY = 'r';

    const CLICK_HOLD_THRESHOLD_MS = 50; // For ignoreing very short, transient clicks
    const DOUBLE_CLICK_DELAY_MS = 250;
    const CURSOR_MOVEMENT_THRESHOLD_PIXELS = 3;

    const SvgActionStateType = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };
    
    let gSvgIconActionState = SvgActionStateType.MOVE;
    let gSelectedIconSvgGroup = null;
    let gSvgIconDragData = null;
    let gSvgIconActionData = null;

    let gSelectedPathSvgGroup = null;
    let gSvgPathEditData = null;
    
    let gClickStart = null;
    let gClickTimeout = null;
    let gLastMousePosition = { x: 0, y: 0 };

    // For re-ordering items (buttons, lists, etc)
    let gDraggedElement = null;

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

    const PATH_EDIT_PROXY_POINT_RADIUS_PIXELS = 12;
    const PATH_EDIT_PROXY_LINE_WIDTH_PIXELS = 5;
    const PATH_EDIT_NEW_PATH_RADIUS_PERCENT = 5; // Better if it matches server default path sizing.
    const PATH_EDIT_PROXY_LINE_COLOR = 'red';
    const PATH_EDIT_PROXY_POINT_COLOR = 'red';
    
    const ProxyPathType = {
	OPEN: 'open',
	CLOSED: 'closed'
    };
    
    
    $(document).ready(function() {

	$('.draggable').on('dragstart', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragStart( event );
	});
	$('.draggable').on('dragend', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragEnd( event );
	});
	$('.draggable').on('dragover', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragOver( event );
	});
	$('.draggable').on('dragenter', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragEnter( event );
	});
	$('.draggable').on('dragleave', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragLeave( event );
	});

	$(document).on('mousedown', LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseDown( event );
	});
	$(document).on('mousemove', LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseMove( event );
	});
	$(document).on('mouseup', LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseUp( event );
	});
	$(document).on('keydown', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleKeyDown( event );
	});
	$(document).on('keyup', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleKeyUp( event );
	});
    });

    function handleDragStart( event ) {
	if ( DEBUG ) { console.log('event.currentTarget:', event.currentTarget); }

        gDraggedElement = event.currentTarget;
	
        // Hide the dragged element during the drag operation for better visuals
        setTimeout(() => {
            $(gDraggedElement).hide();
	    console.log('Hidden class added');
        }, 0);
    }
    
    function handleDragEnd( event ) {
	if ( DEBUG ) { console.log('Drag end:'); }
        $(gDraggedElement).show();
        gDraggedElement = null;
	$( DRAGGABLE_SELECTOR ).removeClass( DRAG_OVER_CLASS );
	$( DRAGGABLE_SELECTOR ).css('transform', '');
	
        var htmlIdList = [];
	var parentContainer = $(event.currentTarget).closest( DRAGGABLE_CONTAINER_SELECTOR );
        parentContainer.find( DRAGGABLE_SELECTOR ).each(function() {
            htmlIdList.push( $(this).attr( DATA_ID_ATTR ));
        });
	
	if ( DEBUG ) { console.log(`Drag end ids: ${htmlIdList}`); }

	let data = {
	    html_id_list: JSON.stringify( htmlIdList ),
	};
	AN.post( API_REORDER_ITEMS_URL, data );
    }
    
    function handleDragOver( event ) {
	if ( DEBUG ) { console.log('Drag over:'); }
        event.preventDefault();
	
        // Ensure the dragged element is in the same parent container
        if (( gDraggedElement !== event.currentTarget )
	    && ( $(event.currentTarget).parent()[0] === $(gDraggedElement).parent()[0] )) {
            const bounding = event.currentTarget.getBoundingClientRect();
            const offset = bounding.y + bounding.height / 2;

            // Insert dragged element before or after depending on mouse position
            if (event.clientY - offset > 0) {
                $(event.currentTarget).css('transform', 'translateX(50px)');
               $(event.currentTarget).after(gDraggedElement);
            } else {
                $(event.currentTarget).css('transform', 'translateX(-50px)');
               $(event.currentTarget).before(gDraggedElement);
            }
        }	
    }
    
    function handleDragEnter( event ) {
	if ( DEBUG ) { console.log('Drag enter:'); }
	// Only allow visual feedback if in the same parent container
        if ( $(event.currentTarget).parent()[0] === $(gDraggedElement).parent()[0] ) {
            $(event.currentTarget).addClass( DRAG_OVER_CLASS );
        }
    }
    
    function handleDragLeave( event ) {
	if ( DEBUG ) { console.log('Drag leave:'); }
	$(event.currentTarget).removeClass( DRAG_OVER_CLASS );
	$(event.currentTarget).css('transform', '');  
    }
    
    function handleMouseDown( event ) {
	if ( DEBUG ) {
            displayEventInfo( 'Mouse down event: ', event );
            displayElementInfo( 'Event target: ', $(event.target) );
	}

	// Path editing does its own special mouse event handling on a per-element basis..
	if ( gSvgPathEditData ) {
	    return;
	}
	
	// Need to track start time to differentiate drag/scale/rotate actions from regular clicks.
	gClickStart = {
	    x: event.clientX,
	    y: event.clientY,
	    time: Date.now()
	};
	
	if ( gSvgIconActionState == SvgActionStateType.MOVE ) {

	    const enclosingSvgGroup = $(event.target).closest('g');
	    if ( enclosingSvgGroup.length < 1 ) {
		return;
	    }
	    const svgDataType = $(enclosingSvgGroup).attr( DATA_TYPE_ATTR );
	    if ( svgDataType == DATA_TYPE_ICON_VALUE ) {
		createIconDragData( event, enclosingSvgGroup );
	    }
	    return;
	} 
	if ( gSvgIconActionData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionData.isScaling = true;
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionData.isRotating = true;
	    }
	}
    }
    
    function handleMouseUp( event ) {
	if ( gSvgIconDragData ) {
	    if ( gSvgIconDragData.isDragging ) {
		endDrag( event );
		$(BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '');
		return;
	    }
	    $(BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '' );
	    gSvgIconDragData = null;
	}
	
	else if ( gSvgIconActionData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionData.isScaling = false;
		iconActionScaleApply();
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionData.isRotating = false;
		iconActionRotateApply();
	    }
	    gSvgIconActionState = SvgActionStateType.MOVE;
	    $(BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '');
	    gSvgIconActionData = null;

	} else if ( gSvgPathEditData && gSvgPathEditData.dragProxyPoint ) {
	    return;
	} else {
	    const clickEndTime = Date.now();
	    const elapsedTime = clickEndTime - gClickStart.time;
	    if ( DEBUG ) { console.log( `Click Elapsed: ${elapsedTime}` ); }
	    if (elapsedTime < CLICK_HOLD_THRESHOLD_MS) {
		return;
	    }
	    if ( gClickTimeout ) {
		clearTimeout( gClickTimeout );
		gClickTimeout = null;
		if ( elapsedTime < DOUBLE_CLICK_DELAY_MS ) {
		    handleDoubleClick( event );
		}
	    } else {
		gClickTimeout = setTimeout(() => {
		    gClickTimeout = null;
		    handleClick( event );
		}, DOUBLE_CLICK_DELAY_MS );
	    }
	}
    }
    
    function handleMouseMove( event ) {

	const currentMousePosition = {
	    x: event.clientX,
	    y: event.clientY
	};
	
	if ( gSvgIconDragData ) {
	    const distanceX = Math.abs( currentMousePosition.x - gClickStart.x );
	    const distanceY = Math.abs( currentMousePosition.y - gClickStart.y );
	    
	    if ( gSvgIconDragData.isDragging
		 || ( distanceX > CURSOR_MOVEMENT_THRESHOLD_PIXELS )
		 || ( distanceY > CURSOR_MOVEMENT_THRESHOLD_PIXELS )) {
		gSvgIconDragData.isDragging = true;
		$(BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, SvgActionStateType.MOVE);
		updateDrag(event);
	    }
	}
	else if ( gSvgIconActionData ) {
	    if ( gSvgIconActionData.isScaling ) {
		iconActionScaleUpdate( currentMousePosition );
	    } else if ( gSvgIconActionData.isRotating ) {
		iconActionRotateUpdate( currentMousePosition );
	    }
	}
	
	gLastMousePosition = currentMousePosition;
    }
    
    function handleKeyDown( event ) {
	if ( $(event.target).is('input[type="text"], textarea') ) {
            return;
	}
	else if ( gSelectedIconSvgGroup ) {
	    handleSvgIconSelectedKeyDown( event );
	}
	else if ( gSvgPathEditData ) {
	    handleSvgPathEditKeyDown( event );
	}
    }

    function handleSvgIconSelectedKeyDown( event ) {
	const targetArea = $(LOCATION_VIEW_AREA_SELECTOR);
        const targetOffset = targetArea.offset();
        const targetWidth = targetArea.outerWidth();
        const targetHeight = targetArea.outerHeight();
	
        if (gLastMousePosition.x >= targetOffset.left && 
	    gLastMousePosition.x <= targetOffset.left + targetWidth &&
	    gLastMousePosition.y >= targetOffset.top &&
	    gLastMousePosition.y <= targetOffset.top + targetHeight) {

            displayEventInfo( 'Key Down', event );

	    if ( event.key == ICON_ACTION_SCALE_KEY ) {
		iconActionRotateAbort();
		iconActionScaleStart();
		
	    } else if ( event.key == ICON_ACTION_ROTATE_KEY ) {
		iconActionScaleAbort();
		iconActionRotateStart();
		
	    } else if ( event.key == 'Escape' ) {
		iconActionScaleAbort();
		iconActionRotateAbort();
		gSvgIconActionState = SvgActionStateType.MOVE;
		$(BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '');
		
	    } else {
		return;
	    }
	
	    event.stopPropagation();
	    event.preventDefault();   		
        }
    }
    
    function handleKeyUp( event ) {
        displayEventInfo( 'Key Up', event );
    }

    function handleClick( event ) {
        displayEventInfo( 'Click', event );
        displayElementInfo( 'Event Target', $(event.target) );
		
	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length > 0 ) {
            displayElementInfo( 'SVG Target Element', enclosingSvgGroup );
	    const selectable = $(enclosingSvgGroup).hasClass( SELECTABLE_CLASS );
	    const svgItemId = enclosingSvgGroup.attr('id');
	    if ( selectable && svgItemId ) {
		handleSvgItemClick( event, enclosingSvgGroup );
		return;
	    }
	}

	if ( gSvgPathEditData ) {
	    handleSvgPathEditClick( event );
	} else {
	    if ( DEBUG ) { console.log( 'No SVG group for click target'  ); }
	    clearSelectedAll();
            AN.get( API_EDIT_DETAILS_URL );
	    return;
	}
    }

    function handleSvgItemClick( event, enclosingSvgGroup ) {
	const svgItemId = $(enclosingSvgGroup).attr('id');
	const svgDataType = $(enclosingSvgGroup).attr( DATA_TYPE_ATTR );
	if ( svgDataType == DATA_TYPE_ICON_VALUE ) {
	    clearSelectedAll();
	    gSelectedIconSvgGroup = enclosingSvgGroup;
            $(enclosingSvgGroup).addClass( HIGHLIGHTED_CLASS );
            AN.get( `${API_EDIT_DETAILS_URL}/${svgItemId}` );
	    
	} else if ( svgDataType == DATA_TYPE_PATH_VALUE ) {
	    clearSelectedAll();
	    gSelectedPathSvgGroup = enclosingSvgGroup;
	    expandSvgPath( enclosingSvgGroup );
            AN.get( `${API_EDIT_DETAILS_URL}/${svgItemId}` );
	    
	} else {
	    if ( DEBUG ) { console.log( `Unrecognized SVG group "${svgDataType}" for click target`  ); }
	}
	
    }
    
    function handleDoubleClick( event ) {
	// Currently no special double click handling defined. Revert to single click for now.
	handleClick( event );
    }
    
    function clearSelectedAll() {
	clearSelectedSvgIcon();
	clearSelectedSvgPath();
	$( SELECTABLE_SELECTOR ).removeClass( HIGHLIGHTED_CLASS );
    }

    function clearSelectedSvgIcon() {
	if ( gSelectedIconSvgGroup ) {
	    $(gSelectedIconSvgGroup).removeClass( HIGHLIGHTED_CLASS );
	    gSelectedIconSvgGroup = null;
	}
    }

    function clearSelectedSvgPath() {
	if ( gSelectedPathSvgGroup ) {
	    collapseSvgPath( );
	    gSelectedPathSvgGroup = null;
	}
    }

    function createIconDragData( event, enclosingSvgGroup ) {	

	const dragElement = enclosingSvgGroup;
        displayElementInfo( 'Drag Element', dragElement );
	
	const baseSvgElement = $(BASE_SVG_SELECTOR);
	displayElementInfo( 'Base SVG', baseSvgElement );

        let transform = dragElement.attr('transform') || '';
        let { scale, translate, rotate } = getSvgTransformValues( transform );
        let cursorSvgPoint = toSvgPoint( baseSvgElement, event.clientX, event.clientY );

	const cursorSvgOffset = {
	    x : (cursorSvgPoint.x / scale.x) - translate.x,
	    y : (cursorSvgPoint.y / scale.y) - translate.y
	};

	gSvgIconDragData = {
	    element: dragElement,
	    baseSvgElement: baseSvgElement,
	    cursorSvgOffset: cursorSvgOffset,
	    elementSvgCenterPoint: getSvgCenterPoint( dragElement, baseSvgElement ),
	    originalSvgScale: scale,
	    originalSvgRotate: rotate,
	    isDragging: false
	};
	
	if ( DEBUG ) {
	    console.log( `Drag Start:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ), 
    SVG Cursor Offset: ( ${gSvgIconDragData.cursorSvgOffset.x}, ${gSvgIconDragData.cursorSvgOffset.y} ),
    SVG Center Point: ( ${gSvgIconDragData.elementSvgCenterPoint.x}, ${gSvgIconDragData.elementSvgCenterPoint.y} )`); 
	}
	
    }
    
    function updateDrag( event ) {
        if ( gSvgIconDragData == null ) {
	    return;
	}
        displayEventInfo( 'Update Drag', event );
        displayElementInfo( 'Drag Element', gSvgIconDragData.element );

        let cursorSvgPoint = toSvgPoint( gSvgIconDragData.baseSvgElement, event.clientX, event.clientY );

	let scale = gSvgIconDragData.originalSvgScale;
	let rotate = gSvgIconDragData.originalSvgRotate;
	
        let newX = (cursorSvgPoint.x / scale.x) - gSvgIconDragData.cursorSvgOffset.x;
        let newY = (cursorSvgPoint.y / scale.y) - gSvgIconDragData.cursorSvgOffset.y;

        let transform = gSvgIconDragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        gSvgIconDragData.element.attr('transform', newTransform);	    

	gSvgIconDragData.elementSvgCenterPoint = getSvgCenterPoint( gSvgIconDragData.element, gSvgIconDragData.baseSvgElement );
	
	if ( DEBUG ) {
	    console.log( `Drag Update:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ),
    TRANSFORM Result: ${newTransform},
    SVG Center Point: ( ${gSvgIconDragData.elementSvgCenterPoint.x}, ${gSvgIconDragData.elementSvgCenterPoint.y} )`); 
	}
    }
    
    function endDrag( event ) {
        if ( gSvgIconDragData == null ) {
	    return;
	}
	
        displayEventInfo( 'End Drag', event );
        displayElementInfo( 'Drag Element', gSvgIconDragData.element );
	updateDrag( event );

	let svgItemId = gSvgIconDragData.element.attr('id');
	let data = {
	    svg_x: gSvgIconDragData.elementSvgCenterPoint.x,
	    svg_y: gSvgIconDragData.elementSvgCenterPoint.y,
	    svg_scale: gSvgIconDragData.originalSvgScale.x,
	    svg_rotate: gSvgIconDragData.originalSvgRotate.angle
	};
	AN.post( `${API_EDIT_SVG_POSITION_URL}/${svgItemId}`, data );

	gSvgIconDragData = null;
    }
 
    function saveIconSvgPosition( element ) {

        let transform = element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );

	const baseSvgElement = $(BASE_SVG_SELECTOR);
	const center = getSvgCenterPoint( element, baseSvgElement );

	let svgItemId = element.attr('id');
	let data = {
	    svg_x: center.x,
	    svg_y: center.y,
	    svg_scale: scale.x,
	    svg_rotate: rotate.angle,
	};
	AN.post( `${API_EDIT_SVG_POSITION_URL}/${svgItemId}`, data );
    }

    function createIconEditActionData( actionState ) {
	if ( gSelectedIconSvgGroup ) {
            let transform = gSelectedIconSvgGroup.attr('transform');
            let { scale, translate, rotate } = getSvgTransformValues( transform );

	    gSvgIconActionData = {
		element: gSelectedIconSvgGroup,
		scaleStart: scale,
		translateStart: translate,
		rotateStart: rotate,
		isScaling: false,
		isRotating: false
	    };

	    gSvgIconActionState = actionState;
	    $(BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, actionState );
	}
    }

    function revertIconAction( element ) {
	if ( gSvgIconActionData ) {
	    setSvgTransformAttr( gSvgIconActionData.element,
				 gSvgIconActionData.scaleStart,
				 gSvgIconActionData.translateStart,
				 gSvgIconActionData.rotateStart );
	    gSvgIconActionData = null;
	}
    }
    
    function iconActionScaleStart() {
	createIconEditActionData( SvgActionStateType.SCALE );	
    }

    function iconActionScaleUpdate( currentMousePosition ) {

	let center = getScreenCenterPoint( gSvgIconActionData.element );

	let scaleFactor = getScaleFactor( center.x, center.y,
					  gLastMousePosition.x, gLastMousePosition.y,
					  currentMousePosition.x, currentMousePosition.y );
        let transform = gSvgIconActionData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );

	const newScale = {
	    x: scale.x * scaleFactor,
	    y: scale.y * scaleFactor
	};
		
	translate.x = translate.x * scale.x / newScale.x;
	translate.y = translate.y * scale.y / newScale.y;

	if ( DEBUG ) {
	    console.log( `Scale Update:
    Transform:  ${transform}
    Scale = ${scale.x}, T = ${translate.x}, R = ${rotate.angle}` );
	}

	setSvgTransformAttr( gSvgIconActionData.element, newScale, translate, rotate );

    }

    function iconActionScaleApply() {
	if ( DEBUG ) { console.log( 'Scale Apply' ); }
	saveIconSvgPosition( gSvgIconActionData.element );
    }

    function iconActionScaleAbort() {
	if ( gSvgIconActionState != SvgActionStateType.SCALE ) {
	    return;
	}
	revertIconAction();
    }

    function iconActionRotateStart() {
	createIconEditActionData( SvgActionStateType.ROTATE );	
    }

    function iconActionRotateUpdate( currentMousePosition ) {
	if ( DEBUG ) { console.log( 'Rotate Update' ); }

	center = getScreenCenterPoint( gSvgIconActionData.element );

	let deltaAngle = getIconRotationAngle( center.x, center.y,
					   gLastMousePosition.x, gLastMousePosition.y,
					   currentMousePosition.x, currentMousePosition.y );

        let transform = gSvgIconActionData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );
	rotate.angle += deltaAngle;
	rotate.angle = normalizeAngle( rotate.angle );
	setSvgTransformAttr( gSvgIconActionData.element, scale, translate, rotate );
    }

    function getIconRotationAngle( centerX, centerY, startX, startY, endX, endY ) {

	const startVectorX = startX - centerX;
	const startVectorY = startY - centerY;

	const endVectorX = endX - centerX;
	const endVectorY = endY - centerY;

	const startAngle = Math.atan2(startVectorY, startVectorX);
	const endAngle = Math.atan2(endVectorY, endVectorX);

	let angleDifference = endAngle - startAngle;

	// Normalize the angle to be between -π and π
	if (angleDifference > Math.PI) {
            angleDifference -= 2 * Math.PI;
	} else if (angleDifference < -Math.PI) {
            angleDifference += 2 * Math.PI;
	}

	const angleDifferenceDegrees = angleDifference * (180 / Math.PI);

	return angleDifferenceDegrees;
    }

    
    function iconActionRotateApply() {
	saveIconSvgPosition( gSvgIconActionData.element );
    }
    
    function iconActionRotateAbort() {
	if ( gSvgIconActionState != SvgActionStateType.ROTATE ) {
	    return;
	}	
	revertIconAction();
    }

    function getScreenCenterPoint( element ) {
	try {
            let rect = element[0].getBoundingClientRect();
	    if ( rect ) {
		const screenCenterX = rect.left + ( rect.width / 2.0 );
		const screenCenterY = rect.top + ( rect.height / 2.0 );
		return {
		    x: rect.left + ( rect.width / 2.0 ),
		    y: rect.top + ( rect.height / 2.0 )
		};
	    }
	} catch (e) {
	    console.debug( `Problem getting bounding box: ${e}` );
	}
	return null;
    }
    
    function getSvgCenterPoint( element, svgElement ) {

	try {
            let rect = element[0].getBoundingClientRect();
	    if ( rect ) {
		const screenCenterX = rect.left + ( rect.width / 2.0 );
		const screenCenterY = rect.top + ( rect.height / 2.0 );
		return toSvgPoint( svgElement, screenCenterX, screenCenterY );
	    }
	} catch (e) {
	    console.debug( `Problem getting bounding box: ${e}` );
	}
	return { x: 0, y: 0 };
    }
    
    function toSvgPoint( svgElement, clientX, clientY) {
        let point = svgElement[0].createSVGPoint();
        point.x = clientX;
        point.y = clientY;
        return point.matrixTransform( svgElement[0].getScreenCTM().inverse() );
    }

    function getPixelsPerSvgUnit( svgElement ) {
	let ctm = svgElement[0].getScreenCTM();
	return {
            scaleX: ctm.a,
            scaleY: ctm.d
	};
    }
    
    function getSvgTransformValues(transform) {
	let scale = { x: 1, y: 1 }, rotate = { angle: 0, cx: 0, cy: 0 }, translate = { x: 0, y: 0 };

	let scaleMatch = transform.match(/scale\(([^)]+)\)/);
	if (scaleMatch) {
	    let scaleValues = scaleMatch[1].trim().split(/[ ,]+/).map(parseFloat);
	    scale.x = scaleValues[0];
	    if ( scaleValues.length == 1 ) {
		scale.y = scale.x;
	    } else {
		scale.y = scaleValues[1];
	    }
	}

	let translateMatch = transform.match(/translate\(([^)]+)\)/);
	if (translateMatch) {
            let [x, y] = translateMatch[1].trim().split(/[ ,]+/).map(parseFloat);
            translate.x = x;
            translate.y = y;
	}

	let rotateMatch = transform.match(/rotate\(([^)]+)\)/);
	if (rotateMatch) {
            let rotateValues = rotateMatch[1].trim().split(/[ ,]+/).map(parseFloat);
            rotate.angle = rotateValues[0];

            // Check if cx and cy are provided
            if (rotateValues.length === 3) {
		rotate.cx = rotateValues[1];
		rotate.cy = rotateValues[2];
            } else {
		rotate.cx = 0;
		rotate.cy = 0;
	    }
	}

	if ( DEBUG ) {
	    console.log( `TRANSFORM:
    Raw: ${transform},
    Parsed: scale=${JSON.stringify(scale)} translate=${JSON.stringify(translate)} rotate=${JSON.stringify(rotate)}` );
	}
	
	return { scale, translate, rotate };
    }

    function setSvgTransformAttr( element, scale, translate, rotate ) {
        let newTransform = `scale(${scale.x} ${scale.y}) translate(${translate.x}, ${translate.y}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;
        element.attr('transform', newTransform);	    
    }
    
    function getSvgViewBox( svgElement ) {
	let x = null;
	let y = null;
	let width = null;
	let height = null;

	if (svgElement.length < 1 ) {
	    return { x, y, width, height };
	}
        let viewBoxValue = svgElement.attr('viewBox');
        if ( ! viewBoxValue) {
	    return { x, y, width, height };
	}
	
	let viewBoxArray = viewBoxValue.split(' ').map(Number);
	x = viewBoxArray[0];
	y = viewBoxArray[1];
	width = viewBoxArray[2];
	height = viewBoxArray[3];

	return { x, y, width, height };
    }

    function getScaleFactor( centerX, centerY, startX, startY, endX, endY ) {

	const startDistance = Math.sqrt( Math.pow(startX - centerX, 2) + Math.pow(startY - centerY, 2) );
	const endDistance = Math.sqrt( Math.pow(endX - centerX, 2) + Math.pow(endY - centerY, 2) );

	let scaleFactor = 1;
	if (endDistance > startDistance) {
            scaleFactor = 1 + (endDistance - startDistance) / 100;
	} else if (endDistance < startDistance) {
            scaleFactor = 1 - (startDistance - endDistance) / 100;
	}
	return scaleFactor;
    }
    
    function normalizeAngle(angle) {
	return (angle % 360 + 360) % 360;
    }


    /* ================================================================================
      SVG PATH EDITING
      
      - Two types of paths: closed (with ending 'Z') and open.
      - The type is determined by the initial path and not editable.
      - An open path must have at least two proxy points (control points for manipulation).
      - A closed path must have at least 3 proxy points.
      - The behavior of adding to the path depends on its type.
      - An open path gets extended when adding.
      - A closed path has its lines subdivided when adding.
      - Adding is relative to the last selected item.
      - You can select a line or a proxy point.
    */    

    function handleSvgPathEditClick( event ) {
	if ( DEBUG ) { console.log( 'Path Edit Click' ); }

	const isProxyElement = $(event.target).hasClass( PROXY_ITEM_CLASS );
	if ( isProxyElement ) {
	    setSelectedProxyElement( event.target );
	}
	else {
	    extendProxyPath( event );
	}
    }

    function handleSvgPathEditKeyDown( event ) {
        displayEventInfo( 'Key Down', event );
	console.log( `KEY '${event.key}', CODE = ${event.keyCode}` );

	if ( PATH_ACTION_ADD_KEY_CODES.includes( event.keyCode ) ) {
	    addProxyPath();
	} else {
	    if ( ! gSvgPathEditData.selectedProxyElement ) {
		return;
	    }

	    if ( PATH_ACTION_DELETE_KEY_CODES.includes( event.keyCode )) {
		if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_POINT_CLASS ) ) {
		    deleteProxyPoint( gSvgPathEditData.selectedProxyElement );
		    
		} else if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_LINE_CLASS ) ) {
		    deleteProxyLine( gSvgPathEditData.selectedProxyElement );

		} else {
		    return;
		}
		
	    } else if ( PATH_ACTION_INSERT_KEY_CODES.includes( event.keyCode ) ) {
		if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_LINE_CLASS ) ) {
		    divideProxyLine( gSvgPathEditData.selectedProxyElement );
		    
		} else if ( $(gSvgPathEditData.selectedProxyElement).hasClass( PROXY_POINT_CLASS ) ) {
		    let svgProxyLine = getPrecedingProxyLine( gSvgPathEditData.selectedProxyElement );
		    if ( svgProxyLine.length > 0 ) {
			divideProxyLine( svgProxyLine );
			
		    } else {
			// Fallback for case of last proxy point selected.
			let svgProxyLine = getFollowingProxyLine( gSvgPathEditData.selectedProxyElement );
			if( svgProxyLine.length > 0 ) {
			    divideProxyLine( svgProxyLine );
			}
		    }
		} else {
		    return;
		}
	    } else {
		return;
	    }
	}
	
	event.stopPropagation();
	event.preventDefault();
    }

    function setSelectedProxyElement( proxyElement ) {
	if ( ! gSvgPathEditData ) {
	    return;
	}
	$(gSvgPathEditData.proxyPathContainer).find('.' + PROXY_ITEM_CLASS).removeClass( HIGHLIGHTED_CLASS );
	if ( proxyElement ) {
	    $(proxyElement).addClass( HIGHLIGHTED_CLASS );
	}
	gSvgPathEditData.selectedProxyElement = proxyElement;
    }
    
    function expandSvgPath( pathSvgGroup ) {
	if ( DEBUG ) { console.log( 'Expand SVG Path', pathSvgGroup ); }

	pathSvgGroup.hide();

	const baseSvgElement = $(BASE_SVG_SELECTOR)[0];
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
	if ( DEBUG ) { console.log('Path segments', segments ); }

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

	    if ( DEBUG ) { console.log( 'Proxy path group: ', proxyPathGroup ); }
	    
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
	const baseSvgElement = $(BASE_SVG_SELECTOR);
	const svgViewBox = getSvgViewBox( baseSvgElement );
	let svgPoint = toSvgPoint( baseSvgElement, event.clientX, event.clientY );

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

	if ( DEBUG ) { console.log( 'Prepend: First point and line: ', firstProxyPoint, firstLine ); }
	
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

	if ( DEBUG ) { console.log( 'Append: Last point and line: ', lastProxyPoint, lastLine ); }
	
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
	
	if ( DEBUG ) { console.log( 'Insert: ', referenceProxyLine, beforeProxyPoint,
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

	const baseSvgElement = $(BASE_SVG_SELECTOR);
	const svgViewBox = getSvgViewBox( baseSvgElement );
	let svgCenter = {
	    x: svgViewBox.x + ( svgViewBox.width / 2 ),
	    y: svgViewBox.y + ( svgViewBox.height / 2 )
	};
	let svgUnitRadius = {
	    x: svgViewBox.width * ( PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 ),
	    y: svgViewBox.height * ( PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 )
	};

	if ( DEBUG ) { console.log( 'Add proxy path.', svgViewBox, svgCenter ); }
		       
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
	    const bottomLeftSvgPoint = {
		x: svgCenter.x - svgUnitRadius.x,
		y: svgCenter.y + svgUnitRadius.y,
	    };
	    const bottomRightSvgPoint = {
		x: svgCenter.x + svgUnitRadius.x,
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

    function createProxyPathGroup( proxyPathType ) {
	let proxyPathGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
	proxyPathGroup.setAttribute('id', generateUniqueId() );
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
	const baseSvgElement = $(BASE_SVG_SELECTOR);
	const pixelsPerSvgUnit = getPixelsPerSvgUnit( baseSvgElement );
	const svgRadius = PATH_EDIT_PROXY_POINT_RADIUS_PIXELS / pixelsPerSvgUnit.scaleX;
	
	const proxyPoint = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
	proxyPoint.setAttribute('cx', cx);
	proxyPoint.setAttribute('cy', cy);
	proxyPoint.setAttribute('r', svgRadius);
	proxyPoint.setAttribute('id', generateUniqueId() );
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
            const offsetX = event.clientX - parseFloat($(proxyPoint).attr('cx'));
            const offsetY = event.clientY - parseFloat($(proxyPoint).attr('cy'));
            
            // Function to handle mouse movement
            function onMouseMove( event ) {
		event.preventDefault();
		gSvgPathEditData.dragProxyPoint = event.target;
		const newCx = event.clientX - offsetX;
		const newCy = event.clientY - offsetY;
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

            // Function to handle mouse up (end of drag)
            function onMouseUp( event ) {
		event.preventDefault();
		saveSvgPath();
		gSvgPathEditData.dragProxyPoint = null;
		$(document).off('mousemove', onMouseMove);
		$(document).off('mouseup', onMouseUp);
            }

            // Bind the mousemove and mouseup handlers using jQuery
            $(document).on('mousemove', onMouseMove);
            $(document).on('mouseup', onMouseUp);
	});
    }
    
    function collapseSvgPath( ) {
	if ( DEBUG ) { console.log( 'Collapse SVG Path' ); }

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
    
    function generateUniqueId() {
	return 'id-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
    }
    
    function displayEventInfo( label, event ) {
	if ( ! DEBUG ) { return; }
	if ( ! event ) {
            console.log( 'No element to display info for.' );
	    return;
	}
        console.log( `${label} Event: 
    Type: ${event.type}, 
    Key: ${event.key},
    KeyCode: ${event.keyCode},
    Pos: ( ${event.clientX}, ${event.clientY} )` );
    }
    
    function displayElementInfo( label, element ) {
	if ( ! DEBUG ) { return; }
	if ( ! element ) {
            console.log( 'No element to display info for.' );
	    return;
	}
	const elementTag = element.prop('tagName');
	const elementId = element.attr('id') || 'No ID';
	const elementClasses = element.attr('class') || 'No Classes';

	let rectStr = 'No Bounding Rect';
	try {
            let rect = element[0].getBoundingClientRect();
	    if ( rect ) {
		rectStr = `Dim: ${rect.width}px x ${rect.height}px,
    Pos: left=${rect.left}px, top=${rect.top}px`;
	    }
	} catch (e) {
	}
	
	let offsetStr = 'No Offset';
	const offset = element.offset();
	if ( offset ) {
	    offsetStr = `Offset: ( ${offset.left}px,  ${offset.top}px )`;
	}

	let svgStr = 'Not an SVG';
	if ( elementTag == 'svg' ) {
	    let { x, y, width, height } = getSvgViewBox( element );
	    if ( x != null ) {
		svgStr = `Viewbox: ( ${x}, ${y}, ${width}, ${height} )`;
	    } else {
		svgStr = 'No viewbox attribute';
	    }
	}
	
        console.log( `${label}: 
    Name: ${elementTag}, 
    Id: ${elementId},
    Classes: ${elementClasses},
    ${svgStr},
    ${offsetStr},
    ${rectStr}`) ;

    }
    
})();
