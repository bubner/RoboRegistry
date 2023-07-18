/**
 * Dynamic elements for the event creator page.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    mapboxgl.accessToken = MAPBOX_API_KEY;
    const map = new mapboxgl.Map({
        container: "map",
        style: "mapbox://styles/mapbox/streets-v11",
        center: [-96, 37.8],
        zoom: 3,
    });

    const marker = new mapboxgl.Marker({
        draggable: true,
    })
        .setLngLat([-96, 37.8])
        .addTo(map);

    // Get current geolocation from the browser
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) => {
            const userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
            };
            map.setCenter(userLocation);
            marker.setLngLat(userLocation);
            fetch(
                "https://api.mapbox.com/geocoding/v5/mapbox.places/" +
                    userLocation.lng +
                    "," +
                    userLocation.lat +
                    ".json?access_token=" +
                    mapboxgl.accessToken
            )
                .then((response) => response.json())
                .then((data) => {
                    document.getElementById("event_location").value = data.features[0].place_name;
                })
                .catch((error) => {
                    console.log(error);
                });
        });
    }

    document.getElementById("event_location").addEventListener("change", () => geocodeAddress());
    document.getElementById("event_location").addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            e.stopPropagation();
            e.target.blur();
            return false;
        }
        return true;
    });

    // Get the current user's timezone and set it as the default, if there is not one selected before
    if (OLD_DATA_TIMEZONE === "") {
        document.getElementById("event_timezone").value = Intl.DateTimeFormat().resolvedOptions().timeZone;
    }

    const startTimeInput = document.getElementById("event_start_time");
    const endTimeInput = document.getElementById("event_end_time");

    // Add an event listener to the start time input to check if it's after the end time
    startTimeInput.addEventListener("change", () => {
        const startTime = new Date(`1970-01-01T${startTimeInput.value}:00`);
        const endTime = new Date(`1970-01-01T${endTimeInput.value}:00`);
        if (startTime > endTime) {
            alert("Start time cannot be after end time.");
            startTimeInput.value = "";
        }
    });

    // Add an event listener to the end time input to check if it's before the start time
    endTimeInput.addEventListener("change", () => {
        const startTime = new Date(`1970-01-01T${startTimeInput.value}:00`);
        const endTime = new Date(`1970-01-01T${endTimeInput.value}:00`);
        if (endTime < startTime) {
            alert("End time cannot be before start time.");
            endTimeInput.value = "";
        }
    });

    // Manage dynamic elements of email display checkbox
    const displayEmail = document.getElementById("display_email");
    const emailInput = document.getElementById("email");
    const disableWarn = document.getElementById("disablewarn");
    let email = emailInput.value;

    displayEmail.addEventListener("change", () => {
        if (displayEmail.checked) {
            emailInput.disabled = false;
            emailInput.value = email;
            disableWarn.style.display = "none";
        } else {
            emailInput.disabled = true;
            email = emailInput.value;
            emailInput.value = "N/A";
            disableWarn.style.display = "block";
        }
    });
});

function geocodeAddress() {
    const address = document.getElementById("event_location").value;
    if (address === "") {
        return;
    }
    fetch("https://api.mapbox.com/geocoding/v5/mapbox.places/" + address + ".json?access_token=" + mapboxgl.accessToken)
        .then((response) => response.json())
        .then((data) => {
            const location = data.features[0].center;
            map.setCenter(location);
            marker.setLngLat(location);
            map.setZoom(15);
            document.getElementById("event_location").value = data.features[0].place_name;
        })
        .catch((error) => {
            console.log(error);
        });
}
