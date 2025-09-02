/*
 * Home Information - Attribute V2 Modal JavaScript
 * Enhanced entity attribute editing modal functionality
 * Phase 1a: Basic structure and framework
 */

(function() {
    'use strict';
    
    // Internal constants - JS-only, no server dependency
    const ATTR_V2_INTERNAL = {
        // State management data keys (different granularity levels)
        INITIALIZED_DATA_KEY: 'attr-v2-initialized',      // Container-level flag
        PROCESSED_DATA_KEY: 'attr-v2-processed',          // Element-level flag
        
        // Event namespaces
        AJAX_EVENT_NAMESPACE: 'attr-v2-ajax',
        OVERFLOW_EVENT_NAMESPACE: 'input.overflow',
        
        // HTTP/AJAX constants
        CSRF_TOKEN_NAME: 'csrfmiddlewaretoken',
        XML_HTTP_REQUEST_HEADER: 'X-Requested-With',
        AUTOSIZE_INITIALIZED_ATTR: 'data-autosize-initialized',
        
        // CSS state classes (JS-managed, not in templates)
        TRUNCATED_CLASS: 'truncated',
        MARKED_FOR_DELETION_CLASS: 'marked-for-deletion',
        DISPLAY_FIELD_CLASS: 'display-field',
        ACTIVATED_CLASS: 'activated',
        HAS_DIRTY_INDICATOR_CLASS: 'has-dirty-indicator',
        HAS_DIRTY_FIELD_CLASS: 'has-dirty-field',
        ACTIVE_CLASS: 'active',
        
        // Form field name patterns
        NAME_FIELD_SUFFIX: '-name',
        VALUE_FIELD_SUFFIX: '-value',
        DELETE_FIELD_SUFFIX: '-DELETE',
        
        // Status message CSS classes (Bootstrap)
        STATUS_SUCCESS_CLASS: 'text-success',
        STATUS_ERROR_CLASS: 'text-danger',
        STATUS_INFO_CLASS: 'text-info',
        STATUS_WARNING_CLASS: 'text-warning',
        
        // Bootstrap/generic classes
        MODAL_SELECTOR: '.modal',
        FORM_GROUP_SELECTOR: '.form-group'
    };
    
    // Create a namespace for V2 modal functions to avoid global pollution
    window.attrV2 = window.attrV2 || {};
    
    // Make initialization function globally accessible for template-driven initialization
    window.attrV2.initializeContainer = function(containerSelector) {
        const $container = $(containerSelector);
        if ($container.length > 0) {
            initializeAttrV2Container($container);
        }
    };
    
    // Custom Ajax Infrastructure
    window.attrV2.ajax = {
        // Submit form with custom Ajax handling
        submitFormWithAjax: function(form, options = {}) {
            console.log('DEBUG: submitFormWithAjax called with form:', form);
            const $form = $(form);
            
            // Find the container and sync textarea values to hidden fields before submission
            const $container = $form.closest(Hi.ATTR_V2_CONTAINER_SELECTOR);
            if ($container.length > 0) {
                syncTextareaValuesToHiddenFields($container);
            }
            
            const formData = new FormData(form);
            const url = $form.attr('action');
            const method = $form.attr('method') || 'POST';
            
            console.log('DEBUG: Form submission details:', { url, method, form: $form[0] });
            
            // Add CSRF token if not already present
            if (!formData.has(ATTR_V2_INTERNAL.CSRF_TOKEN_NAME)) {
                const csrfToken = $(`[name=${ATTR_V2_INTERNAL.CSRF_TOKEN_NAME}]`).val();
                if (csrfToken) {
                    formData.append(ATTR_V2_INTERNAL.CSRF_TOKEN_NAME, csrfToken);
                }
            }
            
            return $.ajax({
                url: url,
                method: method,
                data: formData,
                processData: false,
                contentType: false,
                headers: {
                    [ATTR_V2_INTERNAL.XML_HTTP_REQUEST_HEADER]: 'XMLHttpRequest'
                }
            }).done((response) => {
                this.handleFormSuccess(response, $form, options);
            }).fail((xhr) => {
                this.handleFormError(xhr, $form);
            });
        },
        
        // Load content into target via GET request
        loadContentIntoTarget: function(url, target, options = {}) {
            return $.ajax({
                url: url,
                method: 'GET',
                headers: {
                    [ATTR_V2_INTERNAL.XML_HTTP_REQUEST_HEADER]: 'XMLHttpRequest'
                }
            }).done((response) => {
                // Handle response for content loading
                if (typeof response === 'string') {
                    this.updateDOMElement(target, response, options.mode || 'replace');
                }
            }).fail((xhr) => {
                console.error('Failed to load content:', xhr);
            });
        },
        
        // Handle successful form submission
        handleFormSuccess: function(response, $form, options = {}) {
            // Try to parse as JSON first
            let data;
            try {
                data = typeof response === 'string' ? JSON.parse(response) : response;
            } catch (e) {
                // Fallback to treating as HTML (legacy antinode format)
                data = { html: response };
            }
            
            // Track the last append target for scrolling decision
            // When scrollToNewContent is requested and multiple updates occur,
            // we scroll to the LAST appended content. This decision assumes that
            // in most cases (like file uploads), the last append is the most
            // relevant/newest content the user wants to see. If different behavior
            // is needed, the caller should handle scrolling manually.
            let lastAppendTarget = null;
            
            if (data.updates && Array.isArray(data.updates)) {
                // New JSON format with multiple updates
                data.updates.forEach(update => {
                    if (update.target && update.html) {
                        this.updateDOMElement(update.target, update.html, update.mode || 'replace');
                        
                        // Track append operations for potential scrolling
                        if (update.mode === 'append') {
                            lastAppendTarget = update.target;
                        }
                    }
                });
            } else if (data.html) {
                // Single HTML update (legacy format)
                const containerId = $form.closest(Hi.ATTR_V2_CONTAINER_SELECTOR).attr('id');
                const target = `#${containerId} .${Hi.ATTR_V2_CONTENT_CLASS}`;
                this.updateDOMElement(target, data.html, 'replace');
            }
            
            // Handle scroll-to-new-content if requested by caller
            if (options.scrollToNewContent && lastAppendTarget) {
                const element = document.querySelector(lastAppendTarget);
                if (element) {
                    // Small delay to ensure DOM is fully updated before scrolling
                    setTimeout(() => {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 100);
                }
            }
            
            // Show success message if provided
            if (data.message) {
                this.showStatusMessage(data.message, 'success', $form);
            }
            
            // Re-initialize containers after update
            setTimeout(() => {
                initializeAllAttrV2Containers();
            }, 50);
            
            // Modal management is handled by antinode.js, not our responsibility
        },
        
        // Handle form submission errors
        handleFormError: function(xhr, $form) {
            let errorMessage = 'An error occurred while saving.';
            
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.message) {
                    errorMessage = response.message;
                } else if (response.errors) {
                    errorMessage = Object.values(response.errors).flat().join('; ');
                }
            } catch (e) {
                // Use default error message
            }
            
            this.showStatusMessage(errorMessage, 'error', $form);
        },
        
        // Update DOM element with new content
        updateDOMElement: function(selector, html, mode = 'replace') {
            const $target = $(selector);
            if ($target.length === 0) {
                console.warn('Target element not found:', selector);
                return;
            }
            
            switch (mode) {
                case 'replace':
                    $target.html(html);
                    break;
                case 'append':
                    $target.append(html);
                    break;
                case 'prepend':
                    $target.prepend(html);
                    break;
                default:
                    $target.html(html);
            }
        },
        
        // Show status message in appropriate container
        showStatusMessage: function(message, type = 'info', $form = null) {
            const $container = $form ? $form.closest(Hi.ATTR_V2_CONTAINER_SELECTOR) : $(Hi.ATTR_V2_CONTAINER_SELECTOR).first();
            const $statusMsg = $container.find(Hi.ATTR_V2_STATUS_MESSAGE_SELECTOR);
            
            if ($statusMsg.length === 0) return;
            
            const cssClass = type === 'success' ? ATTR_V2_INTERNAL.STATUS_SUCCESS_CLASS : 
                           type === 'error' ? ATTR_V2_INTERNAL.STATUS_ERROR_CLASS : ATTR_V2_INTERNAL.STATUS_INFO_CLASS;
            
            $statusMsg.text(message)
                     .removeClass(`${ATTR_V2_INTERNAL.STATUS_SUCCESS_CLASS} ${ATTR_V2_INTERNAL.STATUS_ERROR_CLASS} ${ATTR_V2_INTERNAL.STATUS_INFO_CLASS}`)
                     .addClass(cssClass)
                     .show();
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                $statusMsg.text('').removeClass(cssClass).hide();
            }, 5000);
        }
    };
    
    // Initialize all V2 containers when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeAllAttrV2Containers();
    });
    
    // No longer using antinode.js - initialization handled by custom Ajax callbacks
    
    // Listen for any modal shown events and initialize V2 containers
    $(document).on('shown.bs.modal', ATTR_V2_INTERNAL.MODAL_SELECTOR, function(e) {
        initializeAllAttrV2Containers();
        e.stopPropagation(); // Prevent bubbling to other handlers
    });
    
    // Container-aware utility function for updating form actions and browser history
    // This is a generic helper that can be called from template onclick handlers
    window.attrV2.updateFormAction = function(newUrl, containerId) {
        if (!newUrl || !containerId) {
            console.warn('attrV2.updateFormAction: newUrl and containerId are required');
            return;
        }
        
        // Find the form within the specific container
        const $container = $(`#${containerId}`);
        if ($container.length === 0) {
            console.warn('attrV2.updateFormAction: Container not found:', containerId);
            return;
        }
        
        const $form = $container.find(Hi.ATTR_V2_FORM_CLASS_SELECTOR);
        if ($form.length === 0) {
            console.warn('attrV2.updateFormAction: No form found in container:', containerId);
            return;
        }
        
        // Update form action
        $form.attr('action', newUrl);
        
        // Update browser history without page reload
        history.pushState(null, '', newUrl);
    };
    
    
    // Multi-instance container initialization
    function initializeAllAttrV2Containers() {
        // Initialize all attribute editing containers found on page
        $(Hi.ATTR_V2_CONTAINER_SELECTOR).each(function() {
            initializeAttrV2Container($(this));
        });
    }
    
    function initializeAttrV2Container($container) {
        // Check if this container is already initialized to prevent double-initialization
        if ($container.data(ATTR_V2_INTERNAL.INITIALIZED_DATA_KEY)) {
            console.log('DEBUG: Container already initialized, but reprocessing AJAX handlers for new content:', $container[0]);
            // Always reprocess AJAX handlers to handle newly loaded content
            setupCustomAjaxHandlers($container);
            return;
        }
        
        console.log('DEBUG: Initializing container:', $container[0]);
        
        // Full container initialization - don't assume what persists across AJAX updates
        setupBasicEventListeners($container);
        initializeExpandableTextareas($container); // Must come BEFORE autosize
        initializeAutosizeTextareas($container); // Now only applies to non-truncated
        // Note: Form submission handler removed - textarea sync now handled in Ajax submission
        setupCustomAjaxHandlers($container); // NEW: Custom Ajax form handling
        
        // Reinitialize dirty tracking for this container
        if (window.attrV2 && window.attrV2.DirtyTracking) {
            window.attrV2.DirtyTracking.reinitializeContainer($container);
        }
        
        // Handle auto-dismiss messages for this container
        handleAutoDismissMessages($container);
        
        // Mark this container as initialized
        $container.data(ATTR_V2_INTERNAL.INITIALIZED_DATA_KEY, true);
    }
    
    function handleAutoDismissMessages($container) {
        const $statusMsg = $container.find(Hi.ATTR_V2_STATUS_MESSAGE_SELECTOR);
        const $dismissibleElements = $statusMsg.find(Hi.ATTR_V2_AUTO_DISMISS_SELECTOR);
        if ($dismissibleElements.length > 0) {
            setTimeout(() => {
                $dismissibleElements.remove();
                // Hide the entire status message container if it's now empty
                if ($statusMsg.text().trim() === '') {
                    $statusMsg.hide();
                }
            }, 5000);
        }
    }
    
    // Setup custom Ajax handlers for forms and links in this container
    function setupCustomAjaxHandlers($container) {
        // Handle main form submissions
        const $forms = $container.find(Hi.ATTR_V2_FORM_CLASS_SELECTOR);
        console.log('DEBUG: setupCustomAjaxHandlers called for container:', $container[0], 'found forms:', $forms.length);
        
        $forms.each(function(index) {
            const form = this;
            const $form = $(form);
            
            console.log('DEBUG: Setting up form handler for form', index, 'action:', $form.attr('action'), 'class:', $form.attr('class'));
            
            // Remove any existing handlers to avoid duplicates
            $form.off(`submit.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            // Add custom Ajax submission handler
            $form.on(`submit.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                console.log('DEBUG: Form submit handler triggered!', e);
                e.preventDefault();
                
                window.attrV2.ajax.submitFormWithAjax(form);
            });
        });
        
        // Handle history links
        const $historyLinks = $container.find(Hi.ATTR_V2_HISTORY_LINK_SELECTOR);
        $historyLinks.each(function() {
            const $link = $(this);
            
            // Skip if already processed
            if ($link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY)) {
                return;
            }
            
            $link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY, true);
            $link.off(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            $link.on(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                e.preventDefault();
                
                const url = $link.attr('href');
                
                // Server will return JSON response with target selector and HTML
                $.ajax({
                    url: url,
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                }).done((response) => {
                    window.attrV2.ajax.handleFormSuccess(response, $container.find(Hi.ATTR_V2_FORM_CLASS_SELECTOR));
                }).fail((xhr) => {
                    window.attrV2.ajax.handleFormError(xhr, $container.find(Hi.ATTR_V2_FORM_CLASS_SELECTOR));
                });
            });
        });
        
        // Handle value restore links  
        const $restoreLinks = $container.find(Hi.ATTR_V2_RESTORE_LINK_SELECTOR);
        $restoreLinks.each(function() {
            const $link = $(this);
            
            // Skip if already processed
            if ($link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY)) {
                return;
            }
            
            $link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY, true);
            $link.off(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            $link.on(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                e.preventDefault();
                
                const url = $link.attr('href');
                
                // Server will return JSON response with target selector and HTML
                $.ajax({
                    url: url,
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                }).done((response) => {
                    window.attrV2.ajax.handleFormSuccess(response, $container.find(Hi.ATTR_V2_FORM_CLASS_SELECTOR));
                }).fail((xhr) => {
                    window.attrV2.ajax.handleFormError(xhr, $container.find(Hi.ATTR_V2_FORM_CLASS_SELECTOR));
                });
            });
        });
        
        // Handle file upload forms - find the context-specific file input
        const contextSuffix = $container.attr(Hi.CONTEXT_SUFFIX_DATA_ATTR) || '';
        const fileInputId = `${Hi.ATTR_V2_FILE_INPUT_ID}${contextSuffix}`;
        const uploadContainerId = `${Hi.ATTR_V2_UPLOAD_FORM_CONTAINER_ID}${contextSuffix}`;
        const $fileInput = $(`#${uploadContainerId}`).find(`#${fileInputId}`);
        
        
        if ($fileInput.length > 0) {
            // Skip if already processed
            if ($fileInput.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY)) {
                console.log('DEBUG: File input already processed, skipping');
                return;
            }
            
            console.log('DEBUG: Setting up change handler for file input');
            $fileInput.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY, true);
            $fileInput.off(`change.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            $fileInput.on(`change.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                console.log('DEBUG: File input change event fired!', e);
                const fileInput = this;
                const $uploadForm = $fileInput.closest('form');
                
                console.log('DEBUG: File input details:', {
                    files: fileInput.files,
                    fileCount: fileInput.files ? fileInput.files.length : 0,
                    uploadForm: $uploadForm.length
                });
                
                if (fileInput.files && fileInput.files[0] && $uploadForm.length) {
                    console.log('DEBUG: Submitting form via Ajax');
                    // Use our custom Ajax submission with scroll-to-new-content option
                    // File uploads append new content that users want to see
                    window.attrV2.ajax.submitFormWithAjax($uploadForm[0], {
                        scrollToNewContent: true
                    });
                } else {
                    console.log('DEBUG: Not submitting - missing files or form');
                }
            });
        } else {
            console.log('DEBUG: File input not found!');
        }
    }
    
    
    

    function setupBasicEventListeners() {
        // Try multiple approaches to find the form
        let form = $(Hi.ATTR_V2_FORM_SELECTOR)[0];
        
        // Also try multiple selectors
        let formAlt = $(`${Hi.ATTR_V2_FORM_SELECTOR}, ${Hi.ATTR_V2_MODAL_CLASS_SELECTOR}, form[data-async]`)[0];
        
        if (!form && !formAlt) {
            setTimeout(() => {
                form = $(Hi.ATTR_V2_FORM_SELECTOR)[0];
                formAlt = $(`${Hi.ATTR_V2_FORM_SELECTOR}, ${Hi.ATTR_V2_MODAL_CLASS_SELECTOR}, form[data-async]`)[0];
                
                const finalForm = form || formAlt;
                if (finalForm) {
                    attachKeyHandler(finalForm);
                } else {
                    console.error('setupBasicEventListeners: No form found after timeout');
                }
            }, 100);
            return;
        }
        
        const finalForm = form || formAlt;
        attachKeyHandler(finalForm);
    }
    
    function attachKeyHandler(form) {
        // Handle ENTER key behavior ONLY for V2 form inputs and textareas
        form.addEventListener('keydown', function(event) {
            // IMPORTANT: Only handle events from elements within the V2 form
            if (!event.target.closest(Hi.ATTR_V2_FORM_SELECTOR)) {
                return; // Not our form, don't interfere
            }
            
            if (event.key === 'Enter' || event.keyCode === 13) {
                if (event.target.tagName === 'TEXTAREA') {
                    // For textareas, prevent form submission but allow newline
                    event.preventDefault();
                    
                    const textarea = event.target;
                    const start = textarea.selectionStart;
                    const end = textarea.selectionEnd;
                    const value = textarea.value;
                    
                    // Insert newline at cursor position
                    textarea.value = value.substring(0, start) + '\n' + value.substring(end);
                    textarea.selectionStart = textarea.selectionEnd = start + 1;
                    
                    // Trigger autosize update
                    if (window.autosize) {
                        autosize.update(textarea);
                    }
                    event.stopPropagation(); // Don't let this bubble up
                    return false;
                }
                
                // For text inputs, convert to textarea if they want to add newlines
                // BUT only for value fields, not name fields
                if (event.target.tagName === 'INPUT' && event.target.type === 'text') {
                    const fieldName = event.target.name || event.target.id || '';
                    
                    // Only convert value fields to textarea, never name fields
                    if (fieldName.includes('-name') || fieldName.includes('_name')) {
                        return false; // Just prevent form submission, don't convert
                    }
                    
                    // Convert value fields to textarea
                    if (fieldName.includes('-value') || fieldName.includes('_value')) {
                        const $textarea = convertToTextarea(event.target);
                        const currentValue = $textarea.val();
                        $textarea.val(currentValue + '\n');
                        
                        // Position cursor at end
                        const textarea = $textarea[0];
                        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
                        return false;
                    }
                    
                    // For other text inputs, just prevent form submission
                    return false;
                }
                
                // For all other elements, just prevent form submission (already done above)
                return false;
            }
        }, false); // Changed from capture phase to bubble phase to be less intrusive
        
        // Form submission now handled by antinode.js with data-async and data-stay-in-modal
    }

    // Simple add attribute - just show the last (empty) formset form
    window.showAddAttribute = function(containerSelector = null) {
        // Find the last attribute card (should be the empty extra form)
        const scope = containerSelector ? $(containerSelector) : $(document);
        const attributeCards = scope.find(Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR);
        
        if (attributeCards.length > 0) {
            const lastCard = attributeCards[attributeCards.length - 1];
            const $lastCard = $(lastCard);
            
            // Show the card if hidden
            $lastCard.show();
            
            // Focus on the name field
            const nameField = $lastCard.find('input[name$="-name"]')[0];
            if (nameField) {
                nameField.focus();
            }
            
            // Initialize autosize on any textarea in the new card
            const textarea = $lastCard.find('textarea')[0];
            if (textarea && !textarea.hasAttribute('data-autosize-initialized')) {
                autosize($(textarea));
                textarea.setAttribute('data-autosize-initialized', 'true');
            }
            
            // Scroll into view
            lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    };
    
    // Removed dedicated add attribute form functions - using Django formset approach only
    
    
    window.markFileForDeletion = function(attributeId, containerSelector = null) {
        // Find the file card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $fileCard = scope.find(`${Hi.ATTR_V2_FILE_CARD_SELECTOR}[${Hi.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($fileCard.length === 0) return;
        
        // The display "name" for a file is its attribute.value, *not* attribute.name
        const fileValue = $fileCard.find(Hi.ATTR_V2_FILE_TITLE_INPUT_SELECTOR).val().trim();

        // Find and mark the server-rendered DELETE field for deletion
        const $deleteField = $fileCard.find('input[name="delete_file_attribute"]');
        if ($deleteField.length > 0) {
            // Set value to the attribute ID to mark for deletion
            $deleteField.val(attributeId);
        } else {
            console.warn(`DELETE field not found for file attribute ${attributeId}`);
            return;
        }
        
        // Visual feedback - CSS handles all styling
        $fileCard.addClass('marked-for-deletion');
        
        // Hide delete button and show undo button (both server-rendered)
        $fileCard.find(Hi.ATTR_V2_DELETE_BTN_SELECTOR).hide();
        $fileCard.find(Hi.ATTR_V2_UNDO_BTN_SELECTOR).show();
        
        // Show status message (scoped to container)
        const $statusMsg = scope.find(Hi.ATTR_V2_STATUS_MESSAGE_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`"${fileValue}" will be deleted when you save`)
                    .attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2 text-warning`);
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2`);
            }, 5000);
        }
    };
    
    window.undoFileDeletion = function(attributeId, containerSelector = null) {
        // Find the file card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $fileCard = scope.find(`${Hi.ATTR_V2_FILE_CARD_SELECTOR}[${Hi.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($fileCard.length === 0) return;

        // The display "name" for a file is its attribute.value, *not* attribute.name
        const fileValue = $fileCard.find(Hi.ATTR_V2_FILE_TITLE_INPUT_SELECTOR).val().trim();

        // Unmark the DELETE field
        const $deleteField = $fileCard.find('input[name="delete_file_attribute"]');
        if ($deleteField.length > 0) {
            $deleteField.val("");
        }
        
        // Remove visual feedback - CSS handles all styling
        $fileCard.removeClass('marked-for-deletion');
        
        // Show delete button and hide undo button (both server-rendered)
        $fileCard.find(Hi.ATTR_V2_DELETE_BTN_SELECTOR).show();
        $fileCard.find(Hi.ATTR_V2_UNDO_BTN_SELECTOR).hide();
        
        // Show status message (scoped to container)
        const $statusMsg = scope.find(Hi.ATTR_V2_STATUS_MESSAGE_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`Deletion of "${fileValue}" cancelled`)
                    .attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2 text-success`);
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2`);
            }, 3000);
        }
    };
    
    // History functionality now handled by antinode async pattern
    // History button uses data-async to load content, no JavaScript needed
    
    window.markAttributeForDeletion = function(attributeId, containerSelector = null) {
        // Find the attribute card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $attributeCard = scope.find(`[${Hi.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($attributeCard.length === 0) return;
        
        const attributeName = $attributeCard.find(Hi.ATTR_V2_ATTRIBUTE_NAME_SELECTOR).text().trim().replace('•', '').trim();
        
        // Find and mark the server-rendered DELETE field for deletion
        const $deleteField = $attributeCard.find('input[name$="-DELETE"]');
        if ($deleteField.length > 0) {
            // For hidden fields, set value to "on" (what browsers send for checked checkboxes)
            $deleteField.val("on");
        } else {
            console.warn(`DELETE field not found for attribute ${attributeId}`);
            return;
        }
        
        // Visual feedback - CSS handles all styling
        $attributeCard.addClass('marked-for-deletion');
        
        // Hide delete button and show undo button (both server-rendered)
        $attributeCard.find(Hi.ATTR_V2_DELETE_BTN_SELECTOR).hide();
        $attributeCard.find(Hi.ATTR_V2_UNDO_BTN_SELECTOR).show();
        
        // Show status message (scoped to container)
        const $statusMsg = scope.find(Hi.ATTR_V2_STATUS_MESSAGE_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`"${attributeName}" will be deleted when you save`)
                    .attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2 text-warning`);
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2`);
            }, 5000);
        }
    };
    
    window.undoAttributeDeletion = function(attributeId, containerSelector = null) {
        // Find the attribute card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $attributeCard = scope.find(`[${Hi.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($attributeCard.length === 0) return;
        
        const attributeName = $attributeCard.find(Hi.ATTR_V2_ATTRIBUTE_NAME_SELECTOR).text().trim().replace('•', '').trim();
        
        // Unmark the DELETE field
        const $deleteField = $attributeCard.find('input[name$="-DELETE"]');
        if ($deleteField.length > 0) {
            $deleteField.val("");
        }
        
        // Remove visual feedback - CSS handles all styling
        $attributeCard.removeClass('marked-for-deletion');
        
        // Show delete button and hide undo button (both server-rendered)
        $attributeCard.find(Hi.ATTR_V2_DELETE_BTN_SELECTOR).show();
        $attributeCard.find(Hi.ATTR_V2_UNDO_BTN_SELECTOR).hide();
        
        // Show status message (scoped to container)
        const $statusMsg = scope.find(Hi.ATTR_V2_STATUS_MESSAGE_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`Deletion of "${attributeName}" cancelled`)
                    .attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2 text-success`);
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', `${Hi.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2`);
            }, 3000);
        }
    };

    window.attrV2.toggleSecretField = function(button) {
        const $button = $(button);
        const $input = $button.closest(Hi.ATTR_V2_SECRET_INPUT_WRAPPER_SELECTOR).find(Hi.ATTR_V2_SECRET_INPUT_SELECTOR);
        const $showIcon = $button.find(Hi.ATTR_V2_ICON_SHOW_SELECTOR);
        const $hideIcon = $button.find(Hi.ATTR_V2_ICON_HIDE_SELECTOR);
        const isPassword = $input.attr('type') === 'password';
        
        // Check if field is disabled (non-editable attributes should stay disabled)
        const isDisabled = $input.prop('disabled');
        
        if (isPassword) {
            // Currently hidden - show as text and make editable
            $input.attr('type', 'text');
            $button.attr('title', 'Hide value');
            
            // Remove readonly to allow editing, but only if not disabled
            if (!isDisabled) {
                $input.prop('readonly', false);
                $input.removeAttr('readonly');
            }
            
            // Show hide icon, hide show icon
            $showIcon.hide();
            $hideIcon.show();
        } else {
            // Currently showing - hide as password and make readonly
            $input.attr('type', 'password');
            $button.attr('title', 'Show value');
            
            // Set readonly to prevent editing obfuscated text
            if (!isDisabled) {
                $input.prop('readonly', true);
                $input.attr('readonly', 'readonly');
            }
            
            // Show show icon, hide hide icon
            $showIcon.show();
            $hideIcon.hide();
        }
    };
    
    // Update hidden field when boolean checkbox changes
    window.attrV2.updateBooleanHiddenField = function(checkbox) {
        const hiddenFieldId = checkbox.getAttribute(Hi.DATA_HIDDEN_FIELD_ATTR);
        const hiddenField = document.getElementById(hiddenFieldId);
        
        if (hiddenField) {
            // Update hidden field value based on checkbox state
            hiddenField.value = checkbox.checked ? 'True' : 'False';
        }
    };
    
    
    // Initialize autosize for all textareas in the modal
    function initializeAutosizeTextareas() {
        // Initialize autosize for existing textareas, but exclude truncated ones
        const textareas = $(Hi.ATTR_V2_TEXTAREA_SELECTOR).not('.truncated');
        if (textareas.length > 0) {
            autosize(textareas);
            
            // Update when modal is shown (in case of display issues)
            $('.modal').on('shown.bs.modal', function () {
                autosize.update(textareas);
            });
        }
    }
    
    // Lightweight reinitialization for ajax content updates
    function reinitializeTextareas($container = null) {
        // Find textareas that need initialization (scoped to container if provided)
        const textareas = $container ? 
            $container.find(Hi.ATTR_V2_TEXTAREA_SELECTOR) : 
            $(Hi.ATTR_V2_TEXTAREA_SELECTOR);
        
        // Remove any previous autosize instances to avoid duplicates
        textareas.each(function() {
            if (this._autosize) {
                autosize.destroy($(this));
            }
        });
        
        // Initialize overflow state based on server-rendered attributes
        textareas.each(function() {
            const textarea = $(this);
            const wrapper = textarea.closest(Hi.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
            const isOverflowing = wrapper.attr(Hi.DATA_OVERFLOW_ATTR) === 'true';
            
            // Check if this is a display field (new pattern) or legacy textarea
            const hiddenFieldId = textarea.attr(Hi.DATA_HIDDEN_FIELD_ATTR);
            const hiddenField = hiddenFieldId ? $('#' + hiddenFieldId) : null;
            
            if (isOverflowing) {
                if (hiddenField && hiddenField.length > 0) {
                    applyTruncationFromHidden(textarea, hiddenField);
                } else {
                    applyTruncation(textarea);
                }
            }
        });
        
        // THEN: Apply autosize only to editable, non-truncated textareas 
        // (readonly textareas don't need dynamic resizing)
        const editableTextareas = $(Hi.ATTR_V2_TEXTAREA_SELECTOR).not('.truncated').not('[readonly]');
        if (editableTextareas.length > 0) {
            autosize(editableTextareas);
        }
        
        // Trigger autosize update for editable textareas only
        if (editableTextareas.length > 0) {
            autosize.update(editableTextareas);
        }
    }
    
    // Update overflow state based on current content
    function updateOverflowState(textarea) {
        const content = textarea.val() || '';
        const lineCount = (content.match(/\n/g) || []).length + 1;
        const overflows = lineCount > 4;
        
        const wrapper = textarea.closest(Hi.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        wrapper.attr(Hi.DATA_OVERFLOW_ATTR, overflows ? 'true' : 'false');
        wrapper.attr(Hi.DATA_LINE_COUNT_ATTR, lineCount);
        
        return { lineCount, overflows };
    }
    
    // Apply truncation using hidden field as source (new pattern)
    function applyTruncationFromHidden(displayField, hiddenField) {
        const fullValue = hiddenField.val() || '';
        
        // Destroy autosize first to prevent height override
        if (window.autosize && displayField[0]._autosize) {
            autosize.destroy(displayField);
        }
        
        const lines = fullValue.split('\n');
        const truncatedValue = lines.slice(0, 4).join('\n');
        
        // Apply truncated display
        displayField.val(truncatedValue + '...');
        // Clear any explicit height style that might override rows
        displayField.css('height', '');
        displayField.attr('rows', 4);
        displayField.attr('readonly', 'readonly');
        displayField.prop('readonly', true);
        displayField.addClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
        
        // Show expand controls
        const wrapper = displayField.closest(Hi.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        const expandControls = wrapper.find(Hi.ATTR_V2_EXPAND_CONTROLS_SELECTOR);
        expandControls.show();
    }
    
    // Legacy function - kept for compatibility with reinitializeTextareas
    function applyTruncation(textarea) {
        const value = textarea.val() || '';
        
        // Destroy autosize first to prevent height override
        if (window.autosize && textarea[0]._autosize) {
            autosize.destroy(textarea);
        }
        
        const lines = value.split('\n');
        const truncatedValue = lines.slice(0, 4).join('\n');
        
        // Store full value and show truncated
        textarea.data('full-value', value);
        textarea.data('truncated-value', truncatedValue);
        textarea.val(truncatedValue + '...');
        // Clear any explicit height style that might override rows
        textarea.css('height', '');
        textarea.attr('rows', 4);
        textarea.attr('readonly', 'readonly');
        textarea.prop('readonly', true);
        textarea.addClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
        
        // Show expand controls
        const wrapper = textarea.closest(Hi.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        const expandControls = wrapper.find(Hi.ATTR_V2_EXPAND_CONTROLS_SELECTOR);
        expandControls.show();
    }
    
    function initializeExpandableTextareas() {
        // Initialize based on server-rendered overflow state using hidden field pattern
        const displayTextareas = $('.display-field');
        
        displayTextareas.each(function() {
            const displayField = $(this);
            const isOverflowing = displayField.attr(Hi.DATA_OVERFLOW_ATTR) === 'true';
            const hiddenFieldId = displayField.attr(Hi.DATA_HIDDEN_FIELD_ATTR);
            const hiddenField = $('#' + hiddenFieldId);
            
            if (isOverflowing && hiddenField.length > 0) {
                // Apply truncation using hidden field as source
                applyTruncationFromHidden(displayField, hiddenField);
            }
            // For non-overflowing content, display field already has correct content from server
        });
    }
    
    // Global function for expand/collapse button (namespaced) - enhanced for hidden field pattern
    window.attrV2.toggleExpandedView = function(button) {
        const $button = $(button);
        const wrapper = $button.closest(Hi.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        const displayField = wrapper.find('.display-field, ' + Hi.ATTR_V2_TEXTAREA_SELECTOR); // Support both new and legacy
        const showMoreText = $button.find('.show-more-text');
        const showLessText = $button.find('.show-less-text');
        
        // Get hidden field if using new pattern
        const hiddenFieldId = displayField.attr(Hi.DATA_HIDDEN_FIELD_ATTR);
        const hiddenField = hiddenFieldId ? $('#' + hiddenFieldId) : null;
        
        if (displayField.prop('readonly')) {
            // Currently collapsed - expand it (Show More)
            let fullValue;
            if (hiddenField && hiddenField.length > 0) {
                // New pattern: Get from hidden field
                fullValue = hiddenField.val() || '';
            } else {
                // Legacy pattern: Get from stored data
                fullValue = displayField.data('full-value') || '';
            }
            
            const lineCount = (fullValue.match(/\n/g) || []).length + 1;
            
            displayField.val(fullValue);
            displayField.attr('rows', Math.max(lineCount, 5));
            displayField.prop('readonly', false);
            displayField.attr('readonly', false); // Remove readonly attribute
            displayField.removeClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
            
            showMoreText.hide();
            showLessText.show();
            
            // Apply autosize now that display field is editable
            if (window.autosize) {
                autosize(displayField);
                autosize.update(displayField);
            }
            
            // Set up listener to track content changes
            displayField.off('input.overflow').on('input.overflow', function() {
                updateOverflowState($(this));
            });
        } else {
            // Currently expanded - check if we should collapse (Show Less)
            const { lineCount, overflows } = updateOverflowState(displayField);
            
            if (!overflows) {
                // Content now fits in 4 lines - remove truncation UI
                displayField.attr('rows', lineCount);
                displayField.prop('readonly', false);
                displayField.removeClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
                wrapper.find(Hi.ATTR_V2_EXPAND_CONTROLS_SELECTOR).hide();
                
                // Update wrapper state
                wrapper.attr(Hi.DATA_OVERFLOW_ATTR, 'false');
                
                // Sync to hidden field if using new pattern
                if (hiddenField && hiddenField.length > 0) {
                    hiddenField.val(displayField.val());
                }
            } else {
                // Still overflows - apply truncation with hidden field sync
                const currentValue = displayField.val();
                
                // Sync current content to hidden field before truncating display
                if (hiddenField && hiddenField.length > 0) {
                    hiddenField.val(currentValue);
                    
                    // Apply truncation using hidden field
                    applyTruncationFromHidden(displayField, hiddenField);
                } else {
                    // Legacy pattern
                    applyTruncation(displayField);
                }
                
                showMoreText.show();
                showLessText.hide();
            }
            
            // Remove the input listener
            displayField.off('input.overflow');
        }
    }
    
    // Sync textarea values to hidden fields before form submission
    function syncTextareaValuesToHiddenFields($container) {
        // Process all display fields within this container
        $container.find('.display-field').each(function() {
            const displayField = $(this);
            const hiddenFieldId = displayField.attr(Hi.DATA_HIDDEN_FIELD_ATTR);
            const hiddenField = hiddenFieldId ? $container.find('#' + hiddenFieldId) : null;
            
            if (hiddenField && hiddenField.length > 0) {
                // Only sync if display field is NOT showing truncated data
                if (!displayField.prop('readonly') && !displayField.hasClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS)) {
                    // Display field contains user's edits - copy to hidden field
                    const displayValue = displayField.val();
                    hiddenField.val(displayValue);
                }
                // Display field is readonly/truncated - hidden field already has correct full content
            }
        });
    }
    
    // Convert single-line input to textarea when user adds newlines
    function convertToTextarea(inputElement) {
        const $input = $(inputElement);
        const value = $input.val();
        
        // Create textarea element
        const $textarea = $('<textarea>', {
            rows: 1,
            id: $input.attr('id'),
            name: $input.attr('name'),
            class: $input.attr('class') + ' ' + Hi.ATTR_V2_TEXTAREA_CLASS,
            [Hi.DATA_ORIGINAL_VALUE_ATTR]: $input.attr(Hi.DATA_ORIGINAL_VALUE_ATTR)
        });
        
        // Copy attributes
        if ($input.is(':disabled')) {
            $textarea.prop('disabled', true);
        }
        
        // Set value and replace input
        $textarea.val(value);
        $input.replaceWith($textarea);
        
        // Initialize autosize
        autosize($textarea);
        $textarea.focus();
        
        return $textarea;
    }
    
    
})();
