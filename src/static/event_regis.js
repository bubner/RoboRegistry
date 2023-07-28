/**
 * Dynamic elements for the event registration page.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    // Check to see if the event is full
    if (EVENT_LIMIT !== -1 && EVENT_REGISTRATIONS >= EVENT_LIMIT) {
        document.getElementById("role").value = "visitor";
        handleRoleChange();
        document.getElementById("role").addEventListener("change", (e) => {
            if (e.target.value !== "comp") return;
            alert("This event has reached team registration limit! You will need to contact the event owner.");
            e.target.value = "visitor";
        });
        return;
    }

    document.getElementById("role").addEventListener("change", () => handleRoleChange());
    setTimeout(handleRoleChange, 500);

    document.getElementById("add-button").addEventListener("click", (e) => handleAddTeamNumber(e));
    document.getElementById("tnum").addEventListener("onkeydown", (e) => {
        // As we cannot use a form (due to nesting), we need to manually handle these events
        if (e.key === "Enter") handleAddTeamNumber(e);
    });

    // Some form data is generated dynamically, hijack form submission to include this data
    document.getElementById("regis").addEventListener("formdata", (e) => addFormData(e));
    document.getElementById("regis").addEventListener("submit", (e) => submitForm(e));
});

function addFormData(e) {
    // Don't bother adding data if there is no data to add
    if (document.getElementById("role").value !== "comp") return;
    const formData = e.formData;

    const teams = document.querySelectorAll(".team");

    const teamNames = [];
    const teamNumbers = [];
    for (const team of teams) {
        // If using a dropdown selector, a duplicate team name may be present in the form of "selector-<team number>"
        if (team.parentElement.id.startsWith("selector-")) continue;
        teamNames.push(team.value);
        teamNumbers.push(parseInt(team.parentElement.id));
    }

    // Combine team names and numbers into an object
    const teamData = {};
    for (let i = 0; i < teamNames.length; i++) {
        teamData[teamNumbers[i]] = teamNames[i];
    }

    // Append to form data and continue submission
    formData.set("teams", JSON.stringify(teamData));
}

function submitForm(e) {
    if (document.getElementById("role").value !== "comp") return;

    const teams = document.querySelectorAll(".team");
    const teamSelectionModal = new bootstrap.Modal(document.getElementById("modal"));

    if (teams.length === 0) {
        teamSelectionModal.show();
        alert("Please add at least one team!");
        e.preventDefault();
        return;
    }

    for (const team of teams) {
        if (team.value) continue;
        e.preventDefault();
        teamSelectionModal.show();
        alert(`Missing name for team number ${team.parentElement.id}!`);

        // Highlight the box until the issue is corrected
        team.classList.add("border-danger");
        const revert = () => team.classList.remove("border-danger");
        team.addEventListener("input", () => {
            revert();
            team.removeEventListener("input", revert);
        });
    }
}

function removeTeam(e) {
    if (!confirm("Are you sure you want to remove this team number?")) return;
    e.parentElement.remove();
    api.abortCurrentRequest();
    document.getElementById("add-button").disabled = false;
    document.getElementById("tnum").disabled = false;
    document.getElementById("registernow").disabled = false;
    document.getElementById("waitmsg").style.display = "none";
}

function handleRoleChange() {
    const display = document.getElementById("role").value === "comp" ? "block" : "none";
    const numPeople = document.getElementById("numPeople");
    const numStudents = document.getElementById("numStudents");
    const numMentors = document.getElementById("numMentors");
    const numAdults = document.getElementById("numAdults");

    document.getElementById("addteams").style.display = display;

    numPeople.style.display = display;
    numStudents.style.display = display;
    numMentors.style.display = display;
    numAdults.style.display = display;

    // Set required state as needed
    numPeople.required = display === "block";
    numStudents.required = display === "block";
    numMentors.required = display === "block";

    // Change labels as well
    numPeople.previousElementSibling.style.display = display;
    numStudents.previousElementSibling.style.display = display;
    numMentors.previousElementSibling.style.display = display;
    numAdults.previousElementSibling.style.display = display;
}

function handleAddTeamNumber(e) {
    // Can't be adding a team if the option isn't even selected
    if (document.getElementById("role").value !== "comp") return;

    let teamNumber = document.getElementById("tnum").value;
    // Handler might fire without any data or if the modal is not open
    if (!teamNumber || !document.getElementById("modal").classList.contains("show")) return;

    e.preventDefault();
    teamNumber = parseInt(teamNumber);

    if (isNaN(teamNumber) || teamNumber < 10 || teamNumber > 99999) {
        alert("Invalid!");
        return;
    }

    const teamList = document.getElementById("team-list");
    const currentTeams = document.querySelectorAll("#team-list li label");
    const newTeam = document.createElement("li");

    // Check for duplicates
    for (let i = 0; i < currentTeams.length; i++) {
        if (currentTeams[i].innerText === teamNumber.toString()) {
            alert("Team number already added to the list!");
            return;
        }
    }

    newTeam.innerText = teamNumber;
    newTeam.classList.add("list-group-item", "d-flex", "justify-content-evenly", "align-items-center");
    // Protected as teamNumber is parsed as an int
    newTeam.innerHTML = `
        <label for="${teamNumber}">${teamNumber}</label> <span id='${teamNumber}'><div class="spinner-border spinner-border-sm" role="status"></div> Querying</span>
        <button type="button" class="btn btn-outline-danger btn-sm">Remove</button>
    `;
    newTeam.querySelector("button").addEventListener("click", (e) => removeTeam(e.target));
    teamList.appendChild(newTeam);

    // Disable submitting
    document.getElementById("add-button").disabled = true;
    document.getElementById("tnum").disabled = true;
    document.getElementById("registernow").disabled = true;
    document.getElementById("waitmsg").style.display = "inline";

    document.getElementById("tnum").value = "";

    // internal_api.js
    api.getTeamData(teamNumber).then((data) => {
        try {
            const target = document.getElementById(teamNumber);

            // Handle invalid or timed out requests
            if (!data || !data.valid) {
                target.innerHTML = `<input type="text" class="form-control team" placeholder="Enter team name">`;
                return;
            }

            // Handle rendering of data
            let value;
            if (data.data.length > 1) {
                // More than one team, we need to ask the user which one they want
                value = `<select class="form-select team" id="selector-${teamNumber}">`;
                for (const team of data.data) {
                    value += `<option class="team" value="${DOMPurify.sanitize(team.nickname)}">${DOMPurify.sanitize(team.nickname)}</option>`;
                }
                value += '<option value="other">Other</option></select>';
            } else {
                // Only one team, we can skip straight to rendering
                const team = data.data[0] || {};
                value = `<input type="text" class="form-control team" placeholder="Enter team name" value="${
                    DOMPurify.sanitize(team.nickname) || ""
                }">`;
            }

            target.innerHTML = value;

            if (data.data.length <= 1) return;
            document.getElementById(`selector-${teamNumber}`).addEventListener("change", () => {
                const value = document.getElementById(`selector-${teamNumber}`).value;
                if (value === "other") {
                    if (confirm("Use a custom team name?")) {
                        // Act as if there is no team
                        target.innerHTML = `<input type="text" class="form-control team" placeholder="Enter team name">`;
                    } else {
                        // Reset to first team
                        document.getElementById(`selector-${teamNumber}`).value = data.data[0].nickname;
                    }
                }
            });
        } finally {
            // Restore form action
            document.getElementById("add-button").disabled = false;
            document.getElementById("tnum").disabled = false;
            document.getElementById("registernow").disabled = false;
            document.getElementById("waitmsg").style.display = "none";
        }
    });
}
