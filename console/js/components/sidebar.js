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
    { label: 'Dashboard', icon: '◷', page: 'dashboard', badge: null },
    { section: 'Connect' },
    { label: 'Sources', icon: '⎔', page: 'sources', badge: badges.sources },
    { label: 'Destinations', icon: '▣', page: 'destinations', badge: badges.destinations },
    { section: 'Orchestrate' },
    { label: 'Pipelines', icon: '⇌', page: 'pipelines', badge: badges.pipelines },
    { label: 'Run History', icon: '⊞', page: 'runs', badge: null },
    { label: 'DAG View', icon: '⟐', page: 'dag', badge: badges.dag },
    { section: 'Monitor' },
    { label: 'Notifications', icon: '🔔', page: 'notifications', badge: null },
  ];

  // Only admin can see Configure section
  if (isAdmin) {
    navItems.push({ section: 'Configure' });
    navItems.push({ label: 'Users', icon: '👥', page: 'users', badge: null });
    navItems.push({ label: 'Settings', icon: '⚙', page: 'settings', badge: null });
  }

  const currentPage = hash.startsWith('pipeline/') ? 'runs' : hash;

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
        <span class="logo-icon">Ar</span>
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
