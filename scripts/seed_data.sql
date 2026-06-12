-- ============================================
-- ARUS Seed Data
-- Dummy sources, pipelines, runs for demo
-- ============================================
BEGIN;

-- ============================================
-- 1. SOURCES
-- ============================================

-- Source 1: MySQL E-Commerce DB
INSERT INTO arus_config.sources (id, name, type, host, port, database, username, password_enc, ssl, sync_method, table_include, table_exclude, status, last_tested, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'E-Commerce MySQL', 'mysql',
  '192.168.1.100', 3306, 'ecommerce_prod', 'replicator',
  'gAAAAABncBvZ...Dd1YmXkEcw==',  -- placeholder: encrypted with Fernet
  true, 'auto',
  ARRAY['orders', 'order_items', 'products', 'customers', 'categories', 'payments'],
  ARRAY['sessions', 'logs', 'cache'],
  'connected',
  NOW() - INTERVAL '2 hours',
  NOW() - INTERVAL '3 days',
  NOW() - INTERVAL '30 minutes'
);

-- Source 2: PostgreSQL CRM
INSERT INTO arus_config.sources (id, name, type, host, port, database, username, password_enc, ssl, sync_method, table_include, table_exclude, status, last_tested, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'CRM PostgreSQL', 'postgresql',
  '192.168.1.101', 5432, 'crm_prod', 'replicator',
  'gAAAAABncBvZ...Dd1YmXkEcw==',
  true, 'auto',
  ARRAY['leads', 'contacts', 'deals', 'accounts', 'activities'],
  ARRAY['audit_log', 'temp_imports'],
  'connected',
  NOW() - INTERVAL '1 hour',
  NOW() - INTERVAL '5 days',
  NOW() - INTERVAL '15 minutes'
);

-- Source 3: MariaDB Inventory
INSERT INTO arus_config.sources (id, name, type, host, port, database, username, password_enc, ssl, sync_method, table_include, table_exclude, status, last_tested, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'Inventory MariaDB', 'mariadb',
  '192.168.1.102', 3307, 'inventory_prod', 'replicator',
  'gAAAAABncBvZ...Dd1YmXkEcw==',
  false, 'full_refresh',
  ARRAY['inventory', 'suppliers', 'warehouses', 'stock_movements'],
  ARRAY['temp_staging', 'import_errors'],
  'connected',
  NOW() - INTERVAL '3 hours',
  NOW() - INTERVAL '2 days',
  NOW() - INTERVAL '1 hour'
);

-- ============================================
-- 2. PIPELINES
-- ============================================

-- Pipeline 1: E-Commerce Sync (incremental, every 5 min)
INSERT INTO arus_config.pipelines (id, name, source_id, destination_id, status, schedule, max_retries, timeout_seconds, depends_on, created_at, updated_at)
SELECT
  gen_random_uuid(), 'E-Commerce → Warehouse',
  s.id, d.id, 'active', '*/5 * * * *', 3, 300, NULL,
  NOW() - INTERVAL '3 days', NOW() - INTERVAL '30 minutes'
FROM arus_config.sources s, arus_config.destinations d
WHERE s.name = 'E-Commerce MySQL' AND d.is_default = true;

-- Pipeline 2: CRM Sync (incremental, every 15 min)
INSERT INTO arus_config.pipelines (id, name, source_id, destination_id, status, schedule, max_retries, timeout_seconds, depends_on, created_at, updated_at)
SELECT
  gen_random_uuid(), 'CRM → Warehouse',
  s.id, d.id, 'active', '*/15 * * * *', 5, 600, NULL,
  NOW() - INTERVAL '5 days', NOW() - INTERVAL '15 minutes'
FROM arus_config.sources s, arus_config.destinations d
WHERE s.name = 'CRM PostgreSQL' AND d.is_default = true;

-- Pipeline 3: Inventory Sync (full refresh, every hour)
INSERT INTO arus_config.pipelines (id, name, source_id, destination_id, status, schedule, max_retries, timeout_seconds, depends_on, created_at, updated_at)
SELECT
  gen_random_uuid(), 'Inventory → Warehouse',
  s.id, d.id, 'active', '0 * * * *', 2, 900, NULL,
  NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 hour'
FROM arus_config.sources s, arus_config.destinations d
WHERE s.name = 'Inventory MariaDB' AND d.is_default = true;

-- ============================================
-- 3. PIPELINE TABLES
-- ============================================

-- Pipeline 1: E-Commerce tables
INSERT INTO arus_config.pipeline_tables (id, pipeline_id, source_table, source_schema, sync_mode, watermark_column)
SELECT gen_random_uuid(), p.id, t.*
FROM arus_config.pipelines p, (VALUES
  ('orders', 'public', 'incremental', 'updated_at'),
  ('order_items', 'public', 'incremental', 'updated_at'),
  ('products', 'public', 'incremental', 'updated_at'),
  ('customers', 'public', 'incremental', 'updated_at'),
  ('categories', 'public', 'full_refresh', NULL),
  ('payments', 'public', 'incremental', 'updated_at')
) AS t(source_table, source_schema, sync_mode, watermark_column)
WHERE p.name = 'E-Commerce → Warehouse';

-- Pipeline 2: CRM tables
INSERT INTO arus_config.pipeline_tables (id, pipeline_id, source_table, source_schema, sync_mode, watermark_column)
SELECT gen_random_uuid(), p.id, t.*
FROM arus_config.pipelines p, (VALUES
  ('leads', 'public', 'incremental', 'updated_at'),
  ('contacts', 'public', 'incremental', 'updated_at'),
  ('deals', 'public', 'incremental', 'updated_at'),
  ('accounts', 'public', 'incremental', 'updated_at'),
  ('activities', 'public', 'full_refresh', NULL)
) AS t(source_table, source_schema, sync_mode, watermark_column)
WHERE p.name = 'CRM → Warehouse';

-- Pipeline 3: Inventory tables
INSERT INTO arus_config.pipeline_tables (id, pipeline_id, source_table, source_schema, sync_mode, watermark_column)
SELECT gen_random_uuid(), p.id, t.*
FROM arus_config.pipelines p, (VALUES
  ('inventory', 'public', 'incremental', 'updated_at'),
  ('suppliers', 'public', 'full_refresh', NULL),
  ('warehouses', 'public', 'full_refresh', NULL),
  ('stock_movements', 'public', 'incremental', 'created_at')
) AS t(source_table, source_schema, sync_mode, watermark_column)
WHERE p.name = 'Inventory → Warehouse';

-- ============================================
-- 4. RUN LOGS (arus_run_logs.runs)
-- ============================================

DO $$
DECLARE
  p RECORD;
  run_id UUID;
  run_status TEXT;
  run_duration INT;
  run_trigger TEXT;
  run_start TIMESTAMPTZ;
  run_error TEXT;
  pipeline_names TEXT[] := ARRAY['E-Commerce → Warehouse', 'CRM → Warehouse', 'Inventory → Warehouse'];
  hours_ago INT;
  i INT;
  total_runs INT;
BEGIN
  -- Different run counts per pipeline
  FOR p IN SELECT id, name FROM arus_config.pipelines ORDER BY created_at LOOP
    total_runs := CASE
      WHEN p.name = 'E-Commerce → Warehouse' THEN 60  -- ~every hour for 2.5 days
      WHEN p.name = 'CRM → Warehouse' THEN 25
      ELSE 15
    END;

    FOR i IN 0..total_runs LOOP
      hours_ago := i * 1 + floor(random() * 0.5)::int;

      run_start := NOW() - (hours_ago || ' hours')::INTERVAL;
      run_trigger := CASE WHEN random() < 0.2 THEN 'manual' ELSE 'scheduled' END;

      -- ~12% failure rate, ~3% running (only recent)
      run_status := CASE
        WHEN random() < 0.12 THEN 'failed'
        WHEN random() < 0.03 AND hours_ago < 4 THEN 'running'
        ELSE 'success'
      END;

      run_duration := CASE
        WHEN run_status = 'failed' THEN floor(random() * 120 + 15)::int
        WHEN run_status = 'running' THEN floor(random() * 300 + 60)::int
        ELSE floor(random() * 45 + 8)::int
      END;

      run_error := CASE run_status
        WHEN 'failed' THEN (ARRAY[
          'Connection timeout to source database',
          'Deadlock detected on table orders',
          'Inconsistent watermark value detected',
          'Schema drift: column "tax_rate" added in source',
          'Row deduplication failed — duplicate primary keys found'
        ])[floor(random() * 5 + 1)]::text
        ELSE NULL
      END;

      INSERT INTO arus_run_logs.runs (id, pipeline_id, status, started_at, finished_at, duration_ms, trigger_type, error_message, created_at)
      VALUES (
        gen_random_uuid(),
        p.id,
        run_status,
        run_start,
        CASE WHEN run_status != 'running' THEN run_start + (run_duration || ' seconds')::INTERVAL ELSE NULL END,
        run_duration * 1000,
        run_trigger,
        run_error,
        run_start
      );
    END LOOP;
  END LOOP;
END $$;

-- ============================================
-- 5. RUN TABLE STATS
-- ============================================

DO $$
DECLARE
  r RECORD;
  pipeline_tables TEXT[];
  tbl TEXT;
  rows_extracted INT;
  rows_loaded INT;
  watermark_before_val TEXT;
  watermark_after_val TEXT;
  t_count INT;
BEGIN
  FOR r IN SELECT * FROM arus_run_logs.runs WHERE status IN ('success', 'failed') ORDER BY started_at DESC LIMIT 100 LOOP
    SELECT ARRAY_AGG(source_table ORDER BY source_table) INTO pipeline_tables
    FROM arus_config.pipeline_tables WHERE pipeline_id = r.pipeline_id;

    IF pipeline_tables IS NOT NULL THEN
      t_count := array_length(pipeline_tables, 1);
      FOREACH tbl IN ARRAY pipeline_tables LOOP
        IF random() < 0.2 THEN CONTINUE; END IF; -- skip some for variety

        rows_extracted := floor(random() * 5000 + 100)::int;
        rows_loaded := CASE WHEN r.status = 'failed' THEN 0 ELSE floor(rows_extracted * (random() * 0.15 + 0.85))::int END;

        watermark_before_val := '2026-06-10 00:00:00';
        watermark_after_val := '2026-06-' || LPAD((10 + floor(random() * 2))::text, 2, '0') || ' 23:59:59';

        INSERT INTO arus_run_logs.run_table_stats (id, run_id, table_name, rows_extracted, rows_loaded_raw, rows_loaded_analytics, rows_failed, watermark_before, watermark_after, duration_ms, error_message)
        VALUES (
          gen_random_uuid(),
          r.id,
          tbl,
          rows_extracted,
          rows_loaded,
          floor(rows_loaded * (random() * 0.05 + 0.95))::int,
          rows_extracted - rows_loaded,
          watermark_before_val,
          watermark_after_val,
          floor(random() * 30000 + 1000)::int,
          CASE WHEN r.status = 'failed' THEN 'Connection interrupted during extract' ELSE NULL END
        );
      END LOOP;
    END IF;
  END LOOP;
END $$;

-- ============================================
-- 6. WATERMARKS
-- ============================================

INSERT INTO arus_state.watermarks (id, pipeline_id, source_table, watermark_col, watermark_value, row_count, last_run_id, last_synced_at, created_at, updated_at)
SELECT
  gen_random_uuid(),
  p.id,
  pt.source_table,
  pt.watermark_column,
  CASE pt.source_table
    WHEN 'orders' THEN '2026-06-12 05:45:00'
    WHEN 'order_items' THEN '2026-06-12 05:45:00'
    WHEN 'products' THEN '2026-06-12 05:30:00'
    WHEN 'customers' THEN '2026-06-12 05:30:00'
    WHEN 'payments' THEN '2026-06-12 05:30:00'
    WHEN 'leads' THEN '2026-06-12 05:30:00'
    WHEN 'contacts' THEN '2026-06-12 05:15:00'
    WHEN 'deals' THEN '2026-06-12 05:15:00'
    WHEN 'accounts' THEN '2026-06-12 05:00:00'
    WHEN 'inventory' THEN '2026-06-12 05:00:00'
    WHEN 'stock_movements' THEN '2026-06-12 05:00:00'
    ELSE '2026-06-12 05:00:00'
  END,
  CASE pt.source_table
    WHEN 'orders' THEN 125430
    WHEN 'order_items' THEN 487210
    WHEN 'products' THEN 5430
    WHEN 'customers' THEN 28150
    WHEN 'payments' THEN 98210
    WHEN 'leads' THEN 15780
    WHEN 'contacts' THEN 12340
    WHEN 'deals' THEN 8920
    WHEN 'accounts' THEN 3450
    WHEN 'inventory' THEN 28760
    WHEN 'stock_movements' THEN 345800
    ELSE floor(random() * 100000 + 1000)::int
  END,
  (SELECT id FROM arus_run_logs.runs WHERE pipeline_id = p.id AND status = 'success' ORDER BY started_at DESC LIMIT 1),
  NOW() - INTERVAL '5 minutes',
  NOW() - INTERVAL '3 days',
  NOW() - INTERVAL '5 minutes'
FROM arus_config.pipelines p
JOIN arus_config.pipeline_tables pt ON pt.pipeline_id = p.id
WHERE pt.watermark_column IS NOT NULL;

-- ============================================
-- 7. DATA QUALITY LOGS
-- ============================================

INSERT INTO arus_config.data_quality_log (id, pipeline_id, run_id, table_name, check_type, status, rows_extracted, rows_loaded, discrepancy_pct, null_columns, required_columns, message, passed, checked_at)
SELECT
  gen_random_uuid(),
  p.id,
  (SELECT id FROM arus_run_logs.runs WHERE pipeline_id = p.id AND status = 'success' ORDER BY started_at DESC LIMIT 1),
  t.tbl,
  'row_count',
  CASE WHEN random() < 0.75 THEN 'passed' ELSE 'warning' END,
  floor(random() * 5000 + 500)::int,
  floor(random() * 5000 + 500)::int,
  round((random() * 3)::numeric, 2),
  CASE WHEN random() < 0.3 THEN 'notes, comments' ELSE NULL END,
  CASE WHEN random() < 0.2 THEN 'email, phone' ELSE NULL END,
  CASE WHEN random() < 0.75 THEN '✓ Row count within threshold (0.12% diff)' ELSE '⚠ Row count discrepancy: expected 2500, got 2482 (0.72% diff)' END,
  random() < 0.85,
  NOW() - (floor(random() * 24) || ' hours')::INTERVAL
FROM arus_config.pipelines p
CROSS JOIN (VALUES ('orders'), ('leads'), ('inventory')) AS t(tbl)
LIMIT 15;

-- ============================================
-- 8. DEAD LETTERS
-- ============================================

INSERT INTO staging._dead_letters (id, source_name, table_name, run_id, row_data, error_text, failed_at)
VALUES
(
  gen_random_uuid(),
  'E-Commerce MySQL', 'orders',
  (SELECT id FROM arus_run_logs.runs WHERE status = 'failed' LIMIT 1),
  '{"order_id": 104732, "customer_id": 8912, "total": 249.99, "status": "pending"}',
  'Violates NOT NULL constraint on column "shipping_address"',
  NOW() - INTERVAL '3 hours'
),
(
  gen_random_uuid(),
  'CRM PostgreSQL', 'leads',
  (SELECT id FROM arus_run_logs.runs WHERE status = 'failed' OFFSET 1 LIMIT 1),
  '{"lead_id": 4501, "company": "Tech Corp", "email": null, "score": "invalid"}',
  'Invalid data type for column "score": expected integer, got text',
  NOW() - INTERVAL '6 hours'
),
(
  gen_random_uuid(),
  'E-Commerce MySQL', 'order_items',
  (SELECT id FROM arus_run_logs.runs WHERE status = 'failed' OFFSET 2 LIMIT 1),
  '{"item_id": 98231, "order_id": 104732, "product_id": "PROD-001", "qty": -1, "price": 49.99}',
  'Check constraint violation: qty must be >= 1',
  NOW() - INTERVAL '8 hours'
);

-- ============================================
-- 9. RUN LOG MESSAGES
-- ============================================

DO $$
DECLARE
  r RECORD;
  msg_data TEXT[];
  msg_count INT;
  j INT;
  t TIMESTAMPTZ;
BEGIN
  FOR r IN SELECT * FROM arus_run_logs.runs ORDER BY started_at DESC LIMIT 30 LOOP
    IF r.status = 'success' THEN
      msg_data := ARRAY[
        'Starting pipeline run', 'INFO',
        'Connecting to source database', 'INFO',
        'Connection established', 'INFO',
        'Reading watermark for table increments', 'INFO',
        'Extracting changes since last watermark', 'INFO',
        'Extracted 1,247 new/modified rows', 'INFO',
        'Loading raw data to staging schema', 'INFO',
        'Loaded 1,247 rows to staging layer', 'INFO',
        'Running data quality checks', 'INFO',
        'Quality check passed: row count within threshold', 'INFO',
        'Transforming staging → analytics schema', 'INFO',
        'Transformation complete: 1,247 rows processed', 'INFO',
        'Updating watermark positions', 'INFO',
        'Pipeline run completed successfully', 'INFO'
      ];
      msg_count := 14;
    ELSIF r.status = 'failed' THEN
      msg_data := ARRAY[
        'Starting pipeline run', 'INFO',
        'Connecting to source database', 'INFO',
        'Connection established', 'INFO',
        'Reading watermark for table increments', 'INFO',
        'Extracting incremental changes', 'INFO',
        'Lost connection to source database', 'ERROR',
        'Retry attempt 1/3...', 'WARN',
        'Connection timeout after 30s', 'ERROR',
        'Retry attempt 2/3...', 'WARN',
        'All retries exhausted — aborting', 'ERROR',
        'Pipeline run failed', 'ERROR'
      ];
      msg_count := 11;
    ELSE
      msg_data := ARRAY[
        'Starting pipeline run', 'INFO',
        'Connecting to source database', 'INFO',
        'Connection established', 'INFO',
        'Extracting data from source...', 'INFO',
        'Processing in progress...', 'INFO'
      ];
      msg_count := 5;
    END IF;

    t := r.started_at;
    FOR j IN 1..msg_count LOOP
      INSERT INTO arus_run_logs.run_logs (run_id, timestamp, level, message)
      VALUES (r.id, t, msg_data[j*2], msg_data[j*2-1]);
      t := t + INTERVAL '1 second';
    END LOOP;
  END LOOP;
END $$;

-- ============================================
-- VERIFICATION
-- ============================================
SELECT '✅ Seed data complete!' as status;

SELECT 'Sources connected:' as stat, count(*)::text FROM arus_config.sources WHERE status = 'connected'
UNION ALL
SELECT 'Pipelines active:', count(*)::text FROM arus_config.pipelines WHERE status = 'active'
UNION ALL
SELECT 'Pipeline tables:', count(*)::text FROM arus_config.pipeline_tables
UNION ALL
SELECT 'Total runs:', count(*)::text FROM arus_run_logs.runs
UNION ALL
SELECT '  ▶ success:', count(*)::text FROM arus_run_logs.runs WHERE status = 'success'
UNION ALL
SELECT '  ✗ failed:', count(*)::text FROM arus_run_logs.runs WHERE status = 'failed'
UNION ALL
SELECT '  ● running:', count(*)::text FROM arus_run_logs.runs WHERE status = 'running'
UNION ALL
SELECT 'Table stats:', count(*)::text FROM arus_run_logs.run_table_stats
UNION ALL
SELECT 'Watermarks:', count(*)::text FROM arus_state.watermarks
UNION ALL
SELECT 'Dead letters:', count(*)::text FROM staging._dead_letters
UNION ALL
SELECT 'Quality logs:', count(*)::text FROM arus_config.data_quality_log
UNION ALL
SELECT 'Run log entries:', count(*)::text FROM arus_run_logs.run_logs;

COMMIT;
