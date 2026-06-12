"""Built-in transform step handlers.

Each handler is a function:
    (rows: list[dict], config: dict) -> list[dict]

All rows are processed; filtering is done by returning None for dropped rows
inside compute/filter handlers. The engine handles row-level None filtering
after each step.
"""

import re
import logging

logger = logging.getLogger(__name__)


def handle_rename(rows: list[dict], config: dict) -> list[dict]:
    """Rename columns.

    Config: {"mapping": {"old_name": "new_name", ...}}
    """
    mapping = config.get("mapping", {})
    if not mapping:
        logger.warning("rename transform: empty mapping")
        return rows

    result = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            new_row[mapping.get(k, k)] = v
        result.append(new_row)
    return result


def handle_remove_fields(rows: list[dict], config: dict) -> list[dict]:
    """Remove one or more fields from rows.

    Config: {"fields": ["col1", "col2", ...]}
    """
    fields = set(config.get("fields", []))
    if not fields:
        return rows

    result = []
    for row in rows:
        new_row = {k: v for k, v in row.items() if k not in fields}
        result.append(new_row)
    return result


def handle_compute(rows: list[dict], config: dict) -> list[dict]:
    """Compute a new field from an expression.

    Config: {"expression": "tax = amount * 0.11", "type": "decimal"}
    Expression format: "new_field = python_expression"
    The expression is evaluated safely using only built-in math operations.
    """
    expression = config.get("expression", "")
    if "=" not in expression:
        logger.warning(f"compute transform: invalid expression '{expression}' (missing '=')")
        return rows

    field_name, expr = expression.split("=", 1)
    field_name = field_name.strip()
    expr = expr.strip()

    if not field_name or not expr:
        logger.warning(f"compute transform: invalid expression '{expression}'")
        return rows

    # Safe evaluation context
    safe_builtins = {
        "abs": abs, "float": float, "int": int, "str": str,
        "round": round, "max": max, "min": min, "len": len,
        "sum": sum, "bool": bool,
    }

    result = []
    for row in rows:
        # Build eval context from row values
        context = {}
        for k, v in row.items():
            if isinstance(v, (int, float, str, bool)):
                context[k] = v

        context.update(safe_builtins)

        try:
            computed = eval(expr, {"__builtins__": {}}, context)
            row[field_name] = computed
        except Exception as e:
            logger.warning(f"compute transform failed for row: {e}")

        result.append(row)

    return result


def handle_filter(rows: list[dict], config: dict) -> list[dict]:
    """Filter rows based on a condition.

    Config: {"condition": "status != 'deleted'"}
    Expression is evaluated per row — return True to keep, False to drop.
    """
    condition = config.get("condition", "")
    if not condition:
        return rows

    safe_builtins = {
        "abs": abs, "float": float, "int": int, "str": str,
        "round": round, "max": max, "min": min, "len": len,
        "sum": sum, "bool": bool,
    }

    result = []
    for row in rows:
        context = {}
        for k, v in row.items():
            if isinstance(v, (int, float, str, bool)):
                context[k] = v
        context.update(safe_builtins)

        try:
            keep = bool(eval(condition, {"__builtins__": {}}, context))
            if keep:
                result.append(row)
        except Exception as e:
            logger.warning(f"filter transform failed for row: {e}")
            result.append(row)  # keep on error

    return result


def handle_map_values(rows: list[dict], config: dict) -> list[dict]:
    """Map column values using a lookup table.

    Config: {"column": "status", "mapping": {"1": "active", "0": "inactive"}}
    """
    column = config.get("column", "")
    mapping = config.get("mapping", {})

    if not column or not mapping:
        return rows

    result = []
    for row in rows:
        if column in row:
            val = str(row[column]) if row[column] is not None else None
            if val in mapping:
                row[column] = mapping[val]
        result.append(row)

    return result


def handle_type_cast(rows: list[dict], config: dict) -> list[dict]:
    """Cast column types.

    Config: {"columns": {"price": "float", "is_active": "bool", "count": "int", "tags": "str"}}
    Supported types: int, float, str, bool
    """
    columns = config.get("columns", {})

    if not columns:
        return rows

    type_map = {
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
    }

    result = []
    for row in rows:
        for col_name, target_type in columns.items():
            if col_name in row and row[col_name] is not None:
                cast_fn = type_map.get(target_type)
                if cast_fn:
                    try:
                        row[col_name] = cast_fn(row[col_name])
                    except (ValueError, TypeError) as e:
                        logger.warning(f"type_cast failed for {col_name}: {e}")
        result.append(row)

    return result


def handle_concat_fields(rows: list[dict], config: dict) -> list[dict]:
    """Concatenate multiple fields into one.

    Config: {
        "fields": ["first_name", "last_name"],
        "separator": " ",
        "target": "full_name",
        "drop_source": false
    }
    """
    fields = config.get("fields", [])
    separator = config.get("separator", " ")
    target = config.get("target", "concatenated")
    drop_source = config.get("drop_source", False)

    if not fields:
        return rows

    drop_set = set(fields) if drop_source else set()

    result = []
    for row in rows:
        parts = [str(row.get(f, "")) for f in fields]
        row[target] = separator.join(parts)
        if drop_source:
            for f in drop_set:
                row.pop(f, None)
        result.append(row)

    return result


# Registry of built-in transform handlers
BUILTIN_HANDLERS = {
    "rename": handle_rename,
    "remove_fields": handle_remove_fields,
    "compute": handle_compute,
    "filter": handle_filter,
    "map_values": handle_map_values,
    "type_cast": handle_type_cast,
    "concat_fields": handle_concat_fields,
}
