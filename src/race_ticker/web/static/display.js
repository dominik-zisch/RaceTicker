// Display canvas renderer – scrolling ticker, loop-complete handshake, FPS throttling.

(function () {
  const canvas = document.getElementById("ticker-canvas");
  if (!canvas) return;

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  let lastPayload = null;
  let scrollX = 0;
  let textWidth = 0;
  let lastUpdateTime = 0;
  let lastDrawTime = 0;
  let rafId = null;
  let loopCount = 0;

  function getStyle(ctx, payload) {
    const style = payload.style || {};
    return {
      backgroundColor: style.background_color || "#000000",
      fontFamily: style.font_family || "monospace",
      fontSizePx: style.font_size_px || 64,
      textColor: style.text_color || "#ff9900",
      yPx: style.y_px != null ? style.y_px : 120,
    };
  }

  function measureText(ctx, payload) {
    const style = getStyle(ctx, payload);
    ctx.font = style.fontSizePx + "px " + style.fontFamily;
    return ctx.measureText(payload.ticker_text || "").width;
  }

  function drawFrame(ctx, payload, x) {
    const style = getStyle(ctx, payload);
    ctx.font = style.fontSizePx + "px " + style.fontFamily;
    ctx.fillStyle = style.textColor;
    ctx.textBaseline = "middle";
    ctx.fillText(payload.ticker_text || "", x, style.yPx);
  }

  function stopLoop() {
    if (rafId != null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function loopComplete(payload) {
    stopLoop();
    fetch("/api/loop_complete", { method: "POST" })
      .then(function (res) {
        if (!res.ok) throw new Error("loop_complete failed");
        return res.json();
      })
      .then(function (data) {
        console.log("loop_complete response:", data);
        if (data.swapped) {
          fetchAndStartScroll();
          return;
        }
        loopCount++;
        const everyLoops = payload.show_race_time_every_loops || 3;
        if (loopCount % everyLoops === 0) {
          fetch("/api/clock")
            .then(function (r) { return r.json(); })
            .then(function (clock) {
              const raceTimePayload = Object.assign({}, payload, {
                ticker_text: "RACE TIME: " + (clock.elapsed_display || "0:00")
              });
              scrollX = canvas.width;
              lastUpdateTime = performance.now();
              lastDrawTime = lastUpdateTime;
              runLoop(raceTimePayload);
            })
            .catch(function () {
              scrollX = canvas.width;
              lastUpdateTime = performance.now();
              lastDrawTime = lastUpdateTime;
              runLoop(lastPayload || payload);
            });
        } else {
          scrollX = canvas.width;
          lastUpdateTime = performance.now();
          lastDrawTime = lastUpdateTime;
          runLoop(lastPayload || payload);
        }
      })
      .catch(function (err) {
        console.error(err);
        scrollX = canvas.width;
        lastUpdateTime = performance.now();
        lastDrawTime = lastUpdateTime;
        runLoop(lastPayload || payload);
      });
  }

  function runLoop(payload) {
    const ctx = canvas.getContext("2d");
    if (!ctx || !payload) return;

    textWidth = measureText(ctx, payload);
    const speedPxS = (payload.scroll && payload.scroll.speed_px_s != null)
      ? payload.scroll.speed_px_s
      : 180;
    const targetFps = (payload.scroll && payload.scroll.fps != null)
      ? payload.scroll.fps
      : 30;
    const frameIntervalMs = 1000 / targetFps;

    function tick(now) {
      const deltaS = (now - lastUpdateTime) / 1000;
      lastUpdateTime = now;
      scrollX -= speedPxS * deltaS;

      if (scrollX + textWidth < 0) {
        loopComplete(payload, targetFps);
        return;
      }

      if (now - lastDrawTime >= frameIntervalMs) {
        lastDrawTime = now;
        const style = getStyle(ctx, payload);
        ctx.fillStyle = style.backgroundColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        drawFrame(ctx, payload, scrollX);
      }

      rafId = requestAnimationFrame(tick);
    }

    rafId = requestAnimationFrame(tick);
  }

  function applyNewPayload(payload) {
    lastPayload = payload;
    loopCount = 0;
    stopLoop();
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    textWidth = measureText(ctx, payload);
    scrollX = canvas.width;
    lastUpdateTime = performance.now();
    lastDrawTime = lastUpdateTime;
    runLoop(payload);
  }

  function fetchAndStartScroll() {
    fetch("/api/payload")
      .then(function (res) {
        if (!res.ok) throw new Error("payload fetch failed");
        return res.json();
      })
      .then(function (payload) {
        applyNewPayload(payload);
      })
      .catch(function (err) {
        console.error(err);
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.fillStyle = "#000000";
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = "#ff9900";
          ctx.font = "24px monospace";
          ctx.fillText("Waiting for payload…", 20, 100);
        }
        setTimeout(fetchAndStartScroll, 1000);
      });
  }

  function pollForPayloadUpdate() {
    if (!lastPayload) return;
    fetch("/api/payload")
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (payload) {
        if (payload && payload.version !== lastPayload.version) {
          applyNewPayload(payload);
        }
      })
      .catch(function () {});
  }

  function onResize() {
    resizeCanvas();
    if (lastPayload) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        textWidth = measureText(ctx, lastPayload);
        if (scrollX + textWidth < 0) {
          scrollX = canvas.width;
        }
      }
    }
  }

  resizeCanvas();
  window.addEventListener("resize", onResize);
  fetchAndStartScroll();
  setInterval(pollForPayloadUpdate, 1500);
})();
