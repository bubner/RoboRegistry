/**
 * Dynamic elements for the check in page.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    const itemSelect = document.getElementById("item-select");
    const visitReasonDiv = document.getElementById("visit-reason");

    const toggleAnon = () => {
        visitReasonDiv.style.display = itemSelect.value === "anon" ? "block" : "none";
    };

    itemSelect.addEventListener("change", toggleAnon);
    setTimeout(toggleAnon, 500);
});
