(function() {

    window.Hi = window.Hi || {};

    /*
      FILE VIEWER

      - Shows an app-served file in a full-screen overlay instead of a
        new tab. Any element carrying Hi.FILE_VIEWER_URL_ATTR opens it on
        click; the server renders those attributes (file_viewer_attrs),
        including the kind of viewing, from the file's MIME type.
      - The overlay markup is server-rendered once per page
        (panes/file_viewer.html). This module only shows one region at a
        time, fills slots, and sets media sources; it builds no markup.
      - The overlay stacks above any open Bootstrap modal without closing
        it, so the page and modal state (unsaved edits, tabs, scroll) are
        untouched. Two Bootstrap behaviors would interfere: the modal's
        focus trap (a document-level focusin handler that pulls focus
        back into the modal) and its Escape-to-close. The trap is
        switched off while the viewer is open and re-armed on close;
        it cannot be blocked from the overlay, since jQuery listens for
        focusin in the capture phase. Escape is taken in the capture
        phase while the viewer is open.
      - Each open is a session. Closing aborts the session's signal,
        which cancels its fetch and removes its media listeners, so late
        events from an earlier file cannot touch a later one.
      - Zoom steps are multiples of the fitted size, keeping the point at
        the center of the view in place. Fit never enlarges an image
        beyond its natural size; a PDF fits its page width to the view.
      - PDFs are drawn by file-viewer-pdf.js. When pdf.js cannot run in
        the browser, the viewer says so rather than reporting the file
        as unloadable.
      - Open-in-new-tab links get the file's URL while it is shown. They
        are external links (browser_nav, see device.js). A modal shown
        while the viewer is open, such as the device's "not available"
        message, is raised above the viewer, and keys are left to it.
        When it closes, focus returns to the viewer (antinode would
        otherwise focus an [autofocus] element behind it) and the modal
        underneath keeps its scrolling (Bootstrap clears modal-open).
      - The alert banner stays above the viewer, which starts below it
        while it shows (TOP_INSET_PROPERTY) so it never covers Close.
    */

    // FileViewerKind external names (hi.apps.common.file_viewer).
    const KIND = {
        IMAGE       : 'image',
        PDF         : 'pdf',
        VIDEO       : 'video',
        AUDIO       : 'audio',
        TEXT        : 'text',
        UNSUPPORTED : 'unsupported'
    };

    const STATE_REGION = {
        LOADING         : 'loading',
        ERROR           : 'error',
        PDF_UNSUPPORTED : 'pdf-unsupported'
    };

    const ACTION = {
        CLOSE    : 'close',
        ZOOM_IN  : 'zoom-in',
        ZOOM_OUT : 'zoom-out',
        ZOOM_FIT : 'zoom-fit'
    };

    const SLOT = {
        TITLE      : 'title',
        SUBTITLE   : 'subtitle',
        FILENAME   : 'filename',
        MIME_TYPE  : 'mime-type',
        SIZE       : 'size',
        TEXT       : 'text',
        ZOOM_LEVEL : 'zoom-level',
        PAGE       : 'page-indicator'
    };

    const REGION_ATTR = 'data-file-viewer-region';
    const SLOT_ATTR = 'data-file-viewer-slot';
    const ACTION_ATTR = 'data-file-viewer-action';
    const TOOLBAR_ATTR = 'data-file-viewer-toolbar';
    const PAGE_GROUP_ATTR = 'data-file-viewer-page-group';
    const SCROLL_ATTR = 'data-file-viewer-scroll';
    const STAGE_ATTR = 'data-file-viewer-stage';
    const MEDIA_ATTR = 'data-file-viewer-media';
    const OPEN_TAB_ATTR = 'data-file-viewer-open-tab';
    const PDF_PAGES_ATTR = 'data-file-viewer-pdf-pages';
    const PDF_PAGE_TEMPLATE_ATTR = 'data-file-viewer-pdf-page-template';

    const OPEN_ROOT_CLASS = 'hi-file-viewer-open';
    const TOP_INSET_PROPERTY = '--hi-file-viewer-top-inset';
    const ABOVE_VIEWER_CLASS = 'hi-file-viewer-above';

    // Bootstrap 4 modal internals (bootstrap.js, Modal._enforceFocus).
    const BOOTSTRAP_FOCUS_TRAP_EVENT = 'focusin.bs.modal';
    const BOOTSTRAP_MODAL_DATA_KEY = 'bs.modal';
    const SHOWN_MODAL_SELECTOR = '.modal.show';
    const MODAL_BACKDROP_SELECTOR = '.modal-backdrop';

    const ZOOM_STEPS = [ 1, 1.5, 2, 3, 4 ];
    const ZOOMABLE_KINDS = new Set([ KIND.IMAGE, KIND.PDF ]);

    // Larger text files are not worth reading into the page.
    const TEXT_MAX_BYTES = 1024 * 1024;

    const BOOTSTRAP_MODAL_OPEN_CLASS = 'modal-open';
    const MODAL_SELECTOR = '.modal';

    const FOCUSABLE_SELECTOR = 'a[href], button, video, audio, [tabindex="0"]';

    // Exposed for tests.
    const HiFileViewer = {
        nextZoomIndex: function( zoomIndex, action ) {
            return _nextZoomIndex( zoomIndex, action );
        },
        readTextWithinLimit: function( response, maxBytes ) {
            return _readTextWithinLimit( response, maxBytes );
        }
    };

    window.Hi.fileViewer = HiFileViewer;

    let _viewerElement = null;
    let _bannerObserver = null;
    let _session = null;   // { file, trigger, zoomIndex, abortController, pdfView }

    /* Elements */

    function _viewer() {
        if ( ! _viewerElement || ! _viewerElement.isConnected ) {
            _viewerElement = document.getElementById( Hi.FILE_VIEWER_ID );
        }
        return _viewerElement;
    }

    function _region( name ) {
        return _viewer().querySelector( '[' + REGION_ATTR + '="' + name + '"]' );
    }

    function _slot( name ) {
        return _viewer().querySelector( '[' + SLOT_ATTR + '="' + name + '"]' );
    }

    function _media( kind ) {
        return _region( kind ).querySelector( '[' + MEDIA_ATTR + ']' );
    }

    function _closeButton() {
        return _viewer().querySelector( '[' + ACTION_ATTR + '="' + ACTION.CLOSE + '"]' );
    }

    function _toolbar() {
        return _viewer().querySelector( '[' + TOOLBAR_ATTR + ']' );
    }

    function _pageGroup() {
        return _viewer().querySelector( '[' + PAGE_GROUP_ATTR + ']' );
    }

    function _scrollElementOf( kind ) {
        return _region( kind ).querySelector( '[' + SCROLL_ATTR + ']' );
    }

    /* Opening and closing */

    function _fileOf( triggerElement ) {
        return {
            url      : triggerElement.getAttribute( Hi.FILE_VIEWER_URL_ATTR ),
            kind     : triggerElement.getAttribute( Hi.FILE_VIEWER_KIND_ATTR ) || KIND.UNSUPPORTED,
            title    : triggerElement.getAttribute( Hi.FILE_VIEWER_TITLE_ATTR ) || '',
            filename : triggerElement.getAttribute( Hi.FILE_VIEWER_FILENAME_ATTR ) || '',
            mimeType : triggerElement.getAttribute( Hi.FILE_VIEWER_MIME_TYPE_ATTR ) || '',
            size     : triggerElement.getAttribute( Hi.FILE_VIEWER_SIZE_ATTR ) || ''
        };
    }

    function _open( triggerElement ) {
        if ( ! _viewer() ) {
            return;
        }
        _close();
        const file = _fileOf( triggerElement );
        _session = {
            file            : file,
            trigger         : triggerElement,
            zoomIndex       : 0,
            abortController : new AbortController(),
            pdfView         : null
        };

        // A focused field would keep the on-screen keyboard up.
        if ( document.activeElement instanceof HTMLElement ) {
            document.activeElement.blur();
        }
        _fillHeader( file );
        _setOpenTabUrl( file.url );
        _suspendModalFocusTrap();
        _followAlertBanner();
        document.documentElement.classList.add( OPEN_ROOT_CLASS );
        _viewer().hidden = false;
        _showRegion( STATE_REGION.LOADING );
        _closeButton().focus();

        const loader = LOADERS[ file.kind ] || _loadUnsupported;
        loader( _session );
    }

    function _close() {
        if ( ! _session ) {
            return;
        }
        const session = _session;
        _session = null;
        session.abortController.abort();
        if ( session.pdfView ) {
            session.pdfView.destroy();
        }
        _clearContent();
        _setOpenTabUrl( null );
        _viewer().hidden = true;
        document.documentElement.classList.remove( OPEN_ROOT_CLASS );
        _stopFollowingAlertBanner();
        _restoreModalFocusTrap();
        if ( session.trigger.isConnected ) {
            session.trigger.focus({ preventScroll: true });
        }
    }

    // The banner's height is 0 while hidden, so the inset follows it
    // appearing, collapsing and growing.
    function _followAlertBanner() {
        const bannerElement = document.getElementById( Hi.ALERT_BANNER_CONTAINER_ID );
        if ( ! bannerElement ) {
            return;
        }
        _bannerObserver = new ResizeObserver( function() {
            const bannerBottom = Math.max( 0, bannerElement.getBoundingClientRect().bottom );
            _viewer().style.setProperty( TOP_INSET_PROPERTY, bannerBottom + 'px' );
            _handleResize();
        });
        _bannerObserver.observe( bannerElement );
    }

    function _stopFollowingAlertBanner() {
        if ( _bannerObserver ) {
            _bannerObserver.disconnect();
            _bannerObserver = null;
        }
        _viewer().style.removeProperty( TOP_INSET_PROPERTY );
    }

    function _suspendModalFocusTrap() {
        $( document ).off( BOOTSTRAP_FOCUS_TRAP_EVENT );
    }

    function _restoreModalFocusTrap() {
        const modal = $( SHOWN_MODAL_SELECTOR ).not( '.' + ABOVE_VIEWER_CLASS ).last()
              .data( BOOTSTRAP_MODAL_DATA_KEY );
        if ( modal ) {
            modal._enforceFocus();
        }
    }

    function _clearContent() {
        [ KIND.VIDEO, KIND.AUDIO ].forEach( function( kind ) {
            const mediaElement = _media( kind );
            mediaElement.pause();
            mediaElement.removeAttribute( 'src' );
            mediaElement.load();
        });
        const imageElement = _media( KIND.IMAGE );
        imageElement.removeAttribute( 'src' );
        imageElement.style.width = '';
        imageElement.style.height = '';
        _slot( SLOT.TEXT ).textContent = '';
        _toolbar().hidden = true;
        _pageGroup().hidden = true;
        [ KIND.IMAGE, KIND.PDF ].forEach( function( kind ) {
            const scrollElement = _scrollElementOf( kind );
            scrollElement.scrollTop = 0;
            scrollElement.scrollLeft = 0;
        });
    }

    function _fillHeader( file ) {
        _slot( SLOT.TITLE ).textContent = file.title;
        const subtitleElement = _slot( SLOT.SUBTITLE );
        subtitleElement.textContent = [ file.filename, file.mimeType, file.size ]
            .filter( Boolean )
            .join( subtitleElement.dataset.separator );
    }

    function _setOpenTabUrl( url ) {
        _viewer().querySelectorAll( '[' + OPEN_TAB_ATTR + ']' ).forEach( function( linkElement ) {
            if ( url ) {
                linkElement.setAttribute( 'href', url );
            } else {
                linkElement.removeAttribute( 'href' );
            }
        });
    }

    function _showRegion( name ) {
        _viewer().querySelectorAll( '[' + REGION_ATTR + ']' ).forEach( function( regionElement ) {
            regionElement.hidden = ( regionElement.getAttribute( REGION_ATTR ) !== name );
        });
    }

    // Runs a session's handler only while that session is still open.
    function _ifCurrent( session, handler ) {
        return function( ...args ) {
            if ( session === _session ) {
                handler( ...args );
            }
        };
    }

    function _showError() {
        _showState( STATE_REGION.ERROR );
    }

    function _showState( stateRegion ) {
        _toolbar().hidden = true;
        _showRegion( stateRegion );
    }

    /* Loaders, one per kind */

    function _loadImage( session ) {
        const imageElement = _media( KIND.IMAGE );
        const options = { once: true, signal: session.abortController.signal };
        imageElement.addEventListener( 'load', _ifCurrent( session, function() {
            _showRegion( KIND.IMAGE );
            _toolbar().hidden = false;
            _applyZoom({ keepViewCenter: false });
        }), options );
        imageElement.addEventListener( 'error', _ifCurrent( session, _showError ), options );
        imageElement.src = session.file.url;
    }

    function _loadPdf( session ) {
        const regionElement = _region( KIND.PDF );
        session.pdfView = Hi.fileViewerPdf.createView({
            url           : session.file.url,
            configElement : regionElement,
            scrollElement : _scrollElementOf( KIND.PDF ),
            pagesElement  : regionElement.querySelector( '[' + PDF_PAGES_ATTR + ']' ),
            pageTemplate  : regionElement.querySelector( '[' + PDF_PAGE_TEMPLATE_ATTR + ']' ),
            onPageChange  : _ifCurrent( session, _showPageNumber )
        });
        session.pdfView.load().then(
            _ifCurrent( session, function() {
                _showRegion( KIND.PDF );
                _toolbar().hidden = false;
                _pageGroup().hidden = false;
                _applyZoom({ keepViewCenter: false });
            }),
            _ifCurrent( session, function( error ) {
                _showState( Hi.fileViewerPdf.isDocumentError( error )
                            ? STATE_REGION.ERROR
                            : STATE_REGION.PDF_UNSUPPORTED );
            })
        );
    }

    function _showPageNumber( pageNumber, pageCount ) {
        const pageElement = _slot( SLOT.PAGE );
        pageElement.textContent = pageNumber + pageElement.dataset.separator + pageCount;
    }

    // Shown at once: the native controls show their own loading state,
    // and some browsers skip preloading (e.g. in low-power modes).
    function _loadMedia( session, kind ) {
        const mediaElement = _media( kind );
        const options = { once: true, signal: session.abortController.signal };
        mediaElement.addEventListener( 'error', _ifCurrent( session, _showError ), options );
        mediaElement.src = session.file.url;
        _showRegion( kind );
    }

    function _loadText( session ) {
        fetch( session.file.url, { signal: session.abortController.signal })
            .then( function( response ) {
                return _readTextWithinLimit( response, TEXT_MAX_BYTES );
            })
            .then(
                _ifCurrent( session, function( text ) {
                    if ( text === null ) {
                        _loadUnsupported( session );
                        return;
                    }
                    _slot( SLOT.TEXT ).textContent = text;
                    _showRegion( KIND.TEXT );
                }),
                _ifCurrent( session, _showError )
            );
    }

    // Resolves to the response's text, or to null when it exceeds
    // maxBytes; rejects for an HTTP error. Reads incrementally so an
    // oversized file is not fully downloaded.
    async function _readTextWithinLimit( response, maxBytes ) {
        if ( ! response.ok ) {
            throw new Error( 'File request failed: ' + response.status );
        }
        const declaredLength = Number( response.headers.get( 'Content-Length' ));
        if ( declaredLength > maxBytes ) {
            response.body.cancel();
            return null;
        }
        const reader = response.body.getReader();
        const chunks = [];
        let totalBytes = 0;
        while ( true ) {
            const { done, value } = await reader.read();
            if ( done ) {
                break;
            }
            totalBytes += value.length;
            if ( totalBytes > maxBytes ) {
                reader.cancel();
                return null;
            }
            chunks.push( value );
        }
        return new TextDecoder().decode( await new Blob( chunks ).arrayBuffer() );
    }

    function _loadUnsupported( session ) {
        const file = session.file;
        _fillDetail( SLOT.FILENAME, file.filename );
        _fillDetail( SLOT.MIME_TYPE, file.mimeType );
        _fillDetail( SLOT.SIZE, file.size );
        _showRegion( KIND.UNSUPPORTED );
    }

    function _fillDetail( slotName, value ) {
        const slotElement = _slot( slotName );
        slotElement.textContent = value || slotElement.dataset.emptyText;
    }

    const LOADERS = {
        [ KIND.IMAGE ]       : _loadImage,
        [ KIND.PDF ]         : _loadPdf,
        [ KIND.VIDEO ]       : function( session ) { _loadMedia( session, KIND.VIDEO ); },
        [ KIND.AUDIO ]       : function( session ) { _loadMedia( session, KIND.AUDIO ); },
        [ KIND.TEXT ]        : _loadText,
        [ KIND.UNSUPPORTED ] : _loadUnsupported
    };

    /* Zoom */

    function _nextZoomIndex( zoomIndex, action ) {
        if ( action === ACTION.ZOOM_FIT ) {
            return 0;
        }
        const step = ( action === ACTION.ZOOM_IN ) ? 1 : -1;
        return Math.min( ZOOM_STEPS.length - 1, Math.max( 0, zoomIndex + step ));
    }

    function _zoom( action ) {
        if ( ! _session || ! ZOOMABLE_KINDS.has( _session.file.kind )) {
            return;
        }
        _session.zoomIndex = _nextZoomIndex( _session.zoomIndex, action );
        _applyZoom();
    }

    // The first layout of a file has no view center worth keeping.
    function _applyZoom( { keepViewCenter = true } = {} ) {
        const kind = _session.file.kind;
        const zoomFactor = ZOOM_STEPS[ _session.zoomIndex ];
        _updateZoomControls( _session.zoomIndex );
        const resize = ( kind === KIND.PDF )
              ? function() { _session.pdfView.setZoom( zoomFactor ); }
              : function() { _resizeImage( zoomFactor ); };
        if ( keepViewCenter ) {
            _keepingViewCenter( _scrollElementOf( kind ), resize );
        } else {
            resize();
        }
    }

    // Runs resize, then scrolls so the point that was at the center of
    // the view is at the center again.
    function _keepingViewCenter( scrollElement, resize ) {
        const centerX = ( scrollElement.scrollLeft + scrollElement.clientWidth / 2 ) / scrollElement.scrollWidth;
        const centerY = ( scrollElement.scrollTop + scrollElement.clientHeight / 2 ) / scrollElement.scrollHeight;
        resize();
        scrollElement.scrollLeft = centerX * scrollElement.scrollWidth - scrollElement.clientWidth / 2;
        scrollElement.scrollTop = centerY * scrollElement.scrollHeight - scrollElement.clientHeight / 2;
    }

    function _updateZoomControls( zoomIndex ) {
        _slot( SLOT.ZOOM_LEVEL ).textContent = Math.round( ZOOM_STEPS[ zoomIndex ] * 100 ) + '%';
        const isFit = ( zoomIndex === 0 );
        const isMax = ( zoomIndex === ZOOM_STEPS.length - 1 );
        _toolbar().querySelector( '[' + ACTION_ATTR + '="' + ACTION.ZOOM_OUT + '"]' ).disabled = isFit;
        _toolbar().querySelector( '[' + ACTION_ATTR + '="' + ACTION.ZOOM_FIT + '"]' ).disabled = isFit;
        _toolbar().querySelector( '[' + ACTION_ATTR + '="' + ACTION.ZOOM_IN + '"]' ).disabled = isMax;
    }

    // Sizes the image to the zoom factor over its fitted size. An image
    // without intrinsic dimensions (some SVGs) keeps its default size.
    function _resizeImage( zoomFactor ) {
        const regionElement = _region( KIND.IMAGE );
        const scrollElement = _scrollElementOf( KIND.IMAGE );
        const stageStyle = getComputedStyle( regionElement.querySelector( '[' + STAGE_ATTR + ']' ));
        const imageElement = _media( KIND.IMAGE );
        if ( ! imageElement.naturalWidth || ! imageElement.naturalHeight ) {
            return;
        }

        const availableWidth = scrollElement.clientWidth
              - parseFloat( stageStyle.paddingLeft ) - parseFloat( stageStyle.paddingRight );
        const availableHeight = scrollElement.clientHeight
              - parseFloat( stageStyle.paddingTop ) - parseFloat( stageStyle.paddingBottom );
        const fitScale = Math.min( availableWidth / imageElement.naturalWidth,
                                   availableHeight / imageElement.naturalHeight,
                                   1 );
        imageElement.style.width = Math.round( imageElement.naturalWidth * fitScale * zoomFactor ) + 'px';
        imageElement.style.height = Math.round( imageElement.naturalHeight * fitScale * zoomFactor ) + 'px';
    }

    /* Keyboard: Escape closes; Tab stays within the viewer. */

    function _handleKeydown( event ) {
        if ( ! _session || _hasModalAbove() ) {
            return;
        }
        if ( event.key === 'Escape' ) {
            event.preventDefault();
            event.stopImmediatePropagation();
            _close();
        } else if ( event.key === 'Tab' ) {
            _keepTabFocusInside( event );
        }
    }

    function _keepTabFocusInside( event ) {
        const focusable = Array.from( _viewer().querySelectorAll( FOCUSABLE_SELECTOR ))
              .filter( function( element ) {
                  return ! element.disabled && element.getClientRects().length > 0;
              });
        if ( focusable.length === 0 ) {
            return;
        }
        const first = focusable[ 0 ];
        const last = focusable[ focusable.length - 1 ];
        const isInside = _viewer().contains( document.activeElement );
        if ( event.shiftKey && ( document.activeElement === first || ! isInside )) {
            event.preventDefault();
            last.focus();
        } else if ( ! event.shiftKey && ( document.activeElement === last || ! isInside )) {
            event.preventDefault();
            first.focus();
        }
    }

    /* Modals shown while the viewer is open stack above it. */

    function _raiseModal( event ) {
        if ( ! _session || event.target !== this ) {
            return;
        }
        const modalElement = event.target;
        modalElement.classList.add( ABOVE_VIEWER_CLASS );
        // Bootstrap appends the backdrop right after the show event.
        queueMicrotask( function() {
            const backdrops = document.querySelectorAll( MODAL_BACKDROP_SELECTOR );
            if ( backdrops.length > 0 ) {
                backdrops[ backdrops.length - 1 ].classList.add( ABOVE_VIEWER_CLASS );
            }
        });
    }

    // Bound directly on document, so it runs after antinode's handler on
    // body, which also removes the modal: a delegated binding would no
    // longer match the detached element.
    function _handleModalHidden( event ) {
        const modalElement = event.target;
        if ( ! modalElement.classList.contains( ABOVE_VIEWER_CLASS )) {
            return;
        }
        modalElement.classList.remove( ABOVE_VIEWER_CLASS );
        if ( document.querySelector( SHOWN_MODAL_SELECTOR )) {
            document.body.classList.add( BOOTSTRAP_MODAL_OPEN_CLASS );
        }
        if ( _session ) {
            _closeButton().focus();
        }
    }

    function _hasModalAbove() {
        return Boolean( document.querySelector( SHOWN_MODAL_SELECTOR + '.' + ABOVE_VIEWER_CLASS ));
    }

    /* Event wiring */

    function _handleClick( event ) {
        if ( ! ( event.target instanceof Element )) {
            return;
        }
        const actionElement = event.target.closest( '[' + ACTION_ATTR + ']' );
        if ( actionElement && _viewer() && _viewer().contains( actionElement )) {
            const action = actionElement.getAttribute( ACTION_ATTR );
            if ( action === ACTION.CLOSE ) {
                _close();
            } else {
                _zoom( action );
            }
            return;
        }
        const triggerElement = event.target.closest( '[' + Hi.FILE_VIEWER_URL_ATTR + ']' );
        if ( triggerElement ) {
            event.preventDefault();
            _open( triggerElement );
        }
    }

    function _handleResize() {
        if ( _session && ZOOMABLE_KINDS.has( _session.file.kind ) && ! _region( _session.file.kind ).hidden ) {
            _applyZoom();
        }
    }

    document.addEventListener( 'click', _handleClick );
    document.addEventListener( 'keydown', _handleKeydown, true );
    window.addEventListener( 'resize', _handleResize );
    // show is delegated, like the app's other modal handlers, so one of
    // them stopping propagation (attr.js does for shown) cannot skip it.
    $( document ).on( 'show.bs.modal', MODAL_SELECTOR, _raiseModal );
    $( document ).on( 'hidden.bs.modal', _handleModalHidden );

})();
