/**
 * Management page dynamic functionality.
 * @author Lucas Bubner, 2023
 */

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
        const isComp = role.value === "comp";
        [numPeople, numStudents, numMentors, numAdults].forEach((input) => {
            input.disabled = !isComp;
            input.required = isComp;
            input.value = isComp ? "" : null;
        });
        [teamAdder, teamNum].forEach((input) => {
            input.disabled = !isComp;
            teamOutput.innerHTML = isComp ? teamOutput.innerHTML : "";
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

    // setInterval(tick, 10000);
});

function submitForm(e) {
    if (document.getElementById("role").value !== "comp") return;
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

    });
}

function getTimeData(date, time, offset) {
    // Reused from event_viewer because working with date and time is a nightmare
    return new Date(new Date(`${date} ${time}`).getTime() + offset * 60 * 60 * 1000);
}
