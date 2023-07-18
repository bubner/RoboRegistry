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

    document.getElementById("role").addEventListener("change", () => {
        const display = document.getElementById("role").value == "comp" ? "block" : "none";
        document.getElementById("addteams").style.display = display;
        document.getElementById("numPeople").style.display = display;
        document.getElementById("numStudents").style.display = display;
        document.getElementById("numMentors").style.display = display;
        document.getElementById("numAdults").style.display = display;
        // Change labels as well
        document.getElementById("numPeople").previousElementSibling.style.display = display;
        document.getElementById("numStudents").previousElementSibling.style.display = display;
        document.getElementById("numMentors").previousElementSibling.style.display = display;
        document.getElementById("numAdults").previousElementSibling.style.display = display;
    });

    document.getElementById("add-button").addEventListener("click", (e) => handleAddTeamNumber(e));
    document.getElementById("tnum").addEventListener("onkeydown", (e) => {
        if (e.key == "Enter") handleAddTeamNumber(e);
    });
});

function removeTeam(e) {
    if (!confirm("Are you sure you want to remove this team number?")) return;
    e.parentElement.remove();
    api.abortCurrentRequest();
    document.getElementById("add-button").disabled = false;
    document.getElementById("tnum").disabled = false;
    document.getElementById("registernow").disabled = false;
    document.getElementById("waitmsg").style.display = "none";
}

function handleAddTeamNumber(e) {
    e.preventDefault();
    let teamNumber = document.getElementById("tnum").value;
    teamNumber = parseInt(teamNumber);

    if (isNaN(teamNumber) || teamNumber < 10 || teamNumber > 99999) {
        alert("Invalid!");
        return;
    }

    const teamList = document.getElementById("team-list");
    const newTeam = document.createElement("li");

    // Check for duplicates
    for (let i = 0; i < teamList.children.length; i++) {
        if (teamList.children[i].innerText.includes(teamNumber)) {
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

    // internal_api.js
    api.getTeamData(teamNumber).then((data) => {
        try {
            const target = document.getElementById(teamNumber);

            // Handle invalid or timed out requests
            if (!data || !data.valid) {
                target.innerHTML = `<form class="form-inline"><input type="text" class="form-control" placeholder="Enter team name" required></form>`;
                return;
            }

            // Handle rendering of data
            let value = "";
            if (data.data.length > 1) {
                // More than one team, we need to ask the user which one they want
                value = `<select class="form-select" id="selector-${teamNumber}">`;
                for (const team of data.data) {
                    value += `<option value="${team.nickname}">${team.nickname}</option>`;
                }
                value += '<option value="other">Other</option></select>';
            } else {
                // Only one team, we can skip straight to rendering
                const team = data.data[0] || {};
                value = `<form class="form-inline"><input type="text" class="form-control" placeholder="Enter team name" value="${
                    team.nickname || ""
                }" required></form>`;
            }

            target.innerHTML = value;

            if (data.data.length <= 1) return;
            document.getElementById(`selector-${teamNumber}`).addEventListener("change", () => {
                const value = document.getElementById(`selector-${teamNumber}`).value;
                if (value == "other") {
                    if (confirm("Use a custom team name?")) {
                        // Act as if there is no team
                        target.innerHTML = `<form class="form-inline"><input type="text" class="form-control" placeholder="Enter team name" required></form>`;
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
