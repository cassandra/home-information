function reorderAttributeCard(button, direction) {
    const card = button.closest("[data-attribute-id]");
    const parent = card?.parentElement;

    if (!parent) return;

    switch (direction) {
        case "up":
            moveUp(card, parent);
            break;

        case "down":
            moveDown(card, parent);
            break;

        default:
            console.error(`Invalid direction: ${direction}`);
            return;
    }

    updateOrderIndexes(parent);
}

function moveUp(card, parent) {
    const prev = card.previousElementSibling;
    if (prev) parent.insertBefore(card, prev);
}

function moveDown(card, parent) {
    const next = card.nextElementSibling;
    if (next) parent.insertBefore(next, card);
}

function updateOrderIndexes(container) {
    const cards = container.querySelectorAll('[data-attribute-id]:not([data-attribute-id="None"])');
    cards.forEach((card, index) => {
        const newIndex = index + 1;
        card.dataset.orderIndex = newIndex;
        
        const hiddenInput = card.querySelector('input[name*="order_id"]');
        if (hiddenInput) {
            hiddenInput.value = newIndex;
        }
    });   
}