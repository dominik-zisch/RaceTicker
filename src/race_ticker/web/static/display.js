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

  function getStyle(ctx, payload) {
    const style = payload.style || {};
    var yRaw = style.y_px;
    var yPx = (typeof yRaw === "number" && !Number.isNaN(yRaw)) ? yRaw : Number(yRaw);
    if (!Number.isFinite(yPx) || yPx < 0) yPx = 0;
    return {
      backgroundColor: style.background_color || "#000000",
      fontFamily: style.font_family || "monospace",
      fontSizePx: style.font_size_px || 64,
      textColor: style.text_color || "#ff9900",
      yPx: yPx,
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
    ctx.textBaseline = "top";
    ctx.fillText(payload.ticker_text || "", x, style.yPx);
  }

  function stopLoop() {
    if (rafId != null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
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

      // Loop the same content so the screen is never blank (next segment right behind last).
      if (scrollX + textWidth < 0) {
        scrollX += textWidth;
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
    stopLoop();
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const isFirstLoad = lastPayload === null;
    lastPayload = payload;
    textWidth = measureText(ctx, payload);
    // Only start from the right on first load; otherwise keep scroll position so next segment follows (no blank).
    if (isFirstLoad) {
      scrollX = canvas.width;
    }
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
