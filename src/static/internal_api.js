/**
 * Internal API access for RoboRegistry with abort controller and timeout.
 * @author Lucas Bubner, 2023
 */

class API {
    constructor() {
        this.controller = new AbortController();
        this.teamCache = new Map();
    }

    safeFetch(endpoint) {
        return new Promise((resolve, _) => {
            let data = null;
            const timeout = setTimeout(() => {
                this.abortCurrentRequest();
                console.warn(`API: Request to '${endpoint}' timed out after 15 seconds.`);
                resolve({});
            }, 15000);

            const fetchAndProcessData = async () => {
                const response = await fetch(endpoint, { signal: this.controller.signal });
                try {
                    data = await response.json();
                    clearTimeout(timeout);
                    resolve(data);
                } catch (e) {
                    console.warn(`API: Could not fetch '${endpoint}'. Retrying...`);
                    setTimeout(fetchAndProcessData, 500);
                }
            };

            fetchAndProcessData();
        });
    }

    abortCurrentRequest() {
        this.controller.abort();
        this.controller = new AbortController();
    }

    getTeamData(number) {
        const hit = this.teamCache.get(number);
        if (hit) return hit;
        // FIRSTTeamAPI: https://github.com/bubner/FIRSTTeamAPI
        const miss = this.safeFetch(`https://firstteam.api.bubner.me/get_team/${number}`);
        this.teamCache.set(number, miss);
        return miss;
    }
}

// Allow access to the API from anywhere
const api = new API();
