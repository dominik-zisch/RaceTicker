"""CSV fetching and polling thread."""

import hashlib
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .parser import parse_csv, RaceState

# Late import to avoid circular import at module load (display/format not yet ready)
def _build_and_set_pending(race_state: RaceState, config: dict) -> None:
    from ..format.formatter import build_payload
    from ..display.controller import get_display_controller
    from ..clock.clock import get_clock
    if config.get("mode", {}).get("freeze_updates"):
        return
    version = get_display_controller().get_next_version()
    race_time_str = get_clock().get_elapsed_display()
    payload = build_payload(race_state, config, version=version, race_time_str=race_time_str)
    get_display_controller().set_pending_payload(payload)


logger = logging.getLogger(__name__)

# Thread-safe status: fetcher thread writes, others read.
_fetch_status = {
    "last_fetch_time": None,
    "last_hash": None,
    "hash_changed": False,
    "last_error": None,
    "last_successful_parse_time": None,
    "race_state": None,  # RaceState | None
}
_status_lock = threading.Lock()


def get_fetch_status() -> dict:
    """Return a copy of current fetch status for /status endpoint."""
    with _status_lock:
        out = {
            "last_fetch_time": _fetch_status["last_fetch_time"],
            "last_hash": _fetch_status["last_hash"],
            "hash_changed": _fetch_status["hash_changed"],
            "last_error": _fetch_status["last_error"],
            "last_successful_parse_time": _fetch_status["last_successful_parse_time"],
        }
        rs = _fetch_status["race_state"]
        if rs is not None:
            out["race_state_summary"] = {
                "runner_count": len(rs.runners),
                "updated_at_utc": rs.updated_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": rs.source,
            }
            out["using_last_known_good"] = _fetch_status["last_error"] is not None
        else:
            out["race_state_summary"] = None
            out["using_last_known_good"] = False
        return out


def get_race_state() -> RaceState | None:
    """Return current last-known-good RaceState, or None."""
    with _status_lock:
        return _fetch_status["race_state"]


def _fetch_bytes(url: str, timeout_s: float) -> bytes:
    """Download URL and return raw bytes. Raises on error."""
    req = Request(url, headers={"User-Agent": "RaceTicker/1.0"})
    with urlopen(req, timeout=timeout_s) as resp:
        if resp.status != 200:
            raise HTTPError(url, resp.status, resp.reason, resp.headers, None)
        return resp.read()


def _run_poller(get_config: Callable[[], dict]) -> None:
    """Background loop: fetch CSV URL, compute hash, update status."""
    previous_hash = None
    while True:
        try:
            config = get_config()
            races = config.get("races", {})
            profiles = races.get("profiles", {})
            active_id = races.get("active_race_id")
            if not active_id or active_id not in profiles:
                time.sleep(10)
                continue
            csv_config = config.get("csv", {})
            url = profiles[active_id].get("csv_url")
            if not url:
                time.sleep(10)
                continue
            poll_interval_s = float(csv_config.get("poll_interval_s", 10))
            timeout_s = float(csv_config.get("timeout_s", 5))

            now_utc = datetime.now(timezone.utc)
            fetch_time_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

            data = _fetch_bytes(url, timeout_s)
            current_hash = hashlib.sha256(data).hexdigest()
            hash_changed = previous_hash is not None and current_hash != previous_hash
            previous_hash = current_hash

            with _status_lock:
                _race_state = _fetch_status["race_state"]
            should_parse = hash_changed or _race_state is None

            if should_parse:
                try:
                    race_state = parse_csv(data, config)
                    parse_time_str = race_state.updated_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                    with _status_lock:
                        _fetch_status["race_state"] = race_state
                        _fetch_status["last_successful_parse_time"] = parse_time_str
                        _fetch_status["last_error"] = None
                    _build_and_set_pending(race_state, config)
                except ValueError as e:
                    logger.warning("CSV parse failed: %s", e)
                    with _status_lock:
                        _fetch_status["last_error"] = str(e)

            with _status_lock:
                _fetch_status["last_fetch_time"] = fetch_time_str
                _fetch_status["last_hash"] = current_hash
                _fetch_status["hash_changed"] = hash_changed
        except (URLError, HTTPError, OSError) as e:
            err_msg = str(e)
            logger.warning("CSV fetch failed: %s", err_msg)
            now_utc = datetime.now(timezone.utc)
            fetch_time_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            with _status_lock:
                _fetch_status["last_fetch_time"] = fetch_time_str
                _fetch_status["last_error"] = err_msg
                # leave last_hash and hash_changed as-is
        except Exception as e:
            logger.exception("CSV fetcher error: %s", e)
            with _status_lock:
                _fetch_status["last_error"] = str(e)

        time.sleep(poll_interval_s)


def start_csv_poller(get_config: Callable[[], dict]) -> None:
    """Start the CSV polling background thread. Safe to call once."""
    t = threading.Thread(target=_run_poller, args=(get_config,), daemon=True)
    t.start()
