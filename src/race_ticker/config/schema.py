"""Configuration schema and validation."""

import re
from typing import Any, Dict

# Valid template tags
VALID_TEMPLATE_TAGS = {"runner", "lap", "lap_time", "distance"}


def _validate_template(template: str | None) -> None:
    """Validate template string format and tags.
    
    Args:
        template: Template string to validate (e.g., "NR.{runner:02d} LAP {lap} TIME {lap_time}")
    
    Raises:
        ValueError: If template is invalid
    """
    if template is None:
        return  # Optional field
    
    if not isinstance(template, str):
        raise ValueError("display.template must be a string")
    
    if not template.strip():
        raise ValueError("display.template cannot be empty")
    
    # Find all {tag} or {tag:format} patterns
    tag_pattern = re.compile(r"\{([^}:]+)(?::[^}]*)?\}")
    matches = tag_pattern.findall(template)
    
    # Check for unmatched braces
    open_braces = template.count("{")
    close_braces = template.count("}")
    if open_braces != close_braces:
        raise ValueError("display.template has unmatched braces")
    
    # Validate all tags
    invalid_tags = []
    for tag in matches:
        if tag not in VALID_TEMPLATE_TAGS:
            invalid_tags.append(tag)
    
    if invalid_tags:
        valid_tags_str = ", ".join(sorted(VALID_TEMPLATE_TAGS))
        raise ValueError(
            f"display.template contains invalid tags: {', '.join(set(invalid_tags))}. "
            f"Valid tags are: {valid_tags_str}"
        )


def validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration structure and values.
    
    Raises ValueError if validation fails.
    """
    # App section
    if "app" not in config:
        raise ValueError("Missing 'app' section")
    if not isinstance(config["app"].get("host"), str):
        raise ValueError("app.host must be a string")
    if not isinstance(config["app"].get("port"), int) or config["app"].get("port") < 1:
        raise ValueError("app.port must be a positive integer")
    
    # Mode section
    if "mode" not in config:
        raise ValueError("Missing 'mode' section")
    if config["mode"].get("source") not in ("live", "simulate"):
        raise ValueError("mode.source must be 'live' or 'simulate'")
    if not isinstance(config["mode"].get("freeze_updates"), bool):
        raise ValueError("mode.freeze_updates must be a boolean")
    
    # Races section
    if "races" not in config:
        raise ValueError("Missing 'races' section")
    if not isinstance(config["races"].get("active_race_id"), str):
        raise ValueError("races.active_race_id must be a string")
    if "profiles" not in config["races"]:
        raise ValueError("Missing 'races.profiles' section")
    
    # CSV section
    if "csv" not in config:
        raise ValueError("Missing 'csv' section")
    if not isinstance(config["csv"].get("poll_interval_s"), (int, float)) or config["csv"].get("poll_interval_s") <= 0:
        raise ValueError("csv.poll_interval_s must be a positive number")
    if not isinstance(config["csv"].get("timeout_s"), (int, float)) or config["csv"].get("timeout_s") <= 0:
        raise ValueError("csv.timeout_s must be a positive number")
    
    # Display section
    if "display" not in config:
        raise ValueError("Missing 'display' section")
    if not isinstance(config["display"].get("max_runners"), int) or config["display"].get("max_runners") < 1:
        raise ValueError("display.max_runners must be a positive integer")
    _validate_template(config["display"].get("template"))
    
    # Ticker section
    if "ticker" not in config:
        raise ValueError("Missing 'ticker' section")
    if not isinstance(config["ticker"].get("font_size_px"), int) or config["ticker"].get("font_size_px") < 1:
        raise ValueError("ticker.font_size_px must be a positive integer")
    if not isinstance(config["ticker"].get("speed_px_s"), (int, float)) or config["ticker"].get("speed_px_s") <= 0:
        raise ValueError("ticker.speed_px_s must be a positive number")
    if not isinstance(config["ticker"].get("fps"), int) or config["ticker"].get("fps") < 1:
        raise ValueError("ticker.fps must be a positive integer")
    
    # Race time section
    if "race_time" not in config:
        raise ValueError("Missing 'race_time' section")
    if not isinstance(config["race_time"].get("enabled"), bool):
        raise ValueError("race_time.enabled must be a boolean")
    
    # Clock section
    if "clock" not in config:
        raise ValueError("Missing 'clock' section")
    if config["clock"].get("state") not in ("running", "paused", "stopped"):
        raise ValueError("clock.state must be 'running', 'paused', or 'stopped'")
    if not isinstance(config["clock"].get("accumulated_s"), (int, float)) or config["clock"].get("accumulated_s") < 0:
        raise ValueError("clock.accumulated_s must be a non-negative number")


def validate_patch(patch: Dict[str, Any]) -> None:
    """Validate a partial config patch.
    
    Raises ValueError if validation fails.
    """
    # Create a minimal valid config and apply patch for validation
    # This is a simplified check - full validation happens in update_config
    if "mode" in patch and "source" in patch["mode"]:
        if patch["mode"]["source"] not in ("live", "simulate"):
            raise ValueError("mode.source must be 'live' or 'simulate'")
    
    if "clock" in patch and "state" in patch["clock"]:
        if patch["clock"]["state"] not in ("running", "paused", "stopped"):
            raise ValueError("clock.state must be 'running', 'paused', or 'stopped'")

    if "display" in patch and "sort_runners" in patch["display"]:
        if patch["display"]["sort_runners"] not in ("runner", "csv_order"):
            raise ValueError("display.sort_runners must be 'runner' or 'csv_order'")
    
    if "display" in patch and "template" in patch["display"]:
        _validate_template(patch["display"]["template"])