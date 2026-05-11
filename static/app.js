"use strict";

// ── State ────────────────────────────────────────────────────────
let currentMode = "android";
let jobsState = {};          // id → job object
let activeDetailJobId = null;
let galleryFiles = [];
let viewerIndex = 0;

// ── Helpers ──────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const qs = sel => document.querySelector(sel);

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function statusBadge(status) {
  return `<span class="status-badge badge-${status}">${
    { running: "実行中", completed: "完了", failed: "失敗", stopped: "停止", pending: "待機中" }[status] ?? status
  }</span>`;
}

function dotColor(status) {
  return { running: "dot-running", completed: "dot-completed", failed: "dot-failed", stopped: "dot-stopped", pending: "dot-pending" }[status] ?? "";
}

// ── View navigation ───────────────────────────────────────────────
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
    btn.classList.add("active");
    $(`view-${btn.dataset.view}`).classList.remove("hidden");
    if (btn.dataset.view === "jobs") renderJobList();
  });
});

// ── Mode tabs ─────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;
    $("panel-android").classList.toggle("hidden", currentMode !== "android");
    $("panel-desktop").classList.toggle("hidden", currentMode !== "desktop");
  });
});

function switchTab(mode) {
  document.querySelectorAll(".tab").forEach(b =>
    b.classList.toggle("active", b.dataset.mode === mode));
  currentMode = mode;
  $("panel-android").classList.toggle("hidden", mode !== "android");
  $("panel-desktop").classList.toggle("hidden", mode !== "desktop");
}

// ── Devices ───────────────────────────────────────────────────────
async function loadDevices() {
  try {
    const { devices } = await api("/api/devices");
    const sel = $("device-select");
    sel.innerHTML = devices.length
      ? devices.map(d => `<option value="${d.serial}">${d.serial}${d.model ? " – " + d.model : ""}</option>`).join("")
      : '<option value="">デバイスなし（USB接続・デバッグ有効にしてください）</option>';
  } catch (e) {
    $("device-select").innerHTML = `<option value="">取得失敗: ${e.message}</option>`;
  }
}

$("btn-refresh-devices").addEventListener("click", loadDevices);

$("btn-screen-info").addEventListener("click", async () => {
  const box = $("screen-info-box");
  box.classList.remove("hidden");
  box.textContent = "取得中...";
  try {
    const d = await api(`/api/screen-info?device_serial=${encodeURIComponent($("device-select").value)}`);
    box.textContent = `ネイティブ解像度: ${d.width} × ${d.height} px（${d.megapixels} MP） — PNG ロスレス保存`;
  } catch (e) { box.textContent = "取得失敗: " + e.message; }
});

// ── Preview ───────────────────────────────────────────────────────
$("btn-preview").addEventListener("click", async () => {
  const img = $("preview-img");
  img.style.display = "block";
  img.src = `/api/screenshot/preview?device_serial=${encodeURIComponent($("device-select").value)}&t=${Date.now()}`;
});

$("preview-img").addEventListener("click", () => {
  const src = $("preview-img").src;
  if (!src || src.endsWith("/")) return;
  galleryFiles = [{ name: "preview", src }];
  openViewer(0);
});

// ── Create Job ────────────────────────────────────────────────────
$("btn-start-job").addEventListener("click", async () => {
  const apiKey = $("api-key").value || localStorage.getItem("api_key") || "";
  const body = {
    name: $("job-name").value || "無題の本",
    mode: currentMode,
    device_serial: currentMode === "android" ? $("device-select").value : "",
    total_pages: parseInt($("total-pages").value) || 0,
    auto_pdf: $("auto-pdf").checked,
    auto_ocr: $("auto-ocr").checked,
    api_key: apiKey,
  };
  try {
    $("btn-start-job").disabled = true;
    const job = await api("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    jobsState[job.id] = job;
    renderSidebarJobList();
    openJobDetail(job.id);
    // Switch to jobs view
    document.querySelector('[data-view="jobs"]').click();
  } catch (e) {
    alert("エラー: " + e.message);
  } finally {
    $("btn-start-job").disabled = false;
  }
});

// ── Job list view ─────────────────────────────────────────────────
function renderJobList() {
  const c = $("job-list-container");
  const jobs = Object.values(jobsState).sort((a, b) => b.created_at - a.created_at);
  if (!jobs.length) {
    c.innerHTML = '<p class="info" style="text-align:center;padding:40px">まだジョブがありません。「新しいジョブ」から開始してください。</p>';
    return;
  }
  c.innerHTML = jobs.map(job => {
    const pct = job.total_pages > 0 ? Math.min(100, Math.round(job.page_count / job.total_pages * 100)) : 0;
    const pbar = job.total_pages > 0
      ? `<div class="progress-bar-wrap"><div class="progress-bar" style="width:${pct}%"></div></div>`
      : "";
    const label = job.total_pages > 0
      ? `${job.page_count}/${job.total_pages}`
      : `${job.page_count} ページ`;
    return `<div class="job-card" data-id="${job.id}">
      <div class="job-dot ${dotColor(job.status)}"></div>
      <div class="job-card-body">
        <div class="job-card-name">${escHtml(job.name)}</div>
        <div class="job-card-meta">${job.mode === "android" ? "Android" : "Desktop"} · ${new Date(job.created_at * 1000).toLocaleString("ja-JP")}</div>
      </div>
      <div class="job-progress">
        ${pbar}
        <span class="progress-label">${label}</span>
        ${statusBadge(job.status)}
      </div>
    </div>`;
  }).join("");

  c.querySelectorAll(".job-card").forEach(card => {
    card.addEventListener("click", () => openJobDetail(card.dataset.id));
  });
}

// ── Sidebar job list ──────────────────────────────────────────────
function renderSidebarJobList() {
  const c = $("sidebar-job-list");
  const jobs = Object.values(jobsState).sort((a, b) => b.created_at - a.created_at).slice(0, 10);
  c.innerHTML = jobs.map(job => `
    <div class="sidebar-job-item" data-id="${job.id}">
      <div class="dot ${dotColor(job.status)}"></div>
      <span>${escHtml(job.name)}</span>
    </div>
  `).join("");
  c.querySelectorAll(".sidebar-job-item").forEach(el => {
    el.addEventListener("click", () => openJobDetail(el.dataset.id));
  });
}

// ── Job Detail ────────────────────────────────────────────────────
function openJobDetail(jobId) {
  activeDetailJobId = jobId;
  const job = jobsState[jobId];
  if (!job) return;
  $("job-detail").classList.remove("hidden");
  refreshJobDetail(job);
  loadDetailGallery(jobId);
}

$("detail-close").addEventListener("click", () => {
  $("job-detail").classList.add("hidden");
  activeDetailJobId = null;
});

function refreshJobDetail(job) {
  if (!job) return;
  $("detail-title").textContent = job.name;
  $("detail-status-row").innerHTML = `
    ${statusBadge(job.status)}
    <span style="margin-left:8px;font-size:0.85rem;color:#555">
      ${job.page_count}${job.total_pages > 0 ? " / " + job.total_pages : ""} ページ
    </span>
  `;
  $("detail-log").textContent = (job.logs || []).join("\n") || "—";
  $("detail-log").scrollTop = $("detail-log").scrollHeight;

  $("detail-stop").classList.toggle("hidden",    job.status !== "running");
  $("detail-pdf").classList.toggle("hidden",     job.status !== "completed" || !!job.pdf_path);
  $("detail-download").classList.toggle("hidden", !job.pdf_path);
  $("detail-ocr").classList.toggle("hidden",     job.status !== "completed");
}

$("detail-stop").addEventListener("click", async () => {
  if (!activeDetailJobId) return;
  await api(`/api/jobs/${activeDetailJobId}/stop`, { method: "POST" }).catch(console.error);
});

$("detail-pdf").addEventListener("click", async () => {
  if (!activeDetailJobId) return;
  $("detail-pdf").disabled = true;
  try {
    await api(`/api/jobs/${activeDetailJobId}/pdf`, { method: "POST" });
  } catch (e) { alert("PDF生成失敗: " + e.message); }
  $("detail-pdf").disabled = false;
});

$("detail-download").addEventListener("click", () => {
  if (!activeDetailJobId) return;
  window.open(`/api/jobs/${activeDetailJobId}/download`);
});

$("detail-ocr").addEventListener("click", async () => {
  if (!activeDetailJobId) return;
  const apiKey = localStorage.getItem("api_key") || "";
  $("detail-ocr").disabled = true;
  try {
    await api(`/api/jobs/${activeDetailJobId}/ocr`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: activeDetailJobId, api_key: apiKey }),
    });
  } catch (e) { alert("OCR失敗: " + e.message); }
  $("detail-ocr").disabled = false;
});

// ── Gallery (detail panel) ────────────────────────────────────────
async function loadDetailGallery(jobId) {
  try {
    const data = await api(`/api/jobs/${jobId}/screenshots`);
    const gallery = $("detail-gallery");
    gallery.innerHTML = "";
    galleryFiles = data.files.map(name => ({
      name,
      src: `/jobs/${encodeURIComponent(data.dir.split("/").pop())}/${encodeURIComponent(name)}`,
    }));
    galleryFiles.forEach((file, idx) => {
      const img = document.createElement("img");
      img.src = file.src + `?t=${Date.now()}`;
      img.alt = file.name;
      img.title = file.name;
      img.addEventListener("click", () => openViewer(idx));
      gallery.appendChild(img);
    });
  } catch (e) { /* gallery unavailable */ }
}

$("detail-refresh-gallery").addEventListener("click", () => {
  if (activeDetailJobId) loadDetailGallery(activeDetailJobId);
});

// ── SSE live updates ──────────────────────────────────────────────
function connectSSE() {
  const es = new EventSource("/api/events");
  es.onmessage = e => {
    try {
      const job = JSON.parse(e.data);
      jobsState[job.id] = job;
      renderSidebarJobList();
      if ($("view-jobs") && !$("view-jobs").classList.contains("hidden")) renderJobList();
      if (activeDetailJobId === job.id) refreshJobDetail(job);
    } catch (_) {}
  };
  es.onerror = () => setTimeout(connectSSE, 3000);
}

// ── Chat prompt parser ────────────────────────────────────────────
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
    if (data.mode)        switchTab(data.mode);
    if (data.interval != null) {} // interval handled in job runner
    if (data.total_pages != null) $("total-pages").value = data.total_pages;
    if (data.device_serial) $("device-select").value = data.device_serial;
  } catch (e) {
    result.textContent = "エラー: " + e.message;
  }
});

// ── Settings ──────────────────────────────────────────────────────
$("btn-save-settings").addEventListener("click", () => {
  const key = $("global-api-key").value.trim();
  if (key) localStorage.setItem("api_key", key);
  alert("保存しました");
});

window.addEventListener("load", () => {
  const saved = localStorage.getItem("api_key");
  if (saved) $("global-api-key").value = saved;
});

// ── Fullscreen viewer ─────────────────────────────────────────────
function openViewer(index) {
  viewerIndex = index;
  $("viewer-overlay").classList.remove("hidden");
  updateViewer();
  document.addEventListener("keydown", onViewerKey);
}

function updateViewer() {
  const file = galleryFiles[viewerIndex];
  if (!file) return;
  $("viewer-img").src = file.src;
  $("viewer-caption").textContent = `${file.name}  (${viewerIndex + 1} / ${galleryFiles.length})`;
}

function closeViewer() {
  $("viewer-overlay").classList.add("hidden");
  document.removeEventListener("keydown", onViewerKey);
}

function onViewerKey(e) {
  if (e.key === "Escape") closeViewer();
  else if (e.key === "ArrowRight") { viewerIndex = (viewerIndex + 1) % galleryFiles.length; updateViewer(); }
  else if (e.key === "ArrowLeft")  { viewerIndex = (viewerIndex - 1 + galleryFiles.length) % galleryFiles.length; updateViewer(); }
}

$("viewer-close").addEventListener("click", closeViewer);
$("viewer-overlay").addEventListener("click", e => { if (e.target === $("viewer-overlay")) closeViewer(); });
$("viewer-prev").addEventListener("click", () => { viewerIndex = (viewerIndex - 1 + galleryFiles.length) % galleryFiles.length; updateViewer(); });
$("viewer-next").addEventListener("click", () => { viewerIndex = (viewerIndex + 1) % galleryFiles.length; updateViewer(); });

// ── Utilities ─────────────────────────────────────────────────────
function escHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── Init ──────────────────────────────────────────────────────────
(async () => {
  await loadDevices();
  // Load existing jobs
  try {
    const { jobs: list } = await api("/api/jobs");
    list.forEach(j => { jobsState[j.id] = j; });
    renderSidebarJobList();
  } catch (_) {}
  connectSSE();
})();
