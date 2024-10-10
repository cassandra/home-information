(function() {
    window.Hi = window.Hi || {};
    window.Hi.edit = window.Hi.edit || {};

    const HiEditDragDrop = {
	// Externally accessible functions here.
    };

    window.Hi.edit.path = HiEditDragDrop;

    /*
      DRAG AND DROP EDITING

      General functionality to re-order draggable items in a DOM
      node. e.g., buttons and lists.
    */
    
    const DRAGGABLE_CONTAINER_CLASS = 'draggable-container';
    const DRAGGABLE_CONTAINER_SELECTOR = '.' + DRAGGABLE_CONTAINER_CLASS;
    const DRAGGABLE_CLASS = 'draggable';
    const DRAGGABLE_SELECTOR = '.' + DRAGGABLE_CLASS;
    const DRAG_OVER_CLASS = 'drag-over';

    const API_REORDER_ITEMS_URL = '/edit/reorder-items';
    
    let gDraggedElement = null;
    
    $(document).ready(function() {

	$(DRAGGABLE_SELECTOR).on('dragstart', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragStart( event );
	});
	$(DRAGGABLE_SELECTOR).on('dragend', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragEnd( event );
	});
	$(DRAGGABLE_SELECTOR).on('dragover', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragOver( event );
	});
	$(DRAGGABLE_SELECTOR).on('dragenter', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragEnter( event );
	});
	$(DRAGGABLE_SELECTOR).on('dragleave', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragLeave( event );
	});
    });

    function handleDragStart( event ) {
	if ( Hi.DEBUG ) { console.log('event.currentTarget:', event.currentTarget); }

        gDraggedElement = event.currentTarget;
	
        // Hide the dragged element during the drag operation for better visuals
        setTimeout(() => {
            $(gDraggedElement).hide();
	    console.log('Hidden class added');
        }, 0);
    }
    
    function handleDragEnd( event ) {
	if ( Hi.DEBUG ) { console.log('Drag end:'); }
        $(gDraggedElement).show();
        gDraggedElement = null;
	$( DRAGGABLE_SELECTOR ).removeClass( DRAG_OVER_CLASS );
	$( DRAGGABLE_SELECTOR ).css('transform', '');
	
        var htmlIdList = [];
	var parentContainer = $(event.currentTarget).closest( DRAGGABLE_CONTAINER_SELECTOR );
        parentContainer.find( DRAGGABLE_SELECTOR ).each(function() {
            htmlIdList.push( $(this).attr('id'));
        });
	
	if ( Hi.DEBUG ) { console.log(`Drag end ids: ${htmlIdList}`); }

	let data = {
	    html_id_list: JSON.stringify( htmlIdList ),
	};
	AN.post( API_REORDER_ITEMS_URL, data );
    }
    
    function handleDragOver( event ) {
	if ( Hi.DEBUG ) { console.log('Drag over:'); }
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
	if ( Hi.DEBUG ) { console.log('Drag enter:'); }
	// Only allow visual feedback if in the same parent container
        if ( $(event.currentTarget).parent()[0] === $(gDraggedElement).parent()[0] ) {
            $(event.currentTarget).addClass( DRAG_OVER_CLASS );
        }
    }
    
    function handleDragLeave( event ) {
	if ( Hi.DEBUG ) { console.log('Drag leave:'); }
	$(event.currentTarget).removeClass( DRAG_OVER_CLASS );
	$(event.currentTarget).css('transform', '');  
    }
    
    
})();
