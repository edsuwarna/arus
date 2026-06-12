/* DAG View Page — asset graph (Source → Raw → Target or Source → Target) */
let dagState = { panX: 0, panY: 0, zoom: 1 };
const DAG_LAYERS = ['source', 'raw', 'target'];
const DAG_LABELS = { source: 'SOURCE LAYER', raw: 'RAW LAYER', target: 'TARGET LAYER' };
const LAYER_COLORS = { source: '#3b82f6', raw: '#f59e0b', target: '#10b981' };

async function renderDagPage(container) {
    container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading pipelines...</p></div>`;

    try {
        const dagData = await API.get('/dag');
        const pipelines = Array.isArray(dagData) ? dagData : [];
        dagState.allPipelines = pipelines;

        container.innerHTML = `
            <div class="page-header">
                <div>
                    <h1 class="page-title">DAG View</h1>
                    <p class="page-subtitle">Pipeline asset graph</p>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                    <select id="dag-pipeline-select" class="form-select" style="min-width:220px"
                            onchange="onDagPipelineChange(this.value)">
                        <option value="">— Select pipeline —</option>
                        ${pipelines.map(p => `
                            <option value="${p.id}">${p.name} (${p.table_count} assets)</option>
                        `).join('')}
                    </select>
                    <button class="btn btn-secondary btn-sm" onclick="toggleDagLegend()">ℹ Legend</button>
                </div>
            </div>

            <div class="dag-legend" id="dag-legend" style="display:none">
                <span class="legend-item"><span class="legend-dot" style="background:#10b981"></span> Success</span>
                <span class="legend-item"><span class="legend-dot" style="background:#3b82f6"></span> Running</span>
                <span class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span> Stale</span>
                <span class="legend-item"><span class="legend-dot" style="background:#ef4444"></span> Failed</span>
                <span class="legend-item"><span class="legend-dot" style="background:#6b7280"></span> Not Started</span>
            </div>

            <div id="dag-graph-section" style="display:none">
                <div class="card dag-graph-container">
                    <div class="dag-graph-toolbar">
                        <span style="font-size:13px;font-weight:500" id="dag-pipeline-label">Select a pipeline</span>
                        <div style="display:flex;gap:4px">
                            <button class="btn btn-secondary btn-sm" onclick="dagZoom(0.2)">+</button>
                            <button class="btn btn-secondary btn-sm" onclick="dagZoom(-0.2)">-</button>
                            <button class="btn btn-secondary btn-sm" onclick="resetDagView()">Fit</button>
                        </div>
                    </div>
                    <div class="dag-canvas-wrapper" id="dag-canvas-wrapper"
                         style="overflow:auto;max-height:70vh;"
                         onmousedown="dagStartPan(event)" onmousemove="dagDoPan(event)" onmouseup="dagEndPan()" onmouseleave="dagEndPan()">
                        <svg id="dag-svg" width="100%" height="500" style="cursor:grab;display:block"></svg>
                    </div>
                </div>
            </div>

            <div id="dag-empty-state">
                <div class="empty-state">
                    <div class="empty-icon">🔀</div>
                    <p>Select a pipeline to view its DAG</p>
                </div>
            </div>

            <div id="dag-detail-panel" style="display:none"></div>
        `;
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><p>Error: ${err.message}</p></div>`;
    }
}

function onDagPipelineChange(pipelineId) {
    const graphSection = document.getElementById('dag-graph-section');
    const emptyState = document.getElementById('dag-empty-state');
    const detailPanel = document.getElementById('dag-detail-panel');

    if (!pipelineId) {
        graphSection.style.display = 'none';
        emptyState.style.display = 'block';
        detailPanel.style.display = 'none';
        dagState.selectedPipeline = null;
        dagState.selectedNode = null;
        return;
    }

    const pipelines = dagState.allPipelines || [];
    const p = pipelines.find(x => x.id === pipelineId);
    if (!p) return;

    dagState.selectedPipeline = pipelineId;
    dagState.selectedNode = null;
    dagState.zoom = 1;
    dagState.panX = 0;
    dagState.panY = 0;

    document.getElementById('dag-pipeline-label').textContent = p.name;
    graphSection.style.display = 'block';
    emptyState.style.display = 'none';
    detailPanel.style.display = 'none';

    renderDagGraph([p]);
}

function renderDagGraph(pipelines) {
    const svg = document.getElementById('dag-svg');
    if (!svg) return;

    // Collect all unique assets per layer
    const layers = { source: [], raw: [], target: [] };
    const allEdges = [];
    const seen = { source: new Set(), raw: new Set(), target: new Set() };

    pipelines.forEach(p => {
        (p.assets || []).forEach(a => {
            const layer = a.layer || 'source';
            if (!seen[layer].has(a.name)) {
                seen[layer].add(a.name);
                layers[layer].push(a);
            }
        });
        (p.edges || []).forEach(e => {
            if (!allEdges.some(x => x.from === e.from && x.to === e.to)) {
                allEdges.push(e);
            }
        });
    });

    const maxNodesPerLayer = Math.max(
        (layers.source || []).length,
        (layers.transform || []).length,
        (layers.destination || []).length,
        3
    );
    const W = 900, H = Math.max(450, maxNodesPerLayer * 56 + 100);
    const layerX = { source: 120, raw: 380, target: 650 };
    const NODE_W = 130, NODE_H = 36;
    const layerGap = 60;
    const topMargin = 40;

    // Calculate Y positions per layer
    const nodePositions = {};
    ['source', 'raw', 'target'].forEach(layer => {
        const items = layers[layer] || [];
        const totalH = items.length * (NODE_H + 12) - 12;
        const startY = topMargin + (H - topMargin - 40 - totalH) / 2;
        items.forEach((item, i) => {
            nodePositions[item.name] = {
                x: layerX[layer] - NODE_W / 2,
                y: startY + i * (NODE_H + 12),
                layer: layer,
                status: item.status || 'not_started',
                table: item.table || item.name,
            };
        });
    });

    const statusColors = {
        success: '#10b981', failed: '#ef4444', running: '#3b82f6',
        stale: '#f59e0b', not_started: '#6b7280', paused: '#f59e0b',
        active: '#10b981', inactive: '#6b7280',
    };

    const layerLabels = {
        source: { x: layerX.source, label: 'SOURCE LAYER', color: '#3b82f6' },
        raw: { x: layerX.raw, label: 'RAW LAYER', color: '#f59e0b' },
        target: { x: layerX.target, label: 'TARGET LAYER', color: '#10b981' },
    };

    const g = dagState;
    const zoom = g.zoom || 1;
    const panX = g.panX || 0;
    const panY = g.panY || 0;

    let html = '';
    html += `<g transform="translate(${panX},${panY}) scale(${zoom})">`;

    // Layer headers
    Object.values(layerLabels).forEach(ll => {
        html += `<text x="${ll.x}" y="18" text-anchor="middle" fill="${ll.color}" font-size="10"
                      font-weight="600" letter-spacing="2" opacity="0.7">${ll.label}</text>`;
    });

    // Layer dividers
    [250, 520].forEach(x => {
        html += `<line x1="${x}" y1="30" x2="${x}" y2="${H - 10}" stroke="#23262e" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>`;
    });

    // Edges
    allEdges.forEach(e => {
        const from = nodePositions[e.from];
        const to = nodePositions[e.to];
        if (from && to) {
            const x1 = from.x + NODE_W;
            const y1 = from.y + NODE_H / 2;
            const x2 = to.x;
            const y2 = to.y + NODE_H / 2;
            const cx = (x1 + x2) / 2;
            html += `<path d="M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}" stroke="#4a4e5a" stroke-width="2" fill="none" opacity="0.8"/>`;
        }
    });

    // Nodes
    Object.entries(nodePositions).forEach(([name, pos]) => {
        const color = statusColors[pos.status] || '#6b7280';
        const isSelected = g.selectedNode === name;
        html += `<g class="dag-node" onclick="dagNodeClick('${name}')" style="cursor:pointer">
            <rect x="${pos.x}" y="${pos.y}" width="${NODE_W}" height="${NODE_H}" rx="6"
                  fill="${isSelected ? '#1c1f26' : '#14171d'}"
                  stroke="${isSelected ? color : '#4a4e5a'}"
                  stroke-width="${isSelected ? 2 : 1.5}"/>
            <circle cx="${pos.x + 14}" cy="${pos.y + NODE_H / 2}" r="5" fill="${color}"/>
            <text x="${pos.x + 24}" y="${pos.y + NODE_H / 2 + 4}" fill="#e8eaed" font-size="12"
                  font-family="'Inter',sans-serif" font-weight="500">${name.length > 20 ? name.slice(0, 18) + '...' : name}</text>
        </g>`;
    });

    html += '</g>';
    svg.innerHTML = html;
}

function dagZoom(delta) {
    dagState.zoom = Math.max(0.3, Math.min(2, (dagState.zoom || 1) + delta));
    renderDagGraph(dagState.allPipelines || []);
}

function resetDagView() {
    dagState.zoom = 1;
    dagState.panX = 0;
    dagState.panY = 0;
    dagState.selectedNode = null;
    document.getElementById('dag-detail-panel').style.display = 'none';
    renderDagGraph(dagState.allPipelines || []);
}

let dagPanning = false, dagPanStart = { x: 0, y: 0 };
function dagStartPan(e) {
    dagPanning = true;
    dagPanStart = { x: e.clientX - (dagState.panX || 0), y: e.clientY - (dagState.panY || 0) };
    document.getElementById('dag-svg').style.cursor = 'grabbing';
}
function dagDoPan(e) {
    if (!dagPanning) return;
    dagState.panX = e.clientX - dagPanStart.x;
    dagState.panY = e.clientY - dagPanStart.y;
    renderDagGraph(dagState.allPipelines || []);
}
function dagEndPan() {
    dagPanning = false;
    const svg = document.getElementById('dag-svg');
    if (svg) svg.style.cursor = 'grab';
}

function toggleDagLegend() {
    const el = document.getElementById('dag-legend');
    el.style.display = el.style.display === 'none' ? 'flex' : 'none';
}

function showDagPipeline(pipelineId) {
    const pipelines = dagState.allPipelines || [];
    const p = pipelines.find(x => x.id === pipelineId);
    if (!p) return;
    dagState.selectedPipeline = pipelineId;
    document.getElementById('dag-pipeline-label').textContent = p.name;

    renderDagGraph(pipelines.filter(x => x.id === pipelineId));
}

async function dagNodeClick(nodeName) {
    dagState.selectedNode = nodeName;
    renderDagGraph(dagState.allPipelines || []);

    // Show detail panel
    const panel = document.getElementById('dag-detail-panel');
    if (!panel) return;

    // Find which pipeline this node belongs to
    const pipelines = dagState.allPipelines || [];
    let pipeline;
    let assetInfo;
    for (const p of pipelines) {
        const a = (p.assets || []).find(x => x.name === nodeName);
        if (a) { pipeline = p; assetInfo = a; break; }
    }

    if (!pipeline) {
        panel.style.display = 'none';
        return;
    }

    // Get runs for this pipeline
    try {
        const runsData = await API.get('/pipelines/' + pipeline.id + '/runs?limit=10');
        const runs = Array.isArray(runsData) ? runsData : [];

        const layer = assetInfo?.layer || 'source';
        const upstream = (pipeline.edges || []).filter(e => e.to === nodeName).map(e => e.from);
        const downstream = (pipeline.edges || []).filter(e => e.from === nodeName).map(e => e.to);

        panel.style.display = 'block';
        panel.innerHTML = `
            <div class="card" style="margin-top:16px">
                <div class="dag-detail-header">
                    <div>
                        <strong style="font-size:15px">Asset: ${nodeName}</strong>
                        <span class="badge badge-${assetInfo?.status === 'success' ? 'success' : assetInfo?.status === 'failed' ? 'danger' : 'info'}" style="margin-left:8px">
                            <span class="status-dot ${assetInfo?.status || 'inactive'}"></span> ${assetInfo?.status || 'unknown'}
                        </span>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="document.getElementById('dag-detail-panel').style.display='none'">✕</button>
                </div>
                <div style="display:flex;gap:16px;margin:12px 0">
                    <div><span style="color:var(--text-muted);font-size:11px">LAYER</span><br><span style="font-size:13px;text-transform:uppercase">${layer === 'source' ? '🔵' : layer === 'transform' ? '🟠' : '🟢'} ${layer}</span></div>
                    <div><span style="color:var(--text-muted);font-size:11px">UPSTREAM</span><br><span style="font-size:13px">${upstream.length ? upstream.join(', ') : '(none — root)'}</span></div>
                    <div><span style="color:var(--text-muted);font-size:11px">DOWNSTREAM</span><br><span style="font-size:13px">${downstream.length ? downstream.join(', ') : '(none — terminal)'}</span></div>
                </div>
                ${runs.length ? `
                <div class="table-container" style="margin-top:12px">
                    <table>
                        <thead>
                            <tr><th>Run ID</th><th>Status</th><th>Rows</th><th>Duration</th><th>Error</th></tr>
                        </thead>
                        <tbody>
                            ${runs.slice(0, 5).map(r => `
                            <tr>
                                <td style="font-size:11px;color:var(--text-muted);font-family:monospace">${r.id?.slice(0, 8) || '-'}...</td>
                                <td><span class="badge badge-${r.status === 'success' ? 'success' : r.status === 'failed' ? 'danger' : 'info'}"><span class="status-dot ${r.status}"></span> ${r.status}</span></td>
                                <td>-</td>
                                <td>${formatDuration(r.duration_ms)}</td>
                                <td style="color:var(--danger);font-size:12px;max-width:150px;overflow:hidden;text-overflow:ellipsis">${r.error_message || '-'}</td>
                            </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                ` : '<p style="color:var(--text-muted);font-size:13px;margin-top:8px">No runs recorded.</p>'}
            </div>
        `;
    } catch (err) {
        panel.innerHTML = `<div class="card" style="margin-top:16px"><p style="color:var(--danger)">Error: ${err.message}</p></div>`;
    }
}
