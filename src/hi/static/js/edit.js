(function() {

    window.Hi = window.Hi || {};

    const HiEdit = {
	/*
	  Used for various editing sub-modules to track which one made the last
	  selection so others can clear their selections.
	*/
	SELECTION_MADE_EVENT_NAME: 'event.selectionMade'
	
    };
    
    window.Hi.edit = HiEdit;

    /*
      We use this event bus to allow the editing submodules to coordinate. 
      We want submodules to be independent, but since they need to share 
      the same event space, we need some means of comunicating in a 
      decoupled way.
    */
    const eventBus = {
        events: {},
	
        subscribe: function( eventName, callback ) {
            if (!this.events[eventName]) {
                this.events[eventName] = [];
            }
            this.events[eventName].push(callback);
        },
	
        emit: function( eventName, data ) {
            if (this.events[eventName]) {
                this.events[eventName].forEach( callback => callback(data) );
            }
        }
    };

    window.Hi.edit.eventBus = eventBus;
    
})();
