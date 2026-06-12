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
