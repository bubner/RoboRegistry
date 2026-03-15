/**
 * Management page dynamic functionality.
 * @author Lucas Bubner, 2023
 */
let data = null;
let regisTable = null;
let registeredCheckInTable = null;
let otherCheckInTable = null;

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
        regisTable.download("xlsx", `${EVENT_UID}-regis-export.xlsx`, {
            documentProcessing: (workbook) => {
                // LEGACY BEHAVIOUR: Make a new sheet for for every registration
                // Regular exports can still be done with .csv, so we leave it
                const sheets = [];
                for (const [uid, registration] of Object.entries(data)) {
                    if (uid == "anon_checkin") {
                        continue;
                    }
                    let teamLength = 0;
                    let teamData = [];
                    try {
                        const teams = JSON.parse(registration.teams);
                        teamLength = Object.keys(teams).length;
                        let i = 1;
                        for (const [num, name] of Object.entries(teams)) {
                            teamData.push([`Team ${i}`, `${num} - ${name}`]);
                            i++;
                        }
                    } catch (e) {
                        // Problem parsing JSON, keep as null
                    }
                    const data = [
                        ["Name", registration.repName],
                        ["Is Manual", uid.startsWith("-N")],
                        ["Registered Time", luxon.DateTime.fromSeconds(registration.registered_time).toISO()],
                        ["Role", registration.role],
                        ["Contact Name", registration.contactName],
                        ["Contact Email", registration.contactEmail],
                        ["Contact Phone", registration.contactPhone || "N/A"],
                        ["Number of People", registration.numPeople],
                        ["Number of Students", registration.numStudents],
                        ["Number of Mentors", registration.numMentors],
                        ["Number of Other Adults", registration.numAdults],
                        ["Number of Teams", teamLength],
                        ...teamData,
                    ].filter((row) => row.some((cell) => cell !== null && cell !== ""));
                    if (data.length > 0) {
                        sheets.push({
                            name: uid,
                            data: data,
                        });
                    }
                }
                workbook.SheetNames = sheets.map((sheet) => sheet.name);
                // Add info for each page
                for (const sheet of sheets) {
                    workbook.Sheets[sheet.name] = XLSX.utils.aoa_to_sheet(sheet.data);
                }
                return workbook;
            },
        });
    });
    document.getElementById("r-d-csv").addEventListener("click", () => {
        registeredCheckInTable.download("csv", `${EVENT_UID}-regis-ci-export.csv`, { bom: true });
    });
    document.getElementById("r-d-xl").addEventListener("click", () => {
        registeredCheckInTable.download("xlsx", `${EVENT_UID}-regis-ci-export.xlsx`);
    });
    document.getElementById("ra-d-csv").addEventListener("click", () => {
        otherCheckInTable.download("csv", `${EVENT_UID}-regis-ci-anon-export.csv`, { bom: true });
    });
    document.getElementById("ra-d-xl").addEventListener("click", () => {
        otherCheckInTable.download("xlsx", `${EVENT_UID}-regis-ci-anon-export.xlsx`);
    });

    // Ping the API every 30 seconds
    setInterval(tick, 30000);
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

    api.safeFetch(`/api/data/${EVENT_UID}`).then((newData) => {
        // Little bit of a weird JSON hack, but it works for this application where the data will be in the same order
        if (JSON.stringify(data) != JSON.stringify(newData)) {
            data = newData;
            update();
        }
    });
}

function update() {
    const registrationData = [];
    const registeredCheckInData = [];
    const otherCheckInData = [];
    for (const [uid, registration] of Object.entries(data)) {
        if (uid == "anon_checkin") {
            for (const [uuid, ci] of Object.entries(registration)) {
                otherCheckInData.push({
                    id: uuid,
                    name: ci.name,
                    // Since we don't show an extended box we clean up the data
                    rep: ci.rep === "noregis" ? "unregistered" : ci.rep,
                    time: luxon.DateTime.fromSeconds(ci.time)
                });
            }
            continue;
        }
        let teamLength = null;
        try {
            teamLength = Object.keys(JSON.parse(registration.teams)).length;
        } catch (e) {
            // Problem parsing JSON, keep as null
        }
        if (registration.role === "team") {
            registrationData.push({
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
                isManual: uid.startsWith("-N"),
            });
        } else {
            registrationData.push({
                id: uid,
                name: registration.repName,
                time: luxon.DateTime.fromSeconds(registration.registered_time),
                role: registration.role,
                contactName: registration.contactName,
                contactEmail: registration.contactEmail,
                contactPhone: registration.contactPhone || "N/A",
                isManual: uid.startsWith("-N"),
            });
        }
        registeredCheckInData.push({
            id: uid,
            name: registration.repName,
            contactName: registration.contactName,
            role: registration.role,
            checkedIn: registration.checkin_data.checked_in,
            checkInTime: registration.checkin_data.checked_in ? luxon.DateTime.fromSeconds(registration.checkin_data.time) : "N/A"
        });
    }
    try {
        regisTable = new Tabulator("#registered-table", {
            data: registrationData,
            layout: "fitColumns",
            pagination: "local",
            paginationSize: 10,
            paginationSizeSelector: [10, 25, 50, 100],
            initialSort: [{ column: "time" }],
            columns: [
                { title: "UID", field: "id", visible: false, download: true },
                { title: "Representative Name", field: "name" },
                { title: "Registered Time", field: "time", formatter: "datetime", formatterParams: { outputFormat: "FF" } },
                { title: "Role", field: "role" },
                { title: "Contact Name", field: "contactName", visible: false, download: true },
                { title: "Contact Email", field: "contactEmail", visible: false, download: true },
                { title: "Contact Phone", field: "contactPhone", visible: false, download: true },
                { title: "Declared People", field: "numPeople" },
                { title: "Declared Students", field: "numStudents" },
                { title: "Declared Mentors", field: "numMentors" },
                { title: "Declared Other Adults", field: "numAdults" },
                { title: "Declared FIRST Teams", field: "numTeams" },
                { title: "Team List", field: "teamList", visible: false, download: true },
                { title: "Is Manual", field: "isManual", visible: false, download: true },
            ],
            cssClass: "tabulator",
            selectable: true,
            placeholder: "No data available",
        });
        // Hide export buttons if there is no data
        if (registrationData.length === 0) {
            document.getElementById("d-csv").style.display = "none";
            document.getElementById("d-xl").style.display = "none";
            document.getElementById("viewbox").textContent = "No data available.";
        }
    } catch (e) {
        document.getElementById("registered-table").textContent =
            "Unable to load Tabulator. Please ensure your browser is not blocking the required scripts.";
        return;
    }

    regisTable.on("rowClick", (e, row) => {
        // Select only one row at a time
        regisTable.deselectRow();
        row.select();
        // Get the data for the selected row
        const data = row.getData();
        let info = data.isManual
            ? `<h5>Viewing manual registration data</h5>
                        <h6>→ ${DOMPurify.sanitize(data.name)}</h6>
                         <p class="text-muted small"><b>UID:</b> ${DOMPurify.sanitize(data.id)} (manual)</p>`
            : `<h5>Viewing registration data
                        <h6>→ ${DOMPurify.sanitize(data.name)}</h6>
                        <p class="text-muted small"><b>UID:</b> ${DOMPurify.sanitize(data.id)}</p>`;
        info += `
            <p><b>Registered Time:</b> ${DOMPurify.sanitize(data.time.toLocaleString(luxon.DateTime.DATETIME_FULL))}</p>
            <p><b>Role:</b> ${title(DOMPurify.sanitize(data.role).replaceAll("_", " "))}</p>
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
                <div class="table-responsive">
                    <table class="table table-bordered">
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
            </div>
            `;
        }
        document.getElementById("viewbox2").innerHTML = secondbox;
    });

    try {
        registeredCheckInTable = new Tabulator("#registered-checkin-table", {
            data: registeredCheckInData,
            layout: "fitColumns",
            pagination: "local",
            paginationSize: 10,
            paginationSizeSelector: [10, 25, 50, 100],
            initialSort: [{ column: "time" }],
            columns: [
                { title: "UID", field: "id", visible: false, download: true },
                { title: "Representative Name", field: "name" },
                { title: "Contact Name", field: "contactName" },
                { title: "Role", field: "role" },
                { title: "Checked In?", field: "checkedIn", visible: false, download: true },
                { title: "Check-in Time", field: "checkInTime", formatter: "datetime", formatterParams: { outputFormat: "FF" } },
            ],
            cssClass: "tabulator",
            selectable: true,
            placeholder: "No data available",
        });
        if (registrationData.length === 0) {
            document.getElementById("r-viewbox").textContent = "No data available.";
        }
    } catch (e) {
        document.getElementById("registered-checkin-table").textContent =
            "Unable to load Tabulator. Please ensure your browser is not blocking the required scripts.";
    }

    registeredCheckInTable.on("rowClick", (e, row) => {
        registeredCheckInTable.deselectRow();
        row.select();
        const data = row.getData();
        document.getElementById("r-viewbox").innerHTML = `
            <h5>Viewing registered check-in data</h5>
            <p><b>Representative Name:</b> ${DOMPurify.sanitize(data.name)}</p>
            <p><b>Contact Name:</b> ${DOMPurify.sanitize(data.contactName)}</p>
            <p><b>Role:</b> ${title(DOMPurify.sanitize(data.role).replaceAll("_", " "))}</p>
        `;
        let secondbox = `
            <h5>Check-in Information</h5>
            <p><b>Checked in?</b> ${DOMPurify.sanitize(data.checkedIn) ? "Yes" : "No"}</p>
        `;
        if (data.checkedIn) {
            secondbox += `
                <p><b>Check-in time:</b> ${DOMPurify.sanitize(data.checkInTime.toLocaleString(luxon.DateTime.DATETIME_FULL))}</p>
            `;
        }
        document.getElementById("r-viewbox2").innerHTML = secondbox;
    });
    try {
        otherCheckInTable = new Tabulator("#other-checkin-table", {
            data: otherCheckInData,
            layout: "fitColumns",
            pagination: "local",
            paginationSize: 10,
            paginationSizeSelector: [10, 25, 50, 100],
            initialSort: [{ column: "time" }],
            columns: [
                { title: "UID", field: "id", visible: false, download: true },
                { title: "Time", field: "time", formatter: "datetime", formatterParams: { outputFormat: "FF" } },
                { title: "Representative Name", field: "name" },
                { title: "Affiliation", field: "rep" },
            ],
            cssClass: "tabulator",
            selectable: false,
            placeholder: "No data available",
        });
    } catch (e) {
        document.getElementById("other-checkin-table").textContent =
            "Unable to load Tabulator. Please ensure your browser is not blocking the required scripts.";
    }
}

function _queue_inspection(num, tname, callback) {
    api.getTeamData(num).then((data) => {
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

function title(str) {
    return str
        .split(" ")
        .map((s) => s[0].toUpperCase() + s.substring(1))
        .join(" ");
}
