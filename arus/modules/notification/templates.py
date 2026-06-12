"""
Notification message templates — structured data dicts for multi-platform rendering.
Each builder returns a dict that SENDERS format per platform (Telegram HTML, Discord embed, Slack Block Kit).
"""

# Discord embed color constants
COLOR_RED = 0xE74C3C
COLOR_GREEN = 0x2ECC71
COLOR_ORANGE = 0xF39C12
COLOR_YELLOW = 0xF1C40F
COLOR_BLUE = 0x3498DB


def _text_html(data: dict) -> str:
    """Render structured data as Telegram HTML."""
    lines = [f"{data['emoji']} <b>{data['title']}</b>"]
    for f in data.get("fields", []):
        val = f.get("value", "")
        lines.append(f"{f['name']}: {val}")
    return "\n".join(lines)


def _discord_embeds(data: dict) -> list:
    """Render structured data as Discord embeds."""
    fields = []
    for f in data.get("fields", []):
        val = f.get("value", "")
        # Discord embed field values max 1024 chars; inline for short values
        is_inline = len(val) < 50
        fields.append({
            "name": f["name"],
            "value": val,
            "inline": is_inline,
        })
    return [{
        "title": f"{data['emoji']} {data['title']}",
        "color": data.get("color", COLOR_BLUE),
        "fields": fields,
        "footer": {"text": "Arus Data Pipeline"},
        "timestamp": data.get("timestamp", None),
    }]


def _slack_blocks(data: dict) -> list:
    """Render structured data as Slack Block Kit blocks."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{data['emoji']} {data['title']}", "emoji": True},
        },
        {"type": "divider"},
    ]
    for f in data.get("fields", []):
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{f['name']}*"},
                {"type": "mrkdwn", "text": f.get("value", "")},
            ],
        })
    return blocks


def _discord_content(data: dict) -> str:
    """Fallback plain text content for Discord (if embeds can't be used)."""
    lines = [f"{data['emoji']} **{data['title']}**"]
    for f in data.get("fields", []):
        lines.append(f"**{f['name']}:** {f['value']}")
    return "\n".join(lines)


def _demokeys(event_type: str) -> tuple:
    """Return (pipeline_name, pipeline_id, run_id, source, dest, schedule)."""
    return (
        "Demo Pipeline",
        "p_00000001",
        "run_000001",
        "PostgreSQL (prod-db:5432)",
        "ClickHouse (analytics:8123)",
        "*/5 * * * *",
    )


def _default_extra(event_type: str) -> dict:
    extras = {
        "success": {"rows_synced": 1500, "duration_ms": 4300},
        "dead_letter": {"table": "raw_orders", "row_count": 47},
        "schema_drift": {"table": "customers", "new_columns": ["email", "phone_number", "address_line2"]},
        "quality_breach": {"details": "Null ratio in column 'email' exceeds threshold (35% > 5%)"},
    }
    return extras.get(event_type, {})


def build_test_message() -> dict:
    return {
        "emoji": "🔔",
        "title": "Test Notification",
        "color": COLOR_BLUE,
        "fields": [
            {"name": "Message", "value": "Your notification target is configured correctly!"},
            {"name": "Source", "value": "Arus Data Pipeline"},
        ],
    }


def build_success_message(
    pipeline_name: str = "",
    pipeline_id: str = "",
    run_id: str = "",
    error: str = "",
    extra: dict | None = None,
    source_name: str = "",
    destination_name: str = "",
    schedule: str = "",
) -> dict:
    use_demo = not pipeline_name
    if use_demo:
        pn, pi, ri, src, dst, sched = _demokeys("success")
        pipeline_name = pipeline_name or pn
        pipeline_id = pipeline_id or pi
        run_id = run_id or ri
        source_name = source_name or src
        destination_name = destination_name or dst
        schedule = schedule or sched
        extra = extra or _default_extra("success")

    rows = (extra or {}).get("rows_synced", 1500)
    duration = (extra or {}).get("duration_ms", 4300)

    fields = [
        {"name": "Pipeline", "value": f"<code>{pipeline_name}</code>" if use_demo else pipeline_name},
        {"name": "Run ID", "value": f"<code>{run_id}</code>"},
        {"name": "Rows Synced", "value": f"<b>{rows:,}</b>"},
        {"name": "Duration", "value": f"{duration}ms"},
    ]
    if source_name:
        fields.append({"name": "Source", "value": source_name})
    if destination_name:
        fields.append({"name": "Destination", "value": destination_name})
    if schedule:
        fields.append({"name": "Schedule", "value": schedule})

    return {
        "emoji": "✅",
        "title": "Pipeline Succeeded",
        "color": COLOR_GREEN,
        "fields": fields,
    }


def build_failure_message(
    pipeline_name: str = "",
    pipeline_id: str = "",
    run_id: str = "",
    error: str = "Connection timeout after 30s",
    extra: dict | None = None,
    source_name: str = "",
    destination_name: str = "",
    schedule: str = "",
) -> dict:
    use_demo = not pipeline_name
    if use_demo:
        pn, pi, ri, src, dst, sched = _demokeys("failure")
        pipeline_name = pipeline_name or pn
        pipeline_id = pipeline_id or pi
        run_id = run_id or ri
        source_name = source_name or src
        destination_name = destination_name or dst
        schedule = schedule or sched

    fields = [
        {"name": "Pipeline", "value": f"<code>{pipeline_name}</code>" if use_demo else pipeline_name},
        {"name": "Run ID", "value": f"<code>{run_id}</code>"},
        {"name": "Error", "value": f"<code>{(error or 'Unknown')[:200]}</code>"},
    ]
    if source_name:
        fields.append({"name": "Source", "value": source_name})
    if destination_name:
        fields.append({"name": "Destination", "value": destination_name})

    return {
        "emoji": "🚨",
        "title": "Pipeline Failed",
        "color": COLOR_RED,
        "fields": fields,
    }


def build_dead_letter_message(
    pipeline_name: str = "",
    pipeline_id: str = "",
    run_id: str = "",
    error: str = "Invalid UTF-8 encoding in column 'name'",
    extra: dict | None = None,
    source_name: str = "",
    destination_name: str = "",
    schedule: str = "",
) -> dict:
    use_demo = not pipeline_name
    if use_demo:
        pn, pi, ri, src, dst, sched = _demokeys("dead_letter")
        pipeline_name = pipeline_name or pn
        pipeline_id = pipeline_id or pi
        run_id = run_id or ri
        source_name = source_name or src
        destination_name = destination_name or dst
        schedule = schedule or sched
        extra = extra or _default_extra("dead_letter")

    table = (extra or {}).get("table", "?")
    row_count = (extra or {}).get("row_count", 0)

    fields = [
        {"name": "Pipeline", "value": f"<code>{pipeline_name}</code>" if use_demo else pipeline_name},
        {"name": "Run ID", "value": f"<code>{run_id}</code>"},
        {"name": "Table", "value": f"<code>{table}</code>"},
        {"name": "Rejected Rows", "value": f"<b>{row_count:,}</b>"},
        {"name": "Error", "value": f"<code>{(error or '')[:200]}</code>"},
    ]

    return {
        "emoji": "⚠️",
        "title": "Dead Letter Rows Created",
        "color": COLOR_ORANGE,
        "fields": fields,
    }


def build_schema_drift_message(
    pipeline_name: str = "",
    pipeline_id: str = "",
    run_id: str = "",
    error: str = "",
    extra: dict | None = None,
    source_name: str = "",
    destination_name: str = "",
    schedule: str = "",
) -> dict:
    use_demo = not pipeline_name
    if use_demo:
        pn, pi, ri, src, dst, sched = _demokeys("schema_drift")
        pipeline_name = pipeline_name or pn
        pipeline_id = pipeline_id or pi
        run_id = run_id or ri
        source_name = source_name or src
        destination_name = destination_name or dst
        schedule = schedule or sched
        extra = extra or _default_extra("schema_drift")

    new_columns = (extra or {}).get("new_columns", [])
    table = (extra or {}).get("table", "?")
    cols_str = ", ".join(new_columns) if new_columns else "?"

    fields = [
        {"name": "Pipeline", "value": f"<code>{pipeline_name}</code>" if use_demo else pipeline_name},
        {"name": "Table", "value": f"<code>{table}</code>"},
        {"name": "New Columns", "value": cols_str},
    ]

    return {
        "emoji": "🔀",
        "title": "Schema Drift Detected",
        "color": COLOR_YELLOW,
        "fields": fields,
    }


def build_quality_breach_message(
    pipeline_name: str = "",
    pipeline_id: str = "",
    run_id: str = "",
    error: str = "Null ratio in column 'email' exceeds threshold (35% > 5%)",
    extra: dict | None = None,
    source_name: str = "",
    destination_name: str = "",
    schedule: str = "",
) -> dict:
    use_demo = not pipeline_name
    if use_demo:
        pn, pi, ri, src, dst, sched = _demokeys("quality_breach")
        pipeline_name = pipeline_name or pn
        pipeline_id = pipeline_id or pi
        run_id = run_id or ri
        source_name = source_name or src
        destination_name = destination_name or dst
        schedule = schedule or sched
        extra = extra or _default_extra("quality_breach")

    details = (error or "Threshold breached")[:300]
    if extra and isinstance(extra, dict):
        details = (extra.get("details") or details)[:300]

    fields = [
        {"name": "Pipeline", "value": f"<code>{pipeline_name}</code>" if use_demo else pipeline_name},
        {"name": "Run ID", "value": f"<code>{run_id}</code>"},
        {"name": "Details", "value": details},
    ]

    return {
        "emoji": "📉",
        "title": "Data Quality Breach",
        "color": COLOR_RED,
        "fields": fields,
    }


# Public helpers for senders
def format_for_telegram(data: dict) -> str:
    """Convert structured data to Telegram HTML message."""
    return _text_html(data)


def format_for_discord(data: dict) -> dict:
    """Convert structured data to Discord webhook payload (with embed)."""
    return {
        "content": _discord_content(data),
        "embeds": _discord_embeds(data),
    }


def format_for_slack(data: dict) -> dict:
    """Convert structured data to Slack webhook payload (with Block Kit)."""
    return {
        "text": _discord_content(data),  # fallback text
        "blocks": _slack_blocks(data),
    }


BUILDERS = {
    "test": lambda **kw: build_test_message(),
    "success": build_success_message,
    "failure": build_failure_message,
    "dead_letter": build_dead_letter_message,
    "schema_drift": build_schema_drift_message,
    "quality_breach": build_quality_breach_message,
}
