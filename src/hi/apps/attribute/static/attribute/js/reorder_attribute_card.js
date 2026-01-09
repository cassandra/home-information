document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-reorder-action]");
    if (!button) return;

    const card = button.closest("[data-attribute-id]");
    const parent = card?.parentElement;
    if (!parent) return;
    
    const direction = button.dataset.reorderAction;

    switch (direction) {
        case "up":
            moveUp(card, parent);
            break;
        case "down":
            moveDown(card, parent);
            break;
        default:
            return;
    }

    updateOrderIndexes(parent);
});

function printOrderIndexes(container) {
    const cards = container.querySelectorAll("[data-attribute-id]");
    console.log("--- Order Update ---");
    cards.forEach((card) => {
        const nameInput = card.querySelector('input[name*="name"]');
        const attrName = nameInput?.value || "(new attribute)";
        const orderValue = card.dataset.orderIndex;
        
        console.log(`${orderValue}. ${attrName}`);
    });
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
    const cards = container.querySelectorAll("[data-attribute-id]");
    cards.forEach((card, index) => {
        const newIndex = index + 1;
        card.dataset.orderIndex = newIndex;
        
        const hiddenInput = card.querySelector('input[name*="order_id"]');
        if (hiddenInput) {
            hiddenInput.value = newIndex;
        }
    });
    
    printOrderIndexes(container);
}