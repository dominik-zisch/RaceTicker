# LED Race Ticker System Design Document

## 1. Overview

A Python application that drives a **large LED wall** (connected via HDMI and appearing as a normal display) to show **race lap data** as a **right-to-left scrolling ticker** (stock-ticker style). The system fetches runner data from a configurable CSV URL, validates it, formats it into a message like:

`NR.01 LAP 666 TIME 13:45 // NR.02 LAP 666 TIME 12:45 // ...`

Every loop (or every N loops / N minutes), it also inserts a **race time** message:

`RACE TIME: 4:22:22`

The display is intended to run **fullscreen in Chrome** on the machine driving the LED controller. An **admin UI** (served by Flask) allows operators to change configuration (including switching between race profiles) and persists changes back into YAML.

---

## 2. Hardware + Display Constraints

### 2.1 LED panel geometry (from datasheet)

* Tiles are **50 cm × 50 cm**
* Each tile is **176 px × 176 px** 

Your wall is **~6m wide × 0.5m tall**, which likely maps to:

* **~12 tiles wide × 1 tile high** → **~2112 px × 176 px**
  (Exact resolution should be detected at runtime from the HDMI display mode, but typography/layout must assume a short vertical height.)

### 2.2 Visual constraints

* Background: **solid black**
* Ticker text: **orange**
* Font: **monospace / LED-like** preferred (configurable)
* Pixel-aware typography: font size/position should be adjustable in **pixels**, with optional snapping to integer pixels for crispness.

---

## 3. Functional Requirements

### 3.1 Display / ticker behaviour

* Scrolls right-to-left continuously.
* Uses an HTML5 **Canvas** renderer.
* Runs in a dedicated fullscreen display page: `/display`.
* Display must **never “jump”** mid-scroll:

  * New data becomes visible only after the current scroll loop completes.
* Configurable:

  * Scroll speed (pixels/sec)
  * Font family / fallback stack
  * Font size (px)
  * Letter spacing (px)
  * Ticker vertical position (y) and height (optional)
  * Separator style (`//`, `•`, `|`, etc.)
  * Target FPS (default 30; configurable)

### 3.2 CSV ingest

* CSV is fetched from a configured URL.
* Polling runs in a **background thread** with configurable poll interval.
* Every fetch:

  * Download CSV bytes
  * Compute hash (e.g. SHA-256)
  * If hash unchanged → do nothing
  * If changed → parse + validate + transform into a canonical “race state”
* Constraints:

  * Max **10 runners** at once
  * Columns: `runner_number`, `lap_number`, `lap_time`, `distance` (exact header names may vary; mapping should be configurable)

### 3.3 Race time

* Initially tracked internally:

  * Start/pause/reset via admin UI/API
  * Persisted in YAML (or a small state file) so restarts can recover
* Display insertion:

  * Show race time message every N loops OR every N seconds (configurable)
  * Also allow manual “force show now” for operator

### 3.4 Admin UI

* Simple modern flat HTML5 UI at `/admin`.
* Functions:

  * Select active “race profile” (3 by default; extensible)
  * Edit profile CSV URLs
  * Edit ticker settings (speed, font, size, position, separators, race-time insertion rules, FPS, polling interval)
  * Control race clock (start/pause/reset)
  * Toggle simulation mode
  * Optional: “freeze display updates” toggle
* Any config change in UI:

  * Validated
  * Applied immediately
  * Persisted back to YAML (atomic write)

### 3.5 Health & status

* `/status` endpoint returns JSON:

  * active profile ID/name
  * last CSV fetch time
  * last successful parse time
  * last hash value
  * runner count
  * current mode (live/simulate)
  * display resolution detected (if available)
  * pending update queued? (yes/no)
  * last error (if any)

### 3.6 Simulation mode

* No external files required.
* Generates random but plausible data for up to 10 runners:

  * Runner numbers stable
  * Lap increments over time
  * Lap time updates with variance
* Uses the **same pipeline** as live mode (the renderer and message formatting don’t care).

---

## 4. Non-Functional Requirements

* **Reliability**: display should keep running even if CSV fetch fails.

  * Use “last-known-good” race state.
  * Never crash the renderer due to bad data.
* **Operator safety**: avoid “half updated” content.

  * Use double-buffering: `active_message` and `pending_message`.
* **Performance**:

  * Target FPS default 30 (configurable).
  * Canvas render should be lightweight (single line text, minimal effects).
* **Simplicity**:

  * Single Python service (Flask + poller thread).
  * Frontend served as static assets by Flask.

---

## 5. High-Level Architecture

### 5.1 Components

1. **Config Manager (YAML)**

   * Loads config at startup
   * Applies changes
   * Persists changes (atomic write)
2. **Race Clock**

   * Internal race timer state (running/paused, start time, accumulated elapsed)
   * Exposed to UI/API
3. **Data Ingestor**

   * Polling thread: fetch CSV bytes, hash, parse, validate
   * Produces canonical `RaceState`
4. **Message Formatter**

   * Converts `RaceState` → display strings (`runner ticker string`, `race time string`)
   * Applies content density rules
5. **Display Controller (server-side)**

   * Holds `active_payload` + `pending_payload`
   * On “loop complete” event from frontend swaps pending → active
6. **Frontend Display (Canvas)**

   * Fullscreen canvas
   * Scrolls text at configured speed
   * Calls back to backend when loop completes
7. **Admin Frontend**

   * Simple forms + buttons
   * Calls backend API

### 5.2 Data flow

* Poller fetches + validates CSV → builds `RaceState`
* Formatter creates `pending_payload`
* Frontend scrolls `active_payload`
* When scroll completes, frontend signals backend → backend swaps to pending (if present) → frontend pulls new payload and continues

---

## 6. Data Models

### 6.1 Canonical RaceState (Python)

```python
RaceState:
  updated_at_utc: datetime
  runners: List[RunnerState]  # max 10
  distance_label: str | None
  source: "live" | "simulate"
```

```python
RunnerState:
  runner_number: int
  lap_number: int
  lap_time_str: str   # e.g. "13:45" (string to avoid locale parsing issues)
  distance_str: str | None
```

### 6.2 Display payload (shared via JSON)

```json
{
  "version": 12,
  "generated_at_utc": "2026-02-05T14:55:00Z",
  "ticker_text": "NR.01 LAP 666 TIME 13:45 // ...",
  "race_time_text": "RACE TIME: 4:22:22",
  "show_race_time_every_loops": 3,
  "style": {
    "font_family": "SomeMono, monospace",
    "font_size_px": 64,
    "letter_spacing_px": 2,
    "text_color": "#ff9900",
    "y_px": 120
  },
  "scroll": {
    "speed_px_s": 180,
    "fps": 30
  }
}
```

---

## 7. YAML Configuration

### 7.1 File layout

* `config/config.yaml` (main config)
* Optionally: `config/secrets.yaml` (if auth or tokens ever appear later)

### 7.2 Example `config.yaml`

```yaml
app:
  host: "0.0.0.0"
  port: 5000

mode:
  source: "live"        # live | simulate
  freeze_updates: false

races:
  active_race_id: "race_10k"
  profiles:
    race_10k:
      name: "10K"
      csv_url: "https://.../exportevodatatest.csv"
    race_half:
      name: "Half Marathon"
      csv_url: "https://.../exportevodatatest.csv"
    race_full:
      name: "Marathon"
      csv_url: "https://.../exportevodatatest.csv"

csv:
  poll_interval_s: 10
  timeout_s: 5
  expected_columns:
    runner: "runner number"
    lap: "lap number"
    lap_time: "lap time"
    distance: "distance"

display:
  background_color: "#000000"
  text_color: "#ff9900"
  separator: " // "
  template: "NR.{runner:02d} LAP {lap} TIME {lap_time}"
  max_runners: 10

ticker:
  font_family: "SomeMono, monospace"
  font_size_px: 64
  letter_spacing_px: 1
  y_px: 120
  speed_px_s: 180
  fps: 30
  pixel_snap: true

race_time:
  enabled: true
  insert_every_loops: 3         # alternatively: insert_every_seconds
  insert_every_seconds: null

clock:
  state: "stopped"              # running | paused | stopped
  started_at_utc: null
  accumulated_s: 0
```

**Persistence rule:** any API-driven change updates this YAML on disk via atomic write.

---

## 8. HTTP API (Flask)

### 8.1 Pages

* `GET /display` → fullscreen ticker page (canvas)
* `GET /admin` → operator UI

### 8.2 Config & control

* `GET /api/config` → returns current config (sanitised)
* `POST /api/config` → patch config keys (validated) + persist YAML
* `POST /api/race/select` → `{race_id: "race_half"}`
* `POST /api/mode` → `{source: "live"|"simulate"}`
* `POST /api/freeze` → `{freeze: true|false}`

### 8.3 Clock

* `POST /api/clock/start`
* `POST /api/clock/pause`
* `POST /api/clock/reset`
* `GET /api/clock` → current elapsed + state

### 8.4 Display payload handshake

* `GET /api/payload` → returns current `active_payload`
* `POST /api/loop_complete` → frontend calls when a scroll loop finishes

  * backend swaps pending→active if available
  * returns `{swapped: true|false, version: N}`

### 8.5 Health

* `GET /status` → status JSON described earlier

---

## 9. Frontend Display Design

### 9.1 Canvas renderer responsibilities

* Request payload from backend
* Measure text width
* Scroll text from right edge to left edge:

  * Start x = canvas.width
  * End when x + text_width < 0 → loop complete
* On loop complete:

  * Call `/api/loop_complete`
  * If swapped, fetch new payload (or backend can return updated payload directly)

### 9.2 Pixel-aware typography rules

* Render at integer pixel coordinates when `pixel_snap: true`
* Apply letter spacing manually (canvas doesn’t natively support it reliably):

  * Either draw char-by-char with extra spacing
  * Or approximate with CSS font features if acceptable, but char-by-char is more predictable for LED readability
* Provide config for:

  * `font_size_px`
  * `y_px` baseline
  * `letter_spacing_px`

### 9.3 Fullscreen & black background

* Full-page black body
* Canvas covers entire viewport
* Only ticker line drawn; rest remains black

---

## 10. CSV Validation Rules

Minimum validations:

* CSV fetch succeeded (HTTP 200)
* Has header row (or configured to not require header)
* Required columns exist per `expected_columns` mapping
* For each row used:

  * runner_number parseable int
  * lap_number parseable int
  * lap_time non-empty string (optionally validate time format)
* Deduping:

  * If multiple rows per runner: choose the row with highest lap_number, or latest by appearance (define this)
* Clamp to `max_runners` (10)

Failure handling:

* If parse/validation fails:

  * log error
  * keep last-known-good `RaceState`
  * update `/status` last_error

---

## 11. Implementation Strategy (step-by-step)

The goal is to implement in **small, verifiable increments**. Each step should leave the system runnable.

### Step 1 — Create repository structure (no logic yet)

Deliverable: folder skeleton + empty modules + README.

Proposed structure:

```
race_ticker/
  README.md
  pyproject.toml            # or requirements.txt
  config/
    config.yaml
  src/
    race_ticker/
      __init__.py
      app.py                # Flask entry
      config/
        __init__.py
        manager.py
        schema.py
      clock/
        __init__.py
        clock.py
      ingest/
        __init__.py
        csv_fetcher.py
        parser.py
        simulator.py
      format/
        __init__.py
        formatter.py
      display/
        __init__.py
        controller.py
      web/
        templates/
          admin.html
          display.html
        static/
          admin.css
          admin.js
          display.js
  scripts/
    run_dev.sh
```

### Step 2 — Config manager (load + save YAML)

Deliverable:

* Load `config/config.yaml`
* Provide `get_config()` and `update_config(patch)` with:

  * validation (basic type/range checks)
  * atomic write on save

Add a tiny Flask route `/api/config` returning config.

### Step 3 — Minimal Flask app + two pages

Deliverable:

* Flask app runs
* `/admin` returns a placeholder UI
* `/display` shows a black page
* `/status` returns basic JSON (uptime + config loaded)

### Step 4 — Display controller + payload plumbing

Deliverable:

* Backend holds `active_payload` and returns it from `/api/payload`
* Frontend `display.js` fetches payload and renders *static* text on canvas (no scrolling yet)

### Step 5 — Implement scrolling loop in Canvas

Deliverable:

* Smooth right-to-left scroll
* Loop-complete detection working
* Calls `/api/loop_complete` and logs response
* FPS throttling implemented (default 30, configurable)

At this point you should already be able to display a demo ticker.

### Step 6 — CSV fetcher thread + hashing (no parsing yet)

Deliverable:

* Background thread polling `csv_url`
* Computes SHA-256 hash
* Updates `/status` with:

  * last_fetch_time
  * last_hash
  * changed? flag

No impact on display yet.

### Step 7 — CSV parsing + validation + RaceState

Deliverable:

* Parse CSV into canonical `RaceState`
* Validation + dedupe rules
* If parse fails, keeps last-known-good
* Expose current `RaceState` in `/status` (summary only)

### Step 8 — Message formatter (RaceState → ticker string)

Deliverable:

* Formatting rules implemented:

  * max 10 runners
  * stable ordering (e.g., runner number ascending)
  * separators
* Produces `pending_payload` whenever RaceState changes

### Step 9 — Double-buffer swap only on loop complete

Deliverable:

* Backend sets `pending_payload` on new data
* Swap to `active_payload` only when `/api/loop_complete` called
* Frontend picks up new version seamlessly

This completes the “no mid-scroll jumps” requirement.

### Step 10 — Race clock + race time insertion

Deliverable:

* Internal clock with start/pause/reset
* Race time string appears every `insert_every_loops` (or seconds)
* Config + API + persisted YAML

### Step 11 — Admin UI v1 (usable on site)

Deliverable:

* Admin page:

  * Select race profile
  * Edit URLs
  * Set poll interval, speed, font, size, y position, FPS
  * Start/pause/reset clock
  * Toggle simulation mode
  * Freeze updates toggle
* All changes call API and persist YAML

### Step 12 — Simulation mode

Deliverable:

* Simulator generates RaceState updates in background when enabled
* Same formatting + pending swap behaviour
* Great for testing without AWS

### Step 13 — Polish + hardening

Deliverable:

* Better error messages in UI
* `/status` shows last error and recovery
* Add “test pattern” preset
* Add logging config, log rotation
* Document Chrome fullscreen usage

---

## 12. Testing Plan

* Unit tests:

  * CSV parser validation cases
  * Formatter output correctness
  * Clock elapsed time behaviour (pause/resume)
* Manual tests:

  * Run display full screen; confirm no mid-scroll content change
  * Kill network; ensure ticker continues with last known good data
  * Switch profiles during scroll; ensure change applies next loop only
  * Simulation mode end-to-end

---

## 13. Deployment Notes

* Run Flask app on the LED-driving machine.
* Open Chrome to `http://localhost:5000/display` in fullscreen (kiosk-style operational approach).
* Admin can be used locally or from another device on LAN at `http://<host>:5000/admin`.

(Exact kiosk/autostart steps can be added once you know OS/environment.)
