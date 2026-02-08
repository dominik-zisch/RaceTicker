# Race Ticker

Race Ticker is a Python web application that drives a large LED wall (or any display) to show race lap data as a right-to-left scrolling ticker. It fetches runner data from a configurable CSV URL, validates it, and formats it into a scrolling message. Operators use the admin panel to switch race profiles, adjust the ticker appearance, control the race clock, and monitor data status.

---

## User-facing URLs

| URL | Description |
|-----|--------------|
| **`/display`** | Full-screen ticker view. Open this on the machine connected to the LED wall and put the browser in fullscreen (F11 or kiosk mode). |
| **`/admin`** | Admin panel. Use this to change configuration, start/pause/reset the race clock, and see data status. Can be opened on the same device or from another machine on the network. |
| **`/status`** | JSON status page. Shows health, CSV fetch state, clock state, and a preview of current runner data. Useful for monitoring or debugging. |

All URLs use the same host and port as the app (default: `http://<host>:5001`).

---

## Configuration file

The app is configured via a single YAML file. By default it is loaded from **`config/config.yaml`** (relative to the project root).

### Top-level sections

| Section | Purpose |
|--------|--------|
| **`app`** | Server binding: `host` (e.g. `0.0.0.0` for all interfaces) and `port` (default `5001`). |
| **`mode`** | `source`: `live` or `simulate`. `freeze_updates`: when `true`, the display stops updating from CSV (last data is shown until unfrozen). |
| **`races`** | **`active_race_id`**: which profile is currently used. **`profiles`**: map of profile id → `name` and **`csv_url`** (URL that returns the race CSV). You can define multiple profiles (e.g. 10K, Half Marathon, Marathon) and switch them from the admin. |
| **`csv`** | **`poll_interval_s`**: how often to fetch the CSV (seconds). **`timeout_s`**: HTTP timeout for the fetch. |
| **`display`** | Ticker content and layout: **`background_color`**, **`text_color`** (hex), **`separator`** between runners (e.g. ` // `), **`max_runners`** (how many runners to show, 1–10), **`sort_runners`**: `runner` (by runner number) or `csv_order`. |
| **`ticker`** | Scrolling and typography: **`font_family`**, **`font_size_px`**, **`y_px`** (vertical position), **`speed_px_s`**, **`fps`**. |
| **`race_time`** | **`insert_every_loops`**: how often to insert the race clock text into the ticker (e.g. every 3 scroll loops). |

The **CSV** is expected to have no header. Columns (in order): runner number, lap number, lap time, and optionally distance. The app deduplicates by runner (keeping the latest lap) and sorts according to `display.sort_runners`.

---

## Admin panel

The admin panel at **`/admin`** is split into two columns.

### Left column

- **Race profile**  
  - **Active profile**: dropdown to switch the current race (e.g. 10K, Half Marathon, Marathon).  
  - One URL field per profile: set or change the **CSV URL** for each race. Changes are saved automatically when you edit the field.

- **Ticker**  
  - Background color, text color, separator, max runners, sort order.  
  - Speed (px/s), font family, font size, Y position, FPS.  
  - Poll interval (how often the CSV is fetched).  
  - “Race time every … loops” (how often the race clock is inserted).  
  - **Save ticker settings** applies all ticker/display values to the config.

### Right column

- **Race clock**  
  - Shows current elapsed time. Buttons: **Start**, **Pause**, **Reset**. Use these to control the race clock that can be shown on the ticker.

- **Mode**  
  - **Freeze display updates**: when checked, the ticker stops updating from the CSV; the last loaded data stays on screen until you uncheck it.

- **Data status**  
  - Status message (e.g. “Data OK — 3 runner(s), last update …” or “Last error: …”).  
  - **Current CSV data**: preview of the first *n* runners (n = Max runners) as currently loaded. Refreshes with the status poll (every few seconds).

---

## Setup and running

### 1. Install dependencies

From the project root:

```bash
pip install -e .
```

(Requires Python 3.8+.)

### 2. Configure

- Copy or edit **`config/config.yaml`**.
- Set **`app.host`** and **`app.port`** if needed (default `0.0.0.0:5001`).
- Under **`races.profiles`**, define at least one profile with a **`csv_url`** that returns your race CSV.
- Set **`races.active_race_id`** to the id of the profile you want to use by default.

### 3. Start the application

From the project root (so that `config/config.yaml` is found):

```bash
python -m race_ticker.app
```

Or run the Flask app in your preferred way (e.g. `flask run` with the app factory), ensuring the same config path is used.

The app will start polling the active profile’s CSV URL and serve the display and admin pages.

### 4. Open the display (e.g. on the LED wall machine)

1. On the machine connected to the LED panel, open a browser and go to **`http://<host>:5001/display`** (use the server’s IP or `localhost` if on the same machine).
2. Put the window in fullscreen:
   - **F11** (toggle fullscreen), or  
   - **Browser menu → Full screen**, or  
   - **Presentation mode** (e.g. macOS: View → Enter Full Screen).
3. For kiosk-style use (no address bar or tabs), start Chrome with:
   - **`--kiosk http://<host>:5001/display`**  
   - Example (macOS):  
     `open -a "Google Chrome" --args --kiosk http://localhost:5001/display`

### 5. Use the admin panel

Open **`http://<host>:5001/admin`** on the same device or from another computer on the network. Use it to switch race profiles, change ticker settings, control the race clock, freeze updates, and monitor data status and the CSV preview.
