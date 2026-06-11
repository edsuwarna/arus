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
  settings: 'Settings',
};

const App = {
  user: null,
  currentHash: '',

  async init() {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        this.user = await API.get('/auth/me');
      } catch {
        localStorage.removeItem('token');
      }
    }
    this.render();
    window.addEventListener('hashchange', () => this.render());
  },

  navigate(page) {
    location.hash = page;
    this.closeSidebar();
  },

  render() {
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
    this.renderPage(hash);
    this.updateBadges();
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

  renderPage(hash) {
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

    switch (hash) {
      case 'dashboard': renderDashboardPage(content); break;
      case 'sources': renderSourcesPage(content); break;
      case 'destinations': renderDestinationsPage(content); break;
      case 'pipelines': renderPipelinesPage(content); break;
      case 'runs': renderRunsPage(content); break;
      case 'dag': renderDagPage(content); break;
      case 'settings': renderSettingsPage(content); break;
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
      if (hash === page || (hash.startsWith('pipeline/') && page === 'runs')) {
        el.classList.add('active');
      }
    });
  },

  logout() {
    localStorage.removeItem('token');
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
