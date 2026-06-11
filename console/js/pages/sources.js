/* Sources Page — Mockup Card Grid + Discovered Tables */
async function renderSourcesPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading sources...</p></div>`;

  try {
    const sourcesData = await API.get('/sources');
    const sources = Array.isArray(sourcesData?.data) ? sourcesData.data : (Array.isArray(sourcesData) ? sourcesData : []);
    const totalTables = sources.reduce((sum, s) => sum + (s.table_count || s.enabled_table_count || 0), 0);

    // Update badges
    window._arusBadges.sources = sources.length;
    if (window.App?.updateBadges) App.updateBadges();

    // Get discovered tables from first source or selected source
    let discoveredSource = null;
    let discoveredTables = [];
    if (sources.length > 0) {
      try {
        const disc = await API.get(`/sources/${sources[0].id}/tables`).catch(() => null);
        if (disc?.data) {
          discoveredSource = sources[0];
          discoveredTables = Array.isArray(disc.data) ? disc.data : (disc.data.tables || []);
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
          <button class="btn btn-secondary btn-sm" onclick="rescanAllSources()">⟳ Rescan All</button>
          <button class="btn btn-primary btn-sm" onclick="showAddSourceModal()">+ Add Source</button>
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
              <tr><th style="width:24px;"><input type="checkbox" onchange="toggleAllTables(this)" style="accent-color:var(--emerald);"></th><th>Table</th><th>Rows</th><th>Sync Mode</th><th>Last Sync</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${discoveredTables.length > 0
                ? discoveredTables.map(t => renderDiscoveredRow(t)).join('')
                : `<tr><td colspan="6" style="text-align:center;color:var(--text-tertiary);padding:20px;">No tables discovered. Run a scan.</td></tr>`
              }
            </tbody>
          </table>
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
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error loading sources</h3><p>${err.message}</p></div>`;
  }
}

function renderSourceCard(src) {
  const type = src.type || 'postgresql';
  const iconType = type === 'postgresql' || type === 'pg' ? 'postgres'
    : type === 'mysql' || type === 'mariadb' ? 'mysql'
    : 'postgres';
  const iconLabel = type === 'postgresql' ? 'Pg'
    : type === 'mysql' ? 'SQL'
    : type === 'mariadb' ? 'Ma'
    : type === 'clickhouse' ? 'Ch'
    : type === 'mongodb' ? 'Mo'
    : type.slice(0, 2).toUpperCase();
  const statusDot = src.status === 'connected' || src.status === 'active' ? 'green' : (src.status === 'error' ? 'red' : 'amber');
  const tableCount = src.table_count || src.enabled_table_count || 0;
  const syncInterval = src.sync_interval || src.schedule || '5m';

  return `
    <div class="source-card" onclick="selectSource('${src.id}')">
      <div class="sc-top">
        <div class="sc-icon ${iconType}">${iconLabel}</div>
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

  return `
    <tr>
      <td><input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleTable('${table.name}', this.checked)" style="accent-color:var(--emerald);"></td>
      <td><span style="font-weight:500;color:var(--text-primary);">${table.name}</span></td>
      <td class="font-mono">${numberFormat(rows)}</td>
      <td><span class="tag ${syncTag}">${syncMode === 'incremental' ? 'Incremental' : 'Full Refresh'}</span></td>
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
  App.render();
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
        <button class="btn btn-secondary" onclick="editSource('${sourceId}')">✏ Edit</button>
        <button class="btn btn-danger" onclick="deleteSource('${sourceId}')">🗑 Delete</button>
      </div>
    </div>
  `);
}

async function testSource(id) {
  try {
    const result = await API.post(`/sources/${id}/test`);
    const connected = result?.data?.connected !== false;
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

function editSource(id) {
  App.closeModal();
  App.toast('Edit source feature coming soon', 'info');
}

function toggleAllTables(checkbox) {
  document.querySelectorAll('.table-wrap table tbody input[type="checkbox"]').forEach(cb => {
    cb.checked = checkbox.checked;
  });
}

function toggleTable(tableName, enabled) {
  // Could send update to API
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
          <select id="srcType">
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
        <div class="form-group">
          <label>Host</label>
          <input type="text" id="srcHost" placeholder="host.internal:5432" value="localhost:5432">
        </div>
        <div class="form-row">
          <div class="form-group">
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

async function handleAddSource(event) {
  event.preventDefault();
  const data = {
    name: document.getElementById('srcName').value,
    type: document.getElementById('srcType').value,
    host: document.getElementById('srcHost').value.split(':')[0] || 'localhost',
    port: parseInt(document.getElementById('srcPort').value) || 5432,
    database: document.getElementById('srcDatabase').value,
    username: document.getElementById('srcUser').value,
    password: document.getElementById('srcPassword').value,
    sync_method: document.getElementById('srcSync').value,
  };

  try {
    const result = await API.post('/sources', data);
    App.closeModal();
    App.toast('Source added! Discovering tables...', 'success');
    // Trigger discover
    if (result?.data?.id) {
      API.post(`/sources/${result.data.id}/discover`).catch(() => {});
    }
    setTimeout(() => App.render(), 500);
  } catch (err) {
    App.toast(err.message, 'error');
  }
  return false;
}

// Expose globals
window.showAddSourceModal = showAddSourceModal;
window.handleAddSource = handleAddSource;
window.rescanAllSources = rescanAllSources;
window.selectSource = selectSource;
window.showSourceManage = showSourceManage;
window.testSource = testSource;
window.deleteSource = deleteSource;
window.editSource = editSource;
window.toggleAllTables = toggleAllTables;
window.toggleTable = toggleTable;
