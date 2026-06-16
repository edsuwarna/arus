/* Users Page — User Management for Arus Admin */
async function renderUsersPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading users...</p></div>`;

  try {
    const resp = await API.get('/auth/users');
    const users = resp?.users || [];
    window._usersData = users;
    SortUtils.register('users-table', '_usersData', [
      u => (u.name || u.email || '').toLowerCase(),
      u => (u.email || '').toLowerCase(),
      u => u.role || '',
      u => u.is_active ? '0_active' : '1_disabled',
      u => { const d = u.last_login; return d ? new Date(d).getTime() : 0; },
    ], 'renderUsersTbody', 0);
    const adminCount = users.filter(u => u.role === 'admin').length;
    const editorCount = users.filter(u => u.role === 'editor').length;
    const activeCount = users.filter(u => u.is_active).length;

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Users</h1>
          <div class="subtitle">${users.length} users · ${activeCount} active · ${adminCount} admin · ${editorCount} editor</div>
        </div>
        <div class="header-actions-right">
          <button class="btn btn-primary btn-sm" onclick="showAddUserModal()">+ Add User</button>
        </div>
      </div>

      <div class="card">
        <div class="table-wrap">
          <table id="users-table">
            <thead>
              <tr>
                ${SortUtils.th('users-table', 0, 'Name')}
                ${SortUtils.th('users-table', 1, 'Email')}
                ${SortUtils.th('users-table', 2, 'Role')}
                ${SortUtils.th('users-table', 3, 'Status')}
                ${SortUtils.th('users-table', 4, 'Last Login')}
                <th style="width:120px;">Actions</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    `;
    renderUsersTbody();
    SortUtils.reapply("users-table");
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error loading users</h3><p>${err.message}</p></div>`;
  }
}

window.renderUsersTbody = function() {
  const data = window._usersData || [];
  const tbody = document.querySelector('#users-table tbody');
  if (!tbody) return;
  tbody.innerHTML = data.length ? data.map(u => renderUserRow(u)).join('') : '<tr><td colspan="6" style="text-align:center;color:var(--text-tertiary);padding:40px;">No users yet</td></tr>';
};

function renderUserRow(u) {
  const roleTag = u.role === 'admin' ? 'green' : u.role === 'editor' ? 'purple' : 'blue';
  const statusDot = u.is_active ? 'green' : 'gray';
  const statusLabel = u.is_active ? 'Active' : 'Disabled';
  const initials = (u.name || u.email).split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();

  return `
    <tr>
      <td>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="width:32px;height:32px;border-radius:8px;background:var(--bg-tertiary);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:var(--text-secondary);">${initials}</span>
          <span style="font-weight:500;color:var(--text-primary);">${u.name || '—'}</span>
        </div>
      </td>
      <td style="color:var(--text-secondary);">${u.email}</td>
      <td><span class="tag ${roleTag}">${u.role}</span></td>
      <td><span class="status"><span class="dot ${statusDot}"></span><span class="label ${statusDot}">${statusLabel}</span></span></td>
      <td class="text-sm text-tertiary">${u.last_login ? timeAgo(u.last_login) : 'Never'}</td>
      <td>
        <div style="display:flex;gap:6px;">
          <button class="btn btn-ghost btn-xs" onclick="showEditUserModal('${u.id}','${u.name.replace(/'/g, "\\'")}','${u.email}','${u.role}','${u.is_active}')" title="Edit user">✏</button>
          ${u.role !== 'admin' || u.email !== App.user?.email ? `
          <button class="btn btn-ghost btn-xs" onclick="deleteUser('${u.id}')" title="Delete user" style="color:var(--red);">✕</button>
          ` : '<span style="font-size:11px;color:var(--text-tertiary);">You</span>'}
        </div>
      </td>
    </tr>
  `;
}

/* ===== CREATE USER ===== */
function showAddUserModal() {
  App.showModal(`
    <div class="modal-header">
      <h2>Add User</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form onsubmit="return handleCreateUser(event)">
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Name</label>
          <input class="form-input" id="newUserName" placeholder="John Doe" required />
        </div>
        <div class="form-group">
          <label class="form-label">Email</label>
          <input class="form-input" id="newUserEmail" type="email" placeholder="user@company.com" required />
        </div>
        <div class="form-group">
          <label class="form-label">Password</label>
          <input class="form-input" id="newUserPassword" type="password" placeholder="••••••••" required />
        </div>
        <div class="form-group">
          <label class="form-label">Role</label>
          <select class="form-select" id="newUserRole">
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Create User</button>
      </div>
    </form>
  `);
}

async function handleCreateUser(event) {
  event.preventDefault();
  const btn = event.target.querySelector('button[type="submit"]');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Creating...'; }

  try {
    await API.post('/auth/users', {
      name: document.getElementById('newUserName').value,
      email: document.getElementById('newUserEmail').value,
      password: document.getElementById('newUserPassword').value,
      role: document.getElementById('newUserRole').value,
    });
    App.closeModal();
    App.toast('✅ User created!', 'success');
    App.render();
  } catch (err) {
    App.toast('Failed: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Create User'; }
  }
  return false;
}

/* ===== EDIT USER ===== */
function showEditUserModal(id, name, email, role, isActive) {
  const activeBool = isActive === 'true' || isActive === true;
  App.showModal(`
    <div class="modal-header">
      <h2>Edit User</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form onsubmit="return handleEditUser(event, '${id}')">
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Name</label>
          <input class="form-input" id="editUserName" value="${name || ''}" required />
        </div>
        <div class="form-group">
          <label class="form-label">Email</label>
          <input class="form-input" id="editUserEmail" type="email" value="${email || ''}" required />
        </div>
        <div class="form-group">
          <label class="form-label">Role</label>
          <select class="form-select" id="editUserRole">
            <option value="viewer" ${role === 'viewer' ? 'selected' : ''}>Viewer</option>
            <option value="editor" ${role === 'editor' ? 'selected' : ''}>Editor</option>
            <option value="admin" ${role === 'admin' ? 'selected' : ''}>Admin</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-checkbox" style="display:flex;align-items:center;gap:10px;cursor:pointer;padding:8px 0;">
            <input type="checkbox" id="editUserActive" ${activeBool ? 'checked' : ''} style="accent-color:var(--emerald);width:18px;height:18px;">
            <span style="font-size:13px;color:var(--text-secondary);">Account active</span>
          </label>
        </div>
        <div class="form-group">
          <label class="form-label">New Password <span style="color:var(--text-tertiary);font-weight:400;font-size:11px;">(leave empty to keep current)</span></label>
          <input class="form-input" id="editUserPassword" type="password" placeholder="••••••••" />
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">💾 Save</button>
      </div>
    </form>
  `);
}

async function handleEditUser(event, id) {
  event.preventDefault();
  const btn = event.target.querySelector('button[type="submit"]');
  if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }

  const data = {
    name: document.getElementById('editUserName').value,
    email: document.getElementById('editUserEmail').value,
    role: document.getElementById('editUserRole').value,
    is_active: document.getElementById('editUserActive').checked,
  };
  const pw = document.getElementById('editUserPassword').value;
  if (pw) data.password = pw;

  try {
    await API.put(`/auth/users/${id}`, data);
    App.closeModal();
    App.toast('✅ User updated!', 'success');
    App.render();
  } catch (err) {
    App.toast('Failed: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Save'; }
  }
  return false;
}

/* ===== DELETE USER ===== */
async function deleteUser(id) {
  App.showModal(`
    <div class="modal-header">
      <h2>Confirmation</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px;">Delete this user? This cannot be undone.</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button class="btn btn-danger" id="confirmDeleteUser">Confirm</button>
      </div>
    </div>
  `);
  document.getElementById('confirmDeleteUser').addEventListener('click', async () => {
    App.closeModal();
    try {
      await API.del(`/auth/users/${id}`);
      App.toast('User deleted', 'info');
      App.render();
    } catch (err) {
      App.toast('Failed: ' + err.message, 'error');
    }
  });
}

// Globals
window.renderUsersPage = renderUsersPage;
window.showAddUserModal = showAddUserModal;
window.handleCreateUser = handleCreateUser;
window.showEditUserModal = showEditUserModal;
window.handleEditUser = handleEditUser;
window.deleteUser = deleteUser;
