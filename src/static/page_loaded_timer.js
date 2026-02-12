/**
 * Display of page load time.
 * @author Lucas Bubner, 2026
 */

document.addEventListener("DOMContentLoaded", () => {
    const loaded = Date.now();
    const target = document.getElementById("page-time");
    if (!target) return;
    setInterval(() => {
        target.innerHTML = humanizeDuration(loaded - Date.now(), { round: true, largest: 3 });
    }, 1000);
});
