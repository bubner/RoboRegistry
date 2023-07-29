/**
 * Automatic mapping of event locations using Mapbox.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    mapboxgl.accessToken = MAPBOX_API_KEY;
    mapboxgl.workerUrl = "{{ url_for('static', filename='libs/mapbox-gl-csp-worker_v2.15.0.js') }}";
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
});
