/* Runs Page — Run History with Logs, Pagination & Filtering */
async function renderRunsPage(container) {
  // State
  let _currentPage = 1;
  let _pageSize = 20;
  let _statusFilter = '';
  let _totalRuns = 0;

  // Helper to build query string
  function _buildQuery() {
    const params = new URLSearchParams();
    params.set('limit', String(_pageSize));
    params.set('offset', String((_currentPage - 1) * _pageSize));
    if (_statusFilter) params.set('status', _statusFilter);
    return params.toString();
  }

  async function loadRuns() {
    const tableBody = container.querySelector('#runs-tbody');
    const pageInfo = container.querySelector('#runs-page-info');
    const prevBtn = container.querySelector('#runs-prev-btn');
    const nextBtn = container.querySelector('#runs-next-btn');
    const totalLabel = container.querySelector('#runs-total-label');

    // Show loading state
    tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-tertiary)">Loading...</td></tr>`;
    if (prevBtn) prevBtn.disabled = true;
    if (nextBtn) nextBtn.disabled = true;

    try {
      const qs = _buildQuery();
      const resp = await API.get('/runs?' + qs);
      // Handle both { runs: [...], total: N } and bare array responses
      const runs = Array.isArray(resp) ? resp : (resp?.runs || []);
      _totalRuns = resp?.total != null ? resp.total : runs.length;
      const totalPages = Math.ceil(_totalRuns / _pageSize) || 1;

      if (runs.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-tertiary)">No runs match the current filter.</td></tr>`;
      } else {
        tableBody.innerHTML = runs.map(r => `
          <tr style="cursor:pointer" onclick="location.hash='pipeline/${r.pipeline_id}'">
            <td style="white-space:nowrap;color:var(--text-tertiary);font-size:12px">${formatTime(r.started_at)}</td>
            <td><span style="font-weight:500;color:var(--text-primary);font-size:12px;">${r.pipeline_name || 'Unknown'}</span></td>
            <td><span class="status"><span class="dot ${r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'blue'}"></span><span class="label ${r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'blue'}">${r.status}</span></span></td>
            <td style="color:var(--text-secondary)">${formatDuration(r.duration_ms)}</td>
            <td class="font-mono">${numberFormat(r.rows_synced || 0)}</td>
            <td style="color:var(--text-tertiary);font-size:12px">${r.trigger_type || '-'}</td>
            <td><button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();showRunLogs('${r.id}')">Logs</button>
              ${r.status === 'running' || r.status === 'pending' ? `<button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();cancelRun('${r.id}')" style="color:var(--red)">Cancel</button>` : ''}
              ${r.status === 'failed' ? `<button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();retryRun('${r.id}')" style="color:var(--emerald)">Retry</button>` : ''}
            </td>
          </tr>
        `).join('');
      }

      // Update pagination controls
      if (totalLabel) totalLabel.textContent = `${_totalRuns} run${_totalRuns !== 1 ? 's' : ''}`;
      if (pageInfo) pageInfo.textContent = `Page ${_currentPage} of ${totalPages}`;
      if (prevBtn) prevBtn.disabled = _currentPage <= 1;
      if (nextBtn) nextBtn.disabled = _currentPage >= totalPages;
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--red)">Error: ${err.message}</td></tr>`;
      if (prevBtn) prevBtn.disabled = false;
      if (nextBtn) nextBtn.disabled = false;
    }
  }

  // Build the page skeleton
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Run History</h1>
        <div class="subtitle">Recent pipeline executions across all pipelines</div>
      </div>
      <div class="header-actions-right">
        <button class="btn btn-secondary btn-sm" id="runs-refresh-btn">⟳ Refresh</button>
      </div>
    </div>

    <div class="card">
      <div class="card-header" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <h3>All Runs</h3>
          <span class="text-tertiary text-sm" id="runs-total-label"></span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <label style="font-size:12px;color:var(--text-tertiary)">Status</label>
          <select class="filter-select" id="runs-status-filter">
            <option value="">All</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
          </select>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Time</th><th>Pipeline</th><th>Status</th><th>Duration</th><th>Rows</th><th>Trigger</th><th></th></tr>
          </thead>
          <tbody id="runs-tbody">
            <tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-tertiary)">Loading...</td></tr>
          </tbody>
        </table>
      </div>
      <div class="card-footer" style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;">
        <span class="text-sm text-tertiary" id="runs-page-info"></span>
        <div class="pagination">
          <button class="btn btn-secondary btn-sm" id="runs-prev-btn" disabled>← Previous</button>
          <button class="btn btn-secondary btn-sm" id="runs-next-btn">Next →</button>
        </div>
      </div>
    </div>
  `;

  // Wire up event handlers
  container.querySelector('#runs-status-filter').addEventListener('change', function() {
    _statusFilter = this.value;
    _currentPage = 1;
    loadRuns();
  });

  container.querySelector('#runs-prev-btn').addEventListener('click', function() {
    if (_currentPage > 1) {
      _currentPage--;
      loadRuns();
    }
  });

  container.querySelector('#runs-next-btn').addEventListener('click', function() {
    const totalPages = Math.ceil(_totalRuns / _pageSize) || 1;
    if (_currentPage < totalPages) {
      _currentPage++;
      loadRuns();
    }
  });

  container.querySelector('#runs-refresh-btn').addEventListener('click', function() {
    loadRuns();
  });

  // Initial load
  loadRuns();
}

// Export for router
window.renderRunsPage = renderRunsPage;
