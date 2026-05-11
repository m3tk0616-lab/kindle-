"use strict";

// ── State ────────────────────────────────────────────────────────
let currentMode = "android";
let statusPollTimer = null;
let galleryFiles = [];
let viewerIndex = 0;

// ── Helpers ──────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function setStatus(running, pageCount) {
  const badge = $("status-badge");
  badge.textContent = running ? "実行中" : "停止中";
  badge.className = "badge " + (running ? "badge-running" : "badge-idle");
  $("btn-start").disabled = running;
  $("btn-stop").disabled = !running;

  const counter = $("page-counter");
  if (running || pageCount > 0) {
    counter.textContent = `${pageCount ?? 0} ページ取得済み`;
    counter.classList.remove("hidden");
  } else {
    counter.classList.add("hidden");
  }
}

function showError(msg) {
  alert("エラー: " + msg);
}

// ── Tabs ─────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;
    $("panel-android").classList.toggle("hidden", currentMode !== "android");
    $("panel-desktop").classList.toggle("hidden", currentMode !== "desktop");
  });
});

// ── Devices ──────────────────────────────────────────────────────
async function loadDevices() {
  try {
    const data = await api("/api/devices");
    const sel = $("device-select");
    sel.innerHTML = "";
    if (!data.devices.length) {
      sel.innerHTML = '<option value="">デバイスなし（ADB接続を確認）</option>';
      return;
    }
    data.devices.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.serial;
      opt.textContent = `${d.serial}${d.model ? " – " + d.model : ""}`;
      sel.appendChild(opt);
    });
  } catch (e) {
    $("device-select").innerHTML = '<option value="">取得失敗: ' + e.message + '</option>';
  }
}

$("btn-refresh-devices").addEventListener("click", loadDevices);

// ── Screen info ───────────────────────────────────────────────────
$("btn-screen-info").addEventListener("click", async () => {
  const serial = $("device-select").value;
  const box = $("screen-info-box");
  box.classList.remove("hidden");
  box.textContent = "取得中...";
  try {
    const d = await api(`/api/screen-info?device_serial=${encodeURIComponent(serial)}`);
    box.textContent = `ネイティブ解像度: ${d.width} × ${d.height} px（${d.megapixels} MP）— PNG ロスレス保存`;
  } catch (e) {
    box.textContent = "取得失敗: " + e.message;
  }
});

// ── Preview ──────────────────────────────────────────────────────
$("btn-preview").addEventListener("click", async () => {
  const serial = $("device-select").value;
  const img = $("preview-img");
  img.style.display = "block";
  // Append timestamp to bust cache
  img.src = `/api/screenshot/preview?device_serial=${encodeURIComponent(serial)}&t=${Date.now()}`;
});

$("preview-img").addEventListener("click", () => {
  const src = $("preview-img").src;
  if (!src || src.endsWith("/")) return;
  openViewer([{ name: "preview", src }], 0);
});

// ── Start / Stop ─────────────────────────────────────────────────
$("btn-start").addEventListener("click", async () => {
  const body = {
    mode: currentMode,
    interval: parseFloat($("interval").value) || 3,
    total_pages: parseInt($("total-pages").value) || 0,
    save_dir: $("save-dir").value || "screenshots",
    device_serial: currentMode === "android" ? $("device-select").value : "",
  };
  try {
    await api("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setStatus(true, 0);
    startPolling();
  } catch (e) {
    showError(e.message);
  }
});

$("btn-stop").addEventListener("click", async () => {
  try {
    await api("/api/stop", { method: "POST" });
    setStatus(false, null);
    stopPolling();
    await loadGallery();
  } catch (e) {
    showError(e.message);
  }
});

// ── Status polling ────────────────────────────────────────────────
function startPolling() {
  if (statusPollTimer) return;
  statusPollTimer = setInterval(async () => {
    try {
      const data = await api("/api/status");
      setStatus(data.running, data.page_count);
      if (!data.running) {
        stopPolling();
        await loadGallery();
      }
    } catch (_) {}
  }, 2000);
}

function stopPolling() {
  if (statusPollTimer) {
    clearInterval(statusPollTimer);
    statusPollTimer = null;
  }
}

// ── Prompt parser ─────────────────────────────────────────────────
$("btn-parse").addEventListener("click", async () => {
  const text = $("chat-text").value.trim();
  if (!text) { alert("チャット履歴を貼り付けてください"); return; }
  const result = $("parse-result");
  result.textContent = "解析中...";
  result.classList.remove("hidden");
  try {
    const data = await api("/api/parse-prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_text: text, api_key: $("api-key").value }),
    });
    result.textContent = JSON.stringify(data, null, 2);
    // Auto-apply extracted settings
    if (data.mode)        switchTab(data.mode);
    if (data.interval)    $("interval").value = data.interval;
    if (data.total_pages != null) $("total-pages").value = data.total_pages;
    if (data.save_dir)    $("save-dir").value = data.save_dir;
    if (data.device_serial) $("device-select").value = data.device_serial;
  } catch (e) {
    result.textContent = "エラー: " + e.message;
  }
});

function switchTab(mode) {
  document.querySelectorAll(".tab").forEach(b => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
  currentMode = mode;
  $("panel-android").classList.toggle("hidden", mode !== "android");
  $("panel-desktop").classList.toggle("hidden", mode !== "desktop");
}

// ── Gallery ───────────────────────────────────────────────────────
async function loadGallery() {
  const dir = $("save-dir").value || "screenshots";
  try {
    const data = await api(`/api/screenshots?dir=${encodeURIComponent(dir)}`);
    const gallery = $("gallery");
    gallery.innerHTML = "";

    galleryFiles = data.files.map(name => ({
      name,
      src: `/screenshots/${encodeURIComponent(name)}`,
    }));

    $("gallery-count").textContent = galleryFiles.length
      ? `${galleryFiles.length} 枚`
      : "";

    if (!galleryFiles.length) {
      gallery.textContent = "まだ画像がありません";
      return;
    }

    galleryFiles.forEach((file, idx) => {
      const img = document.createElement("img");
      img.src = file.src + `?t=${Date.now()}`;
      img.alt = file.name;
      img.title = file.name;
      img.addEventListener("click", () => openViewer(galleryFiles, idx));
      gallery.appendChild(img);
    });
  } catch (e) {
    $("gallery").textContent = "取得失敗: " + e.message;
  }
}

$("btn-refresh-gallery").addEventListener("click", loadGallery);

// ── Fullscreen viewer ─────────────────────────────────────────────
function openViewer(files, index) {
  viewerIndex = index;
  $("viewer-overlay").classList.remove("hidden");
  showViewerImage(files);
  document.addEventListener("keydown", onViewerKey);
}

function showViewerImage(files) {
  const file = files[viewerIndex];
  $("viewer-img").src = file.src;
  $("viewer-caption").textContent =
    `${file.name}  (${viewerIndex + 1} / ${files.length})`;
}

function closeViewer() {
  $("viewer-overlay").classList.add("hidden");
  document.removeEventListener("keydown", onViewerKey);
}

function onViewerKey(e) {
  if (e.key === "Escape")      closeViewer();
  else if (e.key === "ArrowRight") navigateViewer(1);
  else if (e.key === "ArrowLeft")  navigateViewer(-1);
}

function navigateViewer(delta) {
  const files = galleryFiles.length ? galleryFiles
    : [{ name: "preview", src: $("preview-img").src }];
  viewerIndex = (viewerIndex + delta + files.length) % files.length;
  showViewerImage(files);
}

$("viewer-close").addEventListener("click", closeViewer);
$("viewer-overlay").addEventListener("click", e => {
  if (e.target === $("viewer-overlay")) closeViewer();
});
$("viewer-prev").addEventListener("click", () => navigateViewer(-1));
$("viewer-next").addEventListener("click", () => navigateViewer(1));

// ── Init ──────────────────────────────────────────────────────────
(async () => {
  await loadDevices();
  await loadGallery();
  try {
    const data = await api("/api/status");
    setStatus(data.running, data.page_count);
    if (data.running) startPolling();
  } catch (_) {}
})();
