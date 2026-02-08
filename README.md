# Race Ticker

A Python application that drives a large LED wall to display race lap data as a right-to-left scrolling ticker. The system fetches runner data from a configurable CSV URL, validates it, and formats it into a scrolling display message. An admin UI allows operators to change configuration and control the race clock.

Implementation follows design_doc.md step-by-step.

## Chrome fullscreen (LED display)

To run the ticker fullscreen on the machine driving the LED panel:

1. Start the app (e.g. `python -m race_ticker.app`).
2. On the display machine, open Chrome and go to `http://<host>:5001/display` (use the host’s IP or `localhost` if running on the same machine).
3. Put the window in fullscreen:
   - **F11** (toggle fullscreen), or
   - **Chrome menu (⋮) → Full screen**, or
   - **Presentation mode** (e.g. on macOS: View → Enter Full Screen).
4. For kiosk-style use (no address bar, no tabs), start Chrome with `--kiosk http://<host>:5001/display` (e.g. on macOS: `open -a "Google Chrome" --args --kiosk http://localhost:5001/display`).

Admin is available at `http://<host>:5001/admin` from the same or another device on the network.
