/* Dashboard Page — Mockup-Aligned */
async function renderDashboardPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading dashboard...</p></div>`;

  try {
    const [summary, recentRuns] = await Promise.all([
      API.get('/dashboard/summary').catch(() => ({})),
      API.get('/dashboard/recent-runs').catch(() => []),
    ]);

    const s = summary || {};
    const runs = Array.isArray(recentRuns) ? recentRuns : [];

    const activeSources = s.active_sources || 0;
    const activePipelines = s.active_pipelines || 0;
    const rowsSynced = s.rows_synced_24h || 0;
    const failedRuns = s.failed_runs_24h || 0;
    const totalTables = s.total_tables_synced || 0;
    const totalSources = s.total_sources || 0;
    const totalDestinations = s.total_destinations || 0;

    // Update badges from summary API directly
    window._arusBadges.sources = totalSources;
    window._arusBadges.destinations = totalDestinations;
    window._arusBadges.pipelines = s.total_pipelines || activePipelines;
    window._arusBadges.dag = s.total_pipelines || activePipelines;

    // Fetch sources for the overview table
    let sourcesList = [];
    try {
      sourcesList = await API.get('/sources');
    } catch(e) {}

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Dashboard</h1>
          <div class="subtitle">Last 24h — all sources syncing to Data Warehouse</div>
        </div>
        <div class="header-actions-right">
          <button class="btn btn-ghost btn-sm" onclick="App.render()">⟳ Refresh</button>
          <button class="btn btn-primary btn-sm" onclick="location.hash='sources'">+ New Source</button>
        </div>
      </div>

      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-icon green">⬍</div>
          <div class="stat-label">Active Sources</div>
          <div class="stat-value">${activeSources}</div>
          <div class="stat-change up">↑ Connected</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon blue">≡</div>
          <div class="stat-label">Pipelines Active</div>
          <div class="stat-value">${activePipelines}</div>
          <div class="stat-change up">↑ ${failedRuns > 0 ? failedRuns + ' failing' : 'All running'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon amber">⚯</div>
          <div class="stat-label">Rows Synced (24h)</div>
          <div class="stat-value">${numberFormat(rowsSynced)}</div>
          <div class="stat-change up">↑ Across all pipelines</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon purple">⊞</div>
          <div class="stat-label">Failed Runs (24h)</div>
          <div class="stat-value">${failedRuns}</div>
          <div class="stat-change up">${failedRuns === 0 ? '✓ All successful' : '⚠ Needs attention'}</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3>Sync Performance</h3>
            <span class="text-tertiary text-sm">Last 7 days</span>
          </div>
          <div class="card-body">
            <div class="bar-chart" style="display:flex;align-items:flex-end;gap:6px;height:100px;padding-top:10px;">
              ${renderBarChart(rowsSynced)}
            </div>
            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-tertiary);margin-top:6px;">
              <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-header">
            <h3>Recent Runs</h3>
            <a href="#runs" style="font-size:12px;color:var(--emerald);text-decoration:none;">View all →</a>
          </div>
          <div class="card-body pt-0">
            ${runs.length > 0 ? runs.slice(0, 5).map(r => renderRunRow(r)).join('') : `
              <div class="empty-state" style="padding:20px">
                <p style="color:var(--text-tertiary);font-size:13px;">No recent runs. Create a pipeline to get started.</p>
              </div>
            `}
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Data Sources Overview</h3>
          <span class="text-tertiary text-sm">Auto-discovered: ${totalTables} tables across ${totalSources} sources</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Source</th><th>Type</th><th>Tables</th><th>Status</th><th>Last Sync</th><th></th></tr>
            </thead>
            <tbody>
              ${renderSourcesTable(sourcesList)}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error loading dashboard</h3><p>${err.message}</p></div>`;
  }

  // Update sidebar badges
  if (window.App?.updateBadges) App.updateBadges();
}

function renderBarChart(totalRows) {
  // Generate mock-ish bar heights
  const days = [0.4, 0.6, 0.35, 0.85, 0.5, 0.65, 0.3];
  const maxVal = Math.max(1, totalRows);
  return days.map((h, i) => {
    const height = Math.max(20, h * 100);
    const isMax = i === 3; // Thursday = peak
    const label = numberFormat(Math.round(h * maxVal));
    return `<div style="flex:1;background:${isMax ? 'var(--emerald)' : 'var(--emerald-dim)'};border-radius:4px 4px 0 0;height:${height}px;position:relative;"><span style="position:absolute;top:-16px;left:50%;transform:translateX(-50%);font-size:10px;color:var(--text-tertiary);white-space:nowrap;">${label}</span></div>`;
  }).join('');
}

function renderRunRow(run) {
  const status = run.status || 'success';
  const isSuccess = status === 'success';
  const isPartial = status === 'partial';
  const dotColor = isSuccess ? 'green' : (isPartial ? 'amber' : 'red');
  const labelColor = dotColor;
  const label = isSuccess ? 'Success' : (isPartial ? 'Partial' : 'Failed');
  const rows = numberFormat(run.rows_synced || 0);
  const path = (run.source_name || 'source') + ' → ' + (run.destination_name || 'dw');
  return `
    <div class="run-item" style="padding-left:0;padding-right:0;cursor:pointer" onclick="location.hash='pipeline/${run.pipeline_id || run.id}'">
      <span class="status"><span class="dot ${dotColor}"></span><span class="label ${dotColor}">${label}</span></span>
      <span class="ri-time">${formatTime(run.started_at || run.created_at)}</span>
      <span class="ri-rows">${rows} rows</span>
      <span class="ri-action font-mono text-tertiary">${path}</span>
    </div>
  `;
}

function renderSourcesTable(sources) {
  if (!sources || sources.length === 0) {
    return `<tr><td colspan="7" style="text-align:center;color:var(--text-tertiary);padding:20px;">No sources configured.</td></tr>`;
  }
  return sources.map(src => {
    const statusDot = src.status === 'connected' || src.status === 'active' ? 'green' : (src.status === 'degraded' ? 'amber' : 'gray');
    const statusLabel = src.status === 'connected' || src.status === 'active' ? 'Active' : (src.status === 'degraded' ? 'Degraded' : 'Inactive');
    return `<tr>
      <td><span style="font-weight:600;color:var(--text-primary);">${src.name || 'Unknown'}</span></td>
      <td><span class="inline-flex items-center" style="gap:4px;font-size:12px;font-weight:500;color:var(--text-secondary)">${getDbIcon(src.type, 14)} ${(src.type || 'postgresql').toUpperCase()}</span></td>
      <td><span class="inline-flex text-emerald font-mono">${src.table_count || src.enabled_table_count || 0}</span></td>
      <td><span class="status"><span class="dot ${statusDot}"></span><span class="label ${statusDot}">${statusLabel}</span></span></td>
      <td class="text-sm">${formatTime(src.last_tested || src.last_synced)}</td>
      <td class="font-mono">${numberFormat(src.rows_per_hour || 0)}</td>
      <td><button class="btn btn-ghost btn-xs" onclick="location.hash='sources'">View</button></td>
    </tr>`;
  }).join('');
}
