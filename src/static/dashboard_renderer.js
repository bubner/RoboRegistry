/**
 * Fetch data from the dashboard API and render it to the dashboard page.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    api.safeFetch("/api/dashboard").then((data) => {
        // Get dashboard boxes and clear them
        const target = document.getElementById("dashboardboxes");
        target.innerHTML = "";

        // Determine if dark mode is on
        const dark = document.cookie.includes("darkmode=on");

        // Loop over data and create boxes
        let row,
            count = 0;

        for (const value of Object.values(data)) {
            // Add rows of 3
            if (count % 3 === 0) {
                row = document.createElement("div");
                row.classList.add("row");
                target.appendChild(row);
            }
            const box = document.createElement("div");
            box.classList.add("col-sm-4");
            const square = document.createElement("div");
            square.classList.add("square");
            square.onclick = () => {
                location.assign(value.path);
            };
            square.style.backgroundColor = dark ? "#333" : "#e9e9e9";
            square.innerHTML = `<p class="db-content">${DOMPurify.sanitize(value.text)}</p>`;
            box.appendChild(square);
            row.appendChild(box);
            count++;
        }
    });
});
