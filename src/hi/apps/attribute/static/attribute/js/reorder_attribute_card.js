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

function moveUp(card, parent) {
    const prev = card.previousElementSibling;
    if (prev) parent.insertBefore(card, prev);
}

function moveDown(card, parent) {
    const next = card.nextElementSibling;
    if (next) parent.insertBefore(next, card);
}

// function updateOrderIndexes(container) {
//     const cards = container.querySelectorAll("[data-attribute-id]");
//     cards.forEach((card, index) => {
//         card.dataset.orderIndex = index + 1;
//     });
// }
