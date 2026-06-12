const API = {
    _refreshing: null,

    async request(method, path, body) {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('access_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(`/api${path}`, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
        });

        // Auto-refresh on 401
        if (res.status === 401 && path !== '/auth/refresh' && path !== '/auth/login') {
            const newToken = await this._tryRefresh();
            if (newToken) {
                headers['Authorization'] = `Bearer ${newToken}`;
                const retry = await fetch(`/api${path}`, {
                    method,
                    headers,
                    body: body ? JSON.stringify(body) : undefined,
                });
                const json = await retry.json();
                if (json.status === 'error') {
                    throw new Error(json.error?.message || 'Request failed');
                }
                return json.data;
            }
            // Refresh failed — redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            location.hash = 'login';
            throw new Error('Session expired');
        }

        const json = await res.json();
        if (json.status === 'error') {
            throw new Error(json.error?.message || 'Request failed');
        }
        return json.data;
    },

    async _tryRefresh() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return null;

        // Dedup concurrent refresh attempts
        if (this._refreshing) return this._refreshing;
        this._refreshing = (async () => {
            try {
                const res = await fetch('/api/auth/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Refresh-Token': refreshToken,
                    },
                });
                const json = await res.json();
                if (json.status === 'ok' && json.data?.access_token) {
                    localStorage.setItem('access_token', json.data.access_token);
                    if (json.data.refresh_token) {
                        localStorage.setItem('refresh_token', json.data.refresh_token);
                    }
                    return json.data.access_token;
                }
                return null;
            } catch {
                return null;
            } finally {
                this._refreshing = null;
            }
        })();
        return this._refreshing;
    },

    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    put(path, body) { return this.request('PUT', path, body); },
    patch(path, body) { return this.request('PATCH', path, body); },
    del(path) { return this.request('DELETE', path); },
};

// Database Icons — Clean monogram-in-circle style (Linear/Vercel inspired)
// Used in Sources, Destinations, Pipeline Detail, Dashboard
window.getDbIcon = function(type, size = 20) {
  const s = size;
  const icons = {
    postgresql: { bg: '#336791', text: '#ffffff', mono: 'PG' },
    postgres:   { bg: '#336791', text: '#ffffff', mono: 'PG' },
    mysql:      { bg: '#00758F', text: '#ffffff', mono: 'MY' },
    mariadb:    { bg: '#A1664A', text: '#ffffff', mono: 'MA' },
    mongodb:    { bg: '#47A248', text: '#ffffff', mono: 'MO' },
    clickhouse: { bg: '#FCC21B', text: '#2d2d2d', mono: 'CH' },
    default:    { bg: '#6B7280', text: '#ffffff', mono: 'DB' },
  };
  const ic = icons[type] || icons.default;

  return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none">
    <rect x="1" y="1" rx="6" width="22" height="22" fill="${ic.bg}"/>
    <text x="12" y="17" text-anchor="middle" fill="${ic.text}" font-size="10" font-weight="700" font-family="Inter, system-ui, -apple-system, sans-serif" letter-spacing="-0.5">${ic.mono}</text>
  </svg>`;
};
