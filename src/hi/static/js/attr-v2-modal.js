/*
 * Home Information - Attribute V2 Modal JavaScript
 * Enhanced entity attribute editing modal functionality
 * Phase 1a: Basic structure and framework
 */

(function() {
    'use strict';
    
    // Create a namespace for V2 modal functions to avoid global pollution
    window.attrV2 = window.attrV2 || {};
    
    // Initialize the V2 modal when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOMContentLoaded event fired');
        if (document.getElementById('attr-v2-form')) {
            console.log('Found attr-v2-form on initial page load');
            initializeAttrV2();
        } else {
            console.log('No attr-v2-form found on initial page load');
        }
    });
    
    // Register with antinode.js to run after any async content is rendered
    if (window.AN && typeof window.AN.addAfterAsyncRenderFunction === 'function') {
        window.AN.addAfterAsyncRenderFunction(function() {
            console.log('antinode afterAsyncRender hook called');
            if (document.getElementById('attr-v2-form')) {
                console.log('V2 form found after async render, reinitializing textareas');
                reinitializeTextareas();
            }
        });
        console.log('Registered V2 textarea reinitialization with AN.addAfterAsyncRenderFunction');
    } else {
        console.error('AN.addAfterAsyncRenderFunction not available - this is a bug in antinode.js');
    }
    
    // Listen for any modal shown events and check if it contains a V2 form
    $(document).on('shown.bs.modal', '.modal', function(e) {
        console.log('Modal shown event detected');
        if (document.getElementById('attr-v2-form')) {
            console.log('Found attr-v2-form after modal shown, initializing');
            initializeAttrV2();
            e.stopPropagation(); // Prevent bubbling to other handlers
        }
    });

    function initializeAttrV2() {
        console.log('=== V2 Modal initialized ===');
        console.log('Current URL:', window.location.href);
        console.log('Document ready state:', document.readyState);
        
        // Basic initialization - more functionality will be added in later phases
        setupBasicEventListeners();
        setupDirtyTracking();
        initializeExpandableTextareas(); // Must come BEFORE autosize
        initializeAutosizeTextareas(); // Now only applies to non-truncated
        setupFormSubmissionHandler();
        
        console.log('=== V2 Modal initialization complete ===');
    }
    

    function setupBasicEventListeners() {
        // Debug: Check what forms exist
        const allForms = document.querySelectorAll('form');
        console.log('All forms on page:', allForms);
        allForms.forEach((form, index) => {
            console.log(`Form ${index}:`, 'id=' + form.id, 'class=' + form.className);
        });
        
        // Try multiple approaches to find the form
        let form = document.getElementById('attr-v2-form');
        console.log('getElementById result:', form);
        
        // Also try querySelector
        let formAlt = document.querySelector('#attr-v2-form, .attr-v2-modal, form[data-async]');
        console.log('querySelector result:', formAlt);
        
        if (!form && !formAlt) {
            setTimeout(() => {
                form = document.getElementById('attr-v2-form');
                formAlt = document.querySelector('#attr-v2-form, .attr-v2-modal, form[data-async]');
                console.log('After timeout - getElementById:', form, 'querySelector:', formAlt);
                
                const finalForm = form || formAlt;
                if (finalForm) {
                    console.log('setupBasicEventListeners: Form found after timeout');
                    attachKeyHandler(finalForm);
                } else {
                    console.error('setupBasicEventListeners: No form found after timeout');
                }
            }, 100);
            return;
        }
        
        const finalForm = form || formAlt;
        console.log('setupBasicEventListeners: Form found immediately:', finalForm);
        attachKeyHandler(finalForm);
    }
    
    function attachKeyHandler(form) {
        console.log('attachKeyHandler: Adding ENTER key handler to form');
        
        // Handle ENTER key behavior ONLY for V2 form inputs and textareas
        form.addEventListener('keydown', function(event) {
            // IMPORTANT: Only handle events from elements within the V2 form
            if (!event.target.closest('#attr-v2-form')) {
                return; // Not our form, don't interfere
            }
            
            console.log('V2 Form keydown event:', event.key, 'Target:', event.target.tagName, event.target.type);
            if (event.key === 'Enter' || event.keyCode === 13) {
                console.log('ENTER key detected in V2 form');
                
                if (event.target.tagName === 'TEXTAREA') {
                    console.log('Handling ENTER in textarea - allowing newline');
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
                        console.log('ENTER in name field - preventing form submission but not converting to textarea');
                        return false; // Just prevent form submission, don't convert
                    }
                    
                    // Convert value fields to textarea
                    if (fieldName.includes('-value') || fieldName.includes('_value')) {
                        console.log('Converting value input to textarea');
                        const $textarea = convertToTextarea(event.target);
                        const currentValue = $textarea.val();
                        $textarea.val(currentValue + '\n');
                        
                        // Position cursor at end
                        const textarea = $textarea[0];
                        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
                        return false;
                    }
                    
                    // For other text inputs, just prevent form submission
                    console.log('ENTER in other text input - preventing form submission');
                    return false;
                }
                
                console.log('Preventing form submission for other elements');
                // For all other elements, just prevent form submission (already done above)
                return false;
            }
        }, false); // Changed from capture phase to bubble phase to be less intrusive
        
        // Form submission now handled by antinode.js with data-async and data-stay-in-modal
    }

    // Simple add property - just show the last (empty) formset form
    window.showAddProperty = function() {
        // Find the last property card (should be the empty extra form)
        const propertyCards = document.querySelectorAll('.attr-v2-property-card');
        console.log('showAddProperty: Found', propertyCards.length, 'property cards');
        
        if (propertyCards.length > 0) {
            const lastCard = propertyCards[propertyCards.length - 1];
            console.log('showAddProperty: Last card:', lastCard);
            console.log('showAddProperty: Last card display:', lastCard.style.display);
            console.log('showAddProperty: Last card data-attribute-id:', lastCard.getAttribute('data-attribute-id'));
            
            // Show the card if hidden
            lastCard.style.display = 'block';
            
            // Focus on the name field
            const nameField = lastCard.querySelector('input[name$="-name"]');
            if (nameField) {
                console.log('showAddProperty: Found name field:', nameField.name);
                nameField.focus();
            } else {
                console.log('showAddProperty: No name field found');
            }
            
            // Initialize autosize on any textarea in the new card
            const textarea = lastCard.querySelector('textarea');
            if (textarea && !textarea.hasAttribute('data-autosize-initialized')) {
                autosize($(textarea));
                textarea.setAttribute('data-autosize-initialized', 'true');
            }
            
            // Scroll into view
            lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            console.log('showAddProperty: No property cards found');
        }
    };
    
    // Removed dedicated add property form functions - using Django formset approach only
    
    
    window.handleFileUpload = function(input) {
        console.log('File upload - to be implemented');
    };
    
    window.showFileHistory = function(attributeId) {
        showOverlayModal('File History', 'Loading file history...');
        
        // TODO: Fetch actual history data in future implementation
        setTimeout(() => {
            const historyContent = `
                <div class="attr-v2-history-list">
                    <div class="attr-v2-history-item">
                        <div class="attr-v2-history-timestamp">2 hours ago</div>
                        <div class="attr-v2-history-action">File uploaded</div>
                        <div class="attr-v2-history-details">Original filename: document.pdf</div>
                    </div>
                    <div class="attr-v2-history-item">
                        <div class="attr-v2-history-timestamp">1 day ago</div>
                        <div class="attr-v2-history-action">Property name changed</div>
                        <div class="attr-v2-history-details">From "Doc" to "Important Document"</div>
                    </div>
                </div>
            `;
            updateOverlayModal('File History', historyContent);
        }, 500);
    };
    
    window.markFileForDeletion = function(attributeId) {
        const $fileCard = $(`.attr-v2-file-card[data-attribute-id="${attributeId}"]`);
        if ($fileCard.length === 0) return;
        
        const fileName = $fileCard.find('.attr-v2-file-name').text().trim();
        
        // Find and mark the server-rendered DELETE field for deletion
        const $deleteField = $fileCard.find('input[name="delete_file_attribute"]');
        if ($deleteField.length > 0) {
            // Set value to the attribute ID to mark for deletion
            $deleteField.val(attributeId);
            console.log(`Marked file attribute ${attributeId} for deletion`);
        } else {
            console.warn(`DELETE field not found for file attribute ${attributeId}`);
            return;
        }
        
        // Visual feedback
        $fileCard.addClass('marked-for-deletion').css('opacity', '0.5');
        
        // Hide delete button and show undo button (both server-rendered)
        $fileCard.find('.attr-v2-delete-btn').hide();
        $fileCard.find('.attr-v2-undo-btn').show();
        
        // Show status message
        const $statusMsg = $('#attr-v2-status-msg');
        if ($statusMsg.length > 0) {
            $statusMsg.text(`"${fileName}" will be deleted when you save`)
                    .attr('class', 'attr-v2-status-message ml-2 text-warning');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
            }, 5000);
        }
    };
    
    window.undoFileDeletion = function(attributeId) {
        const $fileCard = $(`.attr-v2-file-card[data-attribute-id="${attributeId}"]`);
        if ($fileCard.length === 0) return;
        
        const fileName = $fileCard.find('.attr-v2-file-name').text().trim();
        
        // Unmark the DELETE field
        const $deleteField = $fileCard.find('input[name="delete_file_attribute"]');
        if ($deleteField.length > 0) {
            $deleteField.val("");
            console.log(`Unmarked file attribute ${attributeId} for deletion`);
        }
        
        // Remove visual feedback
        $fileCard.removeClass('marked-for-deletion').css('opacity', '1');
        
        // Show delete button and hide undo button (both server-rendered)
        $fileCard.find('.attr-v2-delete-btn').show();
        $fileCard.find('.attr-v2-undo-btn').hide();
        
        // Show status message
        const $statusMsg = $('#attr-v2-status-msg');
        if ($statusMsg.length > 0) {
            $statusMsg.text(`Deletion of "${fileName}" cancelled`)
                    .attr('class', 'attr-v2-status-message ml-2 text-success');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
            }, 3000);
        }
    };
    
    window.showPropertyHistory = function(attributeId) {
        showOverlayModal('Property History', 'Loading property history...');
        
        // TODO: Fetch actual history data in future implementation
        setTimeout(() => {
            const historyContent = `
                <div class="attr-v2-history-list">
                    <div class="attr-v2-history-item">
                        <div class="attr-v2-history-timestamp">5 minutes ago</div>
                        <div class="attr-v2-history-action">Value changed</div>
                        <div class="attr-v2-history-details">Updated property value</div>
                    </div>
                    <div class="attr-v2-history-item">
                        <div class="attr-v2-history-timestamp">2 hours ago</div>
                        <div class="attr-v2-history-action">Property created</div>
                        <div class="attr-v2-history-details">Initial property setup</div>
                    </div>
                </div>
            `;
            updateOverlayModal('Property History', historyContent);
        }, 500);
    };
    
    window.markPropertyForDeletion = function(attributeId) {
        const $propertyCard = $(`[data-attribute-id="${attributeId}"]`);
        if ($propertyCard.length === 0) return;
        
        const propertyName = $propertyCard.find('.attr-v2-property-name').text().trim().replace('•', '').trim();
        
        // Find and mark the server-rendered DELETE field for deletion
        const $deleteField = $propertyCard.find('input[name$="-DELETE"]');
        if ($deleteField.length > 0) {
            // For hidden fields, set value to "on" (what browsers send for checked checkboxes)
            $deleteField.val("on");
            console.log(`Marked ${$deleteField.attr('name')} for deletion`);
        } else {
            console.warn(`DELETE field not found for attribute ${attributeId}`);
            return;
        }
        
        // Visual feedback
        $propertyCard.addClass('marked-for-deletion').css('opacity', '0.5');
        
        // Hide delete button and show undo button (both server-rendered)
        $propertyCard.find('.attr-v2-delete-btn').hide();
        $propertyCard.find('.attr-v2-undo-btn').show();
        
        // Show status message
        const $statusMsg = $('#attr-v2-status-msg');
        if ($statusMsg.length > 0) {
            $statusMsg.text(`"${propertyName}" will be deleted when you save`)
                    .attr('class', 'attr-v2-status-message ml-2 text-warning');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
            }, 5000);
        }
    };
    
    window.undoPropertyDeletion = function(attributeId) {
        const $propertyCard = $(`[data-attribute-id="${attributeId}"]`);
        if ($propertyCard.length === 0) return;
        
        const propertyName = $propertyCard.find('.attr-v2-property-name').text().trim().replace('•', '').trim();
        
        // Unmark the DELETE field
        const $deleteField = $propertyCard.find('input[name$="-DELETE"]');
        if ($deleteField.length > 0) {
            $deleteField.val("");
            console.log(`Unmarked ${$deleteField.attr('name')} for deletion`);
        }
        
        // Remove visual feedback
        $propertyCard.removeClass('marked-for-deletion').css('opacity', '1');
        
        // Show delete button and hide undo button (both server-rendered)
        $propertyCard.find('.attr-v2-delete-btn').show();
        $propertyCard.find('.attr-v2-undo-btn').hide();
        
        // Show status message
        const $statusMsg = $('#attr-v2-status-msg');
        if ($statusMsg.length > 0) {
            $statusMsg.text(`Deletion of "${propertyName}" cancelled`)
                    .attr('class', 'attr-v2-status-message ml-2 text-success');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
            }, 3000);
        }
    };

    // Form submission now handled by antinode.js - no custom handling needed
    
    
    function showFileUploadProgress(fileName) {
        const statusMsg = document.getElementById('attr-v2-status-msg');
        if (statusMsg) {
            statusMsg.textContent = `Uploading ${fileName}...`;
            statusMsg.className = 'attr-v2-status-message ml-2 text-info';
        }
    }
    
    function hideFileUploadProgress() {
        const statusMsg = document.getElementById('attr-v2-status-msg');
        if (statusMsg) {
            statusMsg.textContent = '';
            statusMsg.className = 'attr-v2-status-message ml-2';
        }
    }
    
    function showFileUploadError(errorMessage) {
        const statusMsg = document.getElementById('attr-v2-status-msg');
        if (statusMsg) {
            statusMsg.textContent = errorMessage;
            statusMsg.className = 'attr-v2-status-message ml-2 text-danger';
            
            setTimeout(() => {
                statusMsg.textContent = '';
                statusMsg.className = 'attr-v2-status-message ml-2';
            }, 5000);
        }
    }
    
    
    
    window.attrV2.toggleSecretField = function(button) {
        const $button = $(button);
        const $input = $button.closest('.attr-v2-secret-input-wrapper').find('.attr-v2-secret-input');
        const $showIcon = $button.find('.attr-v2-icon-show');
        const $hideIcon = $button.find('.attr-v2-icon-hide');
        const isPassword = $input.attr('type') === 'password';
        
        if (isPassword) {
            // Currently hidden - show as text
            $input.attr('type', 'text');
            $button.attr('title', 'Hide value');
            // Show hide icon, hide show icon
            $showIcon.hide();
            $hideIcon.show();
        } else {
            // Currently showing - hide as password
            $input.attr('type', 'password');
            $button.attr('title', 'Show value');
            // Show show icon, hide hide icon
            $showIcon.show();
            $hideIcon.hide();
        }
    };
    
    
    
    
    
    
    // Simple dirty tracking setup - leverages existing Hi.AttributeChanges system
    function setupDirtyTracking() {
        // The existing attribute-changes.js system handles dirty tracking automatically
        // for any elements within .hi-attribute-list containers using document delegation
        // No additional setup needed since V2 property list now uses hi-attribute-list class
        console.log('Dirty tracking delegated to existing AttributeChanges system');
    }
    
    // Initialize autosize for all textareas in the modal
    function initializeAutosizeTextareas() {
        // Initialize autosize for existing textareas, but exclude truncated ones
        const textareas = $('.attr-v2-textarea').not('.truncated');
        if (textareas.length > 0) {
            autosize(textareas);
            
            // Update when modal is shown (in case of display issues)
            $('.modal').on('shown.bs.modal', function () {
                autosize.update(textareas);
            });
        }
    }
    
    // Lightweight reinitialization for ajax content updates
    function reinitializeTextareas() {
        console.log('Reinitializing textareas after ajax update');
        
        // Find all textareas that need initialization
        const textareas = $('.attr-v2-textarea');
        console.log('Found ' + textareas.length + ' textareas to reinitialize');
        
        // Remove any previous autosize instances to avoid duplicates
        textareas.each(function() {
            if (this._autosize) {
                autosize.destroy($(this));
            }
        });
        
        // Initialize overflow state based on server-rendered attributes
        textareas.each(function() {
            const textarea = $(this);
            const wrapper = textarea.closest('.attr-v2-text-value-wrapper');
            const isOverflowing = wrapper.attr('data-overflow') === 'true';
            
            if (isOverflowing) {
                console.log('Reinitialization: Applying truncation to overflowing textarea');
                // Apply truncation for overflowing content
                applyTruncation(textarea);
            }
        });
        
        // THEN: Apply autosize only to editable, non-truncated textareas 
        // (readonly textareas don't need dynamic resizing)
        const editableTextareas = $('.attr-v2-textarea').not('.truncated').not('[readonly]');
        console.log('Reinitialization: Applying autosize to', editableTextareas.length, 'editable, non-truncated textareas');
        if (editableTextareas.length > 0) {
            autosize(editableTextareas);
        }
        
        // Trigger autosize update for editable textareas only
        if (editableTextareas.length > 0) {
            autosize.update(editableTextareas);
        }
        
        console.log('Textarea reinitialization complete');
    }
    
    // Update overflow state based on current content
    function updateOverflowState(textarea) {
        const content = textarea.val() || '';
        const lineCount = (content.match(/\n/g) || []).length + 1;
        const overflows = lineCount > 4;
        
        const wrapper = textarea.closest('.attr-v2-text-value-wrapper');
        wrapper.attr('data-overflow', overflows ? 'true' : 'false');
        wrapper.attr('data-line-count', lineCount);
        
        return { lineCount, overflows };
    }
    
    // Apply truncation to textarea
    function applyTruncation(textarea) {
        console.log('applyTruncation: Starting for textarea');
        const value = textarea.val() || '';
        console.log('Original value:', value.substring(0, 100) + (value.length > 100 ? '...' : ''));
        
        // Destroy autosize first to prevent height override
        if (window.autosize && textarea[0]._autosize) {
            console.log('Destroying autosize before truncation');
            autosize.destroy(textarea);
        }
        
        const lines = value.split('\n');
        const truncatedValue = lines.slice(0, 4).join('\n');
        console.log('Truncated to:', truncatedValue.substring(0, 100) + (truncatedValue.length > 100 ? '...' : ''));
        
        // Store full value and show truncated
        textarea.data('full-value', value);
        textarea.data('truncated-value', truncatedValue);
        textarea.val(truncatedValue + '...');
        // Clear any explicit height style that might override rows
        textarea.css('height', '');
        textarea.attr('rows', 4);
        textarea.attr('readonly', 'readonly');
        textarea.prop('readonly', true);
        textarea.addClass('truncated');
        
        console.log('Set readonly and rows=4');
        
        // Show expand controls
        const wrapper = textarea.closest('.attr-v2-text-value-wrapper');
        const expandControls = wrapper.find('.attr-v2-expand-controls');
        console.log('Found expand controls:', expandControls.length);
        expandControls.show();
        
        console.log('applyTruncation: Complete');
    }
    
    function initializeExpandableTextareas() {
        console.log('initializeExpandableTextareas: Starting');
        // Initialize based on server-rendered overflow state
        const textareas = $('.attr-v2-textarea');
        console.log('Found ' + textareas.length + ' textareas to initialize');
        
        textareas.each(function() {
            const textarea = $(this);
            const wrapper = textarea.closest('.attr-v2-text-value-wrapper');
            const isOverflowing = wrapper.attr('data-overflow') === 'true';
            const lineCount = wrapper.attr('data-line-count');
            
            console.log('Textarea - overflow:', isOverflowing, 'lines:', lineCount, 'value length:', textarea.val().length);
            
            if (isOverflowing) {
                console.log('Applying truncation to textarea with', lineCount, 'lines');
                // Apply truncation for overflowing content
                applyTruncation(textarea);
            }
            // For non-overflowing content, server has already set correct rows
        });
        
        console.log('initializeExpandableTextareas: Complete');
    }
    
    // Global function for expand/collapse button (namespaced)
    window.attrV2.toggleExpandedView = function(button) {
        const $button = $(button);
        const wrapper = $button.closest('.attr-v2-text-value-wrapper');
        const textarea = wrapper.find('.attr-v2-textarea');
        const showMoreText = $button.find('.show-more-text');
        const showLessText = $button.find('.show-less-text');
        
        if (textarea.prop('readonly')) {
            // Currently collapsed - expand it
            const fullValue = textarea.data('full-value');
            const lineCount = (fullValue.match(/\n/g) || []).length + 1;
            
            textarea.val(fullValue);
            textarea.attr('rows', Math.max(lineCount, 5));
            textarea.prop('readonly', false);
            textarea.attr('readonly', false); // Remove readonly attribute
            textarea.removeClass('truncated');
            
            showMoreText.hide();
            showLessText.show();
            
            // Apply autosize now that textarea is editable
            if (window.autosize) {
                autosize(textarea);
                autosize.update(textarea);
            }
            
            // Set up listener to track content changes
            textarea.off('input.overflow').on('input.overflow', function() {
                updateOverflowState($(this));
            });
        } else {
            // Currently expanded - check if we should collapse
            const { lineCount, overflows } = updateOverflowState(textarea);
            
            if (!overflows) {
                // Content now fits in 4 lines - remove truncation UI
                textarea.attr('rows', lineCount);
                textarea.prop('readonly', false);
                textarea.removeClass('truncated');
                wrapper.find('.attr-v2-expand-controls').hide();
                
                // Update wrapper state
                wrapper.attr('data-overflow', 'false');
            } else {
                // Still overflows - apply truncation (autosize destruction handled inside)
                applyTruncation(textarea);
                
                showMoreText.show();
                showLessText.hide();
            }
            
            // Remove the input listener
            textarea.off('input.overflow');
        }
    }
    
    // Ensure form submission uses full values, not truncated or placeholder ones
    function setupFormSubmissionHandler() {
        const form = document.getElementById('attr-v2-form');
        if (!form) return;
        
        form.addEventListener('submit', function(e) {
            console.log('Form submission event detected - restoring real values');
            
            // Before submission, restore full values to any truncated textareas
            $('.attr-v2-textarea.truncated').each(function() {
                const textarea = $(this);
                const fullValue = textarea.data('full-value');
                if (fullValue !== undefined) {
                    console.log('Restoring truncated textarea value');
                    textarea.val(fullValue);
                    textarea.prop('readonly', false);
                }
            });
            
        }, true); // Use capture phase to ensure this runs early
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
            class: $input.attr('class') + ' attr-v2-textarea',
            'data-original-value': $input.attr('data-original-value')
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
    
    // Overlay modal functions for history views
    function showOverlayModal(title, content) {
        const overlay = document.getElementById('attr-v2-overlay-modal');
        const titleElement = document.getElementById('attr-v2-overlay-title');
        const bodyElement = document.getElementById('attr-v2-overlay-body');
        
        if (overlay && titleElement && bodyElement) {
            titleElement.textContent = title;
            bodyElement.innerHTML = content;
            overlay.style.display = 'flex';
        }
    }
    
    function updateOverlayModal(title, content) {
        const titleElement = document.getElementById('attr-v2-overlay-title');
        const bodyElement = document.getElementById('attr-v2-overlay-body');
        
        if (titleElement && bodyElement) {
            titleElement.textContent = title;
            bodyElement.innerHTML = content;
        }
    }
    
    window.closeOverlayModal = function() {
        const overlay = document.getElementById('attr-v2-overlay-modal');
        if (overlay) {
            overlay.style.display = 'none';
        }
    };

})();