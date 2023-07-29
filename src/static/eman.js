/**
 * Management page dynamic functionality.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    tick();
    getData();

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

function getData() {
    api.safeFetch(`/api/registrations/${EVENT_UID}`).then((data) => {
        // TODO
    });
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

        if (data.can_checkin) {
            document.getElementById("checkin").textContent = "open.";
        } else {
            document.getElementById("checkin").textContent = "closed.";
        }
    });
}
