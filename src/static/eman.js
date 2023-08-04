/**
 * Management page dynamic functionality.
 * @author Lucas Bubner, 2023
 */
let registeredData = null;
let regisTable = null;

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

    document.getElementById("d-csv").addEventListener("click", () => {
        regisTable.download("csv", `${EVENT_UID}-regis-export.csv`, { bom: true });
    });

    document.getElementById("d-xl").addEventListener("click", () => {
        regisTable.download("xlsx", `${EVENT_UID}-regis-export.xlsx`);
    });

    // Ping the API every 30 seconds
    // setInterval(tick, 30000);
});

function submitForm(e) {
    if (document.getElementById("role").value !== "team") return;
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
                teamList: registration.teams,
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
    regisTable = new Tabulator("#registered-table", {
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
            { title: "Team List", field: "teamList", visible: false },
            { title: "Is Manual", field: "isManual", visible: false }
        ],
        cssClass: "tabulator",
        selectable: true,
        placeholder: "No data available"
    });

    regisTable.on("rowClick", (e, row) => {
        // Select only one row at a time
        regisTable.deselectRow();
        row.select();
        // Get the data for the selected row
        const data = row.getData();
        let info = data.isManual ? 
                        `<h5>Viewing manual registration of '${DOMPurify.sanitize(data.name)}'</h5>
                         <p class="text-muted small"><b>UID:</b> ${DOMPurify.sanitize(data.id)} (manual)</p>`
                        :
                        `<h5>Viewing registration of '${DOMPurify.sanitize(data.name)}'</h5>
                        <p class="text-muted small"><b>UID:</b> ${DOMPurify.sanitize(data.id)}</p>`;
        info += `
            <p><b>Registered Time:</b> ${DOMPurify.sanitize(data.time.toLocaleString(luxon.DateTime.DATETIME_FULL))}</p>
            <p><b>Role:</b> ${DOMPurify.sanitize(data.role)}</p>
        `;
        if (data.numPeople) {
            info += `<p><b>Declared People:</b> ${DOMPurify.sanitize(data.numPeople)}</p>`;
        }
        if (data.numStudents) {
            info += `<p><b>Declared Students:</b> ${DOMPurify.sanitize(data.numStudents)}</p>`;
        }
        if (data.numMentors) {
            info += `<p><b>Declared Mentors:</b> ${DOMPurify.sanitize(data.numMentors)}</p>`;
        }
        if (data.numAdults) {
            info += `<p><b>Declared Other Adults:</b> ${DOMPurify.sanitize(data.numAdults)}</p>`;
        }
        if (data.numTeams) {
            info += `<p><b>Declared FIRST Teams:</b> ${DOMPurify.sanitize(data.numTeams)}</p>`;
        }
        document.getElementById("viewbox").innerHTML = info;
        let secondbox = `
            <h5>Contact Information</h5>
            <p><b>Contact Name:</b> ${DOMPurify.sanitize(data.contactName)}</p>
            <p><b>Contact Email:</b> ${DOMPurify.sanitize(data.contactEmail)}</p>
            <p><b>Contact Phone:</b> ${DOMPurify.sanitize(data.contactPhone)}</p>
        `;
        if (data.numTeams > 0) {
            const teams = JSON.parse(data.teamList);
            secondbox += `
                <br>
                <h5>Declared Teams</h5>
                <table class="table table-bordered team-table">
                    <thead>
                        <tr>
                            <th>Team Number</th>
                            <th>Team Name</th>
                            <th>Number is FIRST registered?</th>
                            <th>Team is using a custom name?</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            for (const [num, name] of Object.entries(teams)) {
                // Need to query FIRSTTeamAPI to get verification status
                _queue_inspection(num, name, (status, name) => {
                    if (status) {
                        document.getElementById(DOMPurify.sanitize(num)).innerHTML = "<span class='green'>yes</span>";
                    } else {
                        document.getElementById(DOMPurify.sanitize(num)).innerHTML = "<span class='red'>no</span>";
                    }
                    if (name) {
                        document.getElementById(DOMPurify.sanitize(num) + "n").innerHTML = "<span class='red'>yes</span>";
                    } else {
                        document.getElementById(DOMPurify.sanitize(num) + "n").innerHTML = "<span class='green'>no</span>";
                    }
                });
                secondbox += `
                    <tr>
                        <td>${DOMPurify.sanitize(num)}</td>
                        <td>${DOMPurify.sanitize(name)}</td>
                        <td id="${DOMPurify.sanitize(num)}"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td>
                        <td id="${DOMPurify.sanitize(num)}n"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td>
                    </tr>
                `;
            }
            secondbox += `
                    </tbody>
                </table>
            `;
        }
        document.getElementById("viewbox2").innerHTML = secondbox;
    });
}

function _queue_inspection(num, tname, callback) {
    // TODO: Optimise with cache
    api.safeFetch(`https://firstteamapi.vercel.app/get_team/${num}`).then((data) => {
        const status = data.valid;
        let nameFound = false;
        for (let i = 0; i < data.data.length; i++) {
            if (data.data[i].nickname === tname) {
                nameFound = true;
                break;
            }
        }
        callback(status, !nameFound);
    });
}


function getTimeData(date, time, offset) {
    // Reused from event_viewer because working with date and time is a nightmare
    return new Date(new Date(`${date} ${time}`).getTime() + offset * 60 * 60 * 1000);
}
