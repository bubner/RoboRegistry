class API {
    constructor() {
        this.controller = new AbortController();
    }

    async safeFetch(endpoint) {
        return new Promise((resolve, reject) => {
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

    async getTeamData(number) {
        // FIRSTTeamAPI: https://github.com/hololb/FIRSTTeamAPI
        return this.safeFetch(`https://firstteamapi.vercel.app/get_team/${number}`);
    }
}

const api = new API();
