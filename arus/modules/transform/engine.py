"""Transform engine — applies transform steps to rows.

Usage:
    from arus.modules.transform.engine import apply_transforms
    transformed = apply_transforms(rows, transform_config, db_session=None)
"""

import logging
import os
import tempfile
from typing import Optional

from arus.modules.transform.builtins import BUILTIN_HANDLERS

logger = logging.getLogger(__name__)


def apply_transforms(
    rows: list[dict],
    transform_config: list[dict],
    db_session=None,
    pipeline_id: str | None = None,
) -> list[dict]:
    """Apply a sequence of transform steps to rows.

    Args:
        rows: List of row dicts from source connector.
        transform_config: List of step dicts, each with "type" and "config".
        db_session: Optional DB session (needed for "script" type steps
                    to look up script content from transform_scripts table).
        pipeline_id: Optional pipeline ID (needed for "script" type steps).

    Returns:
        Transformed list of row dicts.
    """
    if not transform_config or not rows:
        return rows

    current = rows

    for step_idx, step in enumerate(transform_config):
        step_type = step.get("type", "")
        config = step.get("config", {})

        if not step_type:
            logger.warning(f"Transform step {step_idx}: missing 'type', skipping")
            continue

        try:
            handler = _get_handler(step_type, config, db_session=db_session, pipeline_id=pipeline_id)
            if handler:
                current = handler(current, config)
                # Remove None rows (rows returned for filtering/skipping)
                current = [r for r in current if r is not None]
        except Exception as e:
            logger.error(f"Transform step {step_idx} ({step_type}) failed: {e}")
            # On failure, keep current rows and continue to next step

    return current


def _get_handler(step_type: str, config: dict, db_session=None, pipeline_id: str | None = None):
    """Resolve a handler for the given step type.

    Priority:
        1. Built-in handler (rename, compute, filter, etc.)
        2. "script" type — loads Python from transform_scripts table
    """
    if step_type in BUILTIN_HANDLERS:
        return BUILTIN_HANDLERS[step_type]

    if step_type == "script":
        return _make_script_handler(config, db_session, pipeline_id=pipeline_id)

    logger.warning(f"Unknown transform type '{step_type}'")
    return None


def _make_script_handler(config: dict, db_session=None, pipeline_id: str | None = None):
    """Create a handler that runs a Python script from the transform_scripts table.

    Config: {"script_name": "clean_orders"}  — looked up in DB
    """
    script_name = config.get("script_name", "")
    if not script_name:
        logger.warning("script transform: missing 'script_name' in config")
        return None

    if not db_session:
        logger.warning("script transform: no db_session available to look up script")
        return None

    # Look up script content from DB
    from arus.modules.pipeline.models import TransformScript

    if not pipeline_id:
        logger.warning("script transform: no pipeline_id provided for script lookup")
        return None

    script = (
        db_session.query(TransformScript)
        .filter(
            TransformScript.name == script_name,
            TransformScript.pipeline_id == pipeline_id,
        )
        .first()
    )

    if not script:
        logger.warning(f"script transform: transform script '{script_name}' not found")
        return None

    # Compile and return a handler function
    return _compile_script(script.content, script_name)


def _compile_script(content: str, script_name: str):
    """Compile a Python transform script and return a handler function.

    The script must define a `transform(row: dict) -> dict | None` function.
    """
    try:
        compiled = compile(content, f"<transform:{script_name}>", "exec")
    except SyntaxError as e:
        logger.error(f"Script '{script_name}' has syntax error: {e}")
        return None

    # Namespace for the compiled script
    namespace = {}
    try:
        exec(compiled, namespace)
    except Exception as e:
        logger.error(f"Script '{script_name}' exec failed: {e}")
        return None

    transform_fn = namespace.get("transform")
    if not transform_fn or not callable(transform_fn):
        logger.error(f"Script '{script_name}' must define a callable 'transform(row) -> dict | None'")
        return None

    def handler(rows: list[dict], _config: dict) -> list[dict]:
        result = []
        for row in rows:
            try:
                out = transform_fn(row)
                result.append(out)
            except Exception as e:
                logger.warning(f"Script '{script_name}' failed on row: {e}")
                result.append(row)  # keep original on error
        return result

    return handler
