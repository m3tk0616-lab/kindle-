"use strict";

// ── State ────────────────────────────────────────────────────────
let currentMode = "android";
let statusPollTimer = null;

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

function setStatus(running) {
  const badge = $("status-badge");
  badge.textContent = running ? "実行中" : "停止中";
  badge.className = "badge " + (running ? "badge-running" : "badge-idle");
  $("btn-start").disabled = running;
  $("btn-stop").disabled = !running;
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

// ── Preview ──────────────────────────────────────────────────────
$("btn-preview").addEventListener("click", async () => {
  const serial = $("device-select").value;
  const img = $("preview-img");
  img.style.display = "block";
  img.src = `/api/screenshot/preview?device_serial=${encodeURIComponent(serial)}&t=${Date.now()}`;
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
    setStatus(true);
    startPolling();
  } catch (e) {
    showError(e.message);
  }
});

$("btn-stop").addEventListener("click", async () => {
  try {
    await api("/api/stop", { method: "POST" });
    setStatus(false);
    stopPolling();
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
      setStatus(data.running);
      if (!data.running) stopPolling();
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
    if (data.mode)        { switchTab(data.mode); }
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
    if (!data.files.length) {
      gallery.textContent = "まだ画像がありません";
      return;
    }
    data.files.forEach(name => {
      const img = document.createElement("img");
      img.src = `/screenshots/${encodeURIComponent(name)}?t=${Date.now()}`;
      img.alt = name;
      img.title = name;
      img.addEventListener("click", () => window.open(img.src));
      gallery.appendChild(img);
    });
  } catch (e) {
    $("gallery").textContent = "取得失敗: " + e.message;
  }
}

$("btn-refresh-gallery").addEventListener("click", loadGallery);

// ── Init ──────────────────────────────────────────────────────────
(async () => {
  await loadDevices();
  await loadGallery();
  try {
    const data = await api("/api/status");
    setStatus(data.running);
    if (data.running) startPolling();
  } catch (_) {}
})();
