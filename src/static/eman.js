/**
 * Management page dynamic functionality.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    tick();
    // setInterval(tick, 10000);
});

function tick() {
    api.safeFetch(`/api/is_auto_open/${EVENT_UID}`).then((data) => {
        if (data.can_register && EVENT_REGIS) {
            document.getElementById("registration").textContent = "open.";
        } else {
            document.getElementById("registration").textContent = "closed.";
        }

        if (data.can_checkin) {
            document.getElementById("checkin").textContent = "open.";
        } else {
            document.getElementById("checkin").textContent = "closed.";
        }
    });
}