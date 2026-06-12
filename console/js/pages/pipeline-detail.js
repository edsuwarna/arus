/* Pipeline Detail Page — Mockup-Aligned */
async function renderPipelineDetailPage(container, pipelineId) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading pipeline detail...</p></div>`;

  try {
    const [pipelineData, runsData] = await Promise.all([
      API.get('/pipelines/' + pipelineId),
      API.get('/pipelines/' + pipelineId + '/runs?limit=50'),
    ]);

    const p = pipelineData?.data || {};
    const runs = runsData?.data || [];

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
          <div class="subtitle">${(p.tables?.length || 0)} tables · ${p.sync_type || 'incremental'} sync from ${srcName} to ${destName}</div>
        </div>
        <div class="header-actions-right">
          <button class="btn btn-secondary btn-sm" onclick="triggerDetailPipeline('${pipelineId}')">⟳ Sync Now</button>
          ${isRunning
            ? `<button class="btn btn-ghost btn-sm" onclick="pauseDetailPipeline('${pipelineId}')">⏸ Pause</button>`
            : `<button class="btn btn-primary btn-sm" onclick="resumeDetailPipeline('${pipelineId}')">▶ Resume</button>`
          }
        </div>
      </div>

      <!-- Flow diagram -->
      <div class="pipeline-flow">
        <div class="pf-node source">
          <span class="pf-icon">${getDbIcon(srcType, 18)}</span>
          ${srcName}
        </div>
        <span class="pf-arrow">→</span>
        <div class="pf-node" style="background:var(--emerald-dim);color:var(--emerald);">
          <span class="pf-icon">⚡</span>
          CDC Pipeline (${p.tables?.length || 0} tables)
        </div>
        <span class="pf-arrow">→</span>
        <div class="pf-node target">
          <span class="pf-icon">${getDbIcon(destType, 18)}</span>
          ${destName}
        </div>
      </div>

      <!-- Stats cards -->
      <div class="detail-meta">
        <div class="detail-meta-item">
          <div class="dmi-label">Status</div>
          <div class="dmi-value"><span class="status"><span class="dot ${runStatusDot}"></span><span class="label ${runStatusDot}" style="font-size:14px;">${runStatus}</span></span></div>
        </div>
        <div class="detail-meta-item">
          <div class="dmi-label">Schedule</div>
          <div class="dmi-value" style="font-size:14px;">${scheduleLabel}</div>
        </div>
        <div class="detail-meta-item">
          <div class="dmi-label">Total Rows</div>
          <div class="dmi-value">${numberFormat(totalRows)}</div>
        </div>
        <div class="detail-meta-item">
          <div class="dmi-label">Last Sync</div>
          <div class="dmi-value" style="font-size:14px;">${lastSync}</div>
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
              <tr><th>Table</th><th>Sync Mode</th><th>Watermark</th><th>Watermark Value</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${p.tables.map(t => `
              <tr>
                <td><span style="font-weight:500;color:var(--text-primary);">${t.name}</span></td>
                <td><span class="tag ${t.sync_mode === 'incremental' ? 'green' : 'purple'}">${t.sync_mode || 'incremental'}</span></td>
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
