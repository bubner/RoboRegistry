/**
 * Dynamic elements for the event creator page.
 * @author Lucas Bubner, 2023
 */

const ADELAIDE = [138.6, -34.94];

document.addEventListener("DOMContentLoaded", () => {
    mapboxgl.accessToken = MAPBOX_API_KEY;
    mapboxgl.workerUrl = MAPBOX_WORKER;
    const map = new mapboxgl.Map({
        container: "map",
        style: "mapbox://styles/mapbox/streets-v11",
        center: ADELAIDE,
        zoom: 3,
    });

    // Dynamic resizing workaround
    map.on("idle", () => map.resize());

    const marker = new mapboxgl.Marker({
        draggable: true,
    })
        .setLngLat(ADELAIDE)
        .addTo(map);

    const reverseGeocode = (lng, lat) => {
        fetch(
            "https://api.mapbox.com/geocoding/v5/mapbox.places/" +
                lng +
                "," +
                lat +
                ".json?access_token=" +
                mapboxgl.accessToken,
        )
            .then((response) => response.json())
            .then((data) => {
                if (data.features && data.features.length > 0) {
                    document.getElementById("event_location").value = data.features[0].place_name;
                }
            })
            .catch((e) => {
                console.error(e);
            });
    };

    // Handle address from new marker location (dragging mechanic)
    // Old geolocation logic removed as it is too slow and not reusable
    marker.on("dragend", () => {
        const lngLat = marker.getLngLat();
        reverseGeocode(lngLat.lng, lngLat.lat);
    });

    const forwardGeocode = (address) => {
        if (address === "") {
            return;
        }
        fetch("https://api.mapbox.com/geocoding/v5/mapbox.places/" + address + ".json?access_token=" + mapboxgl.accessToken)
            .then((response) => response.json())
            .then((data) => {
                if (data.features && data.features.length > 0) {
                    const location = data.features[0].center;
                    map.setCenter(location);
                    marker.setLngLat(location);
                    map.setZoom(15);
                    document.getElementById("event_location").value = data.features[0].place_name;
                }
            })
            .catch((e) => {
                console.error(e);
            });
    };

    document.getElementById("event_location").addEventListener("change", (e) => forwardGeocode(e.currentTarget.value));
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

    // Manage dynamic elements of email display checkbox
    const displayEmail = document.getElementById("display_email");
    const emailInput = document.getElementById("email");
    const disableWarn = document.getElementById("disablewarn");
    let email = emailInput.value;
    const handleEmailChange = () => {
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
    };
    displayEmail.addEventListener("change", () => handleEmailChange());
    setTimeout(handleEmailChange, 500);
});
