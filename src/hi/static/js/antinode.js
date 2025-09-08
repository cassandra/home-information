// Anti-Node - Less Javascript is Better
//             Server-side rendering for asynchronous interactions 
//
// Copyright 2020-2025 by POMDP, Inc. - All rights reserved

// ====================
// OVERVIEW
// ====================
// Anti-Node (AN) provides a comprehensive framework for handling asynchronous
// content loading and DOM manipulation without full page refreshes. It supports
// both declarative (HTML attributes) and programmatic (JavaScript API) usage.

// ====================
// APPLICABILITY
// ====================
// This module's main use case is to allow ajax and dynamic content udpates
// without needing to add any javascript. By adding element attributes
// and/or with server-side payloads, a fairly rich set of common DOM
// updates can be achieved with zero javascript code.  It also has a lot of
// support for handling bootstrap-style modals.
//
// It is generally not applicabl if you need to have custom Javascript
// for some client-server interactions

// ====================
// PREREQUISITES
// ====================
// 1. jQuery (for AJAX and DOM manipulation)
// 2. Bootstrap (optional, for modal support)
// 3. js-cookie library (for CSRF token handling)
// 4. Include antinode.js after the above libraries:
//    <script src="{% static 'js/antinode.js' %}"></script>
// 5. (Optional) Set window.AN_VERSION variable before loading for version compatibility

// ====================
// DECLARATIVE USAGE (HTML Attributes)
// ====================
// 
// Basic async loading:
//   <a href="/path" data-async="#target-id">Load Content</a>
//   <form action="/submit" data-async="#result-area">...</form>
//
// Attributes:
//   data-async="{selector}"  - jQuery selector for target element, or "modal" for new modal
//   data-mode="insert"       - (default) Replace inner HTML of target
//   data-mode="replace"      - Replace entire target element
//   data-hide="{selector}"   - Hide elements when triggered
//   data-show="{selector}"   - Show elements when triggered
//   data-stay-in-modal       - Don't auto-close modal on submission
//   debounce                 - Prevent double form submission
//   onchange-async="true"    - Auto-submit form on select/checkbox change

// ====================
// PROGRAMMATIC API
// ====================
//
// AN.loadAsyncContent(config) - Load content into specific target
//   config.url              - URL to fetch
//   config.target           - Target selector or jQuery object (required)
//   config.mode             - 'insert' or 'replace' (default: 'insert')
//   config.method           - 'GET' or 'POST' (default: 'GET')
//   config.data             - Data for POST requests
//   config.beforeSend       - Callback: function(jqXHR, settings)
//   config.success          - Callback: function(data, status, xhr)
//   config.error            - Callback: function(xhr, ajaxOptions, thrownError)
//
// AN.get(url)               - GET request, target determined by response
// AN.post(url, data)        - POST request, target determined by response

// ====================
// SERVER RESPONSE FORMATS
// ====================
//
// 1. HTML Response:
//    - Inserted directly into target element
//
// 2. JSON Response - supports multiple operations:
//    {
//      "location": "/redirect/url",        // Redirect browser
//      "refresh": true,                     // Refresh entire page
//      "html": "<div>...</div>",          // Content for main target
//      "insert": {"id1": "...", ...},     // Replace inner HTML by ID
//      "replace": {"id1": "...", ...},    // Replace entire elements by ID
//      "append": {"id1": "...", ...},     // Append to elements by ID
//      "setAttributes": {"id1": {...}},   // Set element attributes
//      "modal": "<div>...</div>",         // Create and show modal
//      "pushUrl": "/new/url",             // Update browser URL without reload
//      "resetScrollbar": true,            // Reset to top of page
//      "scrollTo": "element-id"           // Scroll to specified element ID
//    }

// ====================
// SPECIAL FEATURES
// ====================
//
// Scroll Preservation:
//   Add class "preserve-scroll-bar" to elements to maintain scroll position
//
// Loading Indicator:
//   Automatic loading spinner overlay during async requests
//
// Modal Support:
//   - Auto-display: Place content in #antinode-initial-modal
//   - Dynamic modals: Use data-async="modal"
//   - Handles overlapping show/hide transitions
//
// Version Compatibility:
//   Adds X-AN-Version header to detect version mismatches (see VERSION SUPPORT below)
//
// Post-Update Hook:
//   Define global function handlePostAsyncUpdate() to run after updates
//
// Extension Point:
//   Call addAfterAsyncRenderFunction(func) to add custom post-render logic

// ====================
// ERROR HANDLING
// ====================
// - HTTP errors still process response content (useful for form validation)
// - Console errors logged for debugging
// - Malformed JSON falls back to HTML insertion

// ====================
// CSRF PROTECTION
// ====================
// Automatically adds Django CSRF token to POST requests using js-cookie

// ====================
// VERSION SUPPORT
// ====================
// Asynchronous pages are susceptible to problems when the server-side
// software is updated. If the synchronously loaded CSS or JS files from
// the previous version are used to try to render the asynchronously loaded
// HTML content from a newer version, there can be a mismatch. 
//
// To help the server-side deal with this, this module will add a custom HTTP 
// header to every asynchronous call with the version number. To enable this
// feature, you need to ensure that the javascript variable window.AN_VERSION is
// set to the current version somewhere before this module loads. When
// that variable exists, this module will add the header "X-AN-Version"
// with the value of that variable. 
//
// The server can use this to detect if that matches the currently running 
// server version and take action if needed. A typical action is to render 
// a dialog to force a synchronous refresh and ensure the latest version 
// of the CSS and JS assets are loaded.

(function() {

    const AN = {
        get: function( url ) {
            $.ajax({
                type: 'GET',
                url: url,
        
                success: function(data, status, xhr) {
                    asyncUpdateData( null, null, data, xhr );
                    return false;
                },
                error: function (xhr, ajaxOptions, thrownError) {
                    let http_code = xhr.status;
                    let error_msg = thrownError;
                    asyncUpdateData( null, null, xhr.responseText, xhr );
                    return false;
                } 
            });
        },

        post: function( url, data ) {
            $.ajax({
                type: 'POST',
                url: url,
                data: data,
                async: true,
                cache: false,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                processData: true,
                
                success: function(data, status, xhr) {
                    asyncUpdateData( null, null, data, xhr );
                    return false;
                },
                error: function (xhr, ajaxOptions, thrownError) {
                    let http_code = xhr.status;
                    let error_msg = thrownError;
                    asyncUpdateData( null, null, xhr.responseText, xhr );
                    return false;
                } 
            });
        },

        // New public API for programmatically loading content into a target element
        // This is designed for JavaScript-initiated DOM replacement requests where
        // both the URL and target are specified by the caller.
        //
        // Usage:
        //   AN.loadAsyncContent({
        //       url: '/some/path',
        //       target: '#element-id',  // or jQuery object
        //       mode: 'insert',         // optional: 'insert' (default) or 'replace'
        //       method: 'GET',          // optional: 'GET' (default) or 'POST'
        //       data: {...},            // optional: data for POST requests
        //       beforeSend: function(jqXHR, settings) {...},  // optional callback
        //       success: function(data, status, xhr) {...},   // optional callback
        //       error: function(xhr, ajaxOptions, thrownError) {...}  // optional callback
        //   });
        //
        loadAsyncContent: function( config ) {
            // Validate required parameters
            if ( !config || !config.url || !config.target ) {
                console.error('AN.loadAsyncContent requires config object with url and target');
                return;
            }
            
            // Get target element - support both selector strings and jQuery objects
            let $target = (typeof config.target === 'string') 
                ? $(config.target) 
                : config.target;
            
            // Validate target exists
            if ( !$target || $target.length === 0 ) {
                console.error('AN.loadAsyncContent: target element not found:', config.target);
                return;
            }
            
            // Set defaults for optional parameters
            let mode = config.mode || 'insert';
            let method = (config.method || 'GET').toUpperCase();
            let data = config.data || null;
            let async = config.async !== false;  // default true
            let cache = config.cache !== false;  // default true for GET
            
            // For POST requests, handle data serialization
            let processData = true;
            let contentType = 'application/x-www-form-urlencoded; charset=UTF-8';
            
            if ( method === 'POST' && data ) {
                // If data is already FormData, don't process it
                if ( data instanceof FormData ) {
                    processData = false;
                    contentType = false;
                    cache = false;
                }
            }
            
            // Make the AJAX request
            $.ajax({
                type: method,
                url: config.url,
                data: data,
                async: async,
                cache: cache,
                contentType: contentType,
                processData: processData,
                
                beforeSend: function(jqXHR, ajaxSettings) {
                    // Add version header if available
                    if ( typeof window.AN_VERSION !== 'undefined' ) {
                        jqXHR.setRequestHeader('X-AN-Version', window.AN_VERSION);
                    }
                    
                    // Call custom beforeSend if provided
                    if ( config.beforeSend && typeof config.beforeSend === 'function' ) {
                        config.beforeSend(jqXHR, ajaxSettings);
                    }
                },
                
                success: function(data, status, xhr) {
                    // Use existing response handler with specified target and mode
                    asyncUpdateData($target, mode, data, xhr);
                    
                    // Call custom success callback if provided
                    if ( config.success && typeof config.success === 'function' ) {
                        config.success(data, status, xhr);
                    }
                },
                
                error: function(xhr, ajaxOptions, thrownError) {
                    // Use existing error handler - still processes the response
                    asyncUpdateData($target, mode, xhr.responseText, xhr);
                    
                    // Call custom error callback if provided
                    if ( config.error && typeof config.error === 'function' ) {
                        config.error(xhr, ajaxOptions, thrownError);
                    }
                }
            });
        },
        
        addAfterAsyncRenderFunction: addAfterAsyncRenderFunction
    }
    
    window.AN = AN;

//====================
// The handle for forms that want to  trigger an ansynchonous (aka, ajax)
// request.
//
function asyncSubmitHandler(event) {
    event.preventDefault();
    event.stopPropagation();

    let $form = $(this);
    return asyncSubmitHandlerHelper( $form );
};

function asyncSubmitHandlerHelper( $form ) {

    if ( $form.attr('debounce') ) {
        $form.find('button').prop('disabled', true);
    }

    handleHideShowIfNeeded( $form );

    let $target = getAsyncTarget( $form );

    let $mode = $form.attr('data-mode');
    if ( ! $mode ) {
        $mode = 'insert';
    }

    // If the form lies in a modal, then close the modal.
    beforeAsyncCall( $form );

    // In case the last submit button data was saved.
    // (See: lastButtonClickHandler)
    //
    let lastButtonName = $form.data('lastSubmitButtonName');
    let lastButtonValue = null;
    if ( lastButtonName ) {
        lastButtonValue = $form.data('lastSubmitButtonValue');

        // Make sure to remove it or we might think the submit button
        // we click on the next form submission when something else
        // could have triggered it (e.g., an onchange event)
        //
        $form.removeData('lastSubmitButtonName');
        $form.removeData('lastSubmitButtonValue');
    }
    
    let formData = null;
    let processData = true;
    let contentType = null;
    let async = true;
    let cache = true;

    if (( $($form).attr('method') )
        && ( $($form).attr('method').toUpperCase() == 'GET' )) {
        let formData = $form.serializeArray();
        if ( lastButtonName ) {
            formData.push( { name: lastButtonName, value: lastButtonValue } );
        }
    }
    // Assumes POST
    else {
        formData = new FormData($($form)[0]);
        if ( lastButtonName ) {
            formData.append( lastButtonName, lastButtonValue );
        }
        processData = false;
        contentType = false;
        async = true;
        cache = false;
    }

    if ( $($form).attr('enctype') == 'multipart/form-data' ) {
        let dummy = 0;
    }

    $.ajax({
        type: $form.attr('method'),
        url: $form.attr('action'),
        data: formData,
        async: async,
        cache: cache,
        contentType: contentType,
        processData: processData,

        beforeSend: function (jqXHR, settings) {
            if ( typeof window.AN_VERSION !== 'undefined' ) {
                jqXHR.setRequestHeader('X-AN-Version', window.AN_VERSION );
            }
        },
        
        success: function(data, status, xhr) {
            asyncUpdateData( $target, $mode, data, xhr );
            return false;
        },

        // The allauth module returns a 400 error when the form fails
        // validation. It includes the HTML in a JSON respons, so we have
        // to use that to repopulate the content in the page.

        error: function (xhr, ajaxOptions, thrownError) {
            let http_code = xhr.status;
            let error_msg = thrownError;
            asyncUpdateData( $target, $mode, xhr.responseText, xhr );
            return false;
        }
    });

    return false;
};

//====================
// The handle for anchor tags and other "click" events that want to 
// trigger an ansynchonous (aka, ajax) request.
//
function asyncClickHandler(event) {
    event.preventDefault();
    event.stopPropagation();

    let $anchor = $(this);

    handleHideShowIfNeeded( $anchor );

    // Special case for bootstrap dropdown menus that have data-async links
    // in them.  Since we are suppressing the event propagation here, we
    // have to close the menu ourselves on a click.
    //
    $anchor.closest('.dropdown-menu').removeClass('show');

    $('.an-async-hide').hide();
    $('.an-async-show').show();
    
    let $target = getAsyncTarget( $anchor );
    let $mode = $anchor.attr('data-mode');
    if ( ! $mode ) {
        $mode = 'insert';
    }

    let url = $anchor.attr('href');
    if ( $anchor.attr('data-params') ) {
        url += '?' + $anchor.attr('data-params');
    }

    // If the anchor lies within a modal, then close the modal
    beforeAsyncCall( $anchor );
    
    $.ajax({
        type: 'GET',
        url: url,
        
        beforeSend: function (jqXHR, settings) {
            if ( typeof window.AN_VERSION !== 'undefined' ) {
                jqXHR.setRequestHeader('X-AN-Version', window.AN_VERSION );
            }
        },
        
        success: function(data, status, xhr) {
            asyncUpdateData( $target, $mode, data, xhr );
            return false;
        },
        error: function (xhr, ajaxOptions, thrownError) {
            let http_code = xhr.status;
            let error_msg = thrownError;
            asyncUpdateData( $target, $mode, xhr.responseText, xhr );
            return false;
        } 

    });

    return false;
};

//====================
// For modal dialogs

let lastModalId = 0;

function getNewModal() {
    lastModalId += 1;
    let htmlId = "antinode-modal-"+lastModalId;
    let htmlString = '<div id="'+htmlId+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true"></div>';
    let modalObj = $.parseHTML(htmlString);
    $('body').append( modalObj );
    return $(modalObj);
};


//====================
function handleHideShowIfNeeded( $anchor ) {

    let hide_selector = $anchor.attr('data-hide');
    if ( hide_selector ) {
        $(hide_selector).hide();
    }

    let show_selector = $anchor.attr('data-show');
    if ( show_selector ) {
        $(show_selector).show();
    }

};


//====================
// Common for POST and GET to find the target node for returned content

function getAsyncTarget( anchorNode ) {
    let targetSelector = $(anchorNode).attr('data-async');

    // Special case to allow us to create a modal for the content
    if ( targetSelector == "modal" ) {
        return getNewModal();
    }
    return $(targetSelector);
};


//====================
// The Async "loading" spinner

function insertLoadingImage() {
    // N.B. The negative margins in the css should be half the width of the loading image.
    let htmlString = '<div id="antinode-loader" style="display:none; position: absolute; top: 50%; left: 50%; margin-left: -64px; margin-top: -64px; z-index: 1055;"><img src="/static/img/antinode-loading.gif" alt="Page Loading Interstitial"/></div>';
    let loadingObj = $.parseHTML(htmlString);
    $('body').append( loadingObj );
    return;
};


//====================
// Helper routine for asynchronous repsonses and the different
// variations of what might come back. The two variations:
//
//   - A blob of HTML - get inserted/replaced to the main target area.
//   - Special JSON structure - more general way to target multiple target areas.
//
function asyncUpdateData( $target, $mode, data, xhr ) {

    // In the simplest case, the entire return content is inserted into the
    // $target location.  This requires the return content type to be HTML.
    //
    // Alternatively, there are other types of more complicated response
    // patterns, and each of these are encoded as a JSON document with
    // corresponding content type.
    
    let ct = xhr.getResponseHeader("content-type") || "";
    
    if (ct.indexOf('html') > -1) {
     if ( $target ) {
         if ( $mode == 'replace' ) {
          $target.replaceWith( data );
         }
         else {
          $target.html(data);
         }
         handleNewContentAdded( $target );
     }
    }
    if (ct.indexOf('json') > -1) {
     let json = data;
     
     // The response data might be text that has to be parsed into JSON
     // This raises an exception if data is already a JSON object.
     try {
         json = JSON.parse(data);
     }
     catch (e) {
         // Data already JSON
     }
     
       asyncUpdateDataFromJson( $target, $mode, json );
    } 
};

//====================
// Websocket async updates will not have a default target or mode.  For
// synchronous request, these can be defined in the HTML elements as
// attributes, so they simply will not exist when not originating from a
// normal HTTP request and coming through an unsolicited websocket request.
//
function asyncUpdateDataFromWebsocket( json ) {
    asyncUpdateDataFromJson( null, null, json );
};

//====================
function asyncUpdateDataFromJson( $target, $mode, json ) {
    
    // To allow the server to decide to redirect the page rather than
    // render async content.
    //
    // N.B. The 'location' attribute name is used by antinode.js, but
    // coincidentally is also used by the Django allauth module.
    // If they were different, we would have to check for both here.
    //
    if ( 'location' in json ) {
        let url = json['location'];
        this.document.location.href = url;
        return;
    }
    
    // To allow the server to decide to refresh the page rather than
    // render async content.
    //
    if ( 'refresh' in json ) {
        location.reload();
        window.scrollTo(0, 0);
        return;
    }
    
    // In a JSON response, the 'html' contains the "main" content that
    // should be inserted into the $target.  This allows the same
    // behavior as if the retrun content type was 'html', but also
    // allows the server to do additional things on the page if needed.
    //
    if ( 'html' in json ) {
     if ( $target ) {
         if ( $mode == 'replace' ) {
             $target.replaceWith( json['html'] );
         }
         else {
             $target.empty();
             $target.html( json['html'] );
         }
         handleNewContentAdded( $target );
     }
    }
    
    // This entry should be a map from html ids to content that should
    // be replaced.  This includes replacing the target element itself.
    //
    if ( 'replace' in json ) {
        for ( let htmlId in json['replace'] ) {
            let targetObj = $("#"+htmlId);
            targetObj.replaceWith( json['replace'][htmlId] ).show();
            handleNewContentAdded( targetObj );
        }
    }
    
    // This entry should be a map from html ids to content that should
    // be changed.  This does not include the target element itself.
    //
    if ( 'insert' in json ) {
        for ( let htmlId in json['insert'] ) {
            let targetObj = $("#"+htmlId);
            targetObj.empty();
            targetObj.html( json['insert'][htmlId] ).show();
            handleNewContentAdded( targetObj );
        }
    }
    
    // This entry should be a map from html ids to content that should
    // be appended. This add it as the last child of the target tag id.
    //
    if ( 'append' in json ) {
        for ( let htmlId in json['append'] ) {
            let targetObj = $("#"+htmlId);
            targetObj.append( json['append'][htmlId] ).show();
            handleNewContentAdded( targetObj );
        }
    }
    
    // This entry should be a map from html ids to content that should
    // be appended. This add it as the last child of the target tag id.
    //
    if ( 'setAttributes' in json ) {
        for ( let htmlId in json['setAttributes'] ) {
            let targetObj = $("#"+htmlId);
            let attrMap = json['setAttributes'][htmlId];
            for ( let attrName in attrMap ) {
                let attrValue = attrMap[attrName];
                targetObj.attr( attrName, attrValue );
                handleNewContentAdded( targetObj );
            }
        }
    }
    
    // In case any content with preserved scroll bars was refreshed.
    //
    afterAsyncRender();
    
    if ( 'modal' in json ) {
        let targetObj = getNewModal();
        targetObj.append( json['modal'] )
        showModal( targetObj );
    }
    
    // Allowing re-writing URL so it is preserved for navigation and refresh
    if ( 'pushUrl' in json ) {
        window.history.pushState( {}, "", json['pushUrl']  );
    }

    if ( 'resetScrollbar' in json ) {
        window.scrollTo(0, 0);
    }
    
    // Scroll to specified element after DOM updates are complete
    if ( 'scrollTo' in json ) {
        let targetId = json['scrollTo'];
        let targetElement = $("#" + targetId);
        if ( targetElement.length > 0 ) {
            // Use smooth scrolling for better user experience
            targetElement[0].scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest',
                inline: 'nearest'
            });
        } else {
            console.warn('AntiNode scrollTo: Target element not found:', targetId);
        }
    }
    
    if ( typeof handlePostAsyncUpdate === "function") {
        handlePostAsyncUpdate();
    }
};
        
//====================
function handleNewContentAdded( contentObj ) {
    doAutofocusIfNeeded( contentObj );
    showModalIfNeeded( contentObj );
};

//====================
function doAutofocusIfNeeded( contentObj ) {
    $(contentObj).find( 'input[autofocus]' ).first().focus();
};

//====================
function beforeAsyncCall( $node ) {

    // If the content lies in a modal, then close the modal.
    // Unless the form has data-stay-in-modal attribute.
    if ( ! $node.attr('data-stay-in-modal') ) {
        hideModalIfNeeded( $node );
    }
    saveScrollBarPositions();
};

//====================
// Things that need to run after asynchronous content is rendered

let afterAsyncRenderFunctionList = [];
    
function afterAsyncRender() {

    for ( let i = 0; i < afterAsyncRenderFunctionList.length; i++ ) {
        afterAsyncRenderFunctionList[i]();
    }
    restoreScrollBarPositions();
};

// For adding additional function to run after asyn content inserted.
//
function addAfterAsyncRenderFunction( func_name ) {
    afterAsyncRenderFunctionList.push( func_name );
};

//====================
// Preserving scroll bars should be called just prior to an async request
// (for both form submissions and click events). Restoring them should come
// after all async content is rendered.
//
let scrollTopMap = {};

function saveScrollBarPositions() {

    // Anything marked as needing its scroll bar preserved should have us
    // save the position.
    //
    $('.preserve-scroll-bar').each( function( index ) {
        let id = $(this).attr('id');
        if ( id ) {
            scrollTopMap[id] = $(this).scrollTop();
        }
    });
    
};

function restoreScrollBarPositions() {
    for ( let id in scrollTopMap ) {
        $('#'+id).scrollTop( scrollTopMap[id] );
    }
};

//====================
// Use of the Bootstrap modal dialog has an issue when you 
// you trigger a modal from a modal (for the same modal, but
// with different inserted content).  The hiding and showing 
// happens over time, so a "hide", some ajax call, and then
// a "show" has the showing part sometimes happening before the 
// hide is completed.  This leads to double dark background and
// the modal getting into an inoperable state.  These routines
// help to coordinate things and prevent those problems.
//

// This will either be 'null' or else the epoch miliiseconds when the hide
// event was started.  There were some strange issues with the
// hidden.bs.event not firing after the first time on in Firefox (worked in
// Chrome) so by using the milliseconds, we can detect when this was not
// properly updated to be null and force it to null so that all future
// dialogs are not blocked.
//
let modalHideStartMs = null;

// When a modal show event happens while the hide event is active, we will
// stash the modal object to be show in this global variable so that when
// the hide event triggers, we know that we need to re-show the new modal
// content.
//
let deferredModalShowObj = null;

// This is the safety check to make sure missing hidden.bsmodal events do
// not prevent modals from showing forever (or page refresh really).
//
function checkModalHideState() {
    if ( modalHideStartMs ) {
        let d = new Date();
        let nowMs = d.getTime();
        let diffMs = nowMs - modalHideStartMs;
        if ( diffMs > 5000 ) {
            modalHideStartMs = null;
        }
    }
};

// Pass in the object that the async event fires on.  If
// it is contained in a modal, then we will close the modal.
//
function hideModalIfNeeded( eventObj ) {
    let modalObj = $(eventObj).closest('.modal');
    if ( modalObj.length > 0 ) {
        hideModal( modalObj.first() );
    }
};

// Pass in the object that receives the async data and
// show it if it is contained in a modal.
//
function showModalIfNeeded( targetObj ) {
    let modalObj = $(targetObj).closest('.modal');
    if ( modalObj.length > 0 ) {
        showModal( modalObj.first() );
    }
};

function showModal( modalObj ) {
    if ( ! $(modalObj).modal ) {
        return;
    }
    checkModalHideState();
    if ( modalHideStartMs ) {
        deferredModalShowObj = modalObj;
    } else {
        $(modalObj).modal("show");
    }
};

function hideModal( modalObj ) {
    if ( ! $(modalObj).modal ) {
        return;
    }
    // Note that the globally registered hidden.bs.modal event will be
    // called once the hide is finished, and that will flip
    // modalHideStartMs to 'false'.
    //
    let d = new Date();
    modalHideStartMs = d.getTime();
    $(modalObj).modal("hide");

};

function handleModalHiddenEvent( modalObj ) {
    try {
        modalHideStartMs = null;
        if ( deferredModalShowObj ) {
            showModal( deferredModalShowObj );
        } 
        
    } catch (e) {
        console.error('Problem handling modal hidden event');
    }
    finally {
        modalHideStartMs = null;
        deferredModalShowObj = null;
        $(modalObj).remove();
    }
};

//====================
// Helper routine when an asynchronous repsonse wants to do a redirect
// and the redirect response page should also be rendered asynchronously.
//
function asyncRedirect( $target, $mode, url ) {
    $.ajax({
        type: 'GET',
        url: url,
        
        beforeSend: function (jqXHR, settings) {
            if ( typeof window.AN_VERSION !== 'undefined' ) {
                jqXHR.setRequestHeader('X-AN-Version', window.AN_VERSION );
            }
        },
        success: function(data, status, xhr) {
            asyncUpdateData( $target, $mode, data, xhr );
        },
        error: function (xhr, ajaxOptions, thrownError) {
            let http_code = xhr.status;
            let error_msg = thrownError;
            asyncUpdateData( $target, $mode, xhr.responseText, xhr );
        }
    });
};

//====================
// Some messy bits for Async Form Submissions of multipart/form data
// in bootstrap modals.  This has to do with the way Django does there
// cross-site request forgery (CSRF) tokens.

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if ( csrfSafeMethod( settings.type ) ) {
            return;
        }

        let csrftoken = Cookies.get('csrftoken');
        if ( ! this.crossDomain ) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

//====================
// Using the jQuery serialize method to asynchronously submit a form
// does *NOT* include the button name and value.  Thus, if you want to
// have multiple submit buttons to cause different behavior you need to
// hack around this problem.  We do this by always remembering the last
// form button that was clicked.  Then if the submit event occurs, we 
// will pass that along with the rest of the form contents.
//
function lastButtonClickHandler(event) {
    let theForm = $(this).closest('form');
    $(theForm).data('lastSubmitButtonName', this.name);
    $(theForm).data('lastSubmitButtonValue', this.value);
};

function showLoadingIniterstitial() {
    $('#antinode-loader').show();
};

function hideLoadingIniterstitial() {
    $('#antinode-loader').hide();
};

function synchronousSubmitHandler() {
    $('#antinode-loader').show();
    $( this ).find( 'button[type="submit"]' ).prop('disabled', true);
}
    
//====================
// Adding handlers that look at special HTML tag attributes to determine
// which ones want to be done ansynchonously (aka, AJAX)
//
jQuery(function($) {

    // Always want to show some visual indication that an async request
    // is in progress.
    //
    insertLoadingImage();

    // These ensure that we'll pay attention to the special async attributes.
    //
    $('body').on('submit', 'form[data-async]', asyncSubmitHandler );
    $('body').on('click', 'a[data-async]', asyncClickHandler );
    $('body').on('click', 'div[data-async]', asyncClickHandler );
    $('body').on('click', 'form[data-async] button', lastButtonClickHandler );
    $('body').on('submit', 'form[data-synchronous]', synchronousSubmitHandler );

    // This is to support auto-submitting from SELECT elements asnychronously.
    //
    $('body').on('change', 'select[onchange-async]', function() {
        let $form = $(this.form);
        return asyncSubmitHandlerHelper( $form );
    });
    $('body').on('change', 'input[onchange-async]', function() {
        let $form = $(this.form);
        return asyncSubmitHandlerHelper( $form );
    });
    
    // Weirdness of Bootstrap modals means we have to force the autofocus
    // element manually. Yuck.
    //
    $('body').on('shown.bs.modal', '.modal', function() {
        $(this).find('[autofocus]').focus();
    });
    $('body').on('hidden.bs.modal', '.modal', function() {
        handleModalHiddenEvent( $(this) );
        $('body').find('[autofocus]').focus();
    });

    let initial_modal_content = $('#antinode-initial-modal');
    if ( initial_modal_content.length > 0 ) {
        let targetObj = getNewModal();
        targetObj.append( initial_modal_content )
        showModal( targetObj );
    }
    
});

// Extend jQuery to allow some requests to suppress the loading image.
$.ajaxSuppressLoader = false;

$(document)
        .ajaxStart(function () {
            if ( ! $.ajaxSuppressLoader ) {
                $('#antinode-loader').show();
            }
        })
        .ajaxStop(function () {
            $('#antinode-loader').hide();
        });
    
})();
