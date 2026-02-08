"""Flask application entry point."""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, render_template, request

from .config.manager import init_config_manager, get_config_manager
from .display.controller import init_display_controller, get_display_controller
from .ingest.csv_fetcher import start_csv_poller, get_fetch_status
from .clock.clock import init_clock, get_clock

# Uptime start (set when app is created)
_start_time: float | None = None


def _setup_logging(project_root: Path) -> None:
    """Configure logging with RotatingFileHandler (1 MB, 3 backups)."""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "race_ticker.log"
    handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)


def create_app(config_path: Path | None = None) -> Flask:
    """Create and configure Flask application.

    Args:
        config_path: Path to config.yaml. If None, uses default location.

    Returns:
        Configured Flask app instance
    """
    global _start_time
    _start_time = time.time()

    web_dir = Path(__file__).parent / "web"
    app = Flask(
        __name__,
        template_folder=str(web_dir / "templates"),
        static_folder=str(web_dir / "static"),
        static_url_path="/static",
    )

    # Initialize config manager
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"
    else:
        project_root = Path(__file__).parent.parent.parent
    _setup_logging(project_root)
    init_config_manager(config_path)
    init_display_controller(get_config_manager().get_config())
    init_clock(get_config_manager().get_config())
    start_csv_poller(lambda: get_config_manager().get_config())

    @app.route("/api/clock", methods=["GET"])
    def get_clock_status():
        """Current clock state and elapsed time."""
        clock = get_clock()
        return jsonify({
            "state": clock.get_state(),
            "elapsed_seconds": round(clock.get_elapsed_seconds(), 2),
            "elapsed_display": clock.get_elapsed_display(),
        })

    @app.route("/api/clock/start", methods=["GET", "POST"])
    def clock_start():
        get_clock().start()
        return jsonify({"ok": True})

    @app.route("/api/clock/pause", methods=["GET", "POST"])
    def clock_pause():
        get_clock().pause()
        return jsonify({"ok": True})

    @app.route("/api/clock/reset", methods=["GET", "POST"])
    def clock_reset():
        get_clock().reset()
        return jsonify({"ok": True})

    @app.route("/api/payload", methods=["GET"])
    def get_payload():
        """Return current active display payload."""
        return jsonify(get_display_controller().get_active_payload())

    @app.route("/api/loop_complete", methods=["POST"])
    def loop_complete():
        """Frontend signals scroll loop finished; swap pending→active if any. Returns swapped + version."""
        ctrl = get_display_controller()
        swapped = ctrl.swap_pending_to_active()
        payload = ctrl.get_active_payload()
        return jsonify({"swapped": swapped, "version": payload.get("version", 0)})

    @app.route("/admin", methods=["GET"])
    def admin():
        """Operator admin UI (placeholder)."""
        return render_template("admin.html")

    @app.route("/display", methods=["GET"])
    def display():
        """Fullscreen ticker display page."""
        return render_template("display.html")

    @app.route("/status", methods=["GET"])
    def status():
        """Health/status JSON including CSV fetch state and clock."""
        uptime_s = time.time() - _start_time if _start_time else 0
        clock = get_clock()
        out = {
            "current_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "uptime_seconds": round(uptime_s, 2),
            "config_loaded": True,
            "clock": {
                "state": clock.get_state(),
                "elapsed_seconds": round(clock.get_elapsed_seconds(), 2),
                "elapsed_display": clock.get_elapsed_display(),
            },
            **get_fetch_status(),
        }
        return jsonify(out)

    @app.route("/api/config", methods=["GET"])
    def get_config():
        """Return current configuration."""
        manager = get_config_manager()
        return jsonify(manager.get_config())

    @app.route("/api/config", methods=["POST"])
    def patch_config():
        """Patch config (JSON body), validate and persist YAML."""
        patch = request.get_json(silent=True) or {}
        get_config_manager().update_config(patch)
        if any(k in patch for k in ("ticker", "display", "race_time")):
            get_display_controller().refresh_active_from_config(
                get_config_manager().get_config()
            )
        return jsonify(get_config_manager().get_config())

    @app.route("/api/race/select", methods=["POST"])
    def race_select():
        """Set active race profile. Body: { \"race_id\": \"race_half\" }."""
        data = request.get_json(silent=True) or {}
        race_id = data.get("race_id")
        if not race_id or not isinstance(race_id, str):
            return jsonify({"error": "race_id required (string)"}), 400
        get_config_manager().update_config({"races": {"active_race_id": race_id}})
        return jsonify({"ok": True})

    @app.route("/api/mode", methods=["POST"])
    def mode_set():
        """Set mode. Body: { \"source\": \"live\"|\"simulate\" }."""
        data = request.get_json(silent=True) or {}
        source = data.get("source")
        if source not in ("live", "simulate"):
            return jsonify({"error": "source must be 'live' or 'simulate'"}), 400
        get_config_manager().update_config({"mode": {"source": source}})
        return jsonify({"ok": True})

    @app.route("/api/freeze", methods=["POST"])
    def freeze_set():
        """Set freeze display updates. Body: { \"freeze\": true|false }."""
        data = request.get_json(silent=True) or {}
        freeze = data.get("freeze")
        if not isinstance(freeze, bool):
            return jsonify({"error": "freeze must be boolean"}), 400
        get_config_manager().update_config({"mode": {"freeze_updates": freeze}})
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    app = create_app()
    cfg = get_config_manager().get_config()
    app.run(
        host=cfg["app"]["host"],
        port=cfg["app"]["port"],
        debug=True,
    )
