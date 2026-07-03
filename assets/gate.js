/* =============================================================================
   Module Hub — light password gate
   -----------------------------------------------------------------------------
   IMPORTANT: this is a *deterrent*, not real security. The site is hosted on
   public static hosting (GitHub Pages), so the page files can still be reached
   directly by a determined technical user. For genuine protection, move to a
   host with server-side auth (Netlify password / Cloudflare Access / internal
   network SSO).

   The shared password is stored below only as a SHA-256 hash, so the plaintext
   is not visible in the code.

   >>> TO CHANGE THE PASSWORD:
   1. Run:  node -e "const c=require('crypto');console.log(c.createHash('sha256').update('YOUR-NEW-PASSWORD').digest('hex'))"
      (or in a browser console, use crypto.subtle — ask and I can do it for you)
   2. Paste the new hash into PASSWORD_HASH below.
   ========================================================================== */

const PASSWORD_HASH =
  "b5e0e9573cbbabc5a65cd031e7647514cdd025b2ddd6cddcd169c10d93a27ebf"; // SHA-256 of the shared password

const GATE_KEY = "mh_gate_ok"; // localStorage flag: remembered per device

async function sha256Hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

function unlockApp() {
  document.documentElement.classList.remove("locked");
  const g = document.getElementById("gate");
  if (g) g.remove();
}

function buildGate() {
  const el = document.createElement("div");
  el.id = "gate";
  el.innerHTML = `
    <form class="gate-card" id="gate-form" autocomplete="off">
      <div class="gate-mark">M</div>
      <h1>Module Hub</h1>
      <p>Enter the site password to continue.</p>
      <input id="gate-input" type="password" inputmode="text"
             placeholder="Password" autocomplete="current-password" aria-label="Site password">
      <div class="gate-err" id="gate-err" role="alert"></div>
      <button type="submit" class="gate-btn">Unlock</button>
    </form>`;
  document.body.appendChild(el);

  const form = el.querySelector("#gate-form");
  const input = el.querySelector("#gate-input");
  const err = el.querySelector("#gate-err");
  input.focus();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.textContent = "";
    const val = input.value;
    if (!val) return;
    let ok = false;
    try { ok = (await sha256Hex(val)) === PASSWORD_HASH; } catch (_) { ok = false; }
    if (ok) {
      try { localStorage.setItem(GATE_KEY, "1"); } catch (_) {}
      unlockApp();
    } else {
      err.textContent = "Incorrect password. Please try again.";
      input.value = "";
      input.focus();
    }
  });
}

// Run immediately (script is loaded before the app scripts).
(function initGate() {
  let remembered = false;
  try { remembered = localStorage.getItem(GATE_KEY) === "1"; } catch (_) {}
  if (remembered) { unlockApp(); return; }
  if (document.body) buildGate();
  else document.addEventListener("DOMContentLoaded", buildGate);
})();
