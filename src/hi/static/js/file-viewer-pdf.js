(function() {

    window.Hi = window.Hi || {};

    /*
      FILE VIEWER: PDF

      - Renders a PDF for file-viewer.js, using the vendored pdf.js
        legacy build. The library is imported on the first PDF opened;
        its URLs, and those of the resources it fetches as a document
        needs them, come from data- attributes on the shell's PDF region.
      - Each page is a clone of the shell's page template, sized before
        it is drawn so the scroll height is stable. A page not yet
        fetched takes the first page's size until it is.
      - Only pages near the view hold a drawn canvas; pages leaving it
        are released (canvas and pdf.js page resources), which bounds
        memory on long documents. A canvas being dropped is first sized
        to zero: WebKit reclaims canvas memory slowly and caps the total.
      - Zooming resizes every page at once (canvases stretch until
        redrawn), then redraws the pages in view after a short pause so
        repeated taps redraw once. A redraw goes to a fresh canvas that
        replaces the old one when done, so a page never flashes blank.
      - A canvas's backing size is its CSS size times devicePixelRatio,
        reduced when needed to stay within MAX_CANVAS_PIXELS. Large pages
        at high zoom are then slightly soft rather than exhausting
        memory (notably on iPads).
      - The current page is the one crossing the line a third of the way
        down the view.
      - A failed load is either the document's fault (unreachable,
        invalid, password-protected) or pdf.js's: it cannot run in this
        browser (e.g. a missing newer JavaScript feature), whatever the
        document. isDocumentError tells them apart using pdf.js's own
        error types, so no list of browser features has to be kept.
    */

    const MAX_CANVAS_PIXELS = 16 * 1024 * 1024;
    const RENDER_MARGIN = '200px 0px';
    const REDRAW_DELAY_MS = 150;
    const CURRENT_PAGE_LINE_FRACTION = 1 / 3;
    const MAX_FIT_WIDTH_PROPERTY = '--hi-file-viewer-pdf-max-fit-width';

    const HiFileViewerPdf = {
        // options: {
        //   url,
        //   configElement:  carries the data-pdfjs-* asset URLs,
        //   scrollElement:  the scrolling view,
        //   pagesElement:   receives one page element per page,
        //   pageTemplate:   <template> whose first element is a page,
        //   onPageChange( pageNumber, pageCount )
        // }
        createView: function( options ) {
            return new PdfView( options );
        },
        outputScale: function( cssWidth, cssHeight, devicePixelRatio, maxPixels ) {
            return _outputScale( cssWidth, cssHeight, devicePixelRatio, maxPixels );
        },
        pageNumberAt: function( pageTops, offset ) {
            return _pageNumberAt( pageTops, offset );
        },
        isDocumentError: function( error ) {
            return _isDocumentError( error );
        }
    };

    window.Hi.fileViewerPdf = HiFileViewerPdf;

    let _libraryPromise = null;
    let _library = null;   // set once the import succeeds

    function _loadLibrary( configElement ) {
        if ( ! _libraryPromise ) {
            const libraryUrl = configElement.dataset.pdfjsLibraryUrl;
            const workerUrl = configElement.dataset.pdfjsWorkerUrl;
            _libraryPromise = import( libraryUrl ).then( function( pdfjsLib ) {
                pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
                _library = pdfjsLib;
                return pdfjsLib;
            });
            // A failed import may be transient; let the next PDF retry.
            _libraryPromise.catch( function() {
                _libraryPromise = null;
            });
        }
        return _libraryPromise;
    }

    function _isDocumentError( error ) {
        if ( ! _library ) {
            return false;
        }
        return ( error instanceof _library.ResponseException )
            || ( error instanceof _library.InvalidPDFException )
            || ( error instanceof _library.PasswordException );
    }

    function _discardCanvas( canvas ) {
        canvas.width = 0;
        canvas.height = 0;
    }

    function _outputScale( cssWidth, cssHeight, devicePixelRatio, maxPixels ) {
        const pixelRatio = devicePixelRatio || 1;
        const cssPixels = cssWidth * cssHeight;
        if ( cssPixels <= 0 ) {
            return pixelRatio;
        }
        return Math.min( pixelRatio, Math.sqrt( maxPixels / cssPixels ));
    }

    // pageTops ascend; returns the 1-based number of the last page that
    // starts at or above offset (the first page if none do).
    function _pageNumberAt( pageTops, offset ) {
        let low = 0;
        let high = pageTops.length - 1;
        let foundIndex = 0;
        while ( low <= high ) {
            const middle = Math.floor(( low + high ) / 2 );
            if ( pageTops[ middle ] <= offset ) {
                foundIndex = middle;
                low = middle + 1;
            } else {
                high = middle - 1;
            }
        }
        return foundIndex + 1;
    }

    class PdfView {

        constructor( options ) {
            this._url = options.url;
            this._configElement = options.configElement;
            this._scrollElement = options.scrollElement;
            this._pagesElement = options.pagesElement;
            this._pageTemplate = options.pageTemplate;
            this._onPageChange = options.onPageChange;

            this._pdfjsLib = null;
            this._loadingTask = null;
            this._document = null;
            this._firstPageSize = null;   // viewport of page 1 at scale 1
            this._pages = [];             // see _createPage
            this._scale = null;
            this._observer = null;
            this._redrawTimer = null;
            this._scrollFrame = null;
            this._currentPageNumber = null;
            this._isDestroyed = false;
            this._handleScroll = this._handleScroll.bind( this );
        }

        // Resolves once the document is open and its pages laid out, but
        // not yet sized or drawn: that waits for the first setZoom, made
        // once the region is visible and can be measured.
        async load() {
            this._pdfjsLib = await _loadLibrary( this._configElement );
            this._throwIfDestroyed();
            this._loadingTask = this._pdfjsLib.getDocument({
                url                 : this._url,
                wasmUrl             : this._configElement.dataset.pdfjsWasmUrl,
                standardFontDataUrl : this._configElement.dataset.pdfjsStandardFontDataUrl,
                iccUrl              : this._configElement.dataset.pdfjsIccUrl
            });
            this._document = await this._loadingTask.promise;
            this._throwIfDestroyed();
            const firstPage = await this._document.getPage( 1 );
            this._throwIfDestroyed();
            this._firstPageSize = firstPage.getViewport({ scale: 1 });
            for ( let pageNumber = 1; pageNumber <= this._document.numPages; pageNumber++ ) {
                this._pages.push( this._createPage( pageNumber ));
            }
            this._pages[ 0 ].pdfPage = firstPage;
        }

        // Sizes pages to zoomFactor times the fitted width and draws the
        // ones in view.
        setZoom( zoomFactor ) {
            if ( this._isDestroyed || ! this._document ) {
                return;
            }
            const scale = this._fitScale() * zoomFactor;
            if ( scale === this._scale ) {
                return;
            }
            this._scale = scale;
            this._pages.forEach( this._sizePage.bind( this ));
            if ( this._observer ) {
                this._scheduleRedraw();
            } else {
                this._startObserving();
            }
            this._updateCurrentPage();
        }

        destroy() {
            if ( this._isDestroyed ) {
                return;
            }
            this._isDestroyed = true;
            clearTimeout( this._redrawTimer );
            cancelAnimationFrame( this._scrollFrame );
            this._scrollElement.removeEventListener( 'scroll', this._handleScroll );
            if ( this._observer ) {
                this._observer.disconnect();
            }
            this._pages.forEach( function( page ) {
                if ( page.renderTask ) {
                    page.renderTask.cancel();
                }
                _discardCanvas( page.element.firstElementChild );
            });
            if ( this._loadingTask ) {
                // Also destroys the document and stops its worker.
                this._loadingTask.destroy();
            }
            this._pages = [];
            this._pagesElement.replaceChildren();
        }

        _throwIfDestroyed() {
            if ( this._isDestroyed ) {
                throw new Error( 'PDF view closed' );
            }
        }

        _createPage( pageNumber ) {
            const element = this._pageTemplate.content.firstElementChild.cloneNode( true );
            this._pagesElement.appendChild( element );
            return {
                number      : pageNumber,
                element     : element,
                pdfPage     : null,
                renderTask      : null,
                renderingScale  : null,
                drawnScale      : null,
                isNearView      : false
            };
        }

        _fitScale() {
            const pagesStyle = getComputedStyle( this._pagesElement );
            const availableWidth = this._scrollElement.clientWidth
                  - parseFloat( pagesStyle.paddingLeft ) - parseFloat( pagesStyle.paddingRight );
            const maxFitWidth = parseFloat(
                getComputedStyle( this._scrollElement ).getPropertyValue( MAX_FIT_WIDTH_PROPERTY )
            ) || availableWidth;
            return Math.min( availableWidth, maxFitWidth ) / this._firstPageSize.width;
        }

        _pageSize( page ) {
            if ( page.pdfPage ) {
                return page.pdfPage.getViewport({ scale: this._scale });
            }
            return {
                width  : this._firstPageSize.width * this._scale,
                height : this._firstPageSize.height * this._scale
            };
        }

        _sizePage( page ) {
            const size = this._pageSize( page );
            page.element.style.width = Math.floor( size.width ) + 'px';
            page.element.style.height = Math.floor( size.height ) + 'px';
        }

        _startObserving() {
            this._observer = new IntersectionObserver( this._handleIntersection.bind( this ), {
                root       : this._scrollElement,
                rootMargin : RENDER_MARGIN
            });
            this._pages.forEach( function( page ) {
                this._observer.observe( page.element );
            }, this );
            this._scrollElement.addEventListener( 'scroll', this._handleScroll, { passive: true } );
        }

        _handleIntersection( entries ) {
            entries.forEach( function( entry ) {
                const page = this._pageForElement( entry.target );
                if ( ! page ) {
                    return;
                }
                page.isNearView = entry.isIntersecting;
                if ( page.isNearView ) {
                    this._drawPage( page );
                } else {
                    this._releasePage( page );
                }
            }, this );
        }

        _pageForElement( element ) {
            return this._pages.find( function( page ) {
                return page.element === element;
            });
        }

        _scheduleRedraw() {
            clearTimeout( this._redrawTimer );
            this._redrawTimer = setTimeout( function() {
                this._pages.filter( function( page ) {
                    return page.isNearView;
                }).forEach( this._drawPage.bind( this ));
            }.bind( this ), REDRAW_DELAY_MS );
        }

        async _drawPage( page ) {
            const scale = this._scale;
            if ( page.drawnScale === scale ) {
                return;
            }
            if ( ! page.pdfPage ) {
                try {
                    page.pdfPage = await this._document.getPage( page.number );
                } catch ( error ) {
                    if ( ! this._isDestroyed ) {
                        console.warn( 'PDF page ' + page.number + ' failed to load:', error );
                    }
                    return;
                }
                if ( this._isDestroyed ) {
                    return;
                }
                // The placeholder had the first page's size.
                this._sizePage( page );
            }
            if ( ! page.isNearView || scale !== this._scale || page.drawnScale === scale ) {
                return;
            }
            if ( page.renderTask ) {
                if ( page.renderingScale === scale ) {
                    return;
                }
                page.renderTask.cancel();
            }

            const viewport = page.pdfPage.getViewport({ scale: scale });
            const outputScale = _outputScale( viewport.width, viewport.height,
                                              window.devicePixelRatio, MAX_CANVAS_PIXELS );
            const canvas = document.createElement( 'canvas' );
            canvas.className = page.element.firstElementChild.className;
            canvas.width = Math.floor( viewport.width * outputScale );
            canvas.height = Math.floor( viewport.height * outputScale );

            const renderTask = page.pdfPage.render({
                canvas    : canvas,
                viewport  : viewport,
                transform : ( outputScale === 1 ) ? null : [ outputScale, 0, 0, outputScale, 0, 0 ]
            });
            page.renderTask = renderTask;
            page.renderingScale = scale;
            try {
                await renderTask.promise;
            } catch ( error ) {
                if ( ! ( error instanceof this._pdfjsLib.RenderingCancelledException )) {
                    console.warn( 'PDF page ' + page.number + ' failed to render:', error );
                }
                _discardCanvas( canvas );
                return;
            } finally {
                if ( page.renderTask === renderTask ) {
                    page.renderTask = null;
                    page.renderingScale = null;
                }
            }
            if ( this._isDestroyed || ! page.isNearView ) {
                _discardCanvas( canvas );
                return;
            }
            const previousCanvas = page.element.firstElementChild;
            page.element.replaceChildren( canvas );
            _discardCanvas( previousCanvas );
            page.drawnScale = scale;
        }

        _releasePage( page ) {
            if ( page.renderTask ) {
                page.renderTask.cancel();
                page.renderTask = null;
                page.renderingScale = null;
            }
            if ( page.drawnScale !== null ) {
                _discardCanvas( page.element.firstElementChild );
                page.drawnScale = null;
            }
            if ( page.pdfPage ) {
                // Frees pdf.js's cached drawing data; the page itself stays.
                page.pdfPage.cleanup();
            }
        }

        _handleScroll() {
            if ( this._scrollFrame ) {
                return;
            }
            this._scrollFrame = requestAnimationFrame( function() {
                this._scrollFrame = null;
                this._updateCurrentPage();
            }.bind( this ));
        }

        _updateCurrentPage() {
            if ( this._isDestroyed ) {
                return;
            }
            const scrollElement = this._scrollElement;
            const offset = scrollElement.scrollTop + scrollElement.clientHeight * CURRENT_PAGE_LINE_FRACTION;
            const pageTops = this._pages.map( function( page ) {
                return page.element.offsetTop;
            });
            const pageNumber = _pageNumberAt( pageTops, offset );
            if ( pageNumber === this._currentPageNumber ) {
                return;
            }
            this._currentPageNumber = pageNumber;
            this._onPageChange( pageNumber, this._pages.length );
        }
    }

})();
