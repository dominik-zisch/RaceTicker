"""Converts RaceState to display strings and full payload."""

from datetime import datetime, timezone
from typing import Any

from ..ingest.parser import RaceState


def format_ticker_text(race_state: RaceState, config: dict[str, Any]) -> str:
    """Build ticker line from race state: template per runner, joined by separator.
    Runner order is determined by display.sort_runners in parser (runner number or CSV order).
    Config: display.template, display.separator, display.max_runners.
    """
    display = config.get("display", {})
    template = display.get("template", "NR.{runner:02d} LAP {lap} TIME {lap_time}")
    separator = display.get("separator", " // ")
    max_runners = int(display.get("max_runners", 10))
    runners = race_state.runners[:max_runners]
    parts = []
    for r in runners:
        part = template.format(
            runner=r.runner_number,
            lap=r.lap_number,
            lap_time=r.lap_time_str,
            distance=r.distance_str or "",
        )
        parts.append(part)
    return separator.join(parts)


def build_queued_ticker_text(
    race_state: RaceState,
    config: dict[str, Any],
    *,
    race_time_str: str = "0:00:00",
    repeat_count: int = 50,
) -> str:
    """Build one long ticker string as a queue of segments: each segment ends with separator.
    Repeats racer block; every insert_every_loops blocks inserts a race time segment.
    So the next segment always appears right behind the previous (no blank screen).
    """
    display = config.get("display", {})
    separator = display.get("separator", " // ")
    race_time_config = config.get("race_time", {})
    enabled = race_time_config.get("enabled", True)
    show_every_loops = race_time_config.get("insert_every_loops", 3) if enabled else 0

    racer_segment = format_ticker_text(race_state, config) + separator
    race_time_segment = f"RACE TIME: {race_time_str}{separator}"

    segments: list[str] = []
    for i in range(repeat_count):
        segments.append(racer_segment)
        if show_every_loops > 0 and (i + 1) % show_every_loops == 0:
            segments.append(race_time_segment)
    return "".join(segments)


def build_payload(
    race_state: RaceState,
    config: dict[str, Any],
    *,
    version: int = 1,
    race_time_str: str = "0:00:00",
) -> dict[str, Any]:
    """Build full display payload from RaceState and config.
    Ticker text is a long queue of segments (racer + race time every N), each ending with separator,
    so the display scrolls continuously with no blank gap between segments.
    """
    ticker = config.get("ticker", {})
    display = config.get("display", {})
    race_time_config = config.get("race_time", {})
    now_utc = datetime.now(timezone.utc)
    ticker_text = build_queued_ticker_text(
        race_state, config, race_time_str=race_time_str
    )
    enabled = race_time_config.get("enabled", True)
    show_every_loops = race_time_config.get("insert_every_loops", 3) if enabled else 0
    return {
        "version": version,
        "generated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ticker_text": ticker_text,
        "race_time_text": f"RACE TIME: {race_time_str}",
        "show_race_time_every_loops": show_every_loops,
        "style": {
            "background_color": display.get("background_color", "#000000"),
            "font_family": ticker.get("font_family", "monospace"),
            "font_size_px": ticker.get("font_size_px", 64),
            "letter_spacing_px": ticker.get("letter_spacing_px", 1),
            "text_color": display.get("text_color", "#ff9900"),
            "y_px": ticker.get("y_px", 120),
        },
        "scroll": {
            "speed_px_s": ticker.get("speed_px_s", 180),
            "fps": ticker.get("fps", 30),
        },
    }
