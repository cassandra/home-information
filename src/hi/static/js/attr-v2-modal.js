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
        if ($(Hi.ATTR_V2_FORM_SELECTOR).length) {
            initializeAttrV2();
        }
    });
    
    // Register with antinode.js to run after any async content is rendered
    if (window.AN && typeof window.AN.addAfterAsyncRenderFunction === 'function') {
        window.AN.addAfterAsyncRenderFunction(function() {
            if ($(Hi.ATTR_V2_FORM_SELECTOR).length) {
                reinitializeAttrV2ForAjax();
            }
        });
    } else {
        console.error('AN.addAfterAsyncRenderFunction not available - this is a bug in antinode.js');
    }
    
    // Listen for any modal shown events and check if it contains a V2 form
    $(document).on('shown.bs.modal', '.modal', function(e) {
        if ($(Hi.ATTR_V2_FORM_SELECTOR).length) {
            initializeAttrV2();
            e.stopPropagation(); // Prevent bubbling to other handlers
        }
    });
    
    // Handle tab URL updates for configuration settings using event delegation
    $(document).on('shown.bs.tab', `${Hi.SUBSYSTEM_TABS_SELECTOR} a[data-toggle="tab"]`, function(e) {
        const subsystemId = $(e.target).data('subsystem-id');
        const baseUrl = $(e.target).data('config-settings-url');
        
        if (subsystemId && baseUrl) {
            const newUrl = `${baseUrl}/${subsystemId}`;
            // Update URL without page reload using pushState
            history.pushState(null, '', newUrl);
            // Update form action to match current tab
            $(Hi.ATTR_V2_FORM_SELECTOR).attr('action', newUrl);
        }
    });

    function initializeAttrV2() {
        // Basic initialization - more functionality will be added in later phases
        setupBasicEventListeners();
        initializeExpandableTextareas(); // Must come BEFORE autosize
        initializeAutosizeTextareas(); // Now only applies to non-truncated
        setupFormSubmissionHandler();
        
        // Initialize dirty tracking if available
        if (window.attrV2 && window.attrV2.DirtyTracking) {
            window.attrV2.DirtyTracking.reinitialize();
        }
    }
    
    // Safe reinitialization for AJAX updates - handles both textareas and full setup
    function reinitializeAttrV2ForAjax() {
        // Reinitialize textareas (existing functionality)
        reinitializeTextareas();
        
        // Reinitialize dirty tracking if available  
        if (window.attrV2 && window.attrV2.DirtyTracking) {
            window.attrV2.DirtyTracking.reinitialize();
        }
        
        // Note: Form event handlers should persist through DOM updates
        // since the form element itself is not replaced, only its content
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
    window.showAddAttribute = function() {
        // Find the last attribute card (should be the empty extra form)
        const attributeCards = $(Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR);
        
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
    
    
    window.markFileForDeletion = function(attributeId) {
        const $fileCard = $(`${Hi.ATTR_V2_FILE_CARD_SELECTOR}[data-attribute-id="${attributeId}"]`);
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
        
        // Show status message
        const $statusMsg = $(Hi.ATTR_V2_STATUS_MSG_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`"${fileValue}" will be deleted when you save`)
                    .attr('class', 'attr-v2-status-message ml-2 text-warning');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
            }, 5000);
        }
    };
    
    window.undoFileDeletion = function(attributeId) {
        const $fileCard = $(`${Hi.ATTR_V2_FILE_CARD_SELECTOR}[data-attribute-id="${attributeId}"]`);
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
        
        // Show status message
        const $statusMsg = $(Hi.ATTR_V2_STATUS_MSG_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`Deletion of "${fileValue}" cancelled`)
                    .attr('class', 'attr-v2-status-message ml-2 text-success');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
            }, 3000);
        }
    };
    
    // History functionality now handled by antinode async pattern
    // History button uses data-async to load content, no JavaScript needed
    
    window.markAttributeForDeletion = function(attributeId) {
        const $attributeCard = $(`[data-attribute-id="${attributeId}"]`);
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
        
        // Show status message
        const $statusMsg = $(Hi.ATTR_V2_STATUS_MSG_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`"${attributeName}" will be deleted when you save`)
                    .attr('class', 'attr-v2-status-message ml-2 text-warning');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
            }, 5000);
        }
    };
    
    window.undoAttributeDeletion = function(attributeId) {
        const $attributeCard = $(`[data-attribute-id="${attributeId}"]`);
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
        
        // Show status message
        const $statusMsg = $(Hi.ATTR_V2_STATUS_MSG_SELECTOR);
        if ($statusMsg.length > 0) {
            $statusMsg.text(`Deletion of "${attributeName}" cancelled`)
                    .attr('class', 'attr-v2-status-message ml-2 text-success');
            
            setTimeout(() => {
                $statusMsg.text('').attr('class', 'attr-v2-status-message ml-2');
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
        const hiddenFieldId = checkbox.getAttribute('data-hidden-field');
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
    function reinitializeTextareas() {
        // Find all textareas that need initialization
        const textareas = $(Hi.ATTR_V2_TEXTAREA_SELECTOR);
        
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
            const isOverflowing = wrapper.attr('data-overflow') === 'true';
            
            // Check if this is a display field (new pattern) or legacy textarea
            const hiddenFieldId = textarea.attr('data-hidden-field');
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
        wrapper.attr('data-overflow', overflows ? 'true' : 'false');
        wrapper.attr('data-line-count', lineCount);
        
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
        displayField.addClass('truncated');
        
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
        textarea.addClass('truncated');
        
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
            const isOverflowing = displayField.attr('data-overflow') === 'true';
            const hiddenFieldId = displayField.attr('data-hidden-field');
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
        const hiddenFieldId = displayField.attr('data-hidden-field');
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
            displayField.removeClass('truncated');
            
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
                displayField.removeClass('truncated');
                wrapper.find('.attr-v2-expand-controls').hide();
                
                // Update wrapper state
                wrapper.attr('data-overflow', 'false');
                
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
    
    // Pre-save handler with truncation protection for hidden field pattern
    function setupFormSubmissionHandler() {
        const form = $(Hi.ATTR_V2_FORM_SELECTOR)[0];
        if (!form) return;
        
        form.addEventListener('submit', function(e) {
            // Process all display fields using the new hidden field pattern
            $('.display-field').each(function() {
                const displayField = $(this);
                const hiddenFieldId = displayField.attr('data-hidden-field');
                const hiddenField = hiddenFieldId ? $('#' + hiddenFieldId) : null;
                
                if (hiddenField && hiddenField.length > 0) {
                    // Only sync if display field is NOT showing truncated data
                    if (!displayField.prop('readonly') && !displayField.hasClass('truncated')) {
                        // Display field contains user's edits - copy to hidden field
                        const displayValue = displayField.val();
                        hiddenField.val(displayValue);
                    }
                    // Display field is readonly/truncated - hidden field already has correct full content
                }
            });
            
            // Legacy support: restore full values to any remaining old-pattern truncated textareas
            $(Hi.ATTR_V2_TEXTAREA_SELECTOR + '.truncated').not('.display-field').each(function() {
                const textarea = $(this);
                const fullValue = textarea.data('full-value');
                if (fullValue !== undefined) {
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
            class: $input.attr('class') + ' ' + Hi.ATTR_V2_TEXTAREA_CLASS,
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
    
    
})();
