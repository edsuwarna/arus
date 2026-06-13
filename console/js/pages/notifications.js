/* Notifications Page — Manage notification targets */
async function renderNotificationsPage(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading notifications...</p></div>`;

  try {
    const resp = await API.get('/notifications/targets');
    const targets = resp?.data || [];
    const targetList = Array.isArray(targets) ? targets : [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Notifications</h1>
          <div class="subtitle">Configure notification targets — alerts go to Telegram, Discord, or Slack</div>
        </div>
        <div class="header-actions-right">
          ${App.canWrite() ? `
          <button class="btn btn-primary btn-sm" onclick="showAddNotifTargetModal()">+ Add Target</button>
          ` : ''}
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Notification Targets</h3>
        </div>
        ${targetList.length > 0 ? `
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Name</th><th>Type</th><th>Status</th><th>Created</th><th></th></tr>
            </thead>
            <tbody>
              ${targetList.map(t => `
              <tr>
                <td><span style="font-weight:500;color:var(--text-primary);">${t.name}</span></td>
                <td><span class="tag ${t.type === 'telegram' ? 'blue' : t.type === 'discord' ? 'purple' : 'green'}">${getNotifIcon(t.type)} ${t.type}</span></td>
                <td><span class="status"><span class="dot ${t.is_active ? 'green' : 'gray'}"></span><span class="label ${t.is_active ? 'green' : 'gray'}">${t.is_active ? 'Active' : 'Disabled'}</span></span></td>
                <td style="color:var(--text-tertiary);font-size:12px">${formatTime(t.created_at)}</td>
                <td style="display:flex;gap:4px;align-items:center">
                  <select id="testEvt_${t.id}" style="font-size:11px;padding:3px 6px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-secondary);color:var(--text-primary);width:100px" onclick="event.stopPropagation()">
                    <option value="test">Default Test</option>
                    <option value="success">✅ Success</option>
                    <option value="failure">🚨 Failure</option>
                    <option value="dead_letter">⚠️ Dead Letter</option>
                    <option value="schema_drift">🔀 Schema Drift</option>
                    <option value="quality_breach">📉 Quality Breach</option>
                  </select>
                  <button class="btn btn-ghost btn-xs" onclick="testNotifTarget(event, '${t.id}')">📨 Test</button>
                  <button class="btn btn-ghost btn-xs" onclick="editNotifTarget('${t.id}')">✏</button>
                  ${App.canWrite() ? `<button class="btn btn-ghost btn-xs" style="color:var(--red)" onclick="deleteNotifTarget('${t.id}')">✕</button>` : ''}
                </td>
              </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        ` : `
        <div class="card-body">
          <div class="empty-state" style="padding:40px">
            <div class="empty-icon">🔔</div>
            <h3>No notification targets configured</h3>
            <p style="color:var(--text-tertiary);font-size:13px;margin-bottom:16px">
              Add Telegram, Discord, or Slack targets to get alerts when pipelines fail, dead letters appear, or schema drifts detected.
            </p>
            <button class="btn btn-primary" onclick="showAddNotifTargetModal()">+ Add Your First Target</button>
          </div>
        </div>
        `}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Error</h3><p>${err.message}</p></div>`;
  }
}

function getNotifIcon(type) {
  const icons = {
    telegram: { bg: '#26A5E4', mono: 'TG' },
    discord: { bg: '#5865F2', mono: 'DC' },
    slack: { bg: '#4A154B', mono: 'SL' },
  };
  const ic = icons[type];
  if (!ic) return '?';
  const s = 18;
  return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none">
    <rect x="1" y="1" rx="6" width="22" height="22" fill="${ic.bg}"/>
    <text x="12" y="17" text-anchor="middle" fill="#fff" font-size="10" font-weight="700" font-family="Inter,sans-serif">${ic.mono}</text>
  </svg>`;
}

function showAddNotifTargetModal() {
  const modal = App.showModal(`
    <div class="modal-header">
      <h2>Add Notification Target</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <form id="addNotifForm" onsubmit="return handleAddNotifTarget(event)">
      <div class="modal-body">
        <div class="form-group">
          <label>Name</label>
          <input type="text" id="notifName" placeholder="Engineering Team Alert" required style="font-weight:500">
        </div>
        <div class="form-group">
          <label>Type</label>
          <select id="notifType" onchange="updateNotifForm()" required>
            <option value="telegram">Telegram</option>
            <option value="discord">Discord</option>
            <option value="slack">Slack</option>
          </select>
        </div>

        <!-- Telegram fields -->
        <div id="notifTelegramFields">
          <div class="form-group">
            <label>Bot Token</label>
            <input type="password" id="notifTelegramBotToken" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11">
            <div class="hint">From @BotFather on Telegram</div>
          </div>
          <div class="form-group">
            <label>Chat ID</label>
            <input type="text" id="notifTelegramChatId" placeholder="-1001234567890">
            <div class="hint">Can be a group/channel ID or user ID</div>
          </div>
        </div>

        <!-- Discord fields -->
        <div id="notifDiscordFields" style="display:none">
          <div class="form-group">
            <label>Webhook URL</label>
            <input type="password" id="notifDiscordWebhook" placeholder="https://discord.com/api/webhooks/...">
            <div class="hint">Create a webhook in your Discord channel settings</div>
          </div>
        </div>

        <!-- Slack fields -->
        <div id="notifSlackFields" style="display:none">
          <div class="form-group">
            <label>Webhook URL</label>
            <input type="password" id="notifSlackWebhook" placeholder="https://hooks.slack.com/services/...">
            <div class="hint">Create an Incoming Webhook in Slack App settings</div>
          </div>
        </div>

        <div class="form-group" style="margin-top:12px">
          <label class="form-checkbox">
            <input type="checkbox" id="notifActive" checked> Active
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">➕ Add Target</button>
      </div>
    </form>
  `);
}

window.updateNotifForm = function() {
  const type = document.getElementById('notifType').value;
  document.getElementById('notifTelegramFields').style.display = type === 'telegram' ? '' : 'none';
  document.getElementById('notifDiscordFields').style.display = type === 'discord' ? '' : 'none';
  document.getElementById('notifSlackFields').style.display = type === 'slack' ? '' : 'none';
};

async function handleAddNotifTarget(event) {
  event.preventDefault();
  const type = document.getElementById('notifType').value;
  let config = {};

  if (type === 'telegram') {
    config = {
      bot_token: document.getElementById('notifTelegramBotToken').value,
      chat_id: document.getElementById('notifTelegramChatId').value,
    };
  } else if (type === 'discord') {
    config = { webhook_url: document.getElementById('notifDiscordWebhook').value };
  } else if (type === 'slack') {
    config = { webhook_url: document.getElementById('notifSlackWebhook').value };
  }

  const data = {
    name: document.getElementById('notifName').value,
    type: type,
    config: config,
    is_active: document.getElementById('notifActive')?.checked || true,
  };

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Adding...';
  btn.style.opacity = '0.6';

  try {
    await API.post('/notifications/targets', data);
    App.closeModal();
    App.toast('✅ Notification target added!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}

async function editNotifTarget(id) {
  App.closeModal();
  try {
    const res = await API.get('/notifications/targets');
    const targets = Array.isArray(res?.data) ? res.data : [];
    const t = targets.find(x => x.id === id);
    if (!t) { App.toast('Target not found', 'error'); return; }

    const config = t.config || {};
    const isTelegram = t.type === 'telegram';

    App.showModal(`
      <div class="modal-header">
        <h2>Edit Notification Target</h2>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>
      <form id="editNotifForm" onsubmit="return handleEditNotifTarget(event, '${id}')">
        <div class="modal-body">
          <div class="form-group">
            <label>Name</label>
            <input type="text" id="editNotifName" value="${t.name}" required>
          </div>
          <div class="form-group">
            <label>Type</label>
            <select id="editNotifType" onchange="var v=this.value;document.getElementById('editNotifConfig').style.display=v==='telegram'?'':'none';document.getElementById('editNotifWebhook').style.display=v!=='telegram'?'':'none'" required>
              <option value="telegram" ${t.type === 'telegram' ? 'selected' : ''}>Telegram</option>
              <option value="discord" ${t.type === 'discord' ? 'selected' : ''}>Discord</option>
              <option value="slack" ${t.type === 'slack' ? 'selected' : ''}>Slack</option>
            </select>
          </div>
          <div id="editNotifConfig" style="${isTelegram ? '' : 'display:none'}">
            <div class="form-group">
              <label>Bot Token <span style="color:var(--text-tertiary);font-size:11px">(leave blank to keep)</span></label>
              <input type="password" id="editNotifBotToken" value="${config.bot_token || ''}" placeholder="••••••••">
            </div>
            <div class="form-group">
              <label>Chat ID</label>
              <input type="text" id="editNotifChatId" value="${config.chat_id || ''}">
            </div>
          </div>
          <div id="editNotifWebhook" style="${!isTelegram ? '' : 'display:none'}">
            <div class="form-group">
              <label>Webhook URL <span style="color:var(--text-tertiary);font-size:11px">(leave blank to keep)</span></label>
              <input type="password" id="editNotifWebhookUrl" value="${config.webhook_url || ''}" placeholder="••••••••">
            </div>
          </div>
          <div class="form-group" style="margin-top:12px">
            <label class="form-checkbox">
              <input type="checkbox" id="editNotifActive" ${t.is_active ? 'checked' : ''}> Active
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
          <button type="submit" class="btn btn-primary">💾 Save</button>
        </div>
      </form>
    `);
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

async function handleEditNotifTarget(event, id) {
  event.preventDefault();
  const type = document.getElementById('editNotifType').value;
  let config = {};

  if (type === 'telegram') {
    const bt = document.getElementById('editNotifBotToken').value;
    const ci = document.getElementById('editNotifChatId').value;
    if (bt) config.bot_token = bt;
    if (ci) config.chat_id = ci;
  } else {
    const wu = document.getElementById('editNotifWebhookUrl').value;
    if (wu) config.webhook_url = wu;
  }

  const data = {
    name: document.getElementById('editNotifName').value,
    type: type,
    is_active: document.getElementById('editNotifActive')?.checked || false,
  };
  if (Object.keys(config).length > 0) data.config = config;

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Saving...';
  btn.style.opacity = '0.6';

  try {
    await API.put(`/notifications/targets/${id}`, data);
    App.closeModal();
    App.toast('✅ Target updated!', 'success');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}

async function testNotifTarget(event, id) {
  const btn = event?.target;
  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }

  // Read event type from dropdown
  const sel = document.getElementById('testEvt_' + id);
  const eventType = sel ? sel.value : 'test';

  try {
    const payload = { event_type: eventType };
    if (eventType === 'test') {
      payload.message = '🔔 Arus: This is a test notification — your notification target is configured correctly!';
    }
    const result = await API.post(`/notifications/targets/${id}/test`, payload);
    const label = sel ? sel.options[sel.selectedIndex].text : 'Default Test';
    App.toast(`✅ ${label} sent!`, 'success');
  } catch (err) {
    App.toast('❌ ' + err.message, 'error');
  }

  if (btn) { btn.disabled = false; btn.textContent = '📨 Test'; }
}

async function deleteNotifTarget(id) {
  if (!confirm('Delete this notification target? It will be removed from all pipelines.')) return;
  try {
    await API.del(`/notifications/targets/${id}`);
    App.toast('Target deleted', 'info');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

// ===== Pipeline notification link management =====

async function showPipelineNotifConfig(pipelineId, pipelineName) {
  App.showModal(`
    <div class="modal-header">
      <h2>Notifications — ${pipelineName}</h2>
      <button class="modal-close" onclick="App.closeModal()">✕</button>
    </div>
    <div class="modal-body" style="text-align:center;padding:40px">
      <div class="spinner"></div>
      <p style="color:var(--text-tertiary);font-size:13px;margin-top:12px">Loading notification links...</p>
    </div>
  `);

  try {
    const [targetsResp, linksResp] = await Promise.all([
      API.get('/notifications/targets').catch(() => ({data: []})),
      API.get(`/notifications/links/${pipelineId}`).catch(() => ({data: []})),
    ]);

    const targetList = Array.isArray(targetsResp?.data) ? targetsResp.data : [];
    const linkList = Array.isArray(linksResp?.data) ? linksResp.data : [];

    const modal = document.querySelector('.modal');
    if (!modal) return;

    // Build linked targets summary
    const linkedHtml = linkList.length > 0 ? linkList.map(l => {
      const events = (l.event_types || []).join(', ');
      return `
        <div class="notif-item" style="margin-bottom:8px">
          <label class="notif-target-label">
            <span class="notif-target-name">${getNotifIcon(l.target_type)} ${l.target_name}</span>
            <span class="tag ${l.target_type === 'telegram' ? 'blue' : l.target_type === 'discord' ? 'purple' : 'green'}" style="font-size:10px">${l.target_type}</span>
            <span style="margin-left:auto;display:flex;gap:4px">
              <button class="btn btn-ghost btn-xs" onclick="editPipelineNotifLink('${l.id}', '${pipelineId}', '${pipelineName}')">✏</button>
              <button class="btn btn-ghost btn-xs" style="color:var(--red)" onclick="deletePipelineNotifLink('${l.id}', '${pipelineId}')">✕</button>
            </span>
          </label>
          <div style="font-size:11px;color:var(--text-tertiary);padding:2px 0 0 26px">
            Events: <span style="color:var(--emerald)">${events}</span>
          </div>
        </div>
      `;
    }).join('') : '<p style="color:var(--text-tertiary);font-size:13px;padding:12px 0">No notification targets linked to this pipeline.</p>';

    modal.innerHTML = `
      <div class="modal-header">
        <h2>Notifications — ${pipelineName}</h2>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <h3 style="margin-bottom:8px;font-size:14px">Linked Targets</h3>
        <div style="margin-bottom:20px">
          ${linkedHtml}
        </div>

        <h3 style="margin-bottom:8px;font-size:14px">Link a Target</h3>
        ${targetList.length > 0 ? `
        <form id="linkNotifForm" onsubmit="return handleLinkNotif(event, '${pipelineId}')">
          <div class="form-group">
            <label>Target</label>
            <select id="linkTargetId" required>
              <option value="">— Select —</option>
              ${targetList.filter(t => t.is_active).map(t => `
                <option value="${t.id}">${getNotifIcon(t.type)} ${t.name} (${t.type})${linkList.some(l => l.target_id === t.id) ? ' — already linked' : ''}</option>
              `).join('')}
            </select>
          </div>
          <div class="form-group">
            <label>Events</label>
            <div class="notif-event-grid">
              <label class="form-checkbox"><input type="checkbox" name="events" value="failure" checked> ✕ Failure</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="success"> ✓ Success</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="dead_letter"> ⎔ Dead Letter</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="schema_drift"> ⇄ Schema Drift</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="quality_breach"> ◈ Quality Breach</label>
            </div>
          </div>
          <div class="modal-actions" style="margin-top:12px;">
            <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Done</button>
            <button type="submit" class="btn btn-primary">🔗 Link Target</button>
          </div>
        </form>
        ` : `
        <div style="padding:12px;background:var(--amber-dim);border-radius:var(--radius-sm);font-size:12px;color:var(--amber);margin-bottom:8px">
          No notification targets configured. <a href="#" onclick="App.closeModal();location.hash='notifications'" style="color:var(--emerald)">Add a target first</a>.
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Done</button>
        </div>
        `}
      </div>
    `;
  } catch (err) {
    const modal = document.querySelector('.modal');
    if (modal) {
      modal.innerHTML = `
        <div class="modal-header">
          <h2>Notifications — ${pipelineName}</h2>
          <button class="modal-close" onclick="App.closeModal()">✕</button>
        </div>
        <div class="modal-body" style="text-align:center;padding:40px">
          <div style="font-size:48px;margin-bottom:12px;opacity:0.5">⚠️</div>
          <h3>Error</h3>
          <p style="color:var(--text-tertiary);font-size:13px">${err.message}</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
        </div>
      `;
    }
  }
}

async function handleLinkNotif(event, pipelineId) {
  event.preventDefault();
  const targetId = document.getElementById('linkTargetId').value;
  if (!targetId) { App.toast('Select a target', 'error'); return false; }

  const checkboxes = document.querySelectorAll('input[name="events"]:checked');
  const eventTypes = Array.from(checkboxes).map(cb => cb.value);

  if (eventTypes.length === 0) {
    App.toast('Select at least one event type', 'error');
    return false;
  }

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Linking...';
  btn.style.opacity = '0.6';

  try {
    await API.post('/notifications/links', {
      pipeline_id: pipelineId,
      target_id: targetId,
      event_types: eventTypes,
    });
    App.toast('✅ Target linked!', 'success');
    showPipelineNotifConfig(pipelineId, document.querySelector('.modal h2')?.textContent?.replace('Notifications — ', '') || pipelineId);
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}

async function editPipelineNotifLink(linkId, pipelineId, pipelineName) {
  App.closeModal();
  try {
    // Fetch current link data to pre-fill the form
    const linksResp = await API.get(`/notifications/links/${pipelineId}`);
    const links = Array.isArray(linksResp?.data) ? linksResp.data : [];
    const link = links.find(l => l.id === linkId);
    if (!link) { App.toast('Link not found', 'error'); return; }

    const events = link.event_types || [];

    App.showModal(`
      <div class="modal-header">
        <h2>Edit Pipeline Notification</h2>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>
      <form id="editPipelineNotifForm" onsubmit="return handleEditPipelineNotif(event, '${linkId}', '${pipelineId}', '${pipelineName}')">
        <div class="modal-body">
          <div class="form-group">
            <label>Target</label>
            <div style="display:flex;align-items:center;gap:8px;padding:8px 0">
              ${getNotifIcon(link.target_type)} <strong>${link.target_name}</strong>
              <span class="tag ${link.target_type === 'telegram' ? 'blue' : link.target_type === 'discord' ? 'purple' : 'green'}" style="font-size:10px">${link.target_type}</span>
            </div>
          </div>
          <div class="form-group">
            <label>Event Types</label>
            <div class="notif-event-grid">
              <label class="form-checkbox"><input type="checkbox" name="events" value="failure" ${events.includes('failure') ? 'checked' : ''}> ✕ Failure</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="success" ${events.includes('success') ? 'checked' : ''}> ✓ Success</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="dead_letter" ${events.includes('dead_letter') ? 'checked' : ''}> ⎔ Dead Letter</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="schema_drift" ${events.includes('schema_drift') ? 'checked' : ''}> ⇄ Schema Drift</label>
              <label class="form-checkbox"><input type="checkbox" name="events" value="quality_breach" ${events.includes('quality_breach') ? 'checked' : ''}> ◈ Quality Breach</label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
          <button type="button" class="btn btn-danger" style="color:var(--red);border-color:var(--red);margin-right:auto" onclick="deletePipelineNotifLink('${linkId}', '${pipelineId}') && false">🗑 Delete</button>
          <button type="submit" class="btn btn-primary">💾 Save</button>
        </div>
      </form>
    `);
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

async function handleEditPipelineNotif(event, linkId, pipelineId, pipelineName) {
  event.preventDefault();

  const checkboxes = document.querySelectorAll('#editPipelineNotifForm input[name="events"]:checked');
  const eventTypes = Array.from(checkboxes).map(cb => cb.value);

  if (eventTypes.length === 0) {
    App.toast('Select at least one event type', 'error');
    return false;
  }

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Saving...';
  btn.style.opacity = '0.6';

  try {
    await API.put(`/notifications/links/${linkId}`, { event_types: eventTypes });
    App.toast('✅ Link updated!', 'success');
    showPipelineNotifConfig(pipelineId, pipelineName);
  } catch (err) {
    App.toast(err.message, 'error');
    btn.disabled = false;
    btn.textContent = orig;
    btn.style.opacity = '1';
  }
  return false;
}

async function deletePipelineNotifLink(linkId, pipelineId) {
  if (!confirm('Remove this notification link?')) return;
  try {
    await API.del(`/notifications/links/${linkId}`);
    App.toast('Link removed', 'info');
    App.render();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

// Globals
window.renderNotificationsPage = renderNotificationsPage;
window.showAddNotifTargetModal = showAddNotifTargetModal;
window.handleAddNotifTarget = handleAddNotifTarget;
window.editNotifTarget = editNotifTarget;
window.handleEditNotifTarget = handleEditNotifTarget;
window.testNotifTarget = testNotifTarget;
window.deleteNotifTarget = deleteNotifTarget;
window.showPipelineNotifConfig = showPipelineNotifConfig;
window.handleLinkNotif = handleLinkNotif;
window.editPipelineNotifLink = editPipelineNotifLink;
window.handleEditPipelineNotif = handleEditPipelineNotif;
window.deletePipelineNotifLink = deletePipelineNotifLink;
