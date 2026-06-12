/* Runs Page — Run History with Logs */
async function renderRunsPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading run history...</p></div>`;

  try {
    const resp = await API.get('/runs');
    const allRuns = resp?.runs || [];
    const topRuns = allRuns.sort((a, b) => new Date(b.started_at || 0) - new Date(a.started_at || 0)).slice(0, 50);

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Run History</h1>
          <div class="subtitle">Recent pipeline executions across all pipelines</div>
        </div>
        <div class="header-actions-right">
          <button class="btn btn-secondary btn-sm" onclick="App.render()">⟳ Refresh</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>All Runs</h3>
          <span class="text-tertiary text-sm">${topRuns.length} recent runs</span>
        </div>
        ${topRuns.length ? `
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Time</th><th>Pipeline</th><th>Status</th><th>Duration</th><th>Rows</th><th>Trigger</th><th></th></tr>
            </thead>
            <tbody>
              ${topRuns.map(r => `
              <tr style="cursor:pointer" onclick="location.hash='pipeline/${r.pipeline_id}'">
                <td style="white-space:nowrap;color:var(--text-tertiary);font-size:12px">${formatTime(r.started_at)}</td>
                <td><span style="font-weight:500;color:var(--text-primary);font-size:12px;">${r.pipeline_name || 'Unknown'}</span></td>
                <td><span class="status"><span class="dot ${r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'blue'}"></span><span class="label ${r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'blue'}">${r.status}</span></span></td>
                <td style="color:var(--text-secondary)">${formatDuration(r.duration_ms)}</td>
                <td class="font-mono">${numberFormat(r.rows_synced || 0)}</td>
                <td style="color:var(--text-tertiary);font-size:12px">${r.trigger_type || '-'}</td>
                <td><button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();showRunLogs('${r.id}')">Logs</button></td>
              </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        ` : '<div class="card-body"><p style="color:var(--text-tertiary);font-size:13px;">No runs recorded yet.</p></div>'}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error</h3><p>${err.message}</p></div>`;
  }
}
