/**
 * Dynamic elements for the event viewer page.
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

    // Get the local time zone from the internationalisation API
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    // Offset the time to local format
    // getTimezoneOffset returns inverse of the offset, so we need to invert it as well
    const offset = (new Date().getTimezoneOffset() * -1) / 60 - parseFloat(OFFSET);

    // Get the local start and end times
    const startLocalTime = getTimeData(EVENT_DATE, EVENT_START_TIME, offset);
    const endLocalTime = getTimeData(EVENT_DATE, EVENT_END_TIME, offset);

    // Display local time on the page, if required
    const eventTime = document.querySelector("#event-time");
    if (eventTime)
        eventTime.innerHTML = `<i>Local time (${timeZone})</i> <br> <b>From</b>: ${startLocalTime} <br> <b>To</b>: ${endLocalTime}`;

    // Calculate relative event times
    const relativeEventTime = document.querySelector("#relative-event-time");
    let eventState = EventStates.NOT_STARTED;
    let last = null;

    // Refresh time statistics every second
    setInterval(() => {
        // Refresh the page if the eventState has changed
        if (last && eventState !== last) {
            location.reload();
        }
        last = eventState;

        // Interpret event times as local times
        const eventDate = new Date(EVENT_DATE);
        const eventStartTime = new Date(`${eventDate.toDateString()} ${EVENT_START_TIME}`);
        const eventEndTime = new Date(`${eventDate.toDateString()} ${EVENT_END_TIME}`);

        const now = new Date();
        if (now < eventStartTime) {
            eventState = EventStates.NOT_STARTED;
            relativeEventTime.innerHTML = `Starts in ${timeDiff(eventStartTime, now)}`;
        } else if (now < eventEndTime) {
            eventState = EventStates.RUNNING;
            relativeEventTime.innerHTML = `Ends in ${timeDiff(eventEndTime, now)}`;
        } else {
            eventState = EventStates.ENDED;
            relativeEventTime.innerHTML = `Ended ${timeDiff(now, eventEndTime)} ago`;
        }
    }, 1000);
});

// Represent current event state
class EventStates {
    static get NOT_STARTED() {
        return 0;
    }
    static get RUNNING() {
        return 1;
    }
    static get ENDED() {
        return 2;
    }
}

// Convert event time to local time
function getTimeData(date, time, offset) {
    return new Date(new Date(`${date} ${time}`).getTime() + offset * 60 * 60 * 1000).toLocaleString(
        navigator.language,
        {
            year: "numeric",
            month: "numeric",
            day: "numeric",
            hour: "numeric",
            minute: "numeric",
        }
    );
}

// Calculate relative time difference between two dates using humanise-duration
function timeDiff(s, e) {
    const millis = s - e;
    return humanizeDuration(millis, { round: true, largest: 3 });
}

function copyToClipboard(text) {
    const url = `https://roboregistry.vercel.app/${text}`;
    navigator.clipboard.writeText(url);
    alert(`Copied to clipboard: ${url}`);
}