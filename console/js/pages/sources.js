/* Sources Page — Mockup Card Grid + Discovered Tables */
async function renderSourcesPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading sources...</p></div>`;

  try {
    const resp = await API.get('/sources');
    const sources = resp?.sources || [];
    const totalTables = sources.reduce((sum, s) => sum + (s.table_count || s.enabled_table_count || 0), 0);

    // Update badges
    window._arusBadges.sources = sources.length;
    if (window.App?.updateBadges) App.updateBadges();

    // Get discovered tables from selected source
    let discoveredSource = null;
    let discoveredTables = [];
    let selectedSourceId = getState('selectedSourceId');
    if (!selectedSourceId && sources.length > 0) {
      selectedSourceId = sources[0].id;
    }

    if (selectedSourceId) {
      try {
        const disc = await API.post(`/sources/${selectedSourceId}/discover`).catch(() => null);
        if (disc?.tables) {
          discoveredSource = sources.find(s => s.id === selectedSourceId) || sources[0];
          discoveredTables = Array.isArray(disc.tables) ? disc.tables : [];
        }
      } catch {}
    }

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Sources</h1>
          <div class="subtitle">${sources.length} data sources · ${totalTables} tables auto-discovered</div>
        </div>
        <div class="header-actions-right">
          ${App.canWrite() ? `
          <button class="btn btn-secondary btn-sm" onclick="rescanAllSources()">⟳ Rescan All</button>
          <button class="btn btn-primary btn-sm" onclick="showAddSourceModal()">+ Add Source</button>
          ` : ''}
        </div>
      </div>

      <div class="source-grid">
        ${sources.length > 0
          ? sources.map(src => renderSourceCard(src)).join('')
          : `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🗄️</div><h3>No sources yet</h3><p>Add your first data source to get started.</p><button class="btn btn-primary" onclick="showAddSourceModal()">+ Add Source</button></div>`
        }
      </div>

      ${discoveredSource ? `
      <div class="card mt-4">
        <div class="card-header">
          <h3>Discovered Tables — ${discoveredSource.name || 'Source'}</h3>
          <span class="text-tertiary text-sm">${discoveredTables.length} tables</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th style="width:24px;"><input type="checkbox" onchange="toggleAllTables(this)" style="accent-color:var(--emerald);"></th><th>Table</th><th>Rows</th><th>Sync Mode</th><th>Load Mode</th><th>Last Sync</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${discoveredTables.length > 0
                ? discoveredTables.map(t => renderDiscoveredRow(t)).join('')
                : `<tr><td colspan="7" style="text-align:center;color:var(--text-tertiary);padding:20px;">No tables discovered. Run a scan.</td></tr>`
              }
            </tbody>
          </table>
        </div>
        <div style="display:flex;justify-content:flex-end;padding:12px 16px;border-top:1px solid var(--border);gap:8px">
          ${App.canWrite() ? `
          <button class="btn btn-secondary btn-sm" onclick="rescanSource('${discoveredSource.id}')">⟳ Rescan</button>
          <button class="btn btn-primary btn-sm" onclick="saveTableSelection('${discoveredSource.id}')">💾 Save Table Selection</button>
          ` : ''}
        </div>
      </div>
      ` : sources.length > 0 ? `
      <div class="card mt-4">
        <div class="card-header">
          <h3>Discovered Tables</h3>
          <span class="text-tertiary text-sm">Click a source to view tables</span>
        </div>
        <div class="card-body">
          <p style="color:var(--text-tertiary);font-size:13px;">Select a source from the cards above to see its discovered tables.</p>
        </div>
      </div>
      ` : ''}
    `;
  } catch (err) {
    App.renderError(container, err.message, () => App.render());
  }
}

function renderSourceCard(src) {
  const type = src.type || 'postgresql';
  const iconType = type === 'postgresql' || type === 'pg' ? 'postgres'
    : type === 'mariadb' ? 'mariadb'
    : type === 'mysql' ? 'mysql'
    : type === 'clickhouse' ? 'clickhouse'
    : type === 'mongodb' ? 'mongodb'
    : 'postgres';
  const statusDot = src.status === 'connected' || src.status === 'active' ? 'green' : (src.status === 'error' ? 'red' : 'amber');
  const tableCount = src.table_count || src.enabled_table_count || 0;
  const syncInterval = src.sync_interval || src.schedule || '5m';

  return `
    <div class="source-card" onclick="selectSource('${src.id}')">
      <div class="sc-top">
        <div class="sc-icon ${iconType}">${getDbIcon(type, 22)}</div>
        <div>
          <div class="sc-name">${src.name || 'Unnamed Source'}</div>
          <div class="sc-desc">${src.host || 'localhost'}:${src.port || 5432} · ${src.database || '-'}</div>
        </div>
        <span class="status" style="margin-left:auto;"><span class="dot ${statusDot}"></span></span>
      </div>
      <div class="sc-info">
        <span class="tables-count"><strong>${tableCount}</strong> tables</span>
        <span class="text-sm text-tertiary">Sync: ${syncInterval}</span>
        <button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();showSourceManage('${src.id}')">Manage</button>
      </div>
    </div>
  `;
}

function renderDiscoveredRow(table) {
  const syncMode = table.sync_mode || table.detected_sync || 'incremental';
  const isIncremental = syncMode === 'incremental';
  const enabled = table.enabled !== false;
  const statusDot = enabled ? 'green' : 'gray';
  const statusLabel = enabled ? 'Synced' : 'Disabled';
  const syncTag = isIncremental ? 'green' : 'purple';
  const rows = table.row_count_estimate || table.row_count || 0;
  const loadMode = table.load_mode || 'direct';

  return `
    <tr>
      <td><input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleTable('${table.name}', this.checked)" style="accent-color:var(--emerald);"></td>
      <td><span style="font-weight:500;color:var(--text-primary);">${table.name}</span></td>
      <td class="font-mono">${numberFormat(rows)}</td>
      <td><span class="tag ${syncTag}">${syncMode === 'incremental' ? 'Incremental' : 'Full Refresh'}</span></td>
      <td>
        <select class="filter-select" style="font-size:11px;padding:3px 6px;min-width:90px;" onchange="setTableLoadMode('${table.name}', this.value)">
          <option value="direct" ${loadMode === 'direct' ? 'selected' : ''}>Direct</option>
          <option value="raw" ${loadMode === 'raw' ? 'selected' : ''}>Raw → Normalize</option>
        </select>
      </td>
      <td class="text-sm">${formatTime(table.last_synced) || '—'}</td>
      <td><span class="status"><span class="dot ${statusDot}"></span><span class="label ${statusDot}">${statusLabel}</span></span></td>
    </tr>
  `;
}

/* ===== SOURCE CRUD ===== */
async function rescanAllSources() {
  try {
    App.toast('Rescanning all sources...', 'info');
    const result = await API.post('/sources/rescan').catch(() => ({ status: 'ok' }));
    App.toast('Rescan initiated', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

function selectSource(sourceId) {
  // Reload with selected source tables
  setState('selectedSourceId', sourceId);
  App.render();
}

async function rescanSource(sourceId) {
  try {
    App.toast('Rescanning source...', 'info');
    await API.post(`/sources/${sourceId}/discover`);
    App.toast('Rescan complete!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

async function saveTableSelection(sourceId) {
  // Collect enabled tables from checkboxes
  const tableRows = document.querySelectorAll('.table-wrap table tbody tr');
  const tables = [];
  tableRows.forEach(row => {
    const checkbox = row.querySelector('input[type="checkbox"]');
    const nameCell = row.querySelector('td:nth-child(2) span');
    const syncCell = row.querySelector('td:nth-child(4) .tag');
    const loadModeSelect = row.querySelector('td:nth-child(5) select');
    if (nameCell && checkbox) {
      tables.push({
        name: nameCell.textContent.trim(),
        enabled: checkbox.checked,
        load_mode: loadModeSelect ? loadModeSelect.value : 'direct',
        detected_sync: syncCell ? syncCell.textContent.toLowerCase().includes('incremental') ? 'incremental' : 'full_refresh' : 'incremental',
      });
    }
  });

  if (tables.length === 0) {
    App.toast('No tables to save', 'info');
    return;
  }

  try {
    const btn = document.querySelector('.btn-primary');
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; btn.style.opacity = '0.6'; }

    await API.put(`/sources/${sourceId}/tables`, { tables });
    App.toast('Table selection saved! Pipeline auto-created/updated.', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = '💾 Save Table Selection'; btn.style.opacity = '1'; }
  }
}

function showSourceManage(sourceId) {
  App.showModal(`
    <div class="modal-header">
      <h2>Manage Source</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px;">Source ID: ${sourceId}</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn btn-secondary" onclick="testSource('${sourceId}')">🔌 Test Connection</button>
        ${App.canWrite() ? `
        <button class="btn btn-secondary" onclick="editSource('${sourceId}')">✏ Edit</button>
        <button class="btn btn-danger" onclick="deleteSource('${sourceId}')">🗑 Delete</button>
        ` : ''}
      </div>
    </div>
  `);
}

async function testSource(id) {
  try {
    const result = await API.post(`/sources/${id}/test`);
    const connected = result?.connected !== false;
    App.toast(connected ? '✅ Connection successful!' : '❌ Connection failed', connected ? 'success' : 'error');
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

async function deleteSource(id) {
  if (!confirm('Delete this source and all associated pipelines?')) return;
  try {
    await API.del(`/sources/${id}`);
    App.toast('Source deleted');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

async function editSource(id) {
  App.closeModal();
  try {
    const res = await API.get(`/sources/${id}`);
    const s = res?.data || {};
    const isMongo = s.type === 'mongodb';
    App.showModal(`
      <div class="modal-header">
        <h2>Edit Source — ${s.name || ''}</h2>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <form id="edit-source-form" onsubmit="submitEditSource(event, '${id}')">
          <div class="form-group">
            <label class="form-label">Name</label>
            <input class="form-input" name="name" value="${s.name || ''}" required />
          </div>
          ${isMongo ? `
          <div class="form-group">
            <label class="form-label">Connection URI</label>
            <input class="form-input" name="uri" value="${s.uri || ''}" placeholder="mongodb://user:pass@host:27017/db" />
          </div>
          <div class="form-group">
            <label class="form-label">Auth Source</label>
            <input class="form-input" name="auth_source" value="${s.auth_source || 'admin'}" />
          </div>
          ` : `
          <div class="form-row">
            <div class="form-group" style="flex:2">
              <label class="form-label">Host</label>
              <input class="form-input" name="host" value="${s.host || 'localhost'}" />
            </div>
            <div class="form-group" style="flex:1">
              <label class="form-label">Port</label>
              <input class="form-input" name="port" type="number" value="${s.port || 5432}" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Database</label>
            <input class="form-input" name="database" value="${s.database || ''}" />
          </div>
          <div class="form-group">
            <label class="form-label">Username</label>
            <input class="form-input" name="username" value="${s.username || ''}" />
          </div>
          <div class="form-group">
            <label class="form-label">Password <span style="color:var(--text-muted);font-size:11px">(leave blank to keep current)</span></label>
            <input class="form-input" name="password" type="password" value="" placeholder="••••••••" />
          </div>
          `}
          <div class="form-group">
            <label class="form-label">Sync Method</label>
            <select class="form-select" name="sync_method">
              <option value="auto" ${s.sync_method === 'auto' ? 'selected' : ''}>Auto-detect</option>
              <option value="full" ${s.sync_method === 'full' ? 'selected' : ''}>Full Refresh</option>
              <option value="incremental" ${s.sync_method === 'incremental' ? 'selected' : ''}>Incremental</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Schema Filter</label>
            <input class="form-input" name="schema_include_str" value="${(s.schema_include || []).join(', ')}" placeholder="public, sales, hr (leave empty for all)" />
            <div class="hint">Comma-separated schema names to sync. Empty = all non-system.</div>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button type="submit" class="btn btn-primary" id="edit-source-btn">💾 Save Changes</button>
          </div>
        </form>
      </div>
    `);
  } catch (err) {
    App.toast('Failed to load source: ' + err.message, 'error');
  }
}

async function submitEditSource(e, id) {
  e.preventDefault();
  const btn = document.getElementById('edit-source-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Saving...'; }
  const form = new FormData(e.target);
  const data = {};
  for (const [k, v] of form.entries()) {
    if (k === 'password' && !v) continue;
    if (k === 'port') { data[k] = parseInt(v) || 5432; continue; }
    if (k === 'schema_include_str') {
      data['schema_include'] = v ? v.split(',').map(s => s.trim()).filter(Boolean) : [];
      continue;
    }
    data[k] = v;
  }
  try {
    await API.put(`/sources/${id}`, data);
    App.toast('✅ Source updated!', 'success');
    App.closeModal();
    App.render();
  } catch (err) {
    App.toast('Update failed: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = '💾 Save Changes'; }
  }
}

function toggleAllTables(checkbox) {
  document.querySelectorAll('.table-wrap table tbody input[type="checkbox"]').forEach(cb => {
    cb.checked = checkbox.checked;
  });
}

function toggleTable(tableName, enabled) {
  // Track toggle state in memory (saved on "Save Table Selection" click)
  window._tableToggleChanged = true;
  window._arusTableToggles = window._arusTableToggles || {};
  window._arusTableToggles[tableName] = enabled;
}

// Track per-table load_mode selection (stored on DOM via select value)
window._tableLoadModes = window._tableLoadModes || {};

function setTableLoadMode(tableName, mode) {
  window._tableLoadModes[tableName] = mode;
}

function showAddSourceModal() {
  const modal = App.showModal(`
    <div class="modal-header">
      <h2>Add Data Source</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form id="addSourceForm" onsubmit="return handleAddSource(event)">
      <div class="modal-body">
        <div class="form-group">
          <label>Source Type</label>
          <select id="srcType" onchange="updateSourceForm()">
            <option value="postgresql">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="mariadb">MariaDB</option>
            <option value="mongodb">MongoDB</option>
            <option value="clickhouse">ClickHouse</option>
          </select>
        </div>
        <div class="form-group">
          <label>Source Name</label>
          <input type="text" id="srcName" placeholder="Production — Database Name" required>
        </div>
        <div class="form-group" id="srcHostGroup">
          <label>Host</label>
          <input type="text" id="srcHost" placeholder="db.internal.example.com">
        </div>
        <div class="form-group" id="srcMongoUriGroup" style="display:none">
          <label>MongoDB URI</label>
          <input type="text" id="srcMongoUri" placeholder="mongodb://user:pass@host:27017/db?authSource=admin">
          <div class="hint">Full connection string — host, port, auth source all in one.</div>
        </div>
        <div class="form-row">
          <div class="form-group" id="srcDatabaseGroup">
            <label>Database</label>
            <input type="text" id="srcDatabase" placeholder="database_name">
          </div>
          <div class="form-group">
            <label>Port</label>
            <input type="number" id="srcPort" value="5432">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Username</label>
            <input type="text" id="srcUser" placeholder="reader">
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="srcPassword">
          </div>
        </div>
        <div class="form-group" id="srcAuthSourceGroup" style="display:none">
          <label>Authentication Database (authSource)</label>
          <input type="text" id="srcAuthSource" placeholder="admin" value="admin">
          <div class="hint">MongoDB authentication database. Usually "admin".</div>
        </div>
        <div class="form-group">
          <label>Sync Method</label>
          <select id="srcSync">
            <option value="auto">Auto-detect (recommended)</option>
            <option value="incremental">Incremental</option>
            <option value="full_refresh">Full Refresh</option>
          </select>
          <div class="hint">Auto-detect scans all tables and selects the best sync mode per table.</div>
        </div>
        <div class="form-group">
          <label>Advanced — Schema Filter</label>
          <input type="text" id="srcSchemas" placeholder="public, sales, hr (leave empty for all)" value="">
          <div class="hint">Comma-separated schema names to sync. Empty = all non-system schemas.</div>
        </div>
        <div class="form-group">
          <label>Advanced — Table Filters</label>
          <input type="text" id="srcFilters" placeholder="+*, -audit_*, -temp_*" value="+*, -audit_*, -temp_*">
          <div class="hint">+ for include, - for exclude. Supports glob patterns.</div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Add Source &amp; Discover →</button>
      </div>
    </form>
  `);
}

// Dynamic source form: adjust fields + port per type
window.updateSourceForm = function() {
  const type = document.getElementById('srcType').value;
  const portInput = document.getElementById('srcPort');
  const hostGroup = document.getElementById('srcHostGroup');
  const mongoUriGroup = document.getElementById('srcMongoUriGroup');
  const dbGroup = document.getElementById('srcDatabaseGroup');
  const authGroup = document.getElementById('srcAuthSourceGroup');

  const ports = { postgresql: 5432, mysql: 3306, mariadb: 3306, mongodb: 27017, clickhouse: 8123 };
  portInput.value = ports[type] || 5432;

  if (type === 'mongodb') {
    hostGroup.style.display = 'none';
    mongoUriGroup.style.display = '';
    dbGroup.style.display = 'none';
    authGroup.style.display = '';
  } else {
    hostGroup.style.display = '';
    mongoUriGroup.style.display = 'none';
    dbGroup.style.display = '';
    authGroup.style.display = 'none';
  }
};

async function handleAddSource(event) {
  event.preventDefault();
  const type = document.getElementById('srcType').value;
  let data;

  if (type === 'mongodb') {
    const uri = document.getElementById('srcMongoUri').value;
    data = {
      name: document.getElementById('srcName').value,
      type: 'mongodb',
      uri: uri,
      host: 'localhost',
      port: 27017,
      database: '',
      username: '',
      password: '',
      auth_source: document.getElementById('srcAuthSource').value || 'admin',
      sync_method: document.getElementById('srcSync').value,
    };
  } else {
    data = {
      name: document.getElementById('srcName').value,
      type: type,
      host: document.getElementById('srcHost').value || 'localhost',
      port: parseInt(document.getElementById('srcPort').value) || 5432,
      database: document.getElementById('srcDatabase').value,
      username: document.getElementById('srcUser').value,
      password: document.getElementById('srcPassword').value,
      sync_method: document.getElementById('srcSync').value,
      schema_include: (document.getElementById('srcSchemas').value || '').split(',').map(s => s.trim()).filter(Boolean),
    };
  }

  // Parse table filter input
  const filterVal = (document.getElementById('srcFilters')?.value || '').trim();
  if (filterVal) {
    const filters = filterVal.split(',').map(s => s.trim()).filter(Boolean);
    const include = filters.filter(f => !f.startsWith('-')).map(f => f.replace(/^\+/, ''));
    const exclude = filters.filter(f => f.startsWith('-')).map(f => f.slice(1));
    if (include.length > 0) data.table_include = include;
    if (exclude.length > 0) data.table_exclude = exclude;
  }

  try {
    const result = await API.post('/sources', data);
    App.closeModal();
    App.toast('Source added! Discovering tables...', 'success');
    // Trigger discover
    if (result?.id) {
      API.post(`/sources/${result.id}/discover`).catch(() => {});
    }
    setTimeout(() => {
      setState('selectedSourceId', result?.id || '');
      App.render();
    }, 500);
  } catch (err) {
    App.toast(err.message, 'error');
  }
  return false;
}

// Expose globals
window.showAddSourceModal = showAddSourceModal;
window.handleAddSource = handleAddSource;
window.rescanAllSources = rescanAllSources;
window.rescanSource = rescanSource;
window.saveTableSelection = saveTableSelection;
window.selectSource = selectSource;
window.showSourceManage = showSourceManage;
window.testSource = testSource;
window.deleteSource = deleteSource;
window.editSource = editSource;
window.submitEditSource = submitEditSource;
window.toggleAllTables = toggleAllTables;
window.toggleTable = toggleTable;
window.setTableLoadMode = setTableLoadMode;
