// Control module for light dimmer controllers
// Uses jQuery event delegation for dynamically loaded content

$(document).ready(function() {
    
    // Event delegation for brightness slider input (real-time display update)
    $('body').on('input', '.brightness-slider', function() {
        var $slider = $(this);
        var value = $slider.val();
        var $display = $slider.closest('.brightness-control').find('.brightness-value');
        $display.text(value + '%');
    });
    
    // Event delegation for brightness quick-set buttons
    $('body').on('click', '.brightness-btn', function() {
        var $button = $(this);
        var value = $button.data('value');
        var $control = $button.closest('.brightness-control');
        var $slider = $control.find('.brightness-slider');
        var $display = $control.find('.brightness-value');
        
        // Update slider value and display
        $slider.val(value);
        $display.text(value + '%');
        
        // Trigger the change event to submit form via existing onchange-async handler
        $slider.trigger('change');
    });
    
});

// Alternative implementation for manual form submission if needed
// (The existing antinode.js onchange-async handler should handle this automatically)
function setBrightness(controllerId, value) {
    var $slider = $('[data-controller-id="' + controllerId + '"]');
    var $display = $slider.closest('.brightness-control').find('.brightness-value');
    
    $slider.val(value);
    $display.text(value + '%');
    $slider.trigger('change');
}