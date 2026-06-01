/*
 * Home Information - Attribute Dirty State Tracking
 * Container-aware dirty state tracking for attribute editing
 * Supports multiple simultaneous editing contexts and visual dirty indicators
 */

(function() {
    'use strict';

    const DIRTY_TRACKING_INTERNAL = {
        DEBOUNCE_DELAY: 300,

        SINGLE_FIELD_MESSAGE: '1 field modified',
        MULTIPLE_FIELDS_MESSAGE_TEMPLATE: '{count} fields modified',
        DIRTY_INDICATOR_CHAR: '●',
        DIRTY_INDICATOR_TITLE: 'This field has been modified',

        FIELD_DIRTY_CLASS: 'attr-v2-field-dirty',
        DIRTY_INDICATOR_CLASS: 'attr-v2-dirty-indicator',
    };

    window.Hi = window.Hi || {};
    window.Hi.attr = window.Hi.attr || {};

    /**
     * Each editing context gets its own isolated DirtyTracker instance.
     */
    function DirtyTracker(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);

        this.config = {
            formSelector: Hi.ATTR_V2_FORM_CLASS_SELECTOR,
            messageContainerSelector: Hi.ATTR_V2_DIRTY_MESSAGE_SELECTOR,
            debounceDelay: DIRTY_TRACKING_INTERNAL.DEBOUNCE_DELAY,
            dirtyFieldClass: DIRTY_TRACKING_INTERNAL.FIELD_DIRTY_CLASS,
            dirtyIndicatorClass: DIRTY_TRACKING_INTERNAL.DIRTY_INDICATOR_CLASS
        };

        this.state = {
            originalValues: new Map(),
            dirtyFields: new Set(),
            debounceTimers: new Map(),
            isInitialized: false
        };
    }

    DirtyTracker.prototype = {
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

        captureOriginalValues: function() {
            const form = this.container.querySelector(this.config.formSelector);
            if (!form) return;

            // Entity/Location name field
            const nameField = form.querySelector('input[name$="name"]:not([name*="-"])');
            if (nameField) {
                this.captureFieldValue(nameField);
            }

            const attributeFields = form.querySelectorAll(`${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} input, ${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} textarea, ${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} select`);
            attributeFields.forEach(field => {
                // Skip hidden management form fields
                if (field.type === 'hidden' && field.name.includes('_')) return;
                this.captureFieldValue(field);
            });

            // Capture order fields so reorders can be tracked as dirty
            const orderFields = form.querySelectorAll(`${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} input[type="hidden"][name$="-order_id"]`);
            orderFields.forEach(field => {
                this.captureFieldValue(field);
            });

            // File cards aren't in the formset and use the
            // ``file_order_id_*`` naming. Pick them up alongside
            // the formset order fields so file reorder is dirty-
            // tracked the same way.
            const fileOrderFields = form.querySelectorAll('input[type="hidden"][name^="file_order_id_"]');
            fileOrderFields.forEach(field => {
                this.captureFieldValue(field);
            });

            const fileTitleFields = form.querySelectorAll(Hi.ATTR_V2_FILE_TITLE_INPUT_SELECTOR);
            fileTitleFields.forEach(field => {
                this.captureFieldValue(field);
            });
        },

        captureFieldValue: function(field) {
            if (!field.name || !field.id) return;

            let originalValue = this.getFieldValue(field);
            this.state.originalValues.set(field.id, originalValue);
            field.setAttribute('data-original-value', originalValue);
        },

        getFieldValue: function(field) {
            if (field.type === 'checkbox') {
                return field.checked ? 'true' : 'false';
            } else if (field.tagName.toLowerCase() === 'select') {
                return field.value || '';
            } else {
                return (field.value || '').trim();
            }
        },

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

        // Bind event listeners scoped to this container using event delegation
        bindEvents: function() {
            const $container = $(`#${this.containerId}`);
            const form = $container.find(this.config.formSelector);
            if (form.length === 0) return;

            // Remove any existing dirty tracking event handlers to avoid duplicates
            $container.off('.dirty-tracking');

            this.bindDebouncedEvents($container, 'input[type="text"], input[type="password"], input[type="number"], textarea', 'input');

            this.bindImmediateEvents($container, 'select, input[type="checkbox"]', 'change');

            $container.on('submit.dirty-tracking', this.config.formSelector, this.handleFormSubmission.bind(this));

            // Handle file title input activation on focus.
            $container.on('focus.dirty-tracking', '.' + Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS, (e) => {
                $(e.target).addClass('activated');
            });
        },

        bindDebouncedEvents: function($container, selector, eventType) {
            const handler = (e) => {
                const field = e.target;
                const fieldId = field.id;

                if (!fieldId) return;

                if (this.state.debounceTimers.has(fieldId)) {
                    clearTimeout(this.state.debounceTimers.get(fieldId));
                }

                const timer = setTimeout(() => {
                    this.handleFieldChange(field);
                    this.state.debounceTimers.delete(fieldId);
                }, this.config.debounceDelay);

                this.state.debounceTimers.set(fieldId, timer);
            };

            $container.on(`${eventType}.dirty-tracking`, selector, handler);
        },

        bindImmediateEvents: function($container, selector, eventType) {
            const handler = (e) => {
                this.handleFieldChange(e.target);
            };

            $container.on(`${eventType}.dirty-tracking`, selector, handler);
        },

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

        markFieldDirty: function(field) {
            field.classList.add(this.config.dirtyFieldClass);

            // For file title inputs, add activated class for persistent styling
            if (field.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                field.classList.add('activated');
            }

            const container = this.getFieldContainer(field);
            if (container && !container.querySelector('.' + this.config.dirtyIndicatorClass)) {
                const indicator = this.createDirtyIndicator();
                this.insertDirtyIndicator(container, indicator);

                // Add fallback CSS classes for browsers without :has() support
                this.addFallbackClasses(container, field);
            }
        },

        clearFieldDirty: function(field) {
            field.classList.remove(this.config.dirtyFieldClass);

            const container = this.getFieldContainer(field);
            if (container) {
                const indicator = container.querySelector('.' + this.config.dirtyIndicatorClass);
                if (indicator) {
                    indicator.remove();
                }

                this.removeFallbackClasses(container, field);
            }
        },

        getFieldContainer: function(field) {
            if (field.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                const fileInfo = field.closest(Hi.ATTR_V2_FILE_INFO_SELECTOR);
                if (fileInfo) {
                    return field; // Use the input itself as container for positioning
                }
            }

            // File order_id is a hidden input, so the field itself
            // isn't a visible target. Point the dirty indicator at
            // the file info area (title + filename) -- visible and
            // mirrors where file title's dirty cue appears.
            if (field.name && field.name.indexOf('file_order_id_') === 0) {
                const fileCard = field.closest(Hi.ATTR_V2_FILE_CARD_SELECTOR);
                if (fileCard) {
                    return fileCard.querySelector(Hi.ATTR_V2_FILE_INFO_SELECTOR) || fileCard;
                }
            }

            const attributeCard = field.closest(Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR);
            if (attributeCard) {
                return attributeCard.querySelector(Hi.ATTR_V2_ATTRIBUTE_NAME_SELECTOR);
            }

            const formGroup = field.closest('.form-group');
            if (formGroup) {
                return formGroup.querySelector('small, label') || formGroup;
            }

            return field.parentElement;
        },

        createDirtyIndicator: function() {
            const indicator = document.createElement('span');
            indicator.className = this.config.dirtyIndicatorClass;
            indicator.innerHTML = DIRTY_TRACKING_INTERNAL.DIRTY_INDICATOR_CHAR;
            indicator.title = DIRTY_TRACKING_INTERNAL.DIRTY_INDICATOR_TITLE;
            return indicator;
        },

        insertDirtyIndicator: function(container, indicator) {
            container.appendChild(indicator);
        },

        // Add fallback CSS classes for browsers without :has() support
        addFallbackClasses: function(container, field) {
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.classList.add('has-dirty-indicator');
            }

            const formGroup = field.closest('.form-group');
            if (formGroup) {
                formGroup.classList.add('has-dirty-field');
            }
        },

        removeFallbackClasses: function(container, field) {
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.classList.remove('has-dirty-indicator');
            }

            const formGroup = field.closest('.form-group');
            if (formGroup) {
                formGroup.classList.remove('has-dirty-field');
            }
        },

        updateMessageArea: function() {
            // Get fresh reference to container (important for modal scenarios)
            this.container = document.getElementById(this.containerId);
            const messageContainer = this.container ? this.container.querySelector(this.config.messageContainerSelector) : null;
            if (!messageContainer) return;

            const dirtyCount = this.state.dirtyFields.size;
            const isDirty = dirtyCount > 0;

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

            this.updateButtonProminence(isDirty);
        },

        updateButtonProminence: function(isDirty) {
            const $updateButton = $(this.container).find(Hi.ATTR_V2_UPDATE_BTN_SELECTOR);
            if ($updateButton.length === 0) return;

            if (isDirty) {
                $updateButton.addClass('form-dirty');
            } else {
                $updateButton.removeClass('form-dirty');
            }
        },

        handleFormSubmission: function(e) {
            // Handle textarea sync for truncated/hidden field pattern
            this.syncDisplayToHiddenFields();
        },

        syncDisplayToHiddenFields: function() {
            const form = this.container.querySelector(this.config.formSelector);
            if (!form) return;

            const textFieldSelector = `${Hi.ATTR_V2_DISPLAY_FIELD_SELECTOR}, ${Hi.ATTR_V2_TEXT_EDIT_FIELD_SELECTOR}`;
            const displayFields = form.querySelectorAll(textFieldSelector);
            displayFields.forEach(displayField => {
                const hiddenFieldId = displayField.getAttribute('data-hidden-field');
                const hiddenField = hiddenFieldId ? document.getElementById(hiddenFieldId) : null;

                if (hiddenField && !displayField.readOnly && !displayField.classList.contains('truncated')) {
                    hiddenField.value = displayField.value;
                }
            });
        },

        handleOrderFieldChanges: function() {
            const form = this.container.querySelector(this.config.formSelector);
            if (!form) return;

            const orderFields = form.querySelectorAll(`${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} input[type="hidden"][name$="-order_id"]`);
            orderFields.forEach(field => {
                this.handleFieldChange(field);
            });

            // File cards have ad-hoc ``file_order_id_*`` hidden
            // inputs (not formset-prefixed); re-evaluate them so the
            // file-grid reorder path lights up dirty-tracking too.
            const fileOrderFields = form.querySelectorAll('input[type="hidden"][name^="file_order_id_"]');
            fileOrderFields.forEach(field => {
                this.handleFieldChange(field);
            });
        },

        handleFormSuccess: function(e) {
            // Only clear if the success event is for this container's form
            const form = this.container.querySelector(this.config.formSelector);
            if (form && e.target === form) {
                this.clearAllDirtyState();
            }
        },

        clearAllDirtyState: function() {
            const form = this.container.querySelector(this.config.formSelector);
            if (form) {
                form.querySelectorAll('.' + this.config.dirtyFieldClass).forEach(field => {
                    field.classList.remove(this.config.dirtyFieldClass);
                });

                form.querySelectorAll('.' + this.config.dirtyIndicatorClass).forEach(indicator => {
                    indicator.remove();
                });

                form.querySelectorAll('.has-dirty-indicator').forEach(element => {
                    element.classList.remove('has-dirty-indicator');
                });

                form.querySelectorAll('.has-dirty-field').forEach(element => {
                    element.classList.remove('has-dirty-field');
                });
            }

            this.state.dirtyFields.clear();

            this.state.debounceTimers.forEach(timer => clearTimeout(timer));
            this.state.debounceTimers.clear();

            this.updateMessageArea();
        },

        reinitialize: function() {
            this.clearAllDirtyState();
            this.state.originalValues.clear();
            this.state.isInitialized = false;
            this.init();
        }
    };

    const _instances = new Map();

    const HiAttrDirtyTracking = {
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

        init: function() {
            this.initializeAll();
        }
    };

    window.Hi.attr.dirtyTracking = HiAttrDirtyTracking;

    document.addEventListener('DOMContentLoaded', function() {
        HiAttrDirtyTracking.init();
    });

    // Modal content uses a separate initialization path (reinitializeContainer);
    // it is not bound to DOMContentLoaded.

})();
