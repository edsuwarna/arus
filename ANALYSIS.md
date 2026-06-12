# Arus Console — Gap Analysis & Improvement Roadmap

## Files Analysed

| File | Summary |
|------|---------|
| `console/js/pages/dashboard.js` | Dashboard with stat cards (active sources, pipelines, rows, failures), mock bar chart, recent runs list, sources overview table |
| `console/js/pages/sources.js` | Source cards grid, discovered tables with checkboxes, CRUD modals (add/edit/manage/test/delete), schema filter, table-level load mode config |
| `console/js/pages/runs.js` | Basic run history table (last 50 runs), status/duration/rows/trigger columns, log viewer |
| `console/js/pages/users.js` | User table with CRUD, role management (viewer/editor/admin), active status toggle |
| `console/js/pages/notifications.js` | Notification targets CRUD (Telegram/Discord/Slack), pipeline notification linking with event types |
| `console/js/pages/dag.js` | DAG graph with 3-layer model (source/raw/target), SVG rendering, zoom/pan, node detail panel with run history |
| `console/js/pages/pipelines.js` | Pipelines list, create pipeline modal (with notification linking), destinations CRUD, settings page (general/quality/notification toggles) |
| `console/js/pages/pipeline-detail.js` | Pipeline flow diagram, stats, tables with transforms (8 step types), run history, full refresh, backfill, dead letter viewer, edit config |
| `console/js/app.js` | SPA router, auth guard, sidebar rendering, header, toast system, modal manager |
| `console/css/style.css` | 1532-line design system, dark theme, responsive breakpoints at 1024/768/480px |
| `arus/modules/notification/` | Backend: target CRUD, pipeline link CRUD, senders (Telegram/Discord/Slack), 6 template builders (test/success/failure/dead_letter/schema_drift/quality_breach) |
| `arus/modules/settings/router.py` | DB-persisted key-value settings with defaults, GET/PUT API |
| `arus/main.py` | FastAPI app with 10 routers, seeding, scheduler startup |
| `arus/modules/pipeline/router.py` | Pipeline CRUD, trigger/pause/resume/pause-all/full-refresh/backfill/dead-letters |
| `arus/modules/dag/router.py` | Returns 3-layer asset graph per pipeline |

---

## CONCRETE GAPS

### 1. MISSING PAGES / VIEWS

| Missing Page | Why It Matters |
|---|---|
| **Transform Studio** — dedicated page for building/managing transform pipelines | Transforms are only configurable inline per-table in pipeline detail; no global view |
| **Dead Letters Dashboard** — searchable, filterable dead letter queue | Currently only accessible via pipeline detail dropdown; no cross-pipeline dead letter overview |
| **Alert History** — log of all sent notifications | No way to see what alerts were fired, to whom, and whether they succeeded |
| **Audit Log** — user action history | No compliance/security trail for who changed what |
| **Data Catalog** — searchable table catalog across all sources | No ability to discover/explore data assets globally |
| **API Tokens / Service Accounts** | No programmatic access management |
| **Incidents / Pipeline Health Center** | No centralized view of all failing pipelines across the instance |
| **Billing / Usage** | No cost/usage tracking |

### 2. BROKEN / INCOMPLETE UX PATTERNS

| Location | Issue | Severity |
|---|---|---|
| `dashboard.js:128-138` | Bar chart is **completely fake** — always renders same 7-day pattern regardless of actual data | 🔴 High |
| `notifications.js:314` | `testNotifTarget()` references `event?.target` without an `event` parameter — will crash if called directly | 🔴 High |
| `notifications.js:499` | Edit pipeline notification link explicitly says "For now, just delete and re-add" | 🟡 Medium |
| `notifications.js:232-253` | Edit notification modal's Discord/Slack fields don't toggle properly — only Telegram is handled | 🟡 Medium |
| `pipeline-detail.js:358` | DAG detail panel run table has hardcoded `-` for "Rows" column | 🟡 Medium |
| `sources.js:368-370` | `toggleTable()` is an empty no-op function | 🟡 Medium |
| `pipelines.js:248-256` | "Pause All" has zero confirmation — immediate action with no undo | 🟡 Medium |
| `app.js:99-102` | Search bar is decorative — doesn't actually filter anything | 🟡 Medium |
| `app.js:101` | Notification bell always shows "No new notifications" — feature placeholder | 🟢 Low |
| All pages | Delete operations use native `confirm()` dialogs instead of modal confirmation | 🟢 Low |
| All pages | No loading skeletons — only spinner + text | 🟢 Low |

### 3. MISSING ERROR HANDLING

| Location | Issue |
|---|---|
| `dashboard.js:7-8` | Dashboard silently catches API errors — returns `{}` / `[]` with no user feedback if dashboard endpoints fail |
| `sources.js:29-32` | Sources list fetch silently catches errors with empty catch block |
| All pages | No retry mechanism — user must click "Refresh" manually |
| All pages | No global error boundary — an unhandled exception in one page's render could break the entire SPA |
| `app.js:210-222` | Toast notifications auto-dismiss after 3s with no persistent history |
| All API calls | No request timeout handling — could hang indefinitely |
| `pipeline-detail.js:170-172` | Pipeline detail error state is a generic ⚠️ icon — no retry button |

### 4. MISSING FEATURES IN EXISTING PAGES

#### Dashboard
- No time-range selector (only hardcoded "Last 7 days")
- No trend indicators (week-over-week comparison)
- No top errors/incidents widget
- No pipeline health overview chart
- No data volume breakdown by source/destination
- No auto-refresh capability

#### Sources
- **Table filters input exists in form (line 450) but is NEVER sent to API** — the `handleAddSource` function ignores `srcFilters`
- No SSH tunnel / SSL config in connection form
- No connection pooling controls
- No source throughput/lag metrics
- No table column preview after discovery
- Cannot reorder or hide discovered table columns
- Table-level sync mode cannot be changed (only load mode)

#### Runs
- **No pagination** — only shows last 50 runs
- No filtering by pipeline, status, date range
- No column sorting
- No run comparison / diff view
- No export to CSV/JSON
- No bulk re-run of failed runs

#### Pipelines
- No multi-select for bulk actions (bulk pause/resume/trigger)
- No pipeline cloning/duplication
- No pipeline versioning or rollback
- No table-level sync mode override from pipeline detail page
- Pipeline list doesn't show source/destination names clearly

#### DAG View
- No minimap for large DAGs with many nodes
- Layout algorithm is basic (column-based, no edge routing optimization)
- No auto-refresh of DAG state
- No error indicators on edges between nodes
- Node names can be ambiguous when same table name exists in source and target layer

#### Notifications
- No notification history / delivery log
- No templates customization in UI
- Event types are hardcoded (failure/success/dead_letter/schema_drift/quality_breach)
- No notification quiet hours / throttling
- No test for Slack/Discord-specific formatting issues

#### Settings
- **Settings page always fetches from API but saves use hardcoded IDs** — mismatch if DOM IDs change
- `toggle` class toggling on click doesn't send immediate update — requires manual "Save Changes"
- No email server config
- No retention policy config
- No webhook/system integration settings
- No SSO/OAuth configuration
- No feature flags

#### Users
- No password strength indicator
- No email verification flow
- No 2FA / MFA
- No session management (list active sessions)
- No invite-by-email flow

### 5. MISSING API ENDPOINTS (Frontend calls endpoints not found in backend)

| Endpoint Referenced In | Used In | Backend Status |
|---|---|---|
| `GET /pipelines/{id}/runs` | `pipeline-detail.js:8` | May exist in run_log router |
| `GET /runs/{id}/logs` | `pipeline-detail.js:225` | May exist in run_log router |
| `GET /pipelines/{id}/scripts` | `pipeline-detail.js:448` | May exist in transform router |
| `POST /pipelines/{id}/full-refresh` | `pipeline-detail.js:270` | ✅ Exists |
| `POST /pipelines/{id}/backfill` | `pipeline-detail.js:315` | ✅ Exists |
| `PUT /sources/{id}/tables` | `sources.js:212` | May need verification |

### 6. CODE QUALITY CONCERNS

| File | Line | Issue |
|---|---|---|
| `notifications.js` | 314 | `testNotifTarget()` uses `event?.target` without declaring `event` parameter — will throw in strict mode |
| `notifications.js` | 499 | Comment: "// For now, just delete and re-add is the simplest UX" — unfinished feature |
| `templates.py` | 72-81 | All notification builders fall back to hardcoded demo data when no pipeline context is provided |
| `settings/router.py` | 82-99 | Settings PUT accepts any dict with no validation beyond key check — silently ignores unknown keys |
| `dashboard.js` | 128-138 | Mock bar chart with hardcoded day distribution, no real API data |
| `sources.js` | 368-370 | `toggleTable()` is defined as a no-op with comment "Could send update to API" |
| `pipeline-detail.js` | 358 | Run row in DAG panel hardcodes `-` for rows_synced |
| `style.css` | 661-665 | Empty CSS rules for `.source-card .sc-icon.*` selectors |

### 7. MISSING SETTINGS (Backend defaults vs UI coverage)

The `DEFAULT_SETTINGS` dict in `settings/router.py` defines these keys:
- `pipeline_name_prefix`, `default_schedule`, `auto_discover_tables`, `schema_drift_detection`, `auto_alter_schema`, `max_retries`, `initial_backoff`, `quality_check_threshold`, `notify_pipeline_failures`, `notify_schema_drift`, `notify_dead_letter`

**Missing from UI** (in settings router but no toggle/input):
- `auto_alter_schema` — exists in defaults, not in UI
- `initial_backoff` — exists in defaults, not in UI

**Missing entirely** (neither in defaults nor UI):
- Warehouse data retention policy
- Backup/restore config
- Email server (SMTP)
- Rate limiting
- Notification quiet hours
- Session timeout / idle timeout
- Log retention
- Encryption at rest toggle

### 8. RESPONSIVE / ACCESSIBILITY GAPS

- Mobile sidebar toggle works but the DAG view isn't usable on mobile
- No ARIA labels on interactive elements
- Modals take full screen on mobile (acceptable) but no swipe-to-close
- No focus trapping within modals (keyboard accessibility issue)
- No high-contrast mode / theme toggle
- No reduced-motion support for animations

---

## PRIORITIZED IMPROVEMENT ROADMAP

### P0 — Critical Bugs
1. Fix `testNotifTarget` event parameter (will crash)
2. Fix edit notification modal toggling for Discord/Slack
3. Replace mock bar chart with real data from API
4. Implement `toggleTable` — currently a silent no-op

### P1 — UX Blockers
1. Add pagination to Runs page (currently capped at 50)
2. Enable table-level sync mode changes in sources
3. Add confirmation modal for "Pause All"
4. Implement pipeline notification link editing (currently "delete and re-add")
5. Send `table_filters` field to API from add-source form

### P2 — Feature Gaps
1. Build Dead Letters overview page (cross-pipeline)
2. Add notification history / delivery log
3. Add time-range selector to Dashboard
4. Source/Destination connection SSL/TLS config
5. Pipeline cloning
6. Search/filter on Runs page

### P3 — Nice to Have
1. Transform Studio page
2. Audit log
3. API tokens management
4. Data catalog page
5. Loading skeletons
6. Keyboard shortcuts
7. Global error boundary
