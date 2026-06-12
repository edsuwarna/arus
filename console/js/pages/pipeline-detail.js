/* Pipeline Detail Page — Mockup-Aligned */
async function renderPipelineDetailPage(container, pipelineId) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading pipeline detail...</p></div>`;

  try {
    const [pipelineData, runsData] = await Promise.all([
      API.get('/pipelines/' + pipelineId),
      API.get('/pipelines/' + pipelineId + '/runs?limit=50'),
    ]);

    const p = pipelineData || {};
    const runs = runsData || [];

    const statusColor = p.status === 'active' ? 'success' : p.status === 'paused' ? 'warning' : 'muted';
    const srcType = p.source?.type || '?';
    const destType = p.destination?.type || '?';
    const srcName = p.source?.name || 'Unknown';
    const destName = p.destination?.name || 'Unknown';
    const isRunning = p.status === 'active';
    const runStatus = isRunning ? (p.stats?.failed_runs > 0 ? 'Degraded' : 'Running') : (p.status === 'paused' ? 'Paused' : 'Inactive');
    const runStatusDot = isRunning ? (p.stats?.failed_runs > 0 ? 'amber' : 'green') : (p.status === 'paused' ? 'amber' : 'gray');
    const totalRows = p.stats?.total_rows_synced || 0;
    const lastSync = runs[0] ? formatTime(runs[0].started_at) : 'Never';
    const scheduleLabel = p.schedule_label || p.schedule || 'manual';

    container.innerHTML = `
      <div class="page-header">
        <div>
          <div class="flex items-center gap-2" style="margin-bottom:4px;">
            <button class="btn btn-ghost btn-xs" onclick="location.hash='pipelines'">← Back to Pipelines</button>
          </div>
          <h1>${p.name || 'Pipeline Detail'}</h1>
          <div class="subtitle">${(p.tables?.length || 0)} tables · ${p.sync_type || 'incremental'} sync from ${srcName} to ${destName} · <span class="tag blue" style="font-size:11px;padding:1px 5px;">→ ${p.target_schema || 'public'}</span> <span class="tag ${(p.load_mode || 'direct') === 'raw' ? 'blue' : 'green'}" style="font-size:11px;padding:1px 5px;">${(p.load_mode || 'direct') === 'raw' ? 'Raw → Normalize' : 'Direct'}</span></div>
        </div>
        <div class="header-actions-right">
          ${App.canWrite() ? `
          <button class="btn btn-secondary btn-sm" onclick="triggerDetailPipeline('${pipelineId}')">⟳ Sync Now</button>
          ${isRunning
            ? `<button class="btn btn-ghost btn-sm" onclick="pauseDetailPipeline('${pipelineId}')">⏸ Pause</button>`
            : `<button class="btn btn-primary btn-sm" onclick="resumeDetailPipeline('${pipelineId}')">▶ Resume</button>`
          }
          <div class="dropdown" style="position:relative;display:inline-block">
            <button class="btn btn-ghost btn-sm" onclick="this.nextElementSibling.classList.toggle('show')">⋯</button>
            <div class="dropdown-menu" style="display:none;position:absolute;right:0;top:100%;z-index:100;background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:4px;min-width:160px;box-shadow:0 8px 24px rgba(0,0,0,0.3);margin-top:4px">
              <button class="dropdown-item" style="display:block;width:100%;padding:8px 12px;font-size:12px;background:none;border:none;color:var(--text-secondary);cursor:pointer;border-radius:4px;text-align:left" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='none'" onclick="this.closest('.dropdown-menu').classList.remove('show');fullRefreshPipeline('${pipelineId}')">🔄 Full Refresh</button>
              <button class="dropdown-item" style="display:block;width:100%;padding:8px 12px;font-size:12px;background:none;border:none;color:var(--text-secondary);cursor:pointer;border-radius:4px;text-align:left" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='none'" onclick="this.closest('.dropdown-menu').classList.remove('show');showBackfillModal('${pipelineId}')">📅 Backfill</button>
              <button class="dropdown-item" style="display:block;width:100%;padding:8px 12px;font-size:12px;background:none;border:none;color:var(--text-secondary);cursor:pointer;border-radius:4px;text-align:left" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='none'" onclick="this.closest('.dropdown-menu').classList.remove('show');showDeadLetters('${pipelineId}')">📦 Dead Letters</button>
              <button class="dropdown-item" style="display:block;width:100%;padding:8px 12px;font-size:12px;background:none;border:none;color:var(--text-secondary);cursor:pointer;border-radius:4px;text-align:left" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='none'" onclick="this.closest('.dropdown-menu').classList.remove('show');showPipelineNotifConfig('${pipelineId}','${p.name}')">🔔 Notifications</button>
              <button class="dropdown-item" style="display:block;width:100%;padding:8px 12px;font-size:12px;background:none;border:none;color:var(--text-secondary);cursor:pointer;border-radius:4px;text-align:left" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='none'" onclick="this.closest('.dropdown-menu').classList.remove('show');showEditConfigModal('${pipelineId}', '${p.name}','${p.target_schema||'public'}','${p.load_mode||'direct'}','${p.schedule||''}','${p.sync_type||'incremental'}')">⚙️ Edit Config</button>
              <div style="border-top:1px solid var(--border);margin:4px 0"></div>
              <button class="dropdown-item" style="display:block;width:100%;padding:8px 12px;font-size:12px;background:none;border:none;color:var(--red);cursor:pointer;border-radius:4px;text-align:left" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='none'" onclick="this.closest('.dropdown-menu').classList.remove('show');deleteDetailPipeline('${pipelineId}')">🗑 Delete Pipeline</button>
            </div>
          </div>
          ` : ''}
      </div>
      </div>

      <!-- Flow diagram -->
      <div class="pipeline-flow">
        <div class="pf-node source">
          <span class="pf-node-icon">${getDbIcon(srcType, 18)}</span>
          ${srcName}
        </div>
        <span class="pf-arrow">→</span>
        <div class="pf-node pipeline-center">
          <span class="pf-node-icon">⚡</span>
          CDC Pipeline (${p.tables?.length || 0} tables)
        </div>
        <span class="pf-arrow">→</span>
        <div class="pf-node target">
          <span class="pf-node-icon">${getDbIcon(destType, 18)}</span>
          ${destName}
        </div>
      </div>

      <!-- Stats cards -->
      <div class="detail-meta">
        <div class="detail-meta-item">
          <div class="dmi-icon green">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
          <div class="dmi-label">Status</div>
          <div class="dmi-value"><span class="status"><span class="dot ${runStatusDot}"></span><span class="label ${runStatusDot}" style="font-size:18px;">${runStatus}</span></span></div>
        </div>
        <div class="detail-meta-item">
          <div class="dmi-icon purple">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          </div>
          <div class="dmi-label">Schedule</div>
          <div class="dmi-value" style="font-size:16px;font-family:'SF Mono',monospace;display:flex;align-items:center;gap:6px"><span>${scheduleLabel}</span> <button class="btn btn-ghost btn-xs" onclick="showEditScheduleModal('${pipelineId}','${p.schedule||''}')" title="Edit Schedule">✏</button></div>
        </div>
        <div class="detail-meta-item">
          <div class="dmi-icon blue">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
          </div>
          <div class="dmi-label">Total Rows</div>
          <div class="dmi-value">${numberFormat(totalRows)}</div>
        </div>
        <div class="detail-meta-item">
          <div class="dmi-icon amber">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          </div>
          <div class="dmi-label">Last Sync</div>
          <div class="dmi-value" style="font-size:16px;">${lastSync}</div>
        </div>
      </div>

      <!-- Tables -->
      <div class="card" style="margin-bottom:24px;">
        <div class="card-header">
          <h3>Tables (${p.tables?.length || 0})</h3>
        </div>
        ${p.tables?.length ? `
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Table</th><th>Target Schema</th><th>Sync Mode</th><th>Load Mode</th><th>Transform</th><th>Watermark</th><th>Watermark Value</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${p.tables.map(t => `
              <tr>
                <td><span style="font-weight:500;color:var(--text-primary);">${t.name}</span></td>
                <td><span class="tag ${t.target_schema ? 'blue' : 'gray'}">${t.target_schema || '(default)'}</span></td>
                <td><span class="tag ${t.sync_mode === 'incremental' ? 'green' : 'purple'}">${t.sync_mode || 'incremental'}</span></td>
                <td><span class="tag ${t.load_mode === 'raw' ? 'blue' : 'green'}">${t.load_mode === 'raw' ? 'Raw → Normalize' : 'Direct'}</span></td>
                <td>${renderTransformCell(t, pipelineId)}</td>
                <td class="font-mono text-tertiary" style="font-size:12px;">${t.watermark_column || '-'}</td>
                <td class="font-mono text-tertiary" style="font-size:12px;">${t.watermark_value || '-'}</td>
                <td><span class="status"><span class="dot ${t.enabled ? 'green' : 'gray'}"></span><span class="label ${t.enabled ? 'green' : 'gray'}">${t.enabled ? 'Enabled' : 'Disabled'}</span></span></td>
              </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        ` : '<div class="card-body"><p style="color:var(--text-tertiary);font-size:13px;">No tables configured.</p></div>'}
      </div>

      <!-- Run History -->
      <div class="card">
        <div class="card-header">
          <h3>Run History</h3>
          <div class="flex items-center gap-2">
            <span class="text-tertiary text-sm">Last 24 hours</span>
            <button class="btn btn-ghost btn-xs" onclick="App.render()">⟳ Refresh</button>
          </div>
        </div>
        ${runs.length ? `
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Time</th><th>Status</th><th>Duration</th><th>Trigger</th><th>Error</th><th></th></tr>
            </thead>
            <tbody>
              ${runs.map(r => `
              <tr>
                <td style="white-space:nowrap;color:var(--text-tertiary);font-size:12px">${formatTime(r.started_at)}</td>
                <td><span class="status"><span class="dot ${r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'blue'}"></span><span class="label ${r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'blue'}">${r.status}</span></span></td>
                <td style="color:var(--text-secondary)">${formatDuration(r.duration_ms)}</td>
                <td style="color:var(--text-tertiary);font-size:12px">${r.trigger_type || '-'}</td>
                <td style="color:var(--red);font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis">${r.error_message || '-'}</td>
                <td><button class="btn btn-ghost btn-xs" onclick="showRunLogs('${r.id}')">Logs</button></td>
              </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        ` : '<div class="card-body"><p style="color:var(--text-tertiary);font-size:13px;">No runs yet.</p></div>'}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error</h3><p>${err.message}</p></div>`;
  }
}

async function triggerDetailPipeline(id) {
  try {
    const result = await API.post(`/pipelines/${id}/trigger`);
    App.toast(`Run ${result.status || 'triggered'}`, result.status === 'success' ? 'success' : 'info');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

async function pauseDetailPipeline(id) {
  try { await API.post(`/pipelines/${id}/pause`); App.toast('Pipeline paused'); App.render(); }
  catch (err) { App.toast(err.message, 'error'); }
}

async function resumeDetailPipeline(id) {
  try { await API.post(`/pipelines/${id}/resume`); App.toast('Pipeline resumed'); App.render(); }
  catch (err) { App.toast(err.message, 'error'); }
}

async function deleteDetailPipeline(id) {
  App.showModal(`
    <div class="modal-header">
      <h2>🗑 Delete Pipeline</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px;">Are you sure you want to delete this pipeline?</p>
      <p style="color:var(--red);font-size:12px;margin-bottom:20px;">This action cannot be undone.</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button class="btn btn-danger" id="confirm-delete-pipeline">🗑 Delete Pipeline</button>
      </div>
    </div>
  `);
  document.getElementById('confirm-delete-pipeline').addEventListener('click', async () => {
    App.closeModal();
    try {
      await API.del('/pipelines/' + id);
      App.toast('Pipeline deleted', 'success');
      location.hash = 'pipelines';
      App.render();
    } catch (err) {
      App.toast(err.message, 'error');
    }
  });
}

async function showRunLogs(runId) {
  try {
    const data = await API.get(`/runs/${runId}/logs?limit=200`);
    const logs = data?.data?.logs || [];
    App.showModal(`
      <div class="modal-header">
        <h2>Run Logs</h2>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="max-height:400px;overflow-y:auto;background:var(--bg-primary);border-radius:var(--radius-sm);padding:12px">
          ${logs.length ? logs.map(log => `
            <div style="display:flex;gap:8px;font-size:12px;padding:2px 0;font-family:monospace">
              <span style="color:var(--text-tertiary);white-space:nowrap">${log.timestamp ? formatTime(log.timestamp) : ''}</span>
              <span class="log-level log-${(log.level || 'info').toLowerCase()}">${log.level || 'INFO'}</span>
              <span style="color:var(--text-secondary)">${log.message}</span>
            </div>
          `).join('') : '<p style="color:var(--text-tertiary)">No logs available.</p>'}
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
      </div>
    `);
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

// Globals
window.triggerDetailPipeline = triggerDetailPipeline;
window.pauseDetailPipeline = pauseDetailPipeline;
window.resumeDetailPipeline = resumeDetailPipeline;
window.showRunLogs = showRunLogs;
window.fullRefreshPipeline = fullRefreshPipeline;
window.showBackfillModal = showBackfillModal;
window.showDeadLetters = showDeadLetters;
window.showTransformConfig = showTransformConfig;
window.showEditScheduleModal = showEditScheduleModal;
window.handleEditScheduleSave = handleEditScheduleSave;
window.showEditConfigModal = showEditConfigModal;
window.handleEditConfigSave = handleEditConfigSave;

/* ===== Full Refresh ===== */
async function fullRefreshPipeline(id) {
  if (!confirm('This will reset all watermarks and re-sync ALL data from source. Are you sure?')) return;
  try {
    const result = await API.post(`/pipelines/${id}/full-refresh`);
    App.toast('Full refresh triggered!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

/* ===== Backfill Modal ===== */
function showBackfillModal(pipelineId) {
  App.showModal(`
    <div class="modal-header">
      <h2>Backfill Pipeline</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form onsubmit="return handleBackfill(event, '${pipelineId}')">
      <div class="modal-body">
        <div class="form-group">
          <label>Backfill From Date</label>
          <input type="date" id="backfillDate" required style="font-weight:500">
          <div style="font-size:12px;color:var(--text-tertiary);margin-top:4px">
            All rows from this date onward will be re-synced from the source.
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Start Backfill</button>
      </div>
    </form>
  `);
}

async function handleBackfill(event, pipelineId) {
  event.preventDefault();
  const fromDate = document.getElementById('backfillDate').value;
  if (!fromDate) { App.toast('Please select a date', 'error'); return false; }

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Starting...';
  btn.style.opacity = '0.6';

  try {
    const result = await API.post(`/pipelines/${pipelineId}/backfill`, { from: fromDate });
    App.closeModal();
    App.toast('Backfill triggered!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}

/* ===== Dead Letter Viewer ===== */
async function showDeadLetters(pipelineId) {
  App.showModal(`
    <div class="modal-header">
      <h2>Dead Letters</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div id="dead-letter-content" style="text-align:center;padding:20px">
        <div class="spinner"></div>
        <p style="color:var(--text-tertiary);font-size:13px;margin-top:12px">Loading dead letter rows...</p>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
    </div>
  `);

  try {
    const data = await API.get(`/pipelines/${pipelineId}/dead-letters?limit=50`);
    const rows = data?.data || [];
    const content = document.getElementById('dead-letter-content');
    if (!content) return;

    if (rows.length === 0) {
      content.innerHTML = '<div style="padding:20px"><div style="font-size:48px;margin-bottom:12px;opacity:0.5">✅</div><h3>No Dead Letters</h3><p style="color:var(--text-tertiary);font-size:13px">All rows processed successfully.</p></div>';
      return;
    }

    content.innerHTML = `
      <div style="font-size:13px;margin-bottom:12px;color:var(--text-tertiary)">
        ${rows.length} failed rows
      </div>
      <div style="max-height:400px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;font-size:12px">
        ${rows.map(r => `
          <div style="padding:10px 12px;border-bottom:1px solid var(--border);text-align:left">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
              <span style="color:var(--text-primary);font-weight:500">${r.table_name || '-'}</span>
              <span style="color:var(--text-tertiary);font-size:11px">${r.failed_at ? new Date(r.failed_at).toLocaleString() : '-'}</span>
            </div>
            <div style="background:var(--bg-primary);padding:8px;border-radius:4px;margin-bottom:4px;overflow-x:auto">
              <pre style="margin:0;font-size:11px;color:var(--text-secondary);white-space:pre-wrap;word-break:break-all">${JSON.stringify(r.row_data || {}, null, 1).slice(0, 500)}</pre>
            </div>
            <div style="color:var(--red);font-size:11px">${r.error_text || '-'}</div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    const content = document.getElementById('dead-letter-content');
    if (content) content.innerHTML = `<div style="padding:20px"><div style="font-size:48px;margin-bottom:12px;opacity:0.5">⚠️</div><h3>Error</h3><p style="color:var(--text-tertiary);font-size:13px">${err.message}</p></div>`;
  }
}

/* ===== Transform Config ===== */

// Step type metadata for the UI
const TRANSFORM_STEPS = {
  rename:         { label: 'Rename Fields',   icon: '🔄', desc: 'Rename columns using a mapping' },
  remove_fields:  { label: 'Remove Fields',   icon: '❌', desc: 'Remove one or more columns' },
  compute:        { label: 'Compute Field',   icon: '🧮', desc: 'Compute a new field from an expression' },
  filter:         { label: 'Filter Rows',     icon: '🔍', desc: 'Keep rows matching a condition' },
  map_values:     { label: 'Map Values',      icon: '🔀', desc: 'Map column values using a lookup' },
  type_cast:      { label: 'Type Cast',       icon: '🔤', desc: 'Cast columns to a target type' },
  concat_fields:  { label: 'Concat Fields',   icon: '➕', desc: 'Combine fields into one column' },
  script:         { label: 'Script',          icon: '📜', desc: 'Run a custom Python transform script' },
};

function getStepSummary(step) {
  if (!step || !step.type) return '';
  const cfg = step.config || {};
  switch (step.type) {
    case 'rename': return Object.entries(cfg.mapping || {}).map(([k,v]) => `${k} → ${v}`).join(', ') || '•';
    case 'remove_fields': return (cfg.fields || []).join(', ') || '•';
    case 'compute': return cfg.expression || '•';
    case 'filter': return cfg.condition || '•';
    case 'map_values': return `${cfg.column || '?'} → ${Object.keys(cfg.mapping || {}).length} mappings`;
    case 'type_cast': return Object.entries(cfg.columns || {}).map(([k,v]) => `${k}: ${v}`).join(', ') || '•';
    case 'concat_fields': return `${(cfg.fields || []).join('+')} → ${cfg.target || 'concatenated'}`;
    case 'script': return `📜 ${cfg.script_name || '?'}`;
    default: return JSON.stringify(cfg).slice(0, 60);
  }
}

function renderTransformCell(table, pipelineId) {
  const config = table.transform_config;
  if (!config || !Array.isArray(config) || config.length === 0) {
    return `<button class="btn btn-ghost btn-xs" onclick="showTransformConfig('${pipelineId}','${table.name}')" style="opacity:0.5">⚡ Add</button>`;
  }
  const count = config.length;
  const label = count === 1 ? '1 step' : `${count} steps`;
  return `<button class="btn btn-ghost btn-xs" onclick="showTransformConfig('${pipelineId}','${table.name}')" style="color:var(--emerald)">⚡ ${label}</button>`;
}

async function showTransformConfig(pipelineId, tableName) {
  let pipelineData;
  try {
    const resp = await API.get('/pipelines/' + pipelineId);
    pipelineData = resp;
  } catch (err) {
    App.toast(err.message, 'error');
    return;
  }

  const table = (pipelineData.tables || []).find(t => t.name === tableName);
  if (!table) {
    App.toast('Table not found', 'error');
    return;
  }

  let steps = (table.transform_config || []).map(s => ({ ...s }));

  // Store steps on window so save can access them
  window._tfSteps = steps;
  window._tfPipelineId = pipelineId;
  window._tfTableName = tableName;

  // Fetch scripts for this pipeline
  let scripts = [];
  try {
    const s = await API.get(`/pipelines/${pipelineId}/scripts`);
    scripts = Array.isArray(s) ? s : [];
  } catch(e) { /* no scripts yet */ }

  const renderModal = () => {
    // Keep window._tfSteps in sync
    window._tfSteps = steps;

    const stepListHtml = steps.length > 0
      ? steps.map((step, i) => {
          const meta = TRANSFORM_STEPS[step.type] || { label: step.type, icon: '⚙️' };
          const summary = getStepSummary(step);
          return `
            <div class="transform-step" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:6px;background:var(--bg-card)">
              <span style="font-size:14px;min-width:20px">${meta.icon}</span>
              <div style="flex:1;min-width:0">
                <div style="font-size:13px;font-weight:500;color:var(--text-primary)">${meta.label}</div>
                <div style="font-size:11px;color:var(--text-tertiary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${summary}</div>
              </div>
              <div style="display:flex;gap:2px;align-items:center;flex-shrink:0">
                ${i > 0 ? `<button class="btn btn-ghost btn-xs" onclick="moveTransformStep(${i}, -1)" title="Move up">↑</button>` : '<span style="width:26px"></span>'}
                ${i < steps.length - 1 ? `<button class="btn btn-ghost btn-xs" onclick="moveTransformStep(${i}, 1)" title="Move down">↓</button>` : '<span style="width:26px"></span>'}
                <button class="btn btn-ghost btn-xs" onclick="editTransformStep(${i})" title="Edit">✏</button>
                <button class="btn btn-ghost btn-xs" onclick="removeTransformStep(${i})" title="Remove" style="color:var(--red)">✕</button>
              </div>
            </div>
          `;
        }).join('')
      : '<p style="color:var(--text-tertiary);font-size:13px;padding:8px 0;text-align:center">No transforms configured for this table.</p>';

    App.showModal(`
      <div class="modal-header">
        <h2>⚙️ Transform Config — ${tableName}</h2>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="margin-bottom:16px">
          <h3 style="font-size:14px;margin-bottom:8px">Steps (${steps.length})</h3>
          <div id="transformStepList">${stepListHtml}</div>
        </div>

        <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
          <select id="tfAddType" style="flex:1;min-width:140px;font-size:12px;padding:6px 8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-secondary);color:var(--text-primary)">
            <option value="">— Add Step —</option>
            ${Object.entries(TRANSFORM_STEPS).map(([key, v]) => `<option value="${key}">${v.icon} ${v.label}</option>`).join('')}
          </select>
          <button class="btn btn-primary btn-sm" onclick="addTransformStep()">+ Add</button>
          ${steps.length > 0 ? `<button class="btn btn-ghost btn-xs" onclick="clearTransformSteps()" style="color:var(--red)">🗑 Clear All</button>` : ''}
        </div>

        <div id="tfInlineForm" style="display:none;border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px;margin-bottom:12px;background:var(--bg-secondary)"></div>

        <!-- Scripts management -->
        <details style="margin-top:12px;font-size:12px;color:var(--text-tertiary)">
          <summary style="cursor:pointer;font-weight:500">📜 Manage Scripts (${scripts.length})</summary>
          <div style="padding:8px 0">
            ${scripts.length > 0 ? scripts.map(s => `
              <div style="display:flex;align-items:center;gap:8px;padding:6px 8px;border:1px solid var(--border);border-radius:4px;margin-bottom:4px">
                <span style="flex:1;font-weight:500;color:var(--text-primary)">${s.name}</span>
                <span style="font-size:11px;color:var(--text-tertiary);flex:2">${s.description || ''}</span>
                <button class="btn btn-ghost btn-xs" onclick="editTransformScript('${pipelineId}','${s.id}','${s.name}','${(s.description||'').replace(/'/g,"\\'")}','${s.content.replace(/'/g,"\\'").replace(/\n/g,"\\n").replace(/`/g,"\\`")}')">✏</button>
                <button class="btn btn-ghost btn-xs" style="color:var(--red)" onclick="deleteTransformScript('${pipelineId}','${s.id}')">✕</button>
              </div>
            `).join('') : '<p>No custom scripts yet.</p>'}
            <button class="btn btn-ghost btn-xs" onclick="showCreateScriptForm('${pipelineId}')" style="margin-top:4px">+ New Script</button>
          </div>
        </details>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="button" class="btn btn-primary" onclick="saveTransformConfig()">💾 Save Config</button>
      </div>
    `);
  };

  renderModal();

  // ===== Global handlers (onclick from modal) =====

  window.addTransformStep = () => {
    const sel = document.getElementById('tfAddType');
    const type = sel.value;
    if (!type) { App.toast('Select a step type', 'error'); return; }

    const defaultConfigs = {
      rename: { mapping: { 'old_name': 'new_name' } },
      remove_fields: { fields: ['col1'] },
      compute: { expression: 'new_field = col_a + col_b' },
      filter: { condition: 'status != ' },
      map_values: { column: 'col', mapping: { 'from': 'to' } },
      type_cast: { columns: { 'col': 'str' } },
      concat_fields: { fields: ['col1', 'col2'], separator: ' ', target: 'combined', drop_source: false },
      script: { script_name: scripts.length > 0 ? scripts[0].name : '' },
    };

    steps.push({ type, config: defaultConfigs[type] || {} });
    window._tfSteps = steps;
    renderModal();
  };

  window.editTransformStep = (idx) => {
    const step = steps[idx];
    if (!step) return;
    const meta = TRANSFORM_STEPS[step.type] || { label: step.type, icon: '⚙️' };
    const cfg = step.config || {};

    let formHtml = '';
    switch (step.type) {
      case 'rename':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Mapping (JSON, one per line: "old": "new")</label>
            <textarea id="tfRenameMapping" rows="4" style="width:100%;font-family:monospace;font-size:12px;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">${JSON.stringify(cfg.mapping || {}, null, 2)}</textarea>
          </div>`;
        break;
      case 'remove_fields':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Fields to remove (comma separated)</label>
            <input type="text" id="tfRemoveFields" value="${(cfg.fields || []).join(', ')}" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
          </div>`;
        break;
      case 'compute':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Expression (e.g. "tax = amount * 0.11")</label>
            <input type="text" id="tfComputeExpr" value="${cfg.expression || ''}" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary);font-family:monospace">
          </div>`;
        break;
      case 'filter':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Condition (e.g. "status != 'deleted'")</label>
            <input type="text" id="tfFilterCond" value="${cfg.condition || ''}" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary);font-family:monospace">
          </div>`;
        break;
      case 'map_values':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Column</label>
            <input type="text" id="tfMapCol" value="${cfg.column || ''}" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
          </div>
          <div class="form-group">
            <label style="font-size:12px">Mapping (JSON: {"from": "to"})</label>
            <textarea id="tfMapMapping" rows="4" style="width:100%;font-family:monospace;font-size:12px;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">${JSON.stringify(cfg.mapping || {}, null, 2)}</textarea>
          </div>`;
        break;
      case 'type_cast':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Columns (JSON: {"col": "int|float|str|bool"})</label>
            <textarea id="tfCastColumns" rows="4" style="width:100%;font-family:monospace;font-size:12px;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">${JSON.stringify(cfg.columns || {}, null, 2)}</textarea>
          </div>`;
        break;
      case 'concat_fields':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Fields (comma separated)</label>
            <input type="text" id="tfConcatFields" value="${(cfg.fields || []).join(', ')}" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
          </div>
          <div class="form-group">
            <label style="font-size:12px">Separator</label>
            <input type="text" id="tfConcatSep" value="${cfg.separator || ' '}" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
          </div>
          <div class="form-group">
            <label style="font-size:12px">Target Column</label>
            <input type="text" id="tfConcatTarget" value="${cfg.target || 'combined'}" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
          </div>
          <div class="form-group">
            <label class="form-checkbox" style="display:flex;align-items:center;gap:8px;cursor:pointer">
              <input type="checkbox" id="tfConcatDrop" ${cfg.drop_source ? 'checked' : ''} style="accent-color:var(--emerald)"> Drop source fields after concat
            </label>
          </div>`;
        break;
      case 'script':
        formHtml = `
          <div style="font-size:13px;font-weight:500;margin-bottom:8px">${meta.icon} Edit ${meta.label}</div>
          <div class="form-group">
            <label style="font-size:12px">Script Name</label>
            <select id="tfScriptName" style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
              ${scripts.length > 0
                ? scripts.map(s => `<option value="${s.name}" ${s.name === cfg.script_name ? 'selected' : ''}>${s.name}</option>`).join('')
                : '<option value="">No scripts available</option>'}
            </select>
          </div>`;
        break;
    }

    formHtml += `
      <div style="display:flex;gap:8px;margin-top:12px">
        <button class="btn btn-secondary btn-sm" onclick="document.getElementById('tfInlineForm').style.display='none'">Cancel</button>
        <button class="btn btn-primary btn-sm" onclick="saveTransformStepEdit(${idx})">💾 Save Step</button>
      </div>`;

    const formEl = document.getElementById('tfInlineForm');
    formEl.innerHTML = formHtml;
    formEl.style.display = 'block';
    formEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  window.saveTransformStepEdit = (idx) => {
    const step = steps[idx];
    if (!step) return;

    try {
      switch (step.type) {
        case 'rename':
          step.config.mapping = JSON.parse(document.getElementById('tfRenameMapping').value);
          break;
        case 'remove_fields':
          step.config.fields = document.getElementById('tfRemoveFields').value.split(',').map(s => s.trim()).filter(Boolean);
          break;
        case 'compute':
          step.config.expression = document.getElementById('tfComputeExpr').value;
          break;
        case 'filter':
          step.config.condition = document.getElementById('tfFilterCond').value;
          break;
        case 'map_values':
          step.config.column = document.getElementById('tfMapCol').value;
          step.config.mapping = JSON.parse(document.getElementById('tfMapMapping').value);
          break;
        case 'type_cast':
          step.config.columns = JSON.parse(document.getElementById('tfCastColumns').value);
          break;
        case 'concat_fields':
          step.config.fields = document.getElementById('tfConcatFields').value.split(',').map(s => s.trim()).filter(Boolean);
          step.config.separator = document.getElementById('tfConcatSep').value;
          step.config.target = document.getElementById('tfConcatTarget').value;
          step.config.drop_source = document.getElementById('tfConcatDrop').checked;
          break;
        case 'script':
          step.config.script_name = document.getElementById('tfScriptName').value;
          break;
      }
      window._tfSteps = steps;
      document.getElementById('tfInlineForm').style.display = 'none';
      renderModal();
    } catch (e) {
      App.toast('Invalid JSON: ' + e.message, 'error');
    }
  };

  window.removeTransformStep = (idx) => {
    steps.splice(idx, 1);
    window._tfSteps = steps;
    renderModal();
  };

  window.moveTransformStep = (idx, dir) => {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= steps.length) return;
    [steps[idx], steps[newIdx]] = [steps[newIdx], steps[idx]];
    window._tfSteps = steps;
    renderModal();
  };

  window.clearTransformSteps = () => {
    if (!confirm('Remove all transform steps for this table?')) return;
    steps = [];
    window._tfSteps = steps;
    renderModal();
  };
}

async function saveTransformConfig() {
  const pipelineId = window._tfPipelineId;
  const tableName = window._tfTableName;
  const steps = window._tfSteps || [];

  try {
    const pipelineData = await API.get('/pipelines/' + pipelineId);
    const tables = (pipelineData.tables || []).map(t => ({
      name: t.name,
      target_schema: t.target_schema || null,
      load_mode: t.load_mode || 'direct',
      sync_mode: t.sync_mode || 'incremental',
      watermark_column: t.watermark_column || null,
      transform_config: t.name === tableName ? (steps.length > 0 ? steps : null) : (t.transform_config || null),
    }));

    await API.put('/pipelines/' + pipelineId, { tables });
    App.closeModal();
    App.toast('✅ Transform config saved!', 'success');
    App.render();
  } catch (err) {
    App.toast('Error: ' + err.message, 'error');
  }
}

// ===== Script Management =====

async function deleteTransformScript(pipelineId, scriptId) {
  if (!confirm('Delete this transform script?')) return;
  try {
    await API.del(`/pipelines/${pipelineId}/scripts/${scriptId}`);
    App.toast('Script deleted', 'info');
    showTransformConfig(pipelineId, window._tfTableName || '');
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

function showCreateScriptForm(pipelineId) {
  App.showModal(`
    <div class="modal-header">
      <h2>📜 New Transform Script</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form onsubmit="return handleCreateScript(event, '${pipelineId}')">
      <div class="modal-body">
        <div class="form-group">
          <label>Name</label>
          <input type="text" id="scriptName" placeholder="clean_orders" required style="font-family:monospace">
        </div>
        <div class="form-group">
          <label>Description (optional)</label>
          <input type="text" id="scriptDesc" placeholder="Normalize phone numbers and clean addresses">
        </div>
        <div class="form-group">
          <label>Python Script Content</label>
          <textarea id="scriptContent" rows="12" required style="width:100%;font-family:monospace;font-size:12px;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)" placeholder="def transform(row):\n    row['phone'] = row['phone'].replace('-', '')\n    return row"></textarea>
          <div style="font-size:11px;color:var(--text-tertiary);margin-top:4px">
            The function must be <code>def transform(row: dict) -> dict</code>. Return modified row or <code>None</code> to drop it.
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">💾 Save Script</button>
      </div>
    </form>
  `);
}

async function handleCreateScript(event, pipelineId) {
  event.preventDefault();
  const data = {
    name: document.getElementById('scriptName').value,
    description: document.getElementById('scriptDesc').value || null,
    content: document.getElementById('scriptContent').value,
  };

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Saving...';
  btn.style.opacity = '0.6';

  try {
    await API.post(`/pipelines/${pipelineId}/scripts`, data);
    App.closeModal();
    App.toast('✅ Script created!', 'success');
    showTransformConfig(pipelineId, window._tfTableName || '');
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}

/* ===== Pipeline Config Edit ===== */

function showEditScheduleModal(pipelineId, currentSchedule) {
  App.showModal(`
    <div class="modal-header">
      <h2>✏️ Edit Schedule</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form onsubmit="return handleEditScheduleSave(event, '${pipelineId}')">
      <div class="modal-body">
        <div class="form-group">
          <label>Schedule (cron expression)</label>
          <input type="text" id="editScheduleCron" value="${currentSchedule || '*/5 * * * *'}" required
            style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);
            background:var(--bg-primary);color:var(--text-primary);font-family:'SF Mono',monospace;font-size:14px">
          <div style="font-size:12px;color:var(--text-tertiary);margin-top:4px">
            Format: minute hour day month weekday
          </div>
        </div>
        <div class="form-group">
          <label style="font-size:13px;margin-bottom:6px">Presets</label>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            <button type="button" class="btn btn-ghost btn-xs" onclick="document.getElementById('editScheduleCron').value='*/5 * * * *'">Every 5 min</button>
            <button type="button" class="btn btn-ghost btn-xs" onclick="document.getElementById('editScheduleCron').value='*/15 * * * *'">Every 15 min</button>
            <button type="button" class="btn btn-ghost btn-xs" onclick="document.getElementById('editScheduleCron').value='0 * * * *'">Every hour</button>
            <button type="button" class="btn btn-ghost btn-xs" onclick="document.getElementById('editScheduleCron').value='0 */6 * * *'">Every 6 hours</button>
            <button type="button" class="btn btn-ghost btn-xs" onclick="document.getElementById('editScheduleCron').value='0 0 * * *'">Daily midnight</button>
            <button type="button" class="btn btn-ghost btn-xs" onclick="document.getElementById('editScheduleCron').value='0 0 * * 0'">Weekly (Sun)</button>
            <button type="button" class="btn btn-ghost btn-xs" onclick="document.getElementById('editScheduleCron').value=''">Manual only</button>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">💾 Save Schedule</button>
      </div>
    </form>
  `);
}

async function handleEditScheduleSave(event, pipelineId) {
  event.preventDefault();
  const cron = document.getElementById('editScheduleCron').value.trim();
  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Saving...';
  btn.style.opacity = '0.6';
  try {
    await API.put('/pipelines/' + pipelineId, { schedule: cron || null });
    App.closeModal();
    App.toast('✅ Schedule updated!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}

function showEditConfigModal(pipelineId, name, targetSchema, loadMode, schedule, syncType) {
  App.showModal(`
    <div class="modal-header">
      <h2>⚙️ Edit Pipeline Config</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form onsubmit="return handleEditConfigSave(event, '${pipelineId}')">
      <div class="modal-body">
        <div class="form-group">
          <label>Pipeline Name</label>
          <input type="text" id="editConfigName" value="${name}" required
            style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
        </div>
        <div class="form-group">
          <label>Target Schema</label>
          <input type="text" id="editConfigSchema" value="${targetSchema}"
            style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary);font-family:'SF Mono',monospace">
        </div>
        <div class="form-group">
          <label>Load Mode</label>
          <select id="editConfigLoadMode"
            style="width:100%;padding:8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary)">
            <option value="direct" ${loadMode === 'direct' ? 'selected' : ''}>Direct</option>
            <option value="raw" ${loadMode === 'raw' ? 'selected' : ''}>Raw → Normalize</option>
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">💾 Save Config</button>
      </div>
    </form>
  `);
}

async function handleEditConfigSave(event, pipelineId) {
  event.preventDefault();
  const name = document.getElementById('editConfigName').value.trim();
  const targetSchema = document.getElementById('editConfigSchema').value.trim();
  const loadMode = document.getElementById('editConfigLoadMode').value;
  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Saving...';
  btn.style.opacity = '0.6';
  try {
    await API.put('/pipelines/' + pipelineId, {
      name: name || undefined,
      target_schema: targetSchema || undefined,
      load_mode: loadMode || undefined,
    });
    App.closeModal();
    App.toast('✅ Config updated!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}
