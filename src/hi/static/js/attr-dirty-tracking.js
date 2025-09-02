/*
 * Home Information - Attribute Dirty State Tracking
 * Container-aware dirty state tracking for attribute editing
 * Supports multiple simultaneous editing contexts and visual dirty indicators
 */

(function() {
    'use strict';
    
    // Internal constants - dirty tracking specific
    const DIRTY_TRACKING_INTERNAL = {
        // Configuration
        DEBOUNCE_DELAY: 300,
        
        // Messages
        SINGLE_FIELD_MESSAGE: '1 field modified',
        MULTIPLE_FIELDS_MESSAGE_TEMPLATE: '{count} fields modified',
        DIRTY_INDICATOR_CHAR: '●',
        DIRTY_INDICATOR_TITLE: 'This field has been modified',
        
        // Form selectors (will be replaced with Hi.* constants)
        FORM_SELECTOR: '.attr-v2-form',
        MESSAGE_CONTAINER_SELECTOR: '.attr-v2-dirty-message'
    };
    
    // Create namespace  
    window.Hi = window.Hi || {};
    window.Hi.attr = window.Hi.attr || {};
    
    /**
     * DirtyTracker Class - Container-specific instance
     * Each editing context gets its own isolated tracker
     */
    function DirtyTracker(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        
        // Instance-specific configuration
        this.config = {
            formSelector: Hi.ATTR_V2_FORM_CLASS_SELECTOR,
            messageContainerSelector: Hi.ATTR_V2_DIRTY_MESSAGE_SELECTOR,
            debounceDelay: DIRTY_TRACKING_INTERNAL.DEBOUNCE_DELAY,
            dirtyFieldClass: Hi.ATTR_V2_FIELD_DIRTY_CLASS || 'attr-v2-field-dirty',
            dirtyIndicatorClass: Hi.ATTR_V2_DIRTY_INDICATOR_CLASS || 'attr-v2-dirty-indicator'
        };
        
        // Instance-specific state
        this.state = {
            originalValues: new Map(),
            dirtyFields: new Set(),
            debounceTimers: new Map(),
            isInitialized: false
        };
    }
    
    DirtyTracker.prototype = {
        // Initialize the dirty tracking system for this container
        init: function() {
            if (this.state.isInitialized || !this.container) {
                return;
            }
            
            const form = this.container.querySelector(this.config.formSelector);
            if (!form) {
                return;
            }
            
            this.captureOriginalValues();
            this.bindEvents();
            this.state.isInitialized = true;
        },
        
        // Capture original values for all form fields in this container
        captureOriginalValues: function() {
            const form = this.container.querySelector(this.config.formSelector);
            if (!form) return;
            
            // Entity/Location name field
            const nameField = form.querySelector('input[name$="name"]:not([name*="-"])');
            if (nameField) {
                this.captureFieldValue(nameField);
            }
            
            // Attribute form fields
            const attributeFields = form.querySelectorAll(`${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} input, ${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} textarea, ${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} select`);
            attributeFields.forEach(field => {
                // Skip hidden management form fields
                if (field.type === 'hidden' && field.name.includes('_')) return;
                this.captureFieldValue(field);
            });
            
            // File title input fields
            const fileTitleFields = form.querySelectorAll(Hi.ATTR_V2_FILE_TITLE_INPUT_SELECTOR);
            fileTitleFields.forEach(field => {
                this.captureFieldValue(field);
            });
        },
        
        // Capture individual field value
        captureFieldValue: function(field) {
            if (!field.name || !field.id) return;
            
            let originalValue = this.getFieldValue(field);
            this.state.originalValues.set(field.id, originalValue);
            field.setAttribute('data-original-value', originalValue);
        },
        
        // Get normalized field value
        getFieldValue: function(field) {
            if (field.type === 'checkbox') {
                return field.checked ? 'true' : 'false';
            } else if (field.tagName.toLowerCase() === 'select') {
                return field.value || '';
            } else {
                return (field.value || '').trim();
            }
        },
        
        // Check if field has changed
        hasFieldChanged: function(field) {
            const originalValue = this.state.originalValues.get(field.id);
            const currentValue = this.getFieldValue(field);
            
            // Special handling for new attribute forms - consider them dirty if they have content
            const isNewAttributeField = field.closest(Hi.ATTR_V2_NEW_ATTRIBUTE_SELECTOR);
            if (isNewAttributeField && field.name.includes('-name') && currentValue.length > 0) {
                return true;
            }
            
            return originalValue !== currentValue;
        },
        
        // Bind event listeners scoped to this container
        bindEvents: function() {
            const form = this.container.querySelector(this.config.formSelector);
            if (!form) return;
            
            // Text input changes with debouncing
            this.bindDebouncedEvents(form, 'input[type="text"], input[type="password"], input[type="number"], textarea', 'input');
            
            // Immediate changes for selects and checkboxes
            this.bindImmediateEvents(form, 'select, input[type="checkbox"]', 'change');
            
            // Form submission handling
            form.addEventListener('submit', this.handleFormSubmission.bind(this));
            
            // Handle file title input activation (persistent styling on first interaction)
            form.addEventListener('focus', (e) => {
                if (e.target.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                    e.target.classList.add('activated');
                }
            }, true); // Use capture phase to ensure we catch the event
        },
        
        // Bind debounced events for text inputs
        bindDebouncedEvents: function(form, selector, eventType) {
            form.addEventListener(eventType, (e) => {
                if (!e.target.matches(selector)) return;
                
                const field = e.target;
                const fieldId = field.id;
                
                if (!fieldId) return;
                
                // Clear existing timer
                if (this.state.debounceTimers.has(fieldId)) {
                    clearTimeout(this.state.debounceTimers.get(fieldId));
                }
                
                // Set new timer
                const timer = setTimeout(() => {
                    this.handleFieldChange(field);
                    this.state.debounceTimers.delete(fieldId);
                }, this.config.debounceDelay);
                
                this.state.debounceTimers.set(fieldId, timer);
            });
        },
        
        // Bind immediate events for selects and checkboxes
        bindImmediateEvents: function(form, selector, eventType) {
            form.addEventListener(eventType, (e) => {
                if (!e.target.matches(selector)) return;
                this.handleFieldChange(e.target);
            });
        },
        
        // Handle individual field change
        handleFieldChange: function(field) {
            const hasChanged = this.hasFieldChanged(field);
            
            if (hasChanged) {
                this.markFieldDirty(field);
                this.state.dirtyFields.add(field.id);
            } else {
                this.clearFieldDirty(field);
                this.state.dirtyFields.delete(field.id);
            }
            
            this.updateMessageArea();
        },
        
        // Mark field as dirty with visual indicators
        markFieldDirty: function(field) {
            field.classList.add(this.config.dirtyFieldClass);
            
            // For file title inputs, add activated class for persistent styling
            if (field.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                field.classList.add('activated');
            }
            
            // Add indicator to field container
            const container = this.getFieldContainer(field);
            if (container && !container.querySelector('.' + this.config.dirtyIndicatorClass)) {
                const indicator = this.createDirtyIndicator();
                this.insertDirtyIndicator(container, indicator);
                
                // Add fallback CSS classes for browsers without :has() support
                this.addFallbackClasses(container, field);
            }
        },
        
        // Clear dirty state from field
        clearFieldDirty: function(field) {
            field.classList.remove(this.config.dirtyFieldClass);
            
            // Remove indicator
            const container = this.getFieldContainer(field);
            if (container) {
                const indicator = container.querySelector('.' + this.config.dirtyIndicatorClass);
                if (indicator) {
                    indicator.remove();
                }
                
                // Remove fallback CSS classes
                this.removeFallbackClasses(container, field);
            }
        },
        
        // Get appropriate container for field indicator
        getFieldContainer: function(field) {
            // For file title inputs, use the file info container
            if (field.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                const fileInfo = field.closest(Hi.ATTR_V2_FILE_INFO_SELECTOR);
                if (fileInfo) {
                    return field; // Use the input itself as container for positioning
                }
            }
            
            // For attribute cards, use the attribute header
            const attributeCard = field.closest(Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR);
            if (attributeCard) {
                return attributeCard.querySelector(Hi.ATTR_V2_ATTRIBUTE_NAME_SELECTOR);
            }
            
            // For entity name, use the form group
            const formGroup = field.closest('.form-group');
            if (formGroup) {
                return formGroup.querySelector('small, label') || formGroup;
            }
            
            return field.parentElement;
        },
        
        // Create dirty indicator element
        createDirtyIndicator: function() {
            const indicator = document.createElement('span');
            indicator.className = this.config.dirtyIndicatorClass;
            indicator.innerHTML = DIRTY_TRACKING_INTERNAL.DIRTY_INDICATOR_CHAR;
            indicator.title = DIRTY_TRACKING_INTERNAL.DIRTY_INDICATOR_TITLE;
            return indicator;
        },
        
        // Insert dirty indicator in appropriate position
        insertDirtyIndicator: function(container, indicator) {
            // For attribute names, append to the end
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.appendChild(indicator);
            } else {
                // For other containers, insert at the end
                container.appendChild(indicator);
            }
        },
        
        // Add fallback CSS classes for browsers without :has() support
        addFallbackClasses: function(container, field) {
            // For attribute names
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.classList.add('has-dirty-indicator');
            }
            
            // For form groups (entity name)
            const formGroup = field.closest('.form-group');
            if (formGroup) {
                formGroup.classList.add('has-dirty-field');
            }
        },
        
        // Remove fallback CSS classes
        removeFallbackClasses: function(container, field) {
            // For attribute names
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.classList.remove('has-dirty-indicator');
            }
            
            // For form groups (entity name)
            const formGroup = field.closest('.form-group');
            if (formGroup) {
                formGroup.classList.remove('has-dirty-field');
            }
        },
        
        // Update message area with current dirty state (scoped to this container)
        updateMessageArea: function() {
            const messageContainer = this.container.querySelector(this.config.messageContainerSelector);
            if (!messageContainer) return;
            
            const dirtyCount = this.state.dirtyFields.size;
            
            if (dirtyCount === 0) {
                messageContainer.textContent = '';
                messageContainer.className = Hi.ATTR_V2_DIRTY_MESSAGE_CLASS;
            } else {
                const message = dirtyCount === 1 
                    ? DIRTY_TRACKING_INTERNAL.SINGLE_FIELD_MESSAGE
                    : DIRTY_TRACKING_INTERNAL.MULTIPLE_FIELDS_MESSAGE_TEMPLATE.replace('{count}', dirtyCount);
                messageContainer.textContent = message;
                messageContainer.className = `${Hi.ATTR_V2_DIRTY_MESSAGE_CLASS} active`;
            }
        },
        
        // Handle form submission
        handleFormSubmission: function(e) {
            // Handle textarea sync for truncated/hidden field pattern
            this.syncDisplayToHiddenFields();
        },
        
        // Sync display fields to hidden fields before submission
        syncDisplayToHiddenFields: function() {
            const form = this.container.querySelector(this.config.formSelector);
            if (!form) return;
            
            const displayFields = form.querySelectorAll('.display-field');
            displayFields.forEach(displayField => {
                const hiddenFieldId = displayField.getAttribute('data-hidden-field');
                const hiddenField = hiddenFieldId ? document.getElementById(hiddenFieldId) : null;
                
                if (hiddenField && !displayField.readOnly && !displayField.classList.contains('truncated')) {
                    hiddenField.value = displayField.value;
                }
            });
        },
        
        // Handle successful form submission
        handleFormSuccess: function(e) {
            // Only clear if the success event is for this container's form
            const form = this.container.querySelector(this.config.formSelector);
            if (form && e.target === form) {
                this.clearAllDirtyState();
            }
        },
        
        // Clear all dirty state for this container
        clearAllDirtyState: function() {
            // Clear visual indicators
            const form = this.container.querySelector(this.config.formSelector);
            if (form) {
                form.querySelectorAll('.' + this.config.dirtyFieldClass).forEach(field => {
                    field.classList.remove(this.config.dirtyFieldClass);
                });
                
                form.querySelectorAll('.' + this.config.dirtyIndicatorClass).forEach(indicator => {
                    indicator.remove();
                });
                
                // Clear fallback classes
                form.querySelectorAll('.has-dirty-indicator').forEach(element => {
                    element.classList.remove('has-dirty-indicator');
                });
                
                form.querySelectorAll('.has-dirty-field').forEach(element => {
                    element.classList.remove('has-dirty-field');
                });
            }
            
            // Clear state
            this.state.dirtyFields.clear();
            
            // Clear timers
            this.state.debounceTimers.forEach(timer => clearTimeout(timer));
            this.state.debounceTimers.clear();
            
            // Clear message
            this.updateMessageArea();
        },
        
        // Reinitialize for dynamic content
        reinitialize: function() {
            this.clearAllDirtyState();
            this.state.originalValues.clear();
            this.state.isInitialized = false;
            this.init();
        }
    };
    
    /**
     * Private DirtyTracker instance management
     */
    const _instances = new Map();
    
    const HiAttrDirtyTracking = {
        // Instance Management
        getInstance: function(containerId) {
            if (!_instances.has(containerId)) {
                _instances.set(containerId, new DirtyTracker(containerId));
            }
            return _instances.get(containerId);
        },
        
        createInstance: function(containerId) {
            const instance = new DirtyTracker(containerId);
            _instances.set(containerId, instance);
            return instance;
        },
        
        // Bulk Operations  
        initializeAll: function() {
            const containers = document.querySelectorAll(Hi.ATTR_V2_CONTAINER_SELECTOR);
            containers.forEach(container => {
                if (container.id) {
                    const instance = this.getInstance(container.id);
                    instance.init();
                }
            });
        },
        
        reinitializeContainer: function(containerId) {
            const $container = typeof containerId === 'string' ? $(`#${containerId}`) : $(containerId);
            const id = $container.attr('id');
            if (!id) {
                console.warn('DirtyTracking: Container missing ID, skipping initialization');
                return;
            }
            
            const instance = this.getInstance(id);
            instance.reinitialize();
        },
        
        // Event Handling
        handleFormSuccess: function(event) {
            const form = event.target.closest(Hi.ATTR_V2_FORM_CLASS_SELECTOR);
            if (form) {
                const container = form.closest(Hi.ATTR_V2_CONTAINER_SELECTOR);
                if (container && container.id) {
                    const instance = this.getInstance(container.id);
                    instance.handleFormSuccess(event);
                }
            }
        },
        
        // Initialization
        init: function() {
            this.initializeAll();
        }
    };
    
    // Export to Hi namespace
    window.Hi.attr.dirtyTracking = HiAttrDirtyTracking;
    
    // Auto-initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        HiAttrDirtyTracking.init();
    });
    
    // Initialize after modal shown
    document.addEventListener('shown.bs.modal', function(e) {
        // Look for containers within the modal
        const modal = e.target;
        const containers = modal.querySelectorAll(Hi.ATTR_V2_CONTAINER_SELECTOR);
        containers.forEach(container => {
            if (container.id) {
                HiAttrDirtyTracking.reinitializeContainer(container.id);
            }
        });
    });
    
})();