// Anti-Node - Less Javascript is Better
//             For Server-side rendering for asynchronous interactions 
//
// Copyright 2020 by POMDP, Inc. - All rights reserved

// --------------
// (Django) HOWTO
// --------------
//
// 1. Include jQuery and Bootstrap and cookie.js
// 2. Add this to bottom page JS loading items:
//    <script src="{% static 'js/antinode.js' %}"></script>

//========================================
// jQuery asynchronous form submission

// For any anchor tag (<a>) or form submission, you can turn them into an
// asynchonous (aka, AJAX) request by adding the attribute:
//  
//      data-async="mnemonic-or-jquery-selector"
//
// Where the predefined, reserved mnemonics are:
//
//    "modal" - render as a modal dialog
//
// Can also define data-mode with values:
//
//    "replace" - to replace the target instead of inserting into it
//
// This javascript code will add events to those items to send them through
// then jQuery ajax requests and ensure that the returned content get
// rendered inside the DOM element matching then target id or selector.
//
// By default, the async content will be "inserted" into the matching
// selected and overwriting and of its existing contained HTML content
// (but it does not replace the matching node itself). If you want to
// completely replace the target node, then also add the attribute
// data-mode="replace" .
//
// This has special logic to handle Bootstrap modal dialogs as well so that
// if the target points to a (initially hidden) Bootstrap modal, it will
// also ensure that the modal gets shown.
//
// An extra feature is to handle page redirects in the case where the
// anchor or form might render async content or may need to redirect.  In
// this case, if the returntin content is a JSON document with the attribute
// "location", it will assume this is a URL and will redirect the page
// (instead of inserting the content into the DOM).
//
// Another feature it provides is restoring scroll bar positions for
// content that is asynchronously refreshed.  Use the 'preserve-scroll-bar'
// class on the scrollable element to be preserved.
//
// For form submissions with submit buttons, you can help prevent double
// submissions by adding the form property "debounce". Set this on the form
// HTML element, not the buttons.
//
// To support "onchange" submission for SELECT elements, add the following
// attribute to the SELECT (and also add the data-async/data-mode
// attributes to the form)
//
//     onchange-async="true"
//
// If you define the javascript function "AN_handlePostAsyncUpdate()", this
// will be called after each async content update after all updated are
// handled.
//
// You can use the following atributes on a form/link with the data-async
// attribute. These allow you to show or hide content when the async
// submission/click is triggered.
//
//     data-hide="{selector}"   - jQuery selector for content to be hidden on submit/click
//     data-show="{selector}"   - jQuery selector for content to be shown on submit/click
//
// You will probably want an initial CSS rules of "display: none;" on the
// data-show elements.
//
// If you want a synchronously loaded page to display an initial modal afer
// page load, put the modal content in a DIV with the id
// "antinode-initial-modal".

// Version Support
//
// Asynchronous pages are susceptible to problems when the server-side
// software is updated.  If the synchronously loaded CSS or JS files from
// the previous version are used to try to render the asynchronously loaded
// HTML content from a newer version, there can be a mismatch.  To help the
// server-side deal with this, this module will add a custom HTTP header to
// every asynchronous call with the version number.  To enable this
// feature, you need to ensure that the javascript variable AN_VERSION is
// set to the current version somewhere before this module loads.  When
// that variable exists, this module will add the header "X-AN-Version"
// with the value of that variable. The server can use this to detect if
// that matches the currently running server version and take action if
// needed.  A typical action is to render a dialog to the use to force a
// synchronous refresh to ensure the latest version of the CSS and JS
// assets are loaded.

//====================
// The handle for forms that want to  trigger an ansynchonous (aka, ajax)
// request.
//
function asyncSubmitHandler(event) {
    event.preventDefault();
    event.stopPropagation();

    var $form = $(this);
    return asyncSubmitHandlerHelper( $form );
};

function asyncSubmitHandlerHelper( $form ) {

    if ( $form.attr('debounce') ) {
	$form.find('button').prop('disabled', true);
    }

    AN_handleHideShowIfNeeded( $form );

    var $target = getAsyncTarget( $form );

    var $mode = $form.attr('data-mode');
    if ( ! $mode ) {
        $mode = 'insert';
    }

    // If the form lies in a modal, then close the modal.
    beforeAsyncCall( $form );

    // In case the last submit button data was saved.
    // (See: lastButtonClickHandler)
    //
    var lastButtonName = $form.data('lastSubmitButtonName');
    var lastButtonValue = null;
    if ( lastButtonName ) {
        lastButtonValue = $form.data('lastSubmitButtonValue');

        // Make sure to remove it or we might think the submit button
        // we click on the next form submission when something else
        // could have triggered it (e.g., an onchange event)
        //
        $form.removeData('lastSubmitButtonName');
        $form.removeData('lastSubmitButtonValue');
    }
    
    var formData = null;
    var processData = true;
    var contentType = null;
    var async = true;
    var cache = true;


    if (( $($form).attr('method') )
        && ( $($form).attr('method').toUpperCase() == 'GET' )) {
        var formData = $form.serializeArray();
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
        var dummy = 0;
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
	    if ( typeof AN_VERSION !== 'undefined' ) {
		jqXHR.setRequestHeader('X-AN-Version', AN_VERSION );
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
            var http_code = xhr.status;
            var error_msg = thrownError;
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

    var $anchor = $(this);

    AN_handleHideShowIfNeeded( $anchor );

    // Special case for bootstrap dropdown menus that have data-async links
    // in them.  Since we are suppressing the event propagation here, we
    // have to close the menu ourselves on a click.
    //
    $anchor.closest('.dropdown-menu').removeClass('show');

    $('.an-async-hide').hide();
    $('.an-async-show').show();
    
    var $target = getAsyncTarget( $anchor );
    var $mode = $anchor.attr('data-mode');
    if ( ! $mode ) {
        $mode = 'insert';
    }

    var url = $anchor.attr('href');
    if ( $anchor.attr('data-params') ) {
        url += '?' + $anchor.attr('data-params');
    }

    // If the anchor lies within a modal, then close the modal
    beforeAsyncCall( $anchor );
    
    $.ajax({
        type: 'GET',
        url: url,
        
	beforeSend: function (jqXHR, settings) {
	    if ( typeof AN_VERSION !== 'undefined' ) {
		jqXHR.setRequestHeader('X-AN-Version', AN_VERSION );
	    }
	},
	
        success: function(data, status, xhr) {
            asyncUpdateData( $target, $mode, data, xhr );
            return false;
        },
        error: function (xhr, ajaxOptions, thrownError) {
            var http_code = xhr.status;
            var error_msg = thrownError;
            asyncUpdateData( $target, $mode, xhr.responseText, xhr );
            return false;
        } 

    });

    return false;
};

//====================
// For modal dialogs

var AN_lastModalId = 0;

function AN_getNewModal() {
    AN_lastModalId += 1;
    var htmlId = "antinode-modal-"+AN_lastModalId;
    var htmlString = '<div id="'+htmlId+'" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true"></div>';
    var modalObj = $.parseHTML(htmlString);
    $('body').append( modalObj );
    return $(modalObj);
};


//====================
function AN_handleHideShowIfNeeded( $anchor ) {

    var hide_selector = $anchor.attr('data-hide');
    if ( hide_selector ) {
	$(hide_selector).hide();
    }

    var show_selector = $anchor.attr('data-show');
    if ( show_selector ) {
	$(show_selector).show();
    }

};


//====================
// Common for POST and GET to find the target node for returned content

function getAsyncTarget( anchorNode ) {
    var targetSelector = $(anchorNode).attr('data-async');

    // Special case to allow us to create a modal for the content
    if ( targetSelector == "modal" ) {
        return AN_getNewModal();
    }
    return $(targetSelector);
};


//====================
// The Async "loading" spinner

function AN_insertLoadingImage() {
    // N.B. The negative margins in the css should be half the width of the loading image.
    var htmlString = '<div id="antinode-loader" style="display:none; position: absolute; top: 50%; left: 50%; margin-left: -64px; margin-top: -64px; z-index: 1020;"><img src="/static/img/antinode-loading.gif" alt="Page Loading Interstitial"/></div>';
    var loadingObj = $.parseHTML(htmlString);
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
    
    var ct = xhr.getResponseHeader("content-type") || "";
    
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
     var json = data;
     
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
	var url = json['location'];
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
        for ( var htmlId in json['replace'] ) {
            var targetObj = $("#"+htmlId);
            targetObj.replaceWith( json['replace'][htmlId] ).show();
            handleNewContentAdded( targetObj );
        }
    }
    
    // This entry should be a map from html ids to content that should
    // be changed.  This does not include the target element itself.
    //
    if ( 'insert' in json ) {
        for ( var htmlId in json['insert'] ) {
            var targetObj = $("#"+htmlId);
	    targetObj.empty();
            targetObj.html( json['insert'][htmlId] ).show();
            handleNewContentAdded( targetObj );
        }
    }
    
    // This entry should be a map from html ids to content that should
    // be appended. This add it as the last child of the target tag id.
    //
    if ( 'append' in json ) {
        for ( var htmlId in json['append'] ) {
            var targetObj = $("#"+htmlId);
            targetObj.append( json['append'][htmlId] ).show();
            handleNewContentAdded( targetObj );
        }
    }
    
    // In case any content with preserved scroll bars was refreshed.
    //
    afterAsyncRender();
    
    if ( 'modal' in json ) {
        var targetObj = AN_getNewModal();
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
    
    if ( typeof AN_handlePostAsyncUpdate === "function") {
	AN_handlePostAsyncUpdate();
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
    hideModalIfNeeded( $node );
    saveScrollBarPositions();
};

//====================
// Things that need to run after asynchronous content is rendered

var afterAsyncRenderFunctionList = [];
    
function afterAsyncRender() {

    for ( var i = 0; i < afterAsyncRenderFunctionList.length; i++ ) {
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
var scrollTopMap = {};

function saveScrollBarPositions() {

    // Anything marked as needing its scroll bar preserved should have us
    // save the position.
    //
    $('.preserve-scroll-bar').each( function( index ) {
        var id = $(this).attr('id');
        if ( id ) {
            scrollTopMap[id] = $(this).scrollTop();
        }
    });
    
};

function restoreScrollBarPositions() {
    for ( var id in scrollTopMap ) {
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
var AN_modalHideStartMs = null;

// When a modal show event happens while the hide event is active, we will
// stash the modal object to be show in this global variable so that when
// the hide event triggers, we know that we need to re-show the new modal
// content.
//
var AN_deferredModalShowObj = null;

// This is the safety check to make sure missing hidden.bsmodal events do
// not prevent modals from showing forever (or page refresh really).
//
function checkModalHideState() {
    if ( AN_modalHideStartMs ) {
        var d = new Date();
        var nowMs = d.getTime();
        var diffMs = nowMs - AN_modalHideStartMs;
        if ( diffMs > 5000 ) {
            AN_modalHideStartMs = null;
        }
    }
};

// Pass in the object that the async event fires on.  If
// it is contained in a modal, then we will close the modal.
//
function hideModalIfNeeded( eventObj ) {
    var modalObj = $(eventObj).closest('.modal');
    if ( modalObj.length > 0 ) {
        hideModal( modalObj.first() );
    }
};

// Pass in the object that receives the async data and
// show it if it is contained in a modal.
//
function showModalIfNeeded( targetObj ) {
    var modalObj = $(targetObj).closest('.modal');
    if ( modalObj.length > 0 ) {
        showModal( modalObj.first() );
    }
};

function showModal( modalObj ) {
    if ( ! $(modalObj).modal ) {
        return;
    }
    checkModalHideState();
    if ( AN_modalHideStartMs ) {
        AN_deferredModalShowObj = modalObj;
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
    // AN_modalHideStartMs to 'false'.
    //
    var d = new Date();
    AN_modalHideStartMs = d.getTime();
    $(modalObj).modal("hide");

};

function handleModalHiddenEvent( modalObj ) {
    try {
        AN_modalHideStartMs = null;
        if ( AN_deferredModalShowObj ) {
            showModal( AN_deferredModalShowObj );
        } 
        
    } catch (e) {
        console.error('Problem handling modal hidden event');
    }
    finally {
        AN_modalHideStartMs = null;
        AN_deferredModalShowObj = null;
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
	    if ( typeof AN_VERSION !== 'undefined' ) {
		jqXHR.setRequestHeader('X-AN-Version', AN_VERSION );
	    }
	},
        success: function(data, status, xhr) {
            asyncUpdateData( $target, $mode, data, xhr );
        },
        error: function (xhr, ajaxOptions, thrownError) {
            var http_code = xhr.status;
            var error_msg = thrownError;
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

        var csrftoken = Cookies.get('csrftoken');
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
    var theForm = $(this).closest('form');
    $(theForm).data('lastSubmitButtonName', this.name);
    $(theForm).data('lastSubmitButtonValue', this.value);
};

function showLoadingIniterstitial() {
    $('#antinode-loader').show();
};

function hideLoadingIniterstitial() {
    $('#antinode-loader').hide();
};

//====================
// Adding handlers that look at special HTML tag attributes to determine
// which ones want to be done ansynchonously (aka, AJAX)
//
jQuery(function($) {

    // Always want to show some visual indication that an async request
    // is in progress.
    //
    AN_insertLoadingImage();

    // These ensure that we'll pay attention to the special async attributes.
    //
    $('body').on('submit', 'form[data-async]', asyncSubmitHandler );
    $('body').on('click', 'a[data-async]', asyncClickHandler );
    $('body').on('click', 'div[data-async]', asyncClickHandler );
    $('body').on('click', 'form[data-async] button', lastButtonClickHandler );

    // This is to support auto-submitting from SELECT elements asnychronously.
    //
    $('body').on('change', 'select[onchange-async]', function() {
        var $form = $(this.form);
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

    var initial_modal_content = $('#antinode-initial-modal');
    if ( initial_modal_content.length > 0 ) {
	var targetObj = AN_getNewModal();
        targetObj.append( initial_modal_content )
        showModal( targetObj );
    }
    
});

$(document)
    .ajaxStart(function () {
      $('#antinode-loader').show();
    })
    .ajaxStop(function () {
        $('#antinode-loader').hide();
    });

