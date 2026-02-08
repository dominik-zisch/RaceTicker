// Admin UI – load config, persist changes via API

(function () {
  const api = function (path, opts) {
    return fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts));
  };

  function showMessage(text, isError) {
    const el = document.getElementById("message");
    el.textContent = text;
    el.className = "message" + (isError ? " error" : "");
    if (text) setTimeout(function () { el.textContent = ""; }, 4000);
  }

  var lastConfig = null;

  function loadConfig() {
    return api("/api/config").then(function (r) {
      if (!r.ok) throw new Error("Config load failed");
      return r.json();
    }).then(function (cfg) {
      lastConfig = cfg;
      return cfg;
    });
  }

  function fillForm(cfg) {
    const races = cfg.races || {};
    const profiles = races.profiles || {};
    const activeId = races.active_race_id || "";

    const sel = document.getElementById("active-race");
    sel.innerHTML = "";
    Object.keys(profiles).forEach(function (id) {
      const o = document.createElement("option");
      o.value = id;
      o.textContent = profiles[id].name || id;
      if (id === activeId) o.selected = true;
      sel.appendChild(o);
    });

    const urlsDiv = document.getElementById("profile-urls");
    urlsDiv.innerHTML = "";
    Object.keys(profiles).forEach(function (id) {
      const p = document.createElement("p");
      p.innerHTML = "<label>" + (profiles[id].name || id) + " CSV URL <input type=\"url\" data-profile-id=\"" + id + "\" data-field=\"csv_url\" value=\"" + (profiles[id].csv_url || "").replace(/"/g, "&quot;") + "\" style=\"width:100%;max-width:400px;\"></label>";
      urlsDiv.appendChild(p);
    });

    function toHexColor(val, fallback) {
      if (val == null || val === "") return fallback;
      var s = String(val).trim();
      if (/^#[0-9A-Fa-f]{6}$/.test(s)) return s;
      if (/^[0-9A-Fa-f]{6}$/.test(s)) return "#" + s;
      return fallback;
    }
    const d = (cfg.display || {});
    const t = (cfg.ticker || {});
    document.getElementById("background_color").value = toHexColor(d.background_color, "#000000");
    document.getElementById("text_color").value = toHexColor(d.text_color, "#ff9900");
    document.getElementById("separator").value = d.separator != null ? d.separator : " // ";
    document.getElementById("max_runners").value = d.max_runners != null ? d.max_runners : 10;
    document.getElementById("sort_runners").value = (d.sort_runners === "csv_order" ? "csv_order" : "runner");
    document.getElementById("speed_px_s").value = t.speed_px_s != null ? t.speed_px_s : 180;
    var fontVal = (t.font_family || "monospace").trim();
    var fontSelect = document.getElementById("font_family");
    var fontCustom = document.getElementById("font_family_custom");
    var found = false;
    for (var i = 0; i < fontSelect.options.length; i++) {
      if (fontSelect.options[i].value === fontVal || (fontSelect.options[i].value !== "__other__" && fontSelect.options[i].value.indexOf(fontVal) === 0)) {
        fontSelect.selectedIndex = i;
        found = true;
        fontCustom.style.display = "none";
        break;
      }
    }
    if (!found) {
      fontSelect.value = "__other__";
      fontCustom.value = fontVal;
      fontCustom.style.display = "inline";
    } else {
      fontCustom.value = "";
    }
    document.getElementById("font_size_px").value = t.font_size_px != null ? t.font_size_px : 64;
    document.getElementById("y_px").value = t.y_px != null ? t.y_px : 120;
    document.getElementById("fps").value = (cfg.ticker || {}).fps != null ? cfg.ticker.fps : 30;
    document.getElementById("poll_interval_s").value = (cfg.csv || {}).poll_interval_s != null ? cfg.csv.poll_interval_s : 10;
    document.getElementById("insert_every_loops").value = (cfg.race_time || {}).insert_every_loops != null ? cfg.race_time.insert_every_loops : 3;

    document.getElementById("freeze").checked = !!(cfg.mode || {}).freeze_updates;
  }

  function updateClockDisplay() {
    api("/api/clock").then(function (r) { return r.json(); }).then(function (data) {
      document.getElementById("clock-display").textContent = data.elapsed_display || "0:00";
      if (data.state === "running") setTimeout(updateClockDisplay, 500);
    }).catch(function () {});
  }

  function refreshStatus() {
    api("/status").then(function (r) { return r.json(); }).then(function (data) {
      var sumEl = document.getElementById("status-summary");
      var errEl = document.getElementById("status-error");
      var recEl = document.getElementById("status-recovery");
      if (data.last_error) {
        errEl.textContent = "Last error: " + data.last_error;
        errEl.style.display = "block";
      } else {
        errEl.textContent = "";
        errEl.style.display = "none";
      }
      if (data.using_last_known_good) {
        recEl.textContent = "Using last known good data (display continues with cached race data).";
        recEl.style.display = "block";
        sumEl.textContent = "";
        sumEl.style.display = "none";
      } else {
        recEl.textContent = "";
        recEl.style.display = "none";
      }
      if (!data.last_error) {
        if (data.race_state_summary) {
          sumEl.textContent = "Data OK — " + data.race_state_summary.runner_count + " runner(s), last update " + (data.last_successful_parse_time || data.last_fetch_time || "—") + ".";
        } else {
          sumEl.textContent = "Waiting for CSV data…";
        }
        sumEl.style.display = "block";
      } else {
        sumEl.style.display = "none";
      }

      var nEl = document.getElementById("csv-preview-n");
      var preEl = document.getElementById("csv-preview");
      if (nEl) nEl.textContent = data.max_runners != null ? data.max_runners : "—";
      if (preEl) {
        var preview = data.csv_preview;
        if (!preview || preview.length === 0) {
          preEl.textContent = "No runner data yet.";
        } else {
          preEl.textContent = preview.map(function (r) {
            var line = "NR." + r.runner_number + "  LAP " + r.lap_number + "  TIME " + (r.lap_time_str || "—");
            if (r.distance_str) line += "  " + r.distance_str;
            return line;
          }).join("\n");
        }
      }
    }).catch(function () {});
  }

  loadConfig().then(fillForm).then(updateClockDisplay).then(refreshStatus).catch(function (e) {
    showMessage("Failed to load config: " + e.message, true);
  });
  setInterval(refreshStatus, 5000);

  document.getElementById("font_family").addEventListener("change", function () {
    document.getElementById("font_family_custom").style.display = this.value === "__other__" ? "inline" : "none";
  });

  document.getElementById("active-race").addEventListener("change", function () {
    var raceId = this.value;
    api("/api/race/select", { method: "POST", body: JSON.stringify({ race_id: raceId }) })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || "Failed"); });
        showMessage("Profile set to " + raceId);
      })
      .catch(function (e) { showMessage(e.message, true); });
  });

  document.getElementById("profile-urls").addEventListener("input", function (e) {
    var id = e.target.getAttribute("data-profile-id");
    var field = e.target.getAttribute("data-field");
    if (!id || !field || !lastConfig || !lastConfig.races || !lastConfig.races.profiles) return;
    var value = e.target.value;
    var profile = Object.assign({}, lastConfig.races.profiles[id] || {}, { [field]: value });
    api("/api/config", {
      method: "POST",
      body: JSON.stringify({ races: { profiles: { [id]: profile } } })
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || "Failed"); });
      lastConfig.races.profiles[id] = profile;
    }).catch(function (err) { showMessage(err.message, true); });
  });

  document.getElementById("save-ticker").addEventListener("click", function () {
    var patch = {
      display: {
        background_color: document.getElementById("background_color").value.trim() || "#000000",
        text_color: document.getElementById("text_color").value.trim() || "#ff9900",
        separator: document.getElementById("separator").value,
        max_runners: Number(document.getElementById("max_runners").value) || 10,
        sort_runners: document.getElementById("sort_runners").value === "csv_order" ? "csv_order" : "runner"
      },
      ticker: {
        speed_px_s: Number(document.getElementById("speed_px_s").value) || 180,
        font_family: (document.getElementById("font_family").value === "__other__"
          ? document.getElementById("font_family_custom").value.trim()
          : document.getElementById("font_family").value) || "monospace",
        font_size_px: Number(document.getElementById("font_size_px").value) || 64,
        y_px: Number(document.getElementById("y_px").value) || 120,
        fps: Number(document.getElementById("fps").value) || 30
      },
      csv: { poll_interval_s: Number(document.getElementById("poll_interval_s").value) || 10 },
      race_time: { insert_every_loops: Number(document.getElementById("insert_every_loops").value) || 3 }
    };
    api("/api/config", { method: "POST", body: JSON.stringify(patch) })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || "Failed"); });
        showMessage("Ticker settings saved");
      })
      .catch(function (e) { showMessage(e.message, true); });
  });

  ["start", "pause", "reset"].forEach(function (action) {
    document.getElementById("clock-" + action).addEventListener("click", function () {
      api("/api/clock/" + action, { method: "POST" })
        .then(function (r) {
          if (!r.ok) throw new Error("Clock " + action + " failed");
          updateClockDisplay();
          showMessage("Clock " + action + "ed");
        })
        .catch(function (e) { showMessage(e.message, true); });
    });
  });

  document.getElementById("freeze").addEventListener("change", function () {
    api("/api/freeze", { method: "POST", body: JSON.stringify({ freeze: this.checked }) })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || "Failed"); });
        showMessage(this.checked ? "Display updates frozen" : "Display updates resumed");
      }.bind(this))
      .catch(function (e) { showMessage(e.message, true); });
  });

  setInterval(updateClockDisplay, 2000);
})();
