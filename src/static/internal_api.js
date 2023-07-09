async function fetchDashboard() {
    // Fetch data
    let data = null;
    while (!data) {
        const response = await fetch("/api/dashboard");
        try {
            data = await response.json();
        } catch (e) {
            console.warn("API: Could not fetch dashboard content. Retrying...");
        }
    }

    // Get dashboard boxes and clear them
    const target = document.getElementById("dashboardboxes");
    target.innerHTML = "";

    // Determine if dark mode is on
    const dark = document.cookie.includes("darkmode=on");

    // Loop over data and create boxes
    let row, count = 0;
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
        }
        square.style.backgroundColor = dark ? "#333" : "#e9e9e9";
        square.innerHTML = `<p class="db-content">${value.text}</p>`;
        box.appendChild(square);
        row.appendChild(box);
        count++;
    }
}

const controller = new AbortController();
async function setTeamData(number) {
    const signal = controller.signal;

    let data = null;
    while (!data) {
        const response = await fetch(`/api/get_team_data/${number}`, { signal });
        try {
            data = await response.json();
        } catch (e) {
            console.warn(`API: Could not fetch info for team ${number}. Retrying...`);
        }
    }

    const target = document.getElementById(number);
    if (!data.valid) {
        // Team is not FIRST registered, ask for a name manually
        target.innerHTML = `<form class="form-inline"><input type="text" class="form-control" placeholder="Enter team name"></form>`;
        return;
    }

    // Team is registered, display info
    if (data.data.length > 1) {
        // TODO: More than one team, display a dropdown
    } else {
        // Only one team, display info
        const team = data.data[0];
        const suffix = team.program === "FIRST Tech Challenge" ? "FTC" : team.program === "FIRST Robotics Competition" ? "FRC" : "FLL";
        target.innerHTML = `${team.nickname} (${suffix})`;
    }
}
