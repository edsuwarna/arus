const API = {
    async request(method, path, body) {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('token');
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(`/api${path}`, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
        });
        const json = await res.json();
        if (json.status === 'error') {
            throw new Error(json.error?.message || 'Request failed');
        }
        return json.data;
    },
    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    put(path, body) { return this.request('PUT', path, body); },
    del(path) { return this.request('DELETE', path); },
};
