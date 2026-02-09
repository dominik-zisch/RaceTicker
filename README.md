# Race Ticker

Race Ticker is a Python web application that drives a large LED wall (or any display) to show race lap data as a right-to-left scrolling ticker. It fetches runner data from a configurable CSV URL, validates it, and formats it into a scrolling message. Operators use the admin panel to switch race profiles, adjust the ticker appearance, control the race clock, and monitor data status.

---

## Quick Start for Clients

**Install Docker Desktop** from [docker.com/get-docker](https://www.docker.com/get-docker) and start it. Create a file named `docker-compose.yml` with this content (replace `dominikzisch` with the actual Docker Hub username if different):

```yaml
services:
  race-ticker:
    image: dominikzisch/race-ticker:latest
    container_name: race-ticker
    ports:
      - "5001:5001"
    volumes:
      - race-ticker-config:/app/config
      - race-ticker-logs:/app/logs
    restart: unless-stopped

volumes:
  race-ticker-config:
  race-ticker-logs:
```

Open a terminal in the folder containing `docker-compose.yml` and run `docker-compose up -d`. The app will download and start automatically. Open `http://localhost:5001/admin` in a browser to configure race profiles, CSV URLs, ticker appearance, and all other settings—no files to edit, everything is done through the web interface. The display is available at `http://localhost:5001/display` (put this in fullscreen on your LED screen).

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
| **`ticker`** | Scrolling and typography: **`font_family`**, **`font_size_px`**, **`y_px`** (vertical position of top of text in px; 0 = top of screen), **`speed_px_s`**, **`fps`**. |
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

### Quick start

1. **Get the project**  
   Clone or download the repository.

2. **Set up and run**  
   **Option A (Docker)**: Use Docker Compose (see [Running with Docker](#running-with-docker-recommended) section).  
   **Option B (Manual)**: Create a Python virtual environment, install dependencies, and start the app (see [Manual setup](#manual-setup-without-docker) section below).  
   The app runs a web server (default: port 5001).

3. **Display (LED screen)**  
   On the machine connected to the LED display, open a browser and go to **`http://127.0.0.1:5001/display`** (or `http://<IP>:5001/display` if the server is on another machine). Put the browser in **full screen mode** (e.g. F11 or kiosk mode).

4. **Admin panel**  
   In another browser tab or on another machine on the same network, open **`http://127.0.0.1:5001/admin`** (same machine) or **`http://<IP>:5001/admin`** (use the IP of the machine running the app / connected to the LED display). Use the admin to configure position, size, speed, colors, race profile, clock, and other settings.

---

## Running with Docker (recommended)

Docker makes it easy to run Race Ticker without setting up Python environments.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) (optional, but recommended)

### Quick start with Docker

#### Option A: Pull from Docker Hub (recommended for clients)

The Docker image is fully self-contained—no need to clone the repository or manage config files. All configuration is done via the admin panel.

1. **Get docker-compose.yml**  
   Download or create a `docker-compose.yml` file with this content (replace `YOUR_DOCKERHUB_USERNAME` with the actual username):
   ```yaml
   services:
     race-ticker:
       image: YOUR_DOCKERHUB_USERNAME/race-ticker:latest
       container_name: race-ticker
       ports:
         - "5001:5001"
       volumes:
         - race-ticker-config:/app/config
         - race-ticker-logs:/app/logs
       restart: unless-stopped
   
   volumes:
     race-ticker-config:
     race-ticker-logs:
   ```

2. **Run the container**
   ```bash
   docker-compose up -d
   ```
   
   Or run with Docker directly (using named volumes):
   ```bash
   docker run -d -p 5001:5001 \
     -v race-ticker-config:/app/config \
     -v race-ticker-logs:/app/logs \
     --name race-ticker \
     --restart unless-stopped \
     YOUR_DOCKERHUB_USERNAME/race-ticker:latest
   ```

3. **Configure via admin panel**  
   Open **`http://localhost:5001/admin`** and configure:
   - Race profile CSV URLs
   - Ticker appearance (position, size, speed, colors, etc.)
   - Race clock settings
   - All changes are saved automatically and persist across container restarts

#### Option B: Build from source

1. **Build and run**  
   Update `docker-compose.yml` to uncomment `build: .` and comment out `image:`, then:
   ```bash
   docker-compose up -d --build
   ```
   
   Or using Docker directly:
   ```bash
   docker build -t race-ticker .
   docker run -d -p 5001:5001 \
     -v race-ticker-config:/app/config \
     -v race-ticker-logs:/app/logs \
     --name race-ticker \
     --restart unless-stopped \
     race-ticker
   ```

2. **Configure via admin panel**  
   Open **`http://localhost:5001/admin`** to configure all settings. The default config is included in the image, but you can customize everything via the web interface.

### Access the app

- Display: **`http://localhost:5001/display`**  
- Admin: **`http://localhost:5001/admin`**

### Docker details

- **Self-contained**: The image includes default configuration—no need to clone the repository or manage config files. All configuration is done via the admin panel at `/admin`.
- **Ports**: The container exposes port 5001 (configurable via admin panel). Map it to any host port: `-p 8080:5001` to access on port 8080.
- **Volumes**: Uses Docker named volumes for persistence:
  - `race-ticker-config`: Stores configuration (admin panel changes persist here)
  - `race-ticker-logs`: Stores log files
- **Restart**: The container is set to restart automatically unless stopped manually.
- **View logs**: `docker-compose logs -f` or `docker logs -f race-ticker`
- **Stop**: `docker-compose down` or `docker stop race-ticker`
- **Access volumes** (if needed):
  - Config: `docker volume inspect race-ticker-config`
  - Logs: `docker volume inspect race-ticker-logs`

### Publishing to Docker Hub

#### Initial publish

1. **Log in to Docker Hub**
   ```bash
   docker login
   ```

2. **Build and push** (using helper script):
   ```bash
   DOCKERHUB_USERNAME=yourusername ./scripts/docker-push.sh
   ```
   
   Or manually:
   ```bash
   docker build -t YOUR_DOCKERHUB_USERNAME/race-ticker:latest .
   docker push YOUR_DOCKERHUB_USERNAME/race-ticker:latest
   ```

3. **Update docker-compose.yml**  
   Replace `YOUR_DOCKERHUB_USERNAME` in `docker-compose.yml` with your actual Docker Hub username, or have clients update it.

#### Updating the image

After making code changes, rebuild and push the updated image:

**Using the helper script** (recommended):
```bash
# Set your Docker Hub username (or export it in your shell profile)
export DOCKERHUB_USERNAME=yourusername

# Push latest version
./scripts/docker-push.sh

# Or push a specific version tag
./scripts/docker-push.sh v1.0.1
```

**Manually**:
```bash
docker build -t YOUR_DOCKERHUB_USERNAME/race-ticker:latest .
docker push YOUR_DOCKERHUB_USERNAME/race-ticker:latest
```

**Clients update**:
```bash
docker-compose pull
docker-compose up -d
```

Or:
```bash
docker pull YOUR_DOCKERHUB_USERNAME/race-ticker:latest
docker-compose restart
```

**Note**: Client configuration (stored in the `race-ticker-config` volume) persists across image updates. Only code changes require pulling a new image.

### Updating configuration

All configuration is done via the admin panel at `/admin`. Changes are saved automatically and persist across container restarts. No need to edit files or restart the container—just use the web interface.

If you need to reset to defaults, you can remove the config volume:
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d    # Starts fresh with default config
```

---

## Manual setup (without Docker)

### 1. Create and activate a virtual environment

From the project root (requires Python 3.8+):

```bash
python3 -m venv .venv
```

Activate it:

- **Linux / macOS:**  
  `source .venv/bin/activate`
- **Windows (Command Prompt):**  
  `.venv\Scripts\activate.bat`
- **Windows (PowerShell):**  
  `.venv\Scripts\Activate.ps1`

Your prompt should show `(.venv)` when the environment is active.

### 2. Install dependencies

With the virtual environment activated:

```bash
pip install -e .
```

### 3. Configure

- Copy or edit **`config/config.yaml`**.
- Set **`app.host`** and **`app.port`** if needed (default `0.0.0.0:5001`).
- Under **`races.profiles`**, define at least one profile with a **`csv_url`** that returns your race CSV.
- Set **`races.active_race_id`** to the id of the profile you want to use by default.

### 4. Start the application

From the project root (so that `config/config.yaml` is found):

```bash
python -m race_ticker.app
```

Or run the Flask app in your preferred way (e.g. `flask run` with the app factory), ensuring the same config path is used.

The app will start polling the active profile’s CSV URL and serve the display and admin pages.

### 5. Open the display (e.g. on the LED wall machine)

1. On the machine connected to the LED panel, open a browser and go to **`http://<host>:5001/display`** (use the server’s IP or `localhost` if on the same machine).
2. Put the window in fullscreen:
   - **F11** (toggle fullscreen), or  
   - **Browser menu → Full screen**, or  
   - **Presentation mode** (e.g. macOS: View → Enter Full Screen).
3. For kiosk-style use (no address bar or tabs), start Chrome with:
   - **`--kiosk http://<host>:5001/display`**  
   - Example (macOS):  
     `open -a "Google Chrome" --args --kiosk http://localhost:5001/display`

### 6. Use the admin panel

Open **`http://<host>:5001/admin`** on the same device or from another computer on the network. Use it to switch race profiles, change ticker settings, control the race clock, freeze updates, and monitor data status and the CSV preview.
