/**
 * Management page dynamic functionality.
 * @author Lucas Bubner, 2023
 */
let registeredData = null;

document.addEventListener("DOMContentLoaded", () => {
    tick();

    const role = document.getElementById("role");
    const numPeople = document.getElementById("numPeople");
    const numStudents = document.getElementById("numStudents");
    const numMentors = document.getElementById("numMentors");
    const numAdults = document.getElementById("numAdults");
    const teamAdder = document.getElementById("add-button");
    const teamNum = document.getElementById("tnum");
    const teamOutput = document.getElementById("team-list");

    role.addEventListener("change", () => {
        const isTeam = role.value === "team";
        [numPeople, numStudents, numMentors, numAdults].forEach((input) => {
            input.disabled = !isTeam;
            input.required = isTeam;
            input.value = isTeam ? "" : null;
        });
        [teamAdder, teamNum].forEach((input) => {
            input.disabled = !isTeam;
            teamOutput.innerHTML = isTeam ? teamOutput.innerHTML : "";
        });
    });

    document.getElementById("add-button").addEventListener("click", (e) => handleAddTeamNumber(e));
    document.getElementById("tnum").addEventListener("onkeydown", (e) => {
        // As we cannot use a form (due to nesting), we need to manually handle these events
        if (e.key === "Enter") handleAddTeamNumber(e);
    });

    document.getElementById("regis").addEventListener("formdata", (e) => addFormData(e));
    document.getElementById("regis").addEventListener("submit", (e) => submitForm(e));

    const offset = (new Date().getTimezoneOffset() * -1) / 60 - parseFloat(OFFSET);

    setInterval(() => {
        const now = new Date();
        const eventStartTime = getTimeData(EVENT_DATE, EVENT_START_TIME, offset);
        const eventEndTime = getTimeData(EVENT_DATE, EVENT_END_TIME, offset);
        
        const toStartDiff = humanizeDuration(eventStartTime - now, { round: true });
        const toEndDiff = humanizeDuration(eventEndTime - now, { round: true });
        
        if (eventStartTime - now >= 0) {
            document.getElementById("status").textContent = "Registration will automatically close and check-in will auto-open in:";
            document.getElementById("togo").textContent = toStartDiff;
        } else if (eventEndTime - now >= 0) {
            document.getElementById("status").textContent = "Registration has been automatically closed. Check-in is open and will auto-close in:";
            document.getElementById("togo").textContent = toEndDiff;
        } else {
            document.getElementById("status").textContent = "Registration and check-in are closed.";
            document.getElementById("togo").textContent = "";
        }
    }, 1000);

    // Ping the API every 30 seconds
    // setInterval(tick, 30000);
});

function submitForm(e) {
    if (document.getElementById("role").value !== "Team") return;
    const teams = document.querySelectorAll(".team");
    if (teams.length === 0) {
        alert("Please add at least one team!");
        e.preventDefault();
        return;
    }
    for (const team of teams) {
        if (team.value) continue;
        alert(`Missing name for team number ${team.parentElement.id}!`);
        e.preventDefault();
    }
}

function tick() {
    api.safeFetch(`/api/is_auto_open/${EVENT_UID}`).then((data) => {
        if (!EVENT_VISIBLE) {
            document.getElementById("registration").textContent = "closed.";
            document.getElementById("checkin").textContent = "closed.";
            return;
        }

        if (data.can_register && EVENT_REGIS) {
            document.getElementById("registration").textContent = "open.";
        } else {
            document.getElementById("registration").textContent = "closed.";
        }

        if (data.can_checkin && EVENT_CHECKIN) {
            document.getElementById("checkin").textContent = "open.";
        } else {
            document.getElementById("checkin").textContent = "closed.";
        }
    });

    api.safeFetch(`/api/registrations/${EVENT_UID}`).then((data) => {
        // Little bit of a weird JSON hack, but it works for this application where the data will be in the same order
        if (JSON.stringify(data) != JSON.stringify(registeredData)) {
            updateRegistered(data);
        }
    });
}

function updateRegistered(data) {
    registeredData = data;
    const tabulatorData = [];
    for (const [uid, registration] of Object.entries(data)) {
        if (uid == "anon_checkin") {
            continue;
        }
        let teamLength = null;
        try {
            teamLength = Object.keys(JSON.parse(registration.teams)).length;
        } catch (e) {
            // Problem parsing JSON, keep as null
        }
        if (registration.role === "team") {
            tabulatorData.push({
                id: uid,
                name: registration.repName,
                time: luxon.DateTime.fromSeconds(registration.registered_time),
                role: registration.role,
                contactName: registration.contactName,
                contactEmail: registration.contactEmail,
                contactPhone: registration.contactPhone || "N/A",
                numAdults: registration.numAdults,
                numMentors: registration.numMentors,
                numStudents: registration.numStudents,
                numPeople: registration.numPeople,
                numTeams: teamLength || "error",
                isManual: uid.startsWith("-N")
            });
        } else {
            tabulatorData.push({
                id: uid,
                name: registration.repName,
                time: luxon.DateTime.fromSeconds(registration.registered_time),
                role: registration.role,
                contactName: registration.contactName,
                contactEmail: registration.contactEmail,
                contactPhone: registration.contactPhone || "N/A",
                isManual: uid.startsWith("-N")
            });
        }
    }
    const table = new Tabulator("#registered-table", {
        data: tabulatorData,
        layout: "fitColumns",
        pagination: "local",
        paginationSize: 10,
        paginationSizeSelector: [10, 25, 50, 100],
        initialSort: [{ column: "time" }],
        columns: [
            { title: "UID", field: "id", visible: false, download: false },
            { title: "Representative Name", field: "name" },
            { title: "Registered Time", field: "time", formatter: "datetime", formatterParams: { outputFormat: "FF" } },
            { title: "Role", field: "role" },
            { title: "Contact Name", field: "contactName", visible: false },
            { title: "Contact Email", field: "contactEmail", visible: false },
            { title: "Contact Phone", field: "contactPhone", visible: false },
            { title: "Declared People", field: "numPeople" },
            { title: "Declared Students", field: "numStudents" },
            { title: "Declared Mentors", field: "numMentors" },
            { title: "Declared Other Adults", field: "numAdults" },
            { title: "Declared FIRST Teams", field: "numTeams" },
            { title: "Is Manual", field: "isManual", visible: false }
        ],
        cssClass: "tabulator",
        selectable: true,
        placeholder: "No data available"
    });

    table.on("rowClick", (e, row) => {
        // Select only one row at a time
        table.deselectRow();
        row.select();
        // Get the data for the selected row
        const data = row.getData();
        document.getElementById("viewbox").textContent = JSON.stringify(data);
    });
}

function getTimeData(date, time, offset) {
    // Reused from event_viewer because working with date and time is a nightmare
    return new Date(new Date(`${date} ${time}`).getTime() + offset * 60 * 60 * 1000);
}
