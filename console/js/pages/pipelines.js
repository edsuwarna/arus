/* Destinations, Pipelines & Settings Pages — Mockup-Aligned */

/* ===== DESTINATIONS ===== */
async function renderDestinationsPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading destinations...</p></div>`;

  try {
    const resp = await API.get('/destinations');
    const destinations = Array.isArray(resp?.data) ? resp.data : (Array.isArray(resp) ? resp : []);

    window._arusBadges.destinations = destinations.length;
    if (window.App?.updateBadges) App.updateBadges();

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Destinations</h1>
          <div class="subtitle">Where your data lands — data warehouse & lake</div>
        </div>
        <div class="header-actions-right">
          <button class="btn btn-primary btn-sm" onclick="showAddDestinationModal()">+ Add Destination</button>
        </div>
      </div>

      <div class="source-grid">
        ${destinations.length > 0
          ? destinations.map(d => renderDestCard(d)).join('')
          : `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🎯</div><h3>No destinations configured</h3><p>Add a destination to start syncing data.</p><button class="btn btn-primary" onclick="showAddDestinationModal()">Add Your First Destination</button></div>`
        }
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error</h3><p>${err.message}</p></div>`;
  }
}

function renderDestCard(dest) {
  const type = dest.type || 'postgresql';
  const iconColor = type === 'postgresql' ? 'var(--blue)' : type === 'clickhouse' ? 'var(--amber)' : 'var(--emerald)';
  const iconBg = type === 'postgresql' ? 'var(--blue-dim)' : type === 'clickhouse' ? 'var(--amber-dim)' : 'var(--emerald-dim)';
  const iconLabel = type === 'postgresql' ? 'DW' : type === 'clickhouse' ? 'CH' : type === 'mysql' ? 'SQL' : 'DB';
  const statusDot = dest.status === 'connected' || dest.status === 'active' ? 'green' : 'gray';
  const tablesCount = dest.total_tables || dest.table_count || 0;
  const dataSize = dest.disk_usage_mb ? formatSize(dest.disk_usage_mb) : '-';

  return `
    <div class="source-card">
      <div class="sc-top">
        <div class="sc-icon" style="background:${iconBg};color:${iconColor};">${iconLabel}</div>
        <div>
          <div class="sc-name">${dest.name || 'Unnamed'}</div>
          <div class="sc-desc">${dest.host || '-'}:${dest.port || '-'} · ${dest.database || '-'}</div>
        </div>
        <span class="status" style="margin-left:auto;"><span class="dot ${statusDot}"></span></span>
      </div>
      <div class="sc-info">
        <span class="tables-count"><strong>${tablesCount}</strong> tables synced</span>
        <span class="text-sm text-tertiary">${dataSize}</span>
        <button class="btn btn-ghost btn-xs" onclick="manageDestination('${dest.id}')">Manage</button>
      </div>
    </div>
  `;
}

function formatSize(mb) {
  if (!mb) return '-';
  if (mb >= 1024) return (mb / 1024).toFixed(1) + ' TB';
  if (mb >= 1) return mb.toFixed(0) + ' GB';
  return mb + ' MB';
}

async function manageDestination(id) {
  App.showModal(`
    <div class="modal-header">
      <h2>Manage Destination</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px;">Destination ID: ${id}</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn btn-secondary" onclick="testDestination('${id}')">🔌 Test Connection</button>
        <button class="btn btn-danger" onclick="deleteDestination('${id}')">🗑 Delete</button>
      </div>
    </div>
  `);
}

/* ===== PIPELINES ===== */
async function renderPipelinesPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading pipelines...</p></div>`;

  try {
    const resp = await API.get('/pipelines');
    const pipelines = Array.isArray(resp?.data) ? resp.data : (Array.isArray(resp) ? resp : []);

    const activeCount = pipelines.filter(p => p.status === 'active').length;
    const failingCount = pipelines.filter(p => p.status === 'error' || p.status === 'failed').length;
    const totalRows = pipelines.reduce((sum, p) => sum + (p.total_rows_synced || 0), 0);

    window._arusBadges.pipelines = pipelines.length;
    if (window.App?.updateBadges) App.updateBadges();

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Pipelines</h1>
          <div class="subtitle">${activeCount} active pipelines · ${failingCount} failing · ${numberFormat(totalRows)} rows synced in last 24h</div>
        </div>
        <div class="header-actions-right">
          <button class="btn btn-ghost btn-sm" onclick="pauseAllPipelines()">⏸ Pause All</button>
          <button class="btn btn-primary btn-sm" onclick="showAddPipelineModal()">+ New Pipeline</button>
        </div>
      </div>

      <div class="pipeline-list">
        ${pipelines.length > 0
          ? pipelines.map(p => renderPipelineItem(p)).join('')
          : `<div class="empty-state"><div class="empty-icon">🔄</div><h3>No pipelines yet</h3><p>Add a source and discover tables to auto-create pipelines.</p></div>`
        }
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error</h3><p>${err.message}</p></div>`;
  }
}

function renderPipelineItem(p) {
  const isRunning = p.status === 'active';
  const isDegraded = p.status === 'error' || p.error_count_7d > 0;
  const indicatorColor = isRunning ? (isDegraded ? 'amber' : 'green') : (p.status === 'paused' ? 'amber' : 'gray');
  const statusDot = isRunning ? (isDegraded ? 'amber' : 'green') : (p.status === 'paused' ? 'amber' : 'gray');
  const statusLabel = isRunning ? (isDegraded ? 'Degraded' : 'Running') : (p.status === 'paused' ? 'Paused' : 'Inactive');

  const rowsPerHour = numberFormat(p.rows_per_hour || p.total_rows_synced / Math.max(1, 24) || 0);
  const errors = p.error_count_7d || 0;
  const avgLatency = p.avg_latency_ms ? (p.avg_latency_ms / 1000).toFixed(1) + 's' : '-';
  const tableCount = p.enabled_table_count || p.tables?.length || 0;
  const scheduleLabel = p.schedule_label || p.schedule || 'manual';
  const syncType = p.sync_type || 'incremental';

  return `
    <div class="pipeline-item" onclick="location.hash='pipeline/${p.id}'">
      <div class="pi-indicator ${indicatorColor}"></div>
      <div class="pi-info">
        <div class="pi-name">${p.name || 'Unnamed Pipeline'}</div>
        <div class="pi-meta">${tableCount} tables · ${syncType} · ${scheduleLabel}</div>
      </div>
      <div class="pi-stats">
        <div class="ps-item"><div class="ps-val text-emerald">${rowsPerHour}</div><div class="ps-label">Rows/h</div></div>
        <div class="ps-item"><div class="ps-val">${errors}</div><div class="ps-label">${errors === 1 ? 'Error' : 'Errors'}</div></div>
        <div class="ps-item"><div class="ps-val">${avgLatency}</div><div class="ps-label">Avg</div></div>
      </div>
      <span class="status"><span class="dot ${statusDot}"></span><span class="label ${statusDot}">${statusLabel}</span></span>
    </div>
  `;
}

/* ===== PIPELINE ACTIONS ===== */
async function pauseAllPipelines() {
  try {
    await API.post('/pipelines/pause-all').catch(() => {});
    App.toast('All pipelines paused', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

function showAddPipelineModal() {
  App.showModal(`
    <div class="modal-header">
      <h2>New Pipeline</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--text-tertiary);font-size:13px;">Add a source first, then pipelines are auto-created when you discover tables.</p>
      <div style="margin-top:16px;display:flex;gap:8px;">
        <button class="btn btn-secondary" onclick="App.closeModal();location.hash='sources'">Go to Sources</button>
        <button class="btn btn-primary" onclick="App.closeModal();showAddSourceModal()">+ Add Source</button>
      </div>
    </div>
  `);
}

/* ===== SETTINGS ===== */
async function renderSettingsPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading settings...</p></div>`;

  try {
    const resp = await API.get('/settings');
    const s = resp?.data || {};

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Settings</h1>
          <div class="subtitle">Manage your Arus instance, users, and notifications</div>
        </div>
      </div>

      <div class="settings-group">
        <h3>General</h3>
        <div class="settings-row">
          <div class="sr-label">Pipeline Name Prefix <div class="sr-desc">Prefix added to all auto-generated pipeline names.</div></div>
          <div class="sr-value"><input class="form-input" style="width:180px;padding:6px 10px;font-size:13px;" id="set-prefix" value="${s.pipeline_name_prefix || 'arus-prod-'}"></div>
        </div>
        <div class="settings-row">
          <div class="sr-label">Default Sync Interval <div class="sr-desc">How often pipelines check for changes.</div></div>
          <div class="sr-value">
            <select class="filter-select" id="set-schedule" style="min-width:140px;">
              <option value="*/1 * * * *" ${s.default_schedule === '*/1 * * * *' ? 'selected' : ''}>Every minute</option>
              <option value="*/5 * * * *" ${(!s.default_schedule || s.default_schedule === '*/5 * * * *') ? 'selected' : ''}>Every 5 minutes</option>
              <option value="*/15 * * * *" ${s.default_schedule === '*/15 * * * *' ? 'selected' : ''}>Every 15 minutes</option>
              <option value="0 * * * *" ${s.default_schedule === '0 * * * *' ? 'selected' : ''}>Every hour</option>
              <option value="0 */6 * * *" ${s.default_schedule === '0 */6 * * *' ? 'selected' : ''}>Every 6 hours</option>
            </select>
          </div>
        </div>
        <div class="settings-row">
          <div class="sr-label">Auto-discover New Tables <div class="sr-desc">Automatically detect and sync new tables in registered sources.</div></div>
          <button class="toggle ${s.auto_discover_tables !== 'false' ? 'on' : ''}" id="set-autodiscover" onclick="this.classList.toggle('on')"></button>
        </div>
        <div class="settings-row">
          <div class="sr-label">Schema Drift Detection <div class="sr-desc">Alert when source table schema changes.</div></div>
          <button class="toggle ${s.schema_drift_detection !== 'false' ? 'on' : ''}" id="set-drift" onclick="this.classList.toggle('on')"></button>
        </div>
      </div>

      <div class="settings-group">
        <h3>Quality & Retry</h3>
        <div class="settings-row">
          <div class="sr-label">Max Retries <div class="sr-desc">Number of retry attempts before pipeline run fails.</div></div>
          <div class="sr-value"><input class="form-input" style="width:80px;padding:6px 10px;font-size:13px;" type="number" min="0" max="10" id="set-retries" value="${s.max_retries || '3'}"></div>
        </div>
        <div class="settings-row">
          <div class="sr-label">Quality Check Threshold <div class="sr-desc">Max row count discrepancy (%) before flagging.</div></div>
          <div class="sr-value"><input class="form-input" style="width:80px;padding:6px 10px;font-size:13px;" type="number" min="0" max="100" step="0.5" id="set-quality" value="${s.quality_check_threshold || '5'}"></div>
        </div>
      </div>

      <div class="settings-group">
        <h3>Notifications</h3>
        <div class="settings-row">
          <div class="sr-label">Pipeline Failures <div class="sr-desc">Send alert when a pipeline run fails.</div></div>
          <button class="toggle ${s.notify_pipeline_failures !== 'false' ? 'on' : ''}" id="set-notify-fail" onclick="this.classList.toggle('on')"></button>
        </div>
        <div class="settings-row">
          <div class="sr-label">Schema Drift <div class="sr-desc">Notify when source schema changes detected.</div></div>
          <button class="toggle ${s.notify_schema_drift !== 'false' ? 'on' : ''}" id="set-notify-drift" onclick="this.classList.toggle('on')"></button>
        </div>
        <div class="settings-row">
          <div class="sr-label">Dead Letter Rows <div class="sr-desc">Send alert when rows go to dead letter queue.</div></div>
          <button class="toggle ${s.notify_dead_letter !== 'false' ? 'on' : ''}" id="set-notify-dl" onclick="this.classList.toggle('on')"></button>
        </div>
      </div>

      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px;">
        <button class="btn btn-secondary" onclick="App.render()">Cancel</button>
        <button class="btn btn-primary" onclick="saveSettings()">Save Changes</button>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error</h3><p>${err.message}</p></div>`;
  }
}

async function saveSettings() {
  const getVal = (id) => document.getElementById(id)?.value;
  const isOn = (id) => document.getElementById(id)?.classList.contains('on') ? 'true' : 'false';

  const payload = {
    pipeline_name_prefix: getVal('set-prefix'),
    default_schedule: getVal('set-schedule'),
    auto_discover_tables: isOn('set-autodiscover'),
    schema_drift_detection: isOn('set-drift'),
    max_retries: getVal('set-retries'),
    quality_check_threshold: getVal('set-quality'),
    notify_pipeline_failures: isOn('set-notify-fail'),
    notify_schema_drift: isOn('set-notify-drift'),
    notify_dead_letter: isOn('set-notify-dl'),
  };

  try {
    await API.put('/settings', payload);
    App.toast('Settings saved successfully', 'success');
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

/* ===== DESTINATION CRUD ===== */
function showAddDestinationModal() {
  const modal = App.showModal(`
    <div class="modal-header">
      <h2>Add Destination</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form id="addDestinationForm" onsubmit="return handleAddDest(event)">
      <div class="modal-body">
        <div class="form-group">
          <label>Name</label>
          <input type="text" id="destName" placeholder="Production Warehouse" required>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Type</label>
            <select id="destType">
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="clickhouse">ClickHouse</option>
            </select>
          </div>
          <div class="form-group">
            <label>Port</label>
            <input type="number" id="destPort" value="5432">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Host</label>
            <input type="text" id="destHost" placeholder="warehouse.local">
          </div>
          <div class="form-group">
            <label>Database</label>
            <input type="text" id="destDatabase" placeholder="arus_warehouse">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Username</label>
            <input type="text" id="destUser" placeholder="arus">
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="destPassword">
          </div>
        </div>
        <div class="form-group">
          <label class="form-checkbox">
            <input type="checkbox" id="destDefault"> Set as default destination
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Save & Test Connection</button>
      </div>
    </form>
  `);
}

async function handleAddDest(event) {
  event.preventDefault();
  const data = {
    name: document.getElementById('destName').value,
    type: document.getElementById('destType').value,
    host: document.getElementById('destHost').value,
    port: parseInt(document.getElementById('destPort').value),
    database: document.getElementById('destDatabase').value,
    username: document.getElementById('destUser').value,
    password: document.getElementById('destPassword').value,
    is_default: document.getElementById('destDefault')?.checked || false,
  };
  try {
    await API.post('/destinations', data);
    App.closeModal();
    App.toast('Destination created!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
  return false;
}

async function testDestination(id) {
  try {
    const result = await API.post(`/destinations/${id}/test`);
    const data = result?.data || {};
    App.toast(data.connected ? '✅ Connection successful!' : '❌ Connection failed', data.connected ? 'success' : 'error');
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

async function deleteDestination(id) {
  if (!confirm('Delete this destination and disconnect all associated pipelines?')) return;
  try {
    await API.del(`/destinations/${id}`);
    App.toast('Destination deleted');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

// Globals
window.saveSettings = saveSettings;
window.showAddDestinationModal = showAddDestinationModal;
window.handleAddDest = handleAddDest;
window.testDestination = testDestination;
window.deleteDestination = deleteDestination;
window.manageDestination = manageDestination;
window.pauseAllPipelines = pauseAllPipelines;
window.showAddPipelineModal = showAddPipelineModal;
