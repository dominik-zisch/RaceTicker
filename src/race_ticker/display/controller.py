"""Server-side display payload management with double-buffering."""

import threading
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()


def build_default_payload(config: dict[str, Any]) -> dict[str, Any]:
    """Build a default display payload from config (shown until CSV data is loaded)."""
    ticker = config.get("ticker", {})
    display = config.get("display", {})
    race_time = config.get("race_time", {})
    enabled = race_time.get("enabled", True)
    show_every_loops = race_time.get("insert_every_loops", 3) if enabled else 0
    return {
        "version": 1,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ticker_text": "Loading Data",
        "race_time_text": "RACE TIME: 0:00:00",
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


class DisplayController:
    """Holds active (and later pending) payload; swaps on loop complete."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._active_payload = build_default_payload(config)
        self._pending_payload: dict[str, Any] | None = None
        self._next_version = 2  # 1 used by default payload

    def get_active_payload(self) -> dict[str, Any]:
        """Return current active payload (copy)."""
        import copy
        with _lock:
            return copy.deepcopy(self._active_payload)

    def get_next_version(self) -> int:
        """Return and increment version for new payloads (thread-safe)."""
        with _lock:
            v = self._next_version
            self._next_version += 1
            return v

    def set_pending_payload(self, payload: dict[str, Any] | None) -> None:
        """Set pending payload; will become active on next loop complete."""
        with _lock:
            self._pending_payload = payload

    def set_active_payload(self, payload: dict[str, Any]) -> None:
        """Set payload as active immediately (e.g. when CSV data updates). Clears pending."""
        with _lock:
            self._active_payload = payload
            self._pending_payload = None

    def refresh_pending_from_config(self, config: dict[str, Any]) -> None:
        """Rebuild pending payload from current active content but with new config (style/scroll).
        Call after ticker/display/race_time config change so the next loop uses new settings.
        """
        self._apply_config_to_payload(config, set_pending=True)

    def refresh_active_from_config(self, config: dict[str, Any]) -> None:
        """Apply new config to active payload immediately and clear pending.
        Display will pick up the new payload on its next poll (no reload needed).
        """
        self._apply_config_to_payload(config, set_pending=False)

    def _apply_config_to_payload(
        self, config: dict[str, Any], *, set_pending: bool
    ) -> None:
        import copy
        ticker = config.get("ticker", {})
        display = config.get("display", {})
        race_time = config.get("race_time", {})
        with _lock:
            current = copy.deepcopy(self._active_payload)
            v = self._next_version
            self._next_version += 1
        current["version"] = v
        current["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        enabled = race_time.get("enabled", True)
        current["show_race_time_every_loops"] = race_time.get("insert_every_loops", 3) if enabled else 0
        current["style"] = {
            "background_color": display.get("background_color", "#000000"),
            "font_family": ticker.get("font_family", "monospace"),
            "font_size_px": ticker.get("font_size_px", 64),
            "letter_spacing_px": ticker.get("letter_spacing_px", 1),
            "text_color": display.get("text_color", "#ff9900"),
            "y_px": ticker.get("y_px", 120),
        }
        current["scroll"] = {
            "speed_px_s": ticker.get("speed_px_s", 180),
            "fps": ticker.get("fps", 30),
        }
        try:
            from ..ingest.csv_fetcher import get_race_state
            from ..format.formatter import build_queued_ticker_text
            from ..clock.clock import get_clock
            rs = get_race_state()
            if rs is not None:
                race_time_str = get_clock().get_elapsed_display()
                current["ticker_text"] = build_queued_ticker_text(rs, config, race_time_str=race_time_str)
                current["race_time_text"] = "RACE TIME: " + race_time_str
        except Exception:
            pass
        with _lock:
            if set_pending:
                self._pending_payload = current
            else:
                self._active_payload = current
                self._pending_payload = None

    def swap_pending_to_active(self) -> bool:
        """If pending exists, make it active. Returns True if swapped."""
        with _lock:
            if self._pending_payload is None:
                return False
            self._active_payload = self._pending_payload
            self._pending_payload = None
            return True


_display_controller: DisplayController | None = None


def get_display_controller() -> DisplayController:
    """Return the global display controller instance."""
    if _display_controller is None:
        raise RuntimeError("Display controller not initialized.")
    return _display_controller


def init_display_controller(config: dict[str, Any]) -> None:
    """Initialize the global display controller with config."""
    global _display_controller
    _display_controller = DisplayController(config)
