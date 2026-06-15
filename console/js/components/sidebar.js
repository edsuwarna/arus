/* Sidebar Component - Mockup-Aligned */
function renderSidebar(user) {
  const name = user?.name || 'User';
  const email = user?.email || '';
  const initials = name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'U';
  const role = user?.role || 'admin';
  const roleLabels = { admin: 'Admin', editor: 'Editor', viewer: 'Viewer' };
  const roleLabel = roleLabels[role] || role;
  const isAdmin = role === 'admin';
  const hash = location.hash.slice(1) || 'dashboard';

  // Badge counts (updated by page renders)
  const badges = window._arusBadges || {};

  const navItems = [
    { section: 'Overview' },
    { label: 'Dashboard', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/></svg>`, page: 'dashboard', badge: null },
    { section: 'Connect' },
    { label: 'Sources', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`, page: 'sources', badge: badges.sources },
    { label: 'Destinations', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`, page: 'destinations', badge: badges.destinations },
    { section: 'Orchestrate' },
    { label: 'Pipelines', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M15 6l6 6-6 6"/><path d="M9 18l-6-6 6-6"/></svg>`, page: 'pipelines', badge: badges.pipelines },
    { label: 'Run History', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`, page: 'runs', badge: null },
    { label: 'DAG View', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="12" r="3"/><circle cx="6" cy="18" r="3"/><path d="M9 6l6 6"/><path d="M9 18l6-6"/></svg>`, page: 'dag', badge: badges.dag },
    { section: 'Monitor' },
    { label: 'Notifications', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`, page: 'notifications', badge: null },
  ];

  // Only admin can see Configure section
  if (isAdmin) {
    navItems.push({ section: 'Configure' });
    navItems.push({ label: 'Users', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`, page: 'users', badge: null });
    navItems.push({ label: 'Settings', icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`, page: 'settings', badge: null });
  }

  const currentPage = hash.startsWith('pipeline/') ? 'pipelines' : hash;

  let navHtml = '';
  navItems.forEach(item => {
    if (item.section) {
      navHtml += `<div class="nav-label">${item.section}</div>`;
    } else {
      const isActive = currentPage === item.page;
      const badgeHtml = item.badge != null
        ? `<span class="badge-count ${item.badge > 0 ? 'green' : ''}">${item.badge}</span>`
        : '';
      navHtml += `<a class="nav-item ${isActive ? 'active' : ''}" onclick="App.navigate('${item.page}')" data-page="${item.page}">
        <span class="nav-icon">${item.icon}</span> ${item.label} ${badgeHtml}
      </a>`;
    }
  });

  return `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-logo">
        <span class="logo-icon" style="width:28px;height:28px;background:linear-gradient(135deg,#eab308,#ca8a04);border-radius:7px;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;color:#fff;flex-shrink:0;">Ar</span>
        <span>Ar<em>us</em></span>
      </div>
      <nav class="sidebar-nav">${navHtml}</nav>
      <div class="sidebar-footer">
        <div class="avatar">${initials}</div>
        <div class="user-info">
          <div class="name">${name}</div>
          <div class="role">${roleLabel}</div>
        </div>
        <button class="logout-btn" onclick="App.logout()" title="Sign out">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        </button>
      </div>
    </aside>
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="App.closeSidebar()"></div>
  `;
}