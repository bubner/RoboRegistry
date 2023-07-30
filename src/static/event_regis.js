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
            if (e.target.value !== "team") return;
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

function submitForm(e) {
    if (document.getElementById("role").value !== "team") return;

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

function handleRoleChange() {
    const display = document.getElementById("role").value === "team" ? "block" : "none";
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
