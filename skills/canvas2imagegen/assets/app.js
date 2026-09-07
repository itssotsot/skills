"use strict";

(() => {
  const canvas = document.getElementById("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  const byId = (id) => document.getElementById(id);
  const commands = [];
  const undone = [];
  let active = null;
  let tool = "pen";
  let color = "#252933";
  let size = 6;
  let frame = null;
  let handoff = null;
  let revision = 0;
  let sentRevision = -1;
  let sending = false;
  let submission = null;
  let messageTimer;
  let documentSize = { width: canvas.width, height: canvas.height };
  let view = { scale: 1, x: 0, y: 0 };

  function fitDrawing() {
    let left = 0,
      top = 0,
      right = documentSize.width,
      bottom = documentSize.height;
    let first = commands.length - 1;
    while (first >= 0 && commands[first].tool !== "clear") first -= 1;
    for (const command of commands.slice(first + 1)) {
      if (command.image) {
        left = Math.min(left, command.x);
        top = Math.min(top, command.y);
        right = Math.max(right, command.x + command.width);
        bottom = Math.max(bottom, command.y + command.height);
      } else {
        for (const point of command.points) {
          left = Math.min(left, point.x - command.size / 2);
          top = Math.min(top, point.y - command.size / 2);
          right = Math.max(right, point.x + command.size / 2);
          bottom = Math.max(bottom, point.y + command.size / 2);
        }
      }
    }
    const scale = Math.min(
      canvas.width / (right - left),
      canvas.height / (bottom - top),
    );
    view = {
      scale,
      x: (canvas.width - (right - left) * scale) / 2 - left * scale,
      y: (canvas.height - (bottom - top) * scale) / 2 - top * scale,
    };
  }

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const density = 1200 / Math.max(rect.width, rect.height);
    const width = Math.max(1, Math.round(rect.width * density));
    const height = Math.max(1, Math.round(rect.height * density));
    if (width === canvas.width && height === canvas.height) return;
    finishActiveStroke();
    canvas.width = width;
    canvas.height = height;
    if (!commands.length) documentSize = { width, height };
    fitDrawing();
    render();
    revision += 1;
    updateUseButton();
  }

  function updateUseButton() {
    byId("use-sketch").disabled =
      !handoff || !hasDrawing() || sending || revision === sentRevision;
    byId("use-sketch").querySelector("span").textContent = sending
      ? "Sending…"
      : revision === sentRevision
        ? "Sketch sent"
        : "Use sketch";
  }

  function message(text, error = false) {
    clearTimeout(messageTimer);
    byId("status").textContent = text;
    byId("status").classList.toggle("error", error);
    messageTimer = setTimeout(() => {
      byId("status").textContent = "";
    }, 8000);
  }

  function paint(command) {
    if (command.image) {
      context.drawImage(
        command.image,
        command.x,
        command.y,
        command.width,
        command.height,
      );
      return;
    }
    if (command.tool === "clear") {
      context.save();
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.restore();
      return;
    }
    context.strokeStyle = command.tool === "eraser" ? "#ffffff" : command.color;
    context.fillStyle = context.strokeStyle;
    context.lineWidth = command.size;
    context.lineCap = "round";
    context.lineJoin = "round";
    const start = command.points[0];
    const end = command.points[command.points.length - 1];
    context.beginPath();
    if (command.tool === "rect") {
      context.rect(start.x, start.y, end.x - start.x, end.y - start.y);
    } else if (command.tool === "ellipse") {
      context.ellipse(
        (start.x + end.x) / 2,
        (start.y + end.y) / 2,
        Math.abs(end.x - start.x) / 2,
        Math.abs(end.y - start.y) / 2,
        0,
        0,
        Math.PI * 2,
      );
    } else if (command.points.length === 1) {
      context.arc(start.x, start.y, command.size / 2, 0, Math.PI * 2);
      context.fill();
      return;
    } else {
      context.moveTo(start.x, start.y);
      for (const point of command.points.slice(1))
        context.lineTo(point.x, point.y);
    }
    context.stroke();
  }

  function fillRegion(point) {
    const { width, height } = canvas;
    const image = context.getImageData(0, 0, width, height);
    const pixels = image.data;
    const x = Math.max(
      0,
      Math.min(width - 1, Math.floor(point.x * view.scale + view.x)),
    );
    const y = Math.max(
      0,
      Math.min(height - 1, Math.floor(point.y * view.scale + view.y)),
    );
    const seed = y * width + x;
    const target = pixels.slice(seed * 4, seed * 4 + 3);
    const replacement = [1, 3, 5].map((offset) =>
      parseInt(color.slice(offset, offset + 2), 16),
    );
    if (replacement.every((channel, index) => channel === target[index]))
      return null;

    // Scan connected horizontal spans, without recursion or crossing dark outlines.
    const visited = new Uint8Array(width * height);
    const matches = (index) =>
      !visited[index] &&
      Math.abs(pixels[index * 4] - target[0]) <= 24 &&
      Math.abs(pixels[index * 4 + 1] - target[1]) <= 24 &&
      Math.abs(pixels[index * 4 + 2] - target[2]) <= 24;
    const pending = [seed];
    let minX = width,
      maxX = 0,
      minY = height,
      maxY = 0;
    while (pending.length) {
      const index = pending.pop();
      if (!matches(index)) continue;
      const row = Math.floor(index / width);
      let left = index % width;
      while (left > 0 && matches(row * width + left - 1)) left -= 1;
      let above = false,
        below = false;
      for (let column = left; column < width; column += 1) {
        const current = row * width + column;
        if (!matches(current)) break;
        visited[current] = 1;
        pixels.set(replacement, current * 4);
        minX = Math.min(minX, column);
        maxX = Math.max(maxX, column);
        minY = Math.min(minY, row);
        maxY = Math.max(maxY, row);
        const nextAbove = row > 0 && matches(current - width);
        const nextBelow = row < height - 1 && matches(current + width);
        if (nextAbove && !above) pending.push(current - width);
        if (nextBelow && !below) pending.push(current + width);
        above = nextAbove;
        below = nextBelow;
      }
    }

    // Cache the affected rectangle so later pen frames and exports do not flood again.
    const patch = document.createElement("canvas");
    patch.width = maxX - minX + 1;
    patch.height = maxY - minY + 1;
    patch.getContext("2d").putImageData(image, -minX, -minY);
    return {
      tool: "fill",
      image: patch,
      x: (minX - view.x) / view.scale,
      y: (minY - view.y) / view.scale,
      width: patch.width / view.scale,
      height: patch.height / view.scale,
    };
  }

  function hasDrawing() {
    return (
      commands.length > 0 && commands[commands.length - 1].tool !== "clear"
    );
  }

  function render() {
    paint({ tool: "clear" });
    context.setTransform(view.scale, 0, 0, view.scale, view.x, view.y);
    // Nothing before the most recent clear can affect the current paper.
    let start = commands.length - 1;
    while (start >= 0 && commands[start].tool !== "clear") start -= 1;
    for (let i = start + 1; i < commands.length; i += 1) paint(commands[i]);
    if (active) paint(active);
  }

  function scheduleRender() {
    if (frame !== null) return;
    frame = requestAnimationFrame(() => {
      frame = null;
      render();
    });
  }

  function update() {
    revision += 1;
    const drawn = hasDrawing();
    byId("undo").disabled = commands.length === 0;
    byId("redo").disabled = undone.length === 0;
    for (const id of ["clear", "copy", "download"]) byId(id).disabled = !drawn;
    updateUseButton();
    render();
  }

  function selectTool(value) {
    tool = value;
    document.querySelectorAll("[data-tool]").forEach((button) => {
      const selected = button.dataset.tool === tool;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    canvas.style.cursor =
      tool === "eraser" || tool === "fill" ? "cell" : "crosshair";
  }

  function selectColor(value) {
    color = value;
    byId("color").value = color;
    byId("stroke-dot").style.background = color;
    document.querySelectorAll("[data-color]").forEach((button) => {
      const selected = button.dataset.color === color;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    if (tool === "eraser") selectTool("pen");
  }

  function point(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x:
        (Math.max(
          0,
          Math.min(
            canvas.width,
            ((event.clientX - rect.left) * canvas.width) / rect.width,
          ),
        ) -
          view.x) /
        view.scale,
      y:
        (Math.max(
          0,
          Math.min(
            canvas.height,
            ((event.clientY - rect.top) * canvas.height) / rect.height,
          ),
        ) -
          view.y) /
        view.scale,
    };
  }

  function appendPoint(event) {
    const value = point(event);
    const last = active.points[active.points.length - 1];
    if (value.x === last.x && value.y === last.y) return;
    if (active.tool === "pen" || active.tool === "eraser")
      active.points.push(value);
    else active.points[1] = value;
  }

  canvas.addEventListener("pointerdown", (event) => {
    if (active || !event.isPrimary || event.button !== 0) return;
    event.preventDefault();
    if (tool === "fill") {
      render();
      const fill = fillRegion(point(event));
      if (fill) {
        commands.push(fill);
        undone.length = 0;
        update();
      }
      return;
    }
    active = {
      tool,
      color,
      size: size / view.scale,
      points: [point(event)],
      pointerId: event.pointerId,
    };
    canvas.setPointerCapture(event.pointerId);
    render();
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!active || event.pointerId !== active.pointerId) return;
    // Recover if a release happened outside the window and no pointerup arrived.
    if ((event.buttons & 1) === 0) {
      finish(event);
      return;
    }
    const samples = event.getCoalescedEvents?.();
    for (const sample of samples?.length ? samples : [event])
      appendPoint(sample);
    scheduleRender();
  });

  function finish(event, includeEndpoint = false) {
    if (!active || event.pointerId !== active.pointerId) return;
    // Cancellation ends input; it must not erase the user's work. Only pointerup
    // supplies a final drawing coordinate. Capture/focus events may use (0, 0).
    if (includeEndpoint) appendPoint(event);
    delete active.pointerId;
    commands.push(active);
    undone.length = 0;
    active = null;
    if (canvas.hasPointerCapture(event.pointerId))
      canvas.releasePointerCapture(event.pointerId);
    update();
  }

  canvas.addEventListener("pointerup", (event) => finish(event, true));
  canvas.addEventListener("pointercancel", (event) => finish(event));
  canvas.addEventListener("lostpointercapture", (event) => finish(event));
  function finishActiveStroke() {
    if (active) finish({ pointerId: active.pointerId });
  }
  window.addEventListener("blur", finishActiveStroke);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) finishActiveStroke();
  });
  canvas.addEventListener("contextmenu", (event) => event.preventDefault());

  function undo() {
    if (active || !commands.length) return;
    undone.push(commands.pop());
    update();
  }
  function redo() {
    if (active || !undone.length) return;
    commands.push(undone.pop());
    update();
  }

  document
    .querySelectorAll("[data-tool]")
    .forEach((button) =>
      button.addEventListener("click", () => selectTool(button.dataset.tool)),
    );
  document
    .querySelectorAll("[data-color]")
    .forEach((button) =>
      button.addEventListener("click", () => selectColor(button.dataset.color)),
    );
  byId("color").addEventListener("input", (event) =>
    selectColor(event.target.value),
  );
  byId("size").addEventListener("input", (event) => {
    size = Number(event.target.value);
    byId("size-value").value = `${size} px`;
    byId("stroke-dot").style.width = `${size}px`;
    byId("stroke-dot").style.height = `${size}px`;
  });
  byId("undo").addEventListener("click", undo);
  byId("redo").addEventListener("click", redo);
  byId("clear").addEventListener("click", () => {
    if (active) return;
    commands.push({ tool: "clear" });
    undone.length = 0;
    update();
    message("Canvas cleared. Undo to restore.");
  });

  document.addEventListener("keydown", (event) => {
    if (event.target.closest("input, textarea, select, [contenteditable]"))
      return;
    const key = event.key.toLowerCase();
    if (event.metaKey || event.ctrlKey) {
      if (key === "z" || key === "y") {
        event.preventDefault();
        if (key === "y" || event.shiftKey) redo();
        else undo();
      }
      return;
    }
    if (event.altKey) return;
    const shortcuts = {
      b: "pen",
      e: "eraser",
      f: "fill",
      l: "line",
      r: "rect",
      o: "ellipse",
    };
    if (shortcuts[key]) selectTool(shortcuts[key]);
  });

  function pngBlob() {
    // Flush any pending animation frame, then freeze the click-time image.
    render();
    const snapshot = document.createElement("canvas");
    snapshot.width = canvas.width;
    snapshot.height = canvas.height;
    snapshot.getContext("2d").drawImage(canvas, 0, 0);
    return new Promise((resolve, reject) => {
      snapshot.toBlob(
        (blob) =>
          blob ? resolve(blob) : reject(new Error("PNG export failed")),
        "image/png",
      );
    });
  }

  async function connectHandoff() {
    try {
      const response = await fetch("/api/session", { cache: "no-store" });
      if (!response.ok) throw new Error("No local helper");
      const session = await response.json();
      if (!session.enabled || !session.token)
        throw new Error("Handoff disabled");
      handoff = session;
      byId("use-sketch").title =
        "Send this drawing to the active canvas2imagegen session";
      if (session.has_draft) {
        try {
          const draft = await fetch("/api/draft", {
            headers: { "X-Sketch-Token": session.token },
            cache: "no-store",
          });
          if (!draft.ok) throw new Error("Draft unavailable");
          const image = await createImageBitmap(await draft.blob());
          // Never overwrite drawing started while the saved PNG was loading.
          if (!active && !commands.length && !undone.length) {
            documentSize = { width: image.width, height: image.height };
            commands.push({
              tool: "image",
              image,
              x: 0,
              y: 0,
              ...documentSize,
            });
            fitDrawing();
            update();
          } else {
            image.close();
          }
        } catch {
          message(
            "Saved drawing could not be restored. Keep your PNG backup.",
            true,
          );
        }
      }
    } catch {
      byId("use-sketch").title =
        "Open this sketchpad through canvas2imagegen to connect the agent";
    }
    updateUseButton();
  }

  byId("use-sketch").addEventListener("click", async () => {
    if (!handoff || !hasDrawing() || sending || revision === sentRevision)
      return;
    const clickedRevision = revision;
    sending = true;
    updateUseButton();
    try {
      // Retain the click-time image and ID on failure, so a retry cannot submit it twice.
      if (!submission || submission.revision !== clickedRevision) {
        submission = {
          revision: clickedRevision,
          id: crypto.randomUUID(),
          blob: await pngBlob(),
        };
      }
      const pending = submission;
      const response = await fetch("/api/sketch", {
        method: "POST",
        headers: {
          "Content-Type": "image/png",
          "X-Sketch-Token": handoff.token,
          "X-Submission-ID": pending.id,
        },
        body: pending.blob,
        signal: AbortSignal.timeout(15000),
      });
      const receipt = await response.json();
      if (!response.ok || receipt.status !== "submitted") {
        throw new Error(receipt.error || "The sketch could not be sent.");
      }
      sentRevision = clickedRevision;
      message(
        receipt.agent_waiting
          ? "Sketch sent. Continue in chat."
          : "Sketch saved. Resume the agent in chat.",
      );
    } catch (error) {
      message("Sketch not confirmed. Retry or use Copy image.", true);
    } finally {
      sending = false;
      updateUseButton();
    }
  });

  byId("copy").addEventListener("click", async () => {
    if (
      !window.isSecureContext ||
      !navigator.clipboard?.write ||
      !window.ClipboardItem
    ) {
      message("Copy unavailable. Download PNG to attach it.", true);
      return;
    }
    try {
      // Call write inside the click; awaiting toBlob first loses Safari's user activation.
      const blob = pngBlob();
      blob.catch(() => {}); // A synchronous permission failure must not leave an unhandled rejection.
      await navigator.clipboard.write([
        new ClipboardItem({ "image/png": blob }),
      ]);
      message("Image copied! Paste in chat.");
    } catch {
      message("Copy was blocked. Download PNG instead.", true);
    }
  });

  byId("download").addEventListener("click", async () => {
    try {
      const blob = await pngBlob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `canvas2imagegen-${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      message("PNG downloaded.");
    } catch {
      message("The PNG couldn't be exported. Please try again.", true);
    }
  });

  resizeCanvas();
  new ResizeObserver(resizeCanvas).observe(canvas.parentElement);
  update();
  connectHandoff();
})();
