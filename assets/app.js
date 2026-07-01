/* =============================================================================
   Module Hub — app logic
   Routing · directory · module pages · live health · QR labels · QR scanning
   ========================================================================== */

/* ------------------------------- Icons ---------------------------------- */
const SVG = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>',
  scan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="3" y1="12" x2="21" y2="12"/></svg>',
  pdf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
  guide: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6a1 1 0 0 1 1 1v1h1a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1V3a1 1 0 0 1 1-1z"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/></svg>',
  vid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  module: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
};

const STATUS = {
  operational: ["ok", "Operational"],
  attention: ["attention", "Needs attention"],
  down: ["down", "Stopped"],
};

let activeTab = "manuals";
let healthTimer = null;

/* ------------------------------ Routing --------------------------------- */
function render() {
  if (healthTimer) { clearInterval(healthTimer); healthTimer = null; }
  const hash = location.hash || "#/";
  let m;
  if ((m = hash.match(/^#\/module\/([^/]+)\/guide\/(.+)$/))) {
    renderReader(decodeURIComponent(m[1]), decodeURIComponent(m[2]));
  } else if ((m = hash.match(/^#\/module\/(.+)$/))) {
    renderModule(decodeURIComponent(m[1]));
  } else {
    renderHome();
  }
  window.scrollTo(0, 0);
}

function currentId() {
  const m = (location.hash || "").match(/#\/module\/([^/]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

/* ------------------------------- Home ----------------------------------- */
function renderHome() {
  const v = document.getElementById("view");
  const groups = {};
  for (const [id, mod] of Object.entries(MODULES)) {
    (groups[mod.system] = groups[mod.system] || []).push([id, mod]);
  }
  let html = `
    <div class="hero">
      <h1>Scan a module</h1>
      <p>Point the scanner at the QR label on any module to open its manuals, videos and live health. Or browse below.</p>
    </div>
    <label class="search">${SVG.search}
      <input id="q" type="search" placeholder="Search modules, ID or location"
        oninput="filterHome(this.value)" autocomplete="off">
    </label>
    <div id="dir"></div>`;
  v.innerHTML = html;
  drawDir("");
}

function drawDir(query) {
  const q = (query || "").trim().toLowerCase();
  const dir = document.getElementById("dir");
  const groups = {};
  for (const [id, mod] of Object.entries(MODULES)) {
    const hay = (id + " " + mod.name + " " + mod.location + " " + mod.system).toLowerCase();
    if (q && !hay.includes(q)) continue;
    (groups[mod.system] = groups[mod.system] || []).push([id, mod]);
  }
  const systems = Object.keys(groups);
  if (!systems.length) { dir.innerHTML = `<div class="empty">No modules match “${escapeHtml(query)}”.</div>`; return; }

  let html = "";
  for (const sys of systems) {
    html += `<div class="group-label">${sys}</div><div class="list">`;
    for (const [id, mod] of groups[sys]) {
      const [sCls] = STATUS[mod.status] || ["ok"];
      const badgeCls = sys === "SPOX" ? "badge spox" : "badge";
      html += `
        <a class="row" href="#/module/${encodeURIComponent(id)}">
          <div class="${badgeCls}">${SVG.module}</div>
          <div class="info">
            <div class="n">${escapeHtml(mod.name)}</div>
            <div class="c">${escapeHtml(id)} · ${escapeHtml(mod.location)}</div>
          </div>
          <div class="right">
            <span class="status-dot ${sCls}" title="${STATUS[mod.status][1]}"></span>
            <span class="chev">›</span>
          </div>
        </a>`;
    }
    html += `</div>`;
  }
  dir.innerHTML = html;
}
function filterHome(val) { drawDir(val); }

/* ------------------------------ Module ---------------------------------- */
function renderModule(id) {
  const v = document.getElementById("view");
  const mod = MODULES[id];
  if (!mod) {
    v.innerHTML = `
      <button class="back" onclick="location.hash='#/'">${SVG.back} Modules</button>
      <div class="mod-head">
        <div class="mod-name">Module not found</div>
        <div class="mod-loc">Code “${escapeHtml(id)}” isn't in the system yet. Check the label or contact your supervisor.</div>
      </div>`;
    return;
  }
  const [sCls, sLabel] = STATUS[mod.status] || ["ok", "Unknown"];
  v.innerHTML = `
    <button class="back" onclick="location.hash='#/'">${SVG.back} Modules</button>
    <div class="mod-head">
      <span class="mod-tag"><span class="id">${escapeHtml(id)}</span> · ${escapeHtml(mod.system)}</span>
      <div class="mod-name">${escapeHtml(mod.name)}</div>
      <div class="mod-loc">${escapeHtml(mod.location)}</div>
      <div class="mod-summary">${escapeHtml(mod.summary)}</div>
      <div class="pills">
        <span class="pill ${sCls}"><span class="dot"></span>${sLabel}</span>
        <span class="pill">${mod.resources.length} documents</span>
        <span class="pill">${mod.videos.length} videos</span>
        <span class="pill" onclick="showQR('${encodeURIComponent(id)}')" style="cursor:pointer">QR label</span>
      </div>
    </div>
    <div class="segment">
      <button class="${activeTab === "manuals" ? "active" : ""}" onclick="setTab('manuals')">Manuals</button>
      <button class="${activeTab === "videos" ? "active" : ""}" onclick="setTab('videos')">Videos</button>
      <button class="${activeTab === "health" ? "active" : ""}" onclick="setTab('health')">Health</button>
    </div>
    <div id="tabbody"></div>`;
  renderTab(id);
}

function setTab(t) { activeTab = t; renderModule(currentId()); }

function renderTab(id) {
  const mod = MODULES[id];
  const b = document.getElementById("tabbody");
  if (healthTimer) { clearInterval(healthTimer); healthTimer = null; }

  if (activeTab === "manuals") {
    b.innerHTML = mod.resources.map((r) => {
      const icon = SVG[r.type] || SVG.pdf;
      const href = r.type === "guide"
        ? `#/module/${encodeURIComponent(id)}/guide/${encodeURIComponent(r.key)}`
        : (r.url || "#");
      return `<a class="res" href="${href}">
        <div class="ic ${r.type}">${icon}</div>
        <div class="meta"><div class="h">${escapeHtml(r.title)}</div><div class="s">${escapeHtml(r.sub)}</div></div>
        <div class="chev">›</div></a>`;
    }).join("") || `<div class="empty">No manuals linked yet.</div>`;

  } else if (activeTab === "videos") {
    b.innerHTML = mod.videos.map((vd) => `
      <div class="video">
        <div class="frame"><iframe src="https://www.youtube-nocookie.com/embed/${vd.id}" title="${escapeHtml(vd.title)}" allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>
        <div class="cap"><div class="h">${escapeHtml(vd.title)}</div><div class="s">${escapeHtml(vd.sub || "Training video")}</div></div>
      </div>`).join("") || `<div class="empty">No videos linked yet.</div>`;

  } else {
    renderHealth(id);
  }
}

/* --------------------------- Health (simulated) ------------------------- */
function renderHealth(id) {
  const mod = MODULES[id];
  const h = mod.health;
  const b = document.getElementById("tabbody");
  const faults = faultsFor(mod);

  b.innerHTML = `
    <div class="health-banner">
      <span class="live"><span class="blip"></span>LIVE</span>
      <span>Simulated demo data — replace with the site control system (PLC / SCADA) feed.</span>
    </div>
    <div class="metrics">
      <div class="metric">
        <div class="label">Throughput</div>
        <div class="value"><span id="m-tp">–</span><span class="unit">items/h</span></div>
        <canvas id="spark" width="300" height="36"></canvas>
      </div>
      <div class="metric">
        <div class="label">Uptime (24 h)</div>
        <div class="value"><span id="m-up">–</span><span class="unit">%</span></div>
        <div class="bar"><span id="m-up-bar" style="width:0%"></span></div>
      </div>
      <div class="metric">
        <div class="label">Drive temperature</div>
        <div class="value"><span id="m-temp">–</span><span class="unit">°C</span></div>
        <div class="bar"><span id="m-temp-bar" style="width:0%"></span></div>
      </div>
      <div class="metric">
        <div class="label">Vibration</div>
        <div class="value"><span id="m-vib">–</span><span class="unit">mm/s</span></div>
        <div class="bar"><span id="m-vib-bar" style="width:0%"></span></div>
      </div>
      ${h.pneumatic ? `
      <div class="metric wide">
        <div class="label">Air pressure (pneumatic diverts)</div>
        <div class="value"><span id="m-pr">–</span><span class="unit">bar</span></div>
        <div class="bar"><span id="m-pr-bar" style="width:0%"></span></div>
      </div>` : ``}
    </div>
    <div class="faults">
      <div class="head">Recent events</div>
      ${faults.length ? faults.map((f) => `
        <div class="fault">
          <span class="sev ${f.sev}"></span>
          <div class="ft"><div class="t">${escapeHtml(f.title)}</div><div class="m">${escapeHtml(f.msg)}</div></div>
          <div class="when">${escapeHtml(f.when)}</div>
        </div>`).join("") : `<div class="clear">No active faults — running normally.</div>`}
    </div>`;

  // live simulation
  const spark = document.getElementById("spark");
  const hist = [];
  const state = {
    tp: h.throughput, temp: h.temp, vib: h.vibration,
    up: h.baseUptime, pr: h.pressure,
  };
  function step() {
    state.tp = clamp(state.tp + rand(-180, 180), h.tpMax * 0.78, h.tpMax);
    state.temp = clamp(state.temp + rand(-0.8, 0.8), h.temp - 4, h.tempMax - 2);
    state.vib = clamp(state.vib + rand(-0.4, 0.4), 0.6, 8);
    state.up = clamp(state.up + rand(-0.05, 0.04), 92, 100);
    if (h.pneumatic) state.pr = clamp(state.pr + rand(-0.08, 0.08), 5.5, 7);

    setText("m-tp", Math.round(state.tp).toLocaleString());
    setText("m-up", state.up.toFixed(1));
    setText("m-temp", state.temp.toFixed(0));
    setText("m-vib", state.vib.toFixed(1));
    setBar("m-up-bar", state.up, 100, "var(--ok)");
    setBar("m-temp-bar", state.temp, h.tempMax, tempColor(state.temp, h.tempMax));
    setBar("m-vib-bar", state.vib, 8, state.vib > 5 ? "var(--warn)" : "var(--accent)");
    if (h.pneumatic) { setText("m-pr", state.pr.toFixed(1)); setBar("m-pr-bar", state.pr - 5, 2, "var(--accent)"); }

    hist.push(state.tp); if (hist.length > 48) hist.shift();
    drawSpark(spark, hist, h.tpMax);
  }
  step();
  healthTimer = setInterval(step, 1500);
}

function faultsFor(mod) {
  const h = mod.health;
  if (mod.status === "attention") {
    const out = [];
    if (h.vibration > 4.5) out.push({ sev: "warn", title: "Vibration above threshold",
      msg: "Inspect shoes/slats and chain tension at next stop.", when: "12m ago" });
    out.push({ sev: "info", title: "Service due soon",
      msg: "Planned maintenance window in 4 days.", when: "2h ago" });
    out.push({ sev: "info", title: "Throughput below target",
      msg: "Running ~12% under nominal during peak.", when: "Today" });
    return out;
  }
  return [];
}

/* ------------------------------ Reader ---------------------------------- */
function renderReader(id, key) {
  const v = document.getElementById("view");
  const g = GUIDES[key];
  if (!g) { location.hash = `#/module/${encodeURIComponent(id)}`; return; }
  const body = g.body.map((node) => {
    if (node[0] === "h") return `<h3>${escapeHtml(node[1])}</h3>`;
    if (node[0] === "p") return `<p>${escapeHtml(node[1])}</p>`;
    if (node[0] === "ul") return `<ul>${node[1].map((li) => `<li>${escapeHtml(li)}</li>`).join("")}</ul>`;
    return "";
  }).join("");
  v.innerHTML = `
    <button class="back" onclick="history.back()">${SVG.back} ${escapeHtml(MODULES[id] ? MODULES[id].name : "Module")}</button>
    <div class="reader">
      ${g.note ? `<div class="reader-note">${SVG.info}<span>${escapeHtml(g.note)}</span></div>` : ""}
      <h2>${escapeHtml(g.title)}</h2>
      <div class="card">${body}</div>
    </div>`;
}

/* -------------------------- QR label (generate) ------------------------- */
function appBaseURL() { return location.href.split("#")[0]; }

function showQR(idEnc) {
  const id = decodeURIComponent(idEnc);
  const mod = MODULES[id];
  const url = appBaseURL() + "#/module/" + encodeURIComponent(id);
  document.getElementById("qr-name").textContent = mod ? mod.name : id;
  document.getElementById("qr-id").textContent = id;
  document.getElementById("qr-url").textContent = url;
  const box = document.getElementById("qrbox");
  box.innerHTML = "";
  const qr = qrcode(0, "M");
  qr.addData(url);
  qr.make();
  box.innerHTML = qr.createImgTag(6, 8);
  document.getElementById("qr-modal").dataset.url = url;
  document.getElementById("qr-modal").classList.add("show");
}
function closeQR() { document.getElementById("qr-modal").classList.remove("show"); }

function printQR() {
  const name = document.getElementById("qr-name").textContent;
  const id = document.getElementById("qr-id").textContent;
  const url = document.getElementById("qr-modal").dataset.url;
  const qr = qrcode(0, "M"); qr.addData(url); qr.make();
  const data = qr.createDataURL(8, 12);
  const w = window.open("", "_blank");
  w.document.write(`<html><head><title>${id} — label</title>
    <style>body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;text-align:center;padding:48px}
    img{width:320px;height:320px}h2{margin:18px 0 2px;font-size:22px}
    .c{font-family:ui-monospace,monospace;color:#2f6df6;font-size:18px}
    .s{color:#6b7280;margin-top:6px;font-size:13px}</style></head>
    <body><img src="${data}"><h2>${escapeHtml(name)}</h2><div class="c">${escapeHtml(id)}</div>
    <div class="s">Scan with the Module Hub app</div></body></html>`);
  w.document.close(); w.focus(); setTimeout(() => w.print(), 350);
}

/* --------------------------- QR scanning -------------------------------- */
let scanStream = null;
let scanRAF = null;
let barcodeDetector = null;
const scanCanvas = document.createElement("canvas");
const scanCtx = scanCanvas.getContext("2d", { willReadFrequently: true });

async function openScanner() {
  const el = document.getElementById("scanner");
  el.classList.add("show");
  document.getElementById("scan-err").classList.remove("show");
  const video = document.getElementById("scan-video");

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return scanError("Camera not available",
      "Your browser blocked camera access. Open the app over HTTPS (e.g. the hosted site), not as a local file.");
  }
  try {
    scanStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } }, audio: false,
    });
  } catch (e) {
    const msg = e && e.name === "NotAllowedError"
      ? "Camera permission was denied. Allow camera access in your browser settings and try again."
      : "Couldn't start the camera. Make sure no other app is using it, then try again.";
    return scanError("Can't access camera", msg);
  }
  video.srcObject = scanStream;
  await video.play().catch(() => {});

  if ("BarcodeDetector" in window) {
    try {
      const fmts = await window.BarcodeDetector.getSupportedFormats();
      if (fmts.includes("qr_code")) barcodeDetector = new window.BarcodeDetector({ formats: ["qr_code"] });
    } catch (e) { barcodeDetector = null; }
  }
  scanLoop();
}

async function scanLoop() {
  const video = document.getElementById("scan-video");
  if (!scanStream) return;
  if (video.readyState >= 2 && video.videoWidth) {
    let value = null;
    if (barcodeDetector) {
      try {
        const codes = await barcodeDetector.detect(video);
        if (codes && codes.length) value = codes[0].rawValue;
      } catch (e) { /* fall through to jsQR */ }
    }
    if (!value) {
      scanCanvas.width = video.videoWidth;
      scanCanvas.height = video.videoHeight;
      scanCtx.drawImage(video, 0, 0, scanCanvas.width, scanCanvas.height);
      const img = scanCtx.getImageData(0, 0, scanCanvas.width, scanCanvas.height);
      const code = jsQR(img.data, img.width, img.height, { inversionAttempts: "dontInvert" });
      if (code) value = code.data;
    }
    if (value) { onScan(value); return; }
  }
  scanRAF = requestAnimationFrame(scanLoop);
}

function onScan(value) {
  const id = parseModuleId(value);
  if (id && MODULES[id]) {
    if (navigator.vibrate) navigator.vibrate(60);
    closeScanner();
    activeTab = "manuals";
    location.hash = "#/module/" + encodeURIComponent(id);
  } else {
    // keep scanning, but show a brief hint
    const hint = document.getElementById("scan-hint");
    hint.textContent = "Unrecognised code — looking for a module label…";
    scanRAF = requestAnimationFrame(scanLoop);
  }
}

function parseModuleId(value) {
  if (!value) return null;
  let v = String(value).trim();
  const m = v.match(/#\/module\/([^/?&#]+)/);
  if (m) return decodeURIComponent(m[1]);
  // bare id on the label, or "ID" anywhere
  if (MODULES[v]) return v;
  const known = Object.keys(MODULES).find((k) => v.toUpperCase().includes(k));
  return known || null;
}

function closeScanner() {
  const el = document.getElementById("scanner");
  el.classList.remove("show");
  if (scanRAF) { cancelAnimationFrame(scanRAF); scanRAF = null; }
  if (scanStream) { scanStream.getTracks().forEach((t) => t.stop()); scanStream = null; }
  const v = document.getElementById("scan-video");
  if (v) v.srcObject = null;
}

function scanError(title, msg) {
  const err = document.getElementById("scan-err");
  err.querySelector(".big").textContent = title;
  err.querySelector("p").textContent = msg;
  err.classList.add("show");
}

/* ------------------------------ Helpers --------------------------------- */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function rand(a, b) { return a + Math.random() * (b - a); }
function setText(id, t) { const e = document.getElementById(id); if (e) e.textContent = t; }
function setBar(id, val, max, color) {
  const e = document.getElementById(id); if (!e) return;
  e.style.width = clamp((val / max) * 100, 0, 100) + "%";
  if (color) e.style.background = color;
}
function tempColor(t, max) {
  if (t > max * 0.88) return "var(--bad)";
  if (t > max * 0.75) return "var(--warn)";
  return "var(--ok)";
}
function drawSpark(canvas, data, max) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (data.length < 2) return;
  const min = max * 0.7;
  const x = (i) => (i / (data.length - 1)) * w;
  const y = (v) => h - ((v - min) / (max - min)) * (h - 4) - 2;
  ctx.beginPath();
  ctx.moveTo(x(0), y(data[0]));
  for (let i = 1; i < data.length; i++) ctx.lineTo(x(i), y(data[i]));
  ctx.strokeStyle = "#2f6df6"; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.stroke();
  ctx.lineTo(x(data.length - 1), h); ctx.lineTo(x(0), h); ctx.closePath();
  ctx.fillStyle = "rgba(47,109,246,0.12)"; ctx.fill();
}

/* ------------------------------- Boot ----------------------------------- */
document.getElementById("brand-title").textContent = "Module Hub";
document.getElementById("brand-sub").textContent = SITE.location;
window.addEventListener("hashchange", render);
render();
