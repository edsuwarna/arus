/* App - SPA Router + State + Header */
const _state = {};
function getState(key) { return _state[key] || ''; }
function setState(key, val) { _state[key] = val; }

// Global badge counts - set by page renders
window._arusBadges = { sources: 0, destinations: 0, pipelines: 0, dag: 0 };

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  sources: 'Sources',
  destinations: 'Destinations',
  pipelines: 'Pipelines',
  runs: 'Run History',
  dag: 'DAG View',
  users: 'Users',
  settings: 'Settings',
  notifications: 'Notifications',
};

// Global helper: check current user role
const App = {
  user: null,
  currentHash: '',

  isAdmin() { return this.user?.role === 'admin'; },
  isEditor() { return this.user?.role === 'editor'; },
  canWrite() { return this.user?.role === 'admin' || this.user?.role === 'editor'; },

  async init() {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        this.user = await API.get('/auth/me');
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    }
    this.render();
    this.loadBadges(); // fetch badges independent of current page
    window.addEventListener('hashchange', () => this.render());
  },

  async loadBadges() {
    try {
      const resp = await API.get('/dashboard/summary');
      const s = resp?.data || resp || {};
      window._arusBadges.sources = s.total_sources || 0;
      window._arusBadges.destinations = s.total_destinations || 0;
      const pipelines = s.total_pipelines || s.active_pipelines || 0;
      window._arusBadges.pipelines = pipelines;
      window._arusBadges.dag = pipelines;
      this.updateBadges();
    } catch(e) {
      // silent — badges stay at 0 until user visits Dashboard
    }
  },

  navigate(page) {
    location.hash = page;
    this.closeSidebar();
  },

  async render() {
    this.closeModal();
    this.closeSidebar();
    const hash = location.hash.slice(1) || 'dashboard';

    if (!this.user && hash !== 'login') {
      location.hash = 'login';
      return;
    }

    const appEl = document.getElementById('app');

    if (hash === 'login') {
      appEl.innerHTML = renderLogin();
      return;
    }

    const pageTitle = hash.startsWith('pipeline/') ? 'Pipeline Detail'
      : PAGE_TITLES[hash] || 'Dashboard';

    appEl.innerHTML = `
      <div class="layout">
        ${renderSidebar(this.user)}
        <div class="main">
          <header class="header">
            <button class="mobile-toggle" id="mobileToggle" onclick="App.toggleSidebar()">☰</button>
            <div class="header-breadcrumb">
              <span>Arus</span>
              <span class="sep">▶</span>
              <span class="current" id="breadcrumbCurrent">${pageTitle}</span>
            </div>
            <div class="header-search">
              <span class="icon">⌕</span>
              <input type="text" placeholder="Search sources, pipelines..." />
            </div>
            <div class="header-actions">
              <button class="btn-icon" title="Notifications" onclick="App.toast('No new notifications', 'info')">🔔</button>
              <button class="btn-icon" title="Help" onclick="App.toast('Arus Documentation v1.0', 'info')">?</button>
              <button class="btn-icon logout-icon" title="Sign out" onclick="App.logout()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
              </button>
            </div>
          </header>
          <div class="content" id="content">
            <div class="loading"><div class="spinner"></div><p>Loading...</p></div>
          </div>
        </div>
      </div>
    `;

    this.currentHash = hash;
    await this.renderPage(hash);
    this.updateBadges();
    this.loadBadges();
  },

  updateBadges() {
    // Update sidebar badge elements
    document.querySelectorAll('.badge-count').forEach(el => {
      const parent = el.closest('.nav-item');
      if (!parent) return;
      const page = parent.dataset.page;
      if (page && window._arusBadges[page] != null) {
        const count = window._arusBadges[page];
        el.textContent = count;
        el.className = 'badge-count' + (count > 0 ? ' green' : '');
      }
    });
  },

  async renderPage(hash) {
    const content = document.getElementById('content');
    if (!content) return;

    // Update breadcrumb
    const bc = document.getElementById('breadcrumbCurrent');
    if (bc) {
      bc.textContent = hash.startsWith('pipeline/') ? 'Pipeline Detail'
        : PAGE_TITLES[hash] || 'Dashboard';
    }

    if (hash.startsWith('pipeline/')) {
      const id = hash.split('/')[1];
      renderPipelineDetailPage(content, id);
      return;
    }

    // Role-based route guard
    if (hash === 'users' || hash === 'settings') {
      if (!this.isAdmin()) {
        content.innerHTML = `<div class="empty-state"><div class="empty-icon">🚫</div><h3>Access Denied</h3><p>You don't have permission to access this page.</p></div>`;
        return;
      }
    }

    switch (hash) {
      case 'dashboard': await renderDashboardPage(content); break;
      case 'sources': await renderSourcesPage(content); break;
      case 'destinations': await renderDestinationsPage(content); break;
      case 'pipelines': await renderPipelinesPage(content); break;
      case 'runs': await renderRunsPage(content); break;
      case 'dag': await renderDagPage(content); break;
      case 'users': await renderUsersPage(content); break;
      case 'settings': await renderSettingsPage(content); break;
      case 'notifications': await renderNotificationsPage(content); break;
      default:
        content.innerHTML = '<div class="empty-state"><div class="empty-icon">🚧</div><h3>Page not found</h3><p>The page you\'re looking for doesn\'t exist.</p></div>';
    }

    // Highlight active sidebar item
    this.highlightSidebar(hash);
  },

  highlightSidebar(hash) {
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.remove('active');
      const page = el.dataset.page;
      if (hash === page || (hash.startsWith('pipeline/') && page === 'pipelines')) {
        el.classList.add('active');
      }
    });
  },

  logout() {
    // Call backend logout (fire and forget — JWT is stateless)
    API.post('/auth/logout').catch(() => {});
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.user = null;
    location.hash = 'login';
    this.render();
  },

  toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) {
      sidebar.classList.toggle('open');
      if (overlay) overlay.classList.toggle('active');
    }
  },

  closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
  },

  toast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  },

  closeModal() {
    const overlay = document.querySelector('.modal-overlay');
    if (overlay) overlay.remove();
  },

  renderError(container, message, retryFn) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <h3>Something went wrong</h3>
        <p style="color:var(--text-tertiary);font-size:13px;margin-bottom:16px;">${message}</p>
        ${retryFn ? `<button class="btn btn-primary btn-sm" onclick="App.render()">⟳ Retry</button>` : ''}
      </div>
    `;
  },

  showModal(html) {
    App.closeModal();
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `<div class="modal">${html}</div>`;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });
    document.body.appendChild(overlay);
    return overlay.querySelector('.modal');
  },
};

// Utility functions
function formatTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return diffMin + ' min ago';
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return diffHr + 'h ago';
  return d.toLocaleDateString();
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-';
  if (ms < 1000) return ms + 'ms';
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
  return Math.floor(ms / 60000) + 'm ' + Math.floor((ms % 60000) / 1000) + 's';
}

function numberFormat(n) {
  if (!n && n !== 0) return '0';
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toLocaleString();
}

function timeAgo(dateStr) {
  return formatTime(dateStr);
}

document.addEventListener('DOMContentLoaded', () => App.init());
