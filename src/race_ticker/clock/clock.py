"""Internal race timer state management. Persists to config on change."""

import threading
from datetime import datetime, timezone
from typing import Any, Literal

ClockState = Literal["running", "paused", "stopped"]

_lock = threading.Lock()
_clock: "RaceClock | None" = None


def _parse_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def format_elapsed(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    s = int(round(seconds))
    if s < 0:
        s = 0
    h, remainder = divmod(s, 3600)
    m, sec = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


class RaceClock:
    """Race timer: running / paused / stopped. State persisted to YAML via config manager."""

    def __init__(self, config: dict[str, Any]) -> None:
        clock = config.get("clock", {})
        self._state: ClockState = clock.get("state") or "stopped"
        if self._state not in ("running", "paused", "stopped"):
            self._state = "stopped"
        self._started_at_utc: str | None = clock.get("started_at_utc")
        self._accumulated_s: float = float(clock.get("accumulated_s") or 0)
        if self._accumulated_s < 0:
            self._accumulated_s = 0

    def get_state(self) -> ClockState:
        with _lock:
            return self._state

    def get_elapsed_seconds(self) -> float:
        with _lock:
            if self._state == "running" and self._started_at_utc:
                started = _parse_utc(self._started_at_utc)
                if started:
                    delta = (datetime.now(timezone.utc) - started).total_seconds()
                    return self._accumulated_s + delta
            return self._accumulated_s

    def get_elapsed_display(self) -> str:
        return format_elapsed(self.get_elapsed_seconds())

    def _persist(self) -> None:
        from ..config.manager import get_config_manager
        get_config_manager().update_config({
            "clock": {
                "state": self._state,
                "started_at_utc": self._started_at_utc,
                "accumulated_s": self._accumulated_s,
            }
        })

    def start(self) -> None:
        with _lock:
            if self._state == "running":
                return
            if self._state == "paused" or self._state == "stopped":
                self._accumulated_s = self._accumulated_s  # no change
            self._state = "running"
            self._started_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self._persist()

    def pause(self) -> None:
        with _lock:
            if self._state != "running":
                return
            started = _parse_utc(self._started_at_utc)
            if started:
                self._accumulated_s += (datetime.now(timezone.utc) - started).total_seconds()
            self._state = "paused"
            self._started_at_utc = None
            self._persist()

    def reset(self) -> None:
        with _lock:
            self._state = "stopped"
            self._started_at_utc = None
            self._accumulated_s = 0
            self._persist()


def get_clock() -> RaceClock:
    if _clock is None:
        raise RuntimeError("Clock not initialized. Call init_clock() first.")
    return _clock


def init_clock(config: dict[str, Any]) -> None:
    global _clock
    _clock = RaceClock(config)
