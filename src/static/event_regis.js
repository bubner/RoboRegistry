/**
 * Dynamic elements for the event registration page.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    mapboxgl.accessToken = MAPBOX_API_KEY;
    fetch(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${EVENT_LOCATION}.json?access_token=${mapboxgl.accessToken}`
    )
        .then((response) => response.json())
        .then((data) => {
            const coordinates = data.features[0].center;
            const map = new mapboxgl.Map({
                container: "map",
                style: "mapbox://styles/mapbox/streets-v11",
                center: coordinates,
                zoom: 15,
            });
            // Add a marker at the event location
            new mapboxgl.Marker({
                draggable: false,
            })
                .setLngLat(coordinates)
                .addTo(map);

            map.flyTo({
                center: coordinates,
                zoom: 15,
            });
        });

    document.getElementById("role").addEventListener("change", () => handleRoleChange());
    setTimeout(handleRoleChange, 500);

    document.getElementById("add-button").addEventListener("click", (e) => handleAddTeamNumber(e));
    document.getElementById("tnum").addEventListener("onkeydown", (e) => {
        // As we cannot use a form (due to nesting), we need to manually handle these events
        if (e.key == "Enter") handleAddTeamNumber(e);
    });

    // Some form data is generated dynamically, hijack form submission to include this data
    document.getElementById("regis").addEventListener("submit", (e) => submitForm(e));
});

function submitForm(e) {
    // Don't bother adding data if there is no data to add
    if (document.getElementById("role").value != "comp") return;

    e.preventDefault();
    const formData = new FormData(e.target);

    const teams = document.querySelectorAll(".team");
    const teamSelectionModal = new bootstrap.Modal(document.getElementById("modal"));

    if (teams.length === 0) {
        teamSelectionModal.show();
        alert("Please add at least one team!");
        return;
    }

    const teamNames = [];
    const teamNumbers = [];
    for (const team of teams) {
        try {
            if (!team.value) throw new Error;
            teamNames.push(team.value);
            teamNumbers.push(team.parentElement.id);
        } catch (e) {
            teamSelectionModal.show();
            alert(`Missing name for team number ${team.parentElement.id}!`);

            // Highlight the box until the issue is corrected
            team.classList.add("border-danger");
            const revert = () => team.classList.remove("border-danger");
            team.addEventListener("input", () => {
                revert();
                team.removeEventListener("input", revert);
            });

            return;
        }
    }

    // Combine team names and numbers into an object
    const teamData = {};
    for (let i = 0; i < teamNames.length; i++) {
        // FIXME: Errors with selector team names, debug soon
        teamData[teamNumbers[i]] = teamNames[i];
    }

    // Append to form data and mock a form submission
    formData.append("teams", JSON.stringify(teamData));

    const mockForm = e.target.cloneNode(true);
    const mockInput = document.createElement("input");

    mockInput.type = "hidden";
    mockInput.name = "teams";
    mockInput.value = JSON.stringify(teamData);

    mockForm.appendChild(mockInput);
    document.body.appendChild(mockForm);

    mockForm.submit();
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
    const display = document.getElementById("role").value == "comp" ? "block" : "none";
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
    numPeople.required = display == "block";
    numStudents.required = display == "block";
    numMentors.required = display == "block";
    
    // Change labels as well
    numPeople.previousElementSibling.style.display = display;
    numStudents.previousElementSibling.style.display = display;
    numMentors.previousElementSibling.style.display = display;
    numAdults.previousElementSibling.style.display = display;
}

function handleAddTeamNumber(e) {
    // Can't be adding a team if the option isn't even selected
    if (document.getElementById("role").value != "comp") return;
    
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
    const newTeam = document.createElement("li");

    // Check for duplicates
    for (let i = 0; i < teamList.children.length; i++) {
        if (teamList.children[i].textContent.trim() === teamNumber) {
            alert("Team number already added to the list!");
            return;
        }
    }

    newTeam.innerText = teamNumber;
    newTeam.classList.add("list-group-item", "d-flex", "justify-content-evenly", "align-items-center");
    newTeam.innerHTML = `
        <label for="${teamNumber}">${teamNumber}</label> <span id='${teamNumber}'><div class="spinner-border spinner-border-sm" role="status"></div> Querying</span>
        <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeTeam(this)">Remove</button>
    `;
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
            let value = "";
            if (data.data.length > 1) {
                // More than one team, we need to ask the user which one they want
                value = `<select class="form-select team" id="selector-${teamNumber}">`;
                for (const team of data.data) {
                    value += `<option class="team" value="${team.nickname}">${team.nickname}</option>`;
                }
                value += '<option value="other">Other</option></select>';
            } else {
                // Only one team, we can skip straight to rendering
                const team = data.data[0] || {};
                value = `<input type="text" class="form-control team" placeholder="Enter team name" value="${
                    team.nickname || ""
                }">`;
            }

            target.innerHTML = value;

            if (data.data.length <= 1) return;
            document.getElementById(`selector-${teamNumber}`).addEventListener("change", () => {
                const value = document.getElementById(`selector-${teamNumber}`).value;
                if (value == "other") {
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
