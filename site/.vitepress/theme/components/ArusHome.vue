<template>
  <div class="arus-home">
    <!-- Nav -->
    <nav class="nav">
      <div class="nav-inner">
        <div class="nav-left">
          <a href="/" class="logo">
            <span class="logo-icon">A</span>
            <span class="logo-text">Arus</span>
          </a>
          <div class="nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
            <a href="/guide/">Docs</a>
          </div>
        </div>
        <div class="nav-right">
          <a href="/guide/quickstart" class="btn btn-primary">Get Started</a>
        </div>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg-glow"></div>
      <div class="hero-content">
        <span class="hero-badge">LIGHTWEIGHT CDC &amp; ETL</span>
        <h1 class="hero-title">
          Data flows <span class="text-emerald">without the cluster.</span>
        </h1>
        <p class="hero-subtitle">
          A self-hosted CDC &amp; ETL platform that runs on a single VPS.
          No Kubernetes, no Kafka, no complexity.
          <strong>Just <code>docker compose up</code>.</strong>
        </p>
        <div class="hero-actions">
          <a href="/guide/quickstart" class="btn btn-primary btn-lg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Get Started
          </a>
        </div>
      </div>
      <div class="hero-diagram">
        <div class="dag-card">
          <div class="dag-header">
            <span class="dag-title">Pipeline: users_sync</span>
            <span class="dag-status status-active">Running</span>
          </div>
          <div class="dag-body">
            <div class="dag-layer">
              <span class="layer-label">Source</span>
              <div class="dag-nodes">
                <div class="dag-node source"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg> PostgreSQL</div>
                <div class="dag-node source"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg> MySQL</div>
                <div class="dag-node source"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg> MariaDB</div>
              </div>
            </div>
            <div class="dag-arrow"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg></div>
            <div class="dag-layer">
              <span class="layer-label">Raw</span>
              <div class="dag-nodes">
                <div class="dag-node raw"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg> users_raw</div>
                <div class="dag-node raw"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg> orders_raw</div>
              </div>
            </div>
            <div class="dag-arrow"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg></div>
            <div class="dag-layer">
              <span class="layer-label">Target</span>
              <div class="dag-nodes">
                <div class="dag-node target"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg> users</div>
                <div class="dag-node target"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg> orders</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Preview -->
    <section class="preview">
      <div class="screenshot-card">
        <img src="/sketches/arus-dashboard.png" alt="Arus Console Dashboard" class="screenshot" />
      </div>
    </section>

    <!-- Stats -->
    <section class="stats">
      <div class="stat-item">
        <span class="stat-value">3</span>
        <span class="stat-label">Supported Sources</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-value">2</span>
        <span class="stat-label">Sync Modes</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-value">3</span>
        <span class="stat-label">Containers</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-value">~200MB</span>
        <span class="stat-label">RAM Idle</span>
      </div>
    </section>

    <!-- Features -->
    <section id="features" class="features">
      <div class="section-header">
        <h2>Everything you need for data ingestion on a VPS.</h2>
      </div>
      <div class="features-grid">
        <div class="feature-card" v-for="f in features" :key="f.title">
          <div class="feature-icon" v-html="f.icon"></div>
          <h3 class="feature-title">{{ f.title }}</h3>
          <p class="feature-desc">{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Sources -->
    <section class="sources">
      <div class="section-header">
        <h2>Connect your databases.</h2>
      </div>
      <div class="source-logos">
        <div class="source-logo" v-for="s in sources" :key="s.name">
          <div class="source-icon" v-html="s.icon"></div>
          <span class="source-name">{{ s.name }}</span>
        </div>
        <div class="source-logo soon">
          <span class="source-icon">+</span>
          <span class="source-name">More coming</span>
        </div>
      </div>
    </section>

    <!-- How It Works -->
    <section id="how-it-works" class="how-it-works">
      <div class="section-header">
        <h2>Three steps to flowing data.</h2>
      </div>
      <div class="steps">
        <div class="step">
          <div class="step-number">1</div>
          <h3>Connect</h3>
          <p>Add your source database — PostgreSQL, MySQL, MariaDB, or MongoDB.</p>
        </div>
        <div class="step-connector"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg></div>
        <div class="step">
          <div class="step-number">2</div>
          <h3>Configure</h3>
          <p>Select tables, choose sync mode (full or incremental), and set scheduling.</p>
        </div>
        <div class="step-connector"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg></div>
        <div class="step">
          <div class="step-number">3</div>
          <h3>Monitor</h3>
          <p>Watch your data flow through the DAG dashboard with run history and alerts.</p>
        </div>
      </div>
    </section>

    <!-- Comparison -->
    <section class="comparison">
      <div class="section-header">
        <h2>Built for teams without a dedicated infra team.</h2>
      </div>
      <div class="table-wrap">
        <table class="compare-table">
          <thead>
            <tr>
              <th>Feature</th>
              <th class="col-emerald">Arus</th>
              <th>Airbyte OSS</th>
              <th>Debezium</th>
              <th>Custom Script</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in comparison" :key="row.feature">
              <td class="feature-name">{{ row.feature }}</td>
              <td class="col-emerald"><span :class="checkClass(row.arus)">{{ row.arus }}</span></td>
              <td>{{ row.airbyte }}</td>
              <td>{{ row.debezium }}</td>
              <td>{{ row.script }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Code -->
    <section class="code-section">
      <div class="section-header">
        <h2>One command to start.</h2>
      </div>
      <div class="code-blocks">
        <div class="code-block">
          <div class="code-header">
            <span>Copy &amp; paste in your terminal</span>
            <button class="copy-btn" @click="copyCode(0)">{{ copied === 0 ? 'Copied!' : 'Copy' }}</button>
          </div>
          <pre><code>cat > .env << EOF
ARUS_JWT_SECRET=$(openssl rand -hex 32)
ARUS_ENCRYPTION_KEY=$(openssl rand -hex 32)
ARUS_DB_USER=arus
ARUS_DB_PASSWORD=arus_secret
ARUS_DB_NAME=arus_warehouse
ARUS_ADMIN_EMAIL=admin@arus.io
ARUS_ADMIN_PASSWORD=admin123
POSTGRES_USER=arus
POSTGRES_PASSWORD=arus_secret
POSTGRES_DB=arus_warehouse
EOF

docker network create arus-net

docker run -d --network arus-net --name arus-db \
  -v arus-db-data:/var/lib/postgresql/data \
  --env-file .env \
  postgres:15-alpine

docker run -d --network arus-net --name arus-api -p 8081:8081 \
  -e ARUS_DB_HOST=arus-db \
  --env-file .env \
  registry.edsuwarna.xyz/arus-api:main-latest

docker run -d --network arus-net --name arus-console -p 8082:80 \
  registry.edsuwarna.xyz/arus-console:main-latest</code></pre>
        </div>
      </div>
      <p class="code-footnote">
        Your console will be at <a href="http://localhost:8082" style="color:#10b981">http://localhost:8082</a>
        &mdash; login with <code>ARUS_ADMIN_EMAIL</code> / <code>ARUS_ADMIN_PASSWORD</code> from your <code>.env</code> (defaults: <code>admin@arus.io</code> / <code>admin123</code>)
      </p>
    </section>

    <!-- CTA -->
    <section class="cta">
      <div class="cta-card">
        <h2>Ready to ship data pipelines <span class="text-emerald">without the overhead?</span></h2>
        <p>Get Arus running on your VPS in under 10 minutes.</p>
        <div class="cta-actions">
          <a href="/guide/quickstart" class="btn btn-primary btn-lg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Get Started
          </a>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-col">
          <h4>Product</h4>
          <a href="#features">Features</a>
          <a href="#how-it-works">How It Works</a>
          <a href="/guide/">Documentation</a>
        </div>
        <div class="footer-col">
          <h4>Resources</h4>
          <a href="/guide/architecture">Architecture</a>
          <a href="/reference/api">API Reference</a>
          <a href="/guide/deployment">Deployment</a>
        </div>
        <div class="footer-col">
          <h4>Support</h4>
          <a href="/guide/quickstart">Quickstart</a>
          <a href="/guide/">Documentation</a>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; 2024-2026 Endang Suwarna.</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const copied = ref(null)

function copyCode(idx) {
  const codes = [
    'cat > .env << EOF\nARUS_JWT_SECRET=$(openssl rand -hex 32)\nARUS_ENCRYPTION_KEY=$(openssl rand -hex 32)\nARUS_DB_USER=arus\nARUS_DB_PASSWORD=arus_secret\nARUS_DB_NAME=arus_warehouse\nARUS_ADMIN_EMAIL=admin@arus.io\nARUS_ADMIN_PASSWORD=admin123\nPOSTGRES_USER=arus\nPOSTGRES_PASSWORD=arus_secret\nPOSTGRES_DB=arus_warehouse\nEOF\n\ndocker network create arus-net\n\ndocker run -d --network arus-net --name arus-db \\\n  -v arus-db-data:/var/lib/postgresql/data \\\n  --env-file .env \\\n  postgres:15-alpine\n\ndocker run -d --network arus-net --name arus-api -p 8081:8081 \\\n  -e ARUS_DB_HOST=arus-db \\\n  --env-file .env \\\n  registry.edsuwarna.xyz/arus-api:main-latest\n\ndocker run -d --network arus-net --name arus-console -p 8082:80 \\\n  registry.edsuwarna.xyz/arus-console:main-latest',
  ]
  navigator.clipboard.writeText(codes[idx])
  copied.value = idx
  setTimeout(() => { copied.value = null }, 2000)
}

const features = [
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>', title: 'CDC & ETL', desc: 'Built-in change data capture with watermark-based incremental sync. No Kafka dependency.' },
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', title: 'Auto-discover Tables', desc: 'Automatically detects source tables, maps columns and data types to your warehouse.' },
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>', title: 'Visual DAG', desc: 'Interactive DAG visualization showing pipeline structure and real-time run status.' },
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>', title: 'Scheduling', desc: 'APScheduler cron-based scheduling with configurable intervals and auto-retry.' },
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>', title: 'Schema Drift Detection', desc: 'Automatic detection of column changes and optional auto-ALTER to keep in sync.' },
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>', title: 'Alerting', desc: 'Send notifications to Telegram, Discord, or Slack on pipeline failures and anomalies.' },
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', title: 'Run History & Logs', desc: 'Full audit trail of pipeline runs with structured logs and performance metrics.' },
  { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>', title: 'Dead Letter Queue', desc: 'Failed rows are captured and stored for inspection without blocking pipeline execution.' },
]

const sources = [
  { name: 'PostgreSQL', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>' },
  { name: 'MySQL', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>' },
  { name: 'MariaDB', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>' },
]

const comparison = [
  { feature: 'Kubernetes required', arus: '❌ No', airbyte: '✅ Yes', debezium: '❌ No*', script: '❌ No' },
  { feature: 'DAG / Pipeline UI', arus: '✅ Built-in', airbyte: '✅ Basic', debezium: '❌', script: '❌' },
  { feature: 'Setup time', arus: '2 hours', airbyte: '1-2 days', debezium: '3-5 days', script: '1 hour (no UI)' },
  { feature: 'RAM usage (idle)', arus: '~200MB', airbyte: '~2GB', debezium: '~3GB+', script: '~100MB' },
  { feature: 'Auto-retry', arus: '✅', airbyte: '✅', debezium: '✅', script: '❌' },
  { feature: 'Schema drift handling', arus: '✅ Auto', airbyte: '✅ Auto', debezium: '✅', script: '❌' },
  { feature: 'Dead letter queue', arus: '✅', airbyte: '✅', debezium: '❌', script: '❌' },
  { feature: 'Connector language', arus: 'Python', airbyte: 'Python', debezium: 'Java', script: 'Anything' },
]

function checkClass(v) {
  return v.startsWith('✅') || v.includes('Built-in') || v.includes('2 hours') || v.includes('~200MB') || v.includes('Auto') || v.includes('Python') ? 'check' : ''
}
</script>

<style scoped>
/* === RESET === */
* { margin: 0; padding: 0; box-sizing: border-box; }

.arus-home {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0b0d11;
  color: #e8eaed;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
}

/* Hide VitePress default footer on custom layout */
.arus-home ~ .VPFooter,
.arus-home + footer,
.arus-home ~ footer {
  display: none !important;
}

.text-emerald { color: #10b981; }

/* === NAV === */
.nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(11,13,17,0.85); backdrop-filter: blur(12px);
  border-bottom: 1px solid #23262e;
}
.nav-inner {
  max-width: 1200px; margin: 0 auto; padding: 0 24px;
  display: flex; align-items: center; height: 64px; justify-content: space-between;
}
.nav-left { display: flex; align-items: center; gap: 32px; }
.logo { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 18px; color: #e8eaed; text-decoration: none; letter-spacing: -0.3px; }
.logo-icon {
  width: 30px; height: 30px;
  background: linear-gradient(135deg, #10b981, #059669);
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px; color: #fff; flex-shrink: 0;
}
.nav-links { display: flex; gap: 24px; }
.nav-links a { color: #9aa0a8; font-size: 14px; font-weight: 500; text-decoration: none; transition: color 0.2s; }
.nav-links a:hover { color: #e8eaed; }
.nav-right { display: flex; align-items: center; gap: 16px; }

/* === BUTTONS === */
.btn {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: inherit; font-size: 14px; font-weight: 500;
  padding: 10px 20px; border-radius: 6px;
  border: none; cursor: pointer; text-decoration: none;
  transition: all 0.2s;
}
.btn-primary { background: #10b981; color: #fff; }
.btn-primary:hover { background: #059669; }
.btn-outline { background: transparent; color: #e8eaed; border: 1px solid #23262e; }
.btn-outline:hover { background: #1c1f26; border-color: #2a2d35; }
.btn-lg { padding: 14px 28px; font-size: 15px; border-radius: 8px; }

/* === HERO === */
.hero {
  padding: 160px 24px 80px; max-width: 1200px; margin: 0 auto;
  display: flex; flex-direction: column; align-items: center; text-align: center;
  position: relative;
}
.hero-bg-glow {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: 700px; height: 700px;
  background: radial-gradient(circle, rgba(16,185,129,0.06) 0%, transparent 70%);
  pointer-events: none;
}
.hero-content { position: relative; z-index: 1; max-width: 720px; }
.hero-badge {
  display: inline-block; padding: 6px 14px; border-radius: 100px;
  background: rgba(16,185,129,0.1); color: #10b981;
  font-size: 12px; font-weight: 600; letter-spacing: 1px;
  margin-bottom: 20px;
}
.hero-title { font-size: 56px; font-weight: 800; line-height: 1.1; letter-spacing: -1.5px; margin-bottom: 16px; }
.hero-subtitle { font-size: 18px; color: #9aa0a8; margin-bottom: 32px; }
.hero-subtitle code { background: #1c1f26; padding: 2px 8px; border-radius: 4px; font-size: 15px; color: #10b981; }
.hero-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }

/* DAG Card */
.hero-diagram { margin-top: 48px; position: relative; z-index: 1; }
.dag-card {
  background: #14171d; border: 1px solid #23262e; border-radius: 12px;
  padding: 20px; width: 560px;
}
.dag-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.dag-title { font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono', monospace; color: #9aa0a8; }
.dag-status { font-size: 11px; padding: 3px 10px; border-radius: 100px; font-weight: 500; }
.status-active { background: rgba(16,185,129,0.12); color: #10b981; }
.dag-body { display: flex; align-items: center; justify-content: center; gap: 12px; }
.dag-layer { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.layer-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #5c626e; font-weight: 600; }
.dag-nodes { display: flex; flex-direction: column; gap: 6px; }
.dag-node {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 14px; border-radius: 6px; font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
}
.dag-node.source { background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); color: #93c5fd; }
.dag-node.raw { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.2); color: #fcd34d; }
.dag-node.target { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); color: #6ee7b7; }
.dag-arrow { color: #5c626e; display: flex; align-items: center; }

/* === PREVIEW === */
.preview {
  max-width: 1100px; margin: 0 auto; padding: 0 24px 48px;
}
.screenshot-card {
  background: #14171d; border: 1px solid #23262e; border-radius: 12px;
  overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}
.screenshot {
  display: block; width: 100%; height: auto;
}

/* === STATS === */
.stats {
  max-width: 800px; margin: 0 auto; padding: 48px 24px;
  display: flex; align-items: center; justify-content: center; gap: 32px;
}
.stat-item { text-align: center; }
.stat-value { display: block; font-size: 36px; font-weight: 800; color: #10b981; letter-spacing: -1px; }
.stat-label { font-size: 14px; color: #5c626e; margin-top: 4px; }
.stat-divider { width: 1px; height: 48px; background: #23262e; }

/* === SECTION === */
.section-header { text-align: center; margin-bottom: 48px; }
.section-header h2 { font-size: 32px; font-weight: 700; letter-spacing: -0.5px; }

/* === FEATURES === */
.features { max-width: 1200px; margin: 0 auto; padding: 80px 24px; }
.features-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
}
.feature-card {
  background: #14171d; border: 1px solid #23262e; border-radius: 12px;
  padding: 24px; transition: border-color 0.2s, transform 0.2s;
}
.feature-card:hover { border-color: #10b981; transform: translateY(-2px); }
.feature-icon { color: #10b981; margin-bottom: 14px; }
.feature-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.feature-desc { font-size: 14px; color: #9aa0a8; line-height: 1.6; }

/* === SOURCES === */
.sources { max-width: 800px; margin: 0 auto; padding: 80px 24px; }
.source-logos { display: flex; justify-content: center; gap: 32px; flex-wrap: wrap; }
.source-logo {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 24px 32px; background: #14171d; border: 1px solid #23262e;
  border-radius: 12px; min-width: 120px;
}
.source-logo.soon { opacity: 0.5; }
.source-icon { display: flex; align-items: center; justify-content: center; }
.source-name { font-size: 14px; font-weight: 500; }

/* === HOW IT WORKS === */
.how-it-works { max-width: 1000px; margin: 0 auto; padding: 80px 24px; }
.steps { display: flex; align-items: center; justify-content: center; gap: 16px; }
.step { text-align: center; flex: 1; }
.step-number {
  width: 48px; height: 48px; border-radius: 50%;
  background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3);
  color: #10b981; font-size: 20px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 16px;
}
.step h3 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
.step p { font-size: 14px; color: #9aa0a8; line-height: 1.6; max-width: 260px; margin: 0 auto; }
.step-connector { color: #5c626e; flex-shrink: 0; }

/* === COMPARISON === */
.comparison { max-width: 1000px; margin: 0 auto; padding: 80px 24px; }
.table-wrap { overflow-x: auto; }
.compare-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; }
.compare-table th, .compare-table td { padding: 14px 20px; text-align: left; border-bottom: 1px solid #23262e; }
.compare-table th { font-weight: 600; color: #9aa0a8; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
.compare-table thead tr th:first-child { width: 200px; }
.compare-table .col-emerald { color: #10b981; font-weight: 500; }
.compare-table tbody tr:hover { background: rgba(255,255,255,0.02); }
.feature-name { color: #9aa0a8; }
.check { color: #10b981; }

/* === CODE SECTION === */
.code-section { max-width: 700px; margin: 0 auto; padding: 80px 24px; }
.code-blocks { display: flex; flex-direction: column; gap: 16px; }
.code-block {
  background: #111318; border: 1px solid #23262e; border-radius: 12px; overflow: hidden;
}
.code-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: #191b21; border-bottom: 1px solid #23262e;
  font-size: 12px; color: #5c626e; font-weight: 500;
}
.code-header button {
  background: transparent; border: 1px solid #23262e; border-radius: 4px;
  color: #9aa0a8; font-size: 11px; padding: 4px 10px; cursor: pointer;
  font-family: inherit; transition: all 0.2s;
}
.code-header button:hover { border-color: #10b981; color: #10b981; }
.code-block pre {
  padding: 16px; overflow-x: auto;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.7;
  color: #e8eaed;
}
.code-block code { background: none; padding: 0; }

.code-footnote {
  text-align: center; margin-top: 16px; font-size: 14px; color: #9aa0a8;
}
.code-footnote code {
  background: #1c1f26; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #e8eaed;
}

/* === CTA === */
.cta { max-width: 800px; margin: 0 auto; padding: 80px 24px; }
.cta-card {
  background: linear-gradient(135deg, #14171d, #111318);
  border: 1px solid #23262e; border-radius: 16px;
  padding: 64px 48px; text-align: center;
}
.cta-card h2 { font-size: 32px; font-weight: 700; margin-bottom: 12px; }
.cta-card p { color: #9aa0a8; font-size: 16px; margin-bottom: 32px; }
.cta-actions { display: flex; gap: 12px; justify-content: center; }

/* === FOOTER === */
.footer {
  border-top: 1px solid #23262e; padding: 48px 24px 24px;
}
.footer-inner {
  max-width: 1000px; margin: 0 auto; display: flex; gap: 80px;
  justify-content: center; margin-bottom: 32px;
}
.footer-col { display: flex; flex-direction: column; gap: 8px; }
.footer-col h4 { font-size: 12px; font-weight: 600; color: #5c626e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.footer-col a { color: #9aa0a8; font-size: 14px; text-decoration: none; transition: color 0.2s; }
.footer-col a:hover { color: #e8eaed; }
.footer-bottom { text-align: center; font-size: 13px; color: #5c626e; }

/* === RESPONSIVE === */
@media (max-width: 768px) {
  .hero-title { font-size: 36px; }
  .nav-links { display: none; }
  .features-grid { grid-template-columns: 1fr; }
  .steps { flex-direction: column; }
  .step-connector { transform: rotate(90deg); }
  .stats { gap: 16px; flex-wrap: wrap; }
  .dag-card { width: 100%; }
  .dag-body { flex-direction: column; }
  .dag-arrow { transform: rotate(90deg); }
  .footer-inner { gap: 40px; flex-wrap: wrap; }
}
</style>
