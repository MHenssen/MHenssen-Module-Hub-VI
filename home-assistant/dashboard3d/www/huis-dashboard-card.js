/*
 * huis-dashboard-card — fotorealistisch huisdashboard voor Home Assistant.
 *
 * Opbouw (bedoeld voor een tablet, als paneel-weergave):
 *   bovenbalk   weer, goedkoopste stroomblok, klok, live-indicator
 *   tegels      net nu, verbruik vandaag, zon nu, laadpaal, stroomprijs
 *   midden      vooraf gerenderde foto's (Blender/Cycles): Achter, Voor en per
 *               verdieping; lampgroepen worden als lichtlaag over de foto gelegd
 *               (mix-blend-mode: screen) met dekking = helderheid
 *   links       "Nu thuis": alleen meldingen die nu actief zijn
 *   rechts      kamerpaneel met lampen (tik = aan/uit, schuif = dimmen)
 *   onder       wie er thuis is en de status van de deuren
 *   3D          vrij draaibaar model (huis.glb) met losse verdiepingen
 *
 * Onbereikbare entities (unavailable/unknown, bv. Tuya na een stroomdip)
 * worden als "onbekend" getoond, nooit als "uit", en worden niet geschakeld.
 *
 * Alles lokaal: bestanden in /config/www/dashboard3d/ (= /local/dashboard3d/).
 */

const ONBEKEND = ["unavailable", "unknown"];
const LAADPAAL_NL = {
  disconnected: "Geen auto", awaiting_start: "Wacht op start", charging: "Laden", completed: "Klaar",
  ready_to_charge: "Klaar om te laden", paused: "Gepauzeerd", error: "Fout", awaiting_authorization: "Wacht op pas",
  de_authorizing: "Stoppen",
};
const WEER_NL = {
  "clear-night": "Helder", cloudy: "Bewolkt", fog: "Mist", hail: "Hagel", lightning: "Onweer",
  "lightning-rainy": "Onweersbuien", partlycloudy: "Gedeeltelijk bewolkt", pouring: "Zware regen",
  rainy: "Regen", snowy: "Sneeuw", "snowy-rainy": "Natte sneeuw", sunny: "Zonnig", windy: "Winderig",
  "windy-variant": "Winderig", exceptional: "Uitzonderlijk",
};

class HuisDashboardCard extends HTMLElement {
  setConfig(config) {
    this._config = { pad: "/local/dashboard3d", ...config };
    this._view = config.start || "achter";
    this._tijd = "auto"; // auto | dag | avond
    this._labels = true;
    this._kamer = null;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._laad();
  }

  getCardSize() {
    return 14;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._data) this._update();
  }

  connectedCallback() {
    this._klok = setInterval(() => this._data && this._updateKlok(), 1000);
  }

  disconnectedCallback() {
    clearInterval(this._klok);
  }

  async _laad() {
    const url = `${this._config.pad}/verdiepingen.json`;
    try {
      this._data = await (await fetch(url, { cache: "no-cache" })).json();
    } catch (e) {
      this.shadowRoot.innerHTML = `<ha-card style="padding:16px">Kan ${url} niet laden: ${e}</ha-card>`;
      return;
    }
    const d = this._data;
    const start = d.weergaven.find((v) => v.id === this._view);
    this._kamer = (start?.groepen || []).map((g) => g.kamer).find((id) => d.kamers.some((x) => x.id === id)) || d.kamers[0]?.id;
    this._bouw();
    if (this._hass) this._update();
  }

  // ------------------------------------------------------------ helpers
  _s(id) {
    return id && this._hass ? this._hass.states[id] : undefined;
  }

  _num(id) {
    const s = this._s(id);
    if (!s || ONBEKEND.includes(s.state)) return null;
    const v = parseFloat(s.state);
    return isNaN(v) ? null : v;
  }

  // vermogen altijd in W, ook als de sensor kW geeft (bv. sensor.netto_vermogen_kw)
  _watt(id) {
    const v = this._num(id);
    if (v == null) return null;
    const eenheid = (this._s(id).attributes.unit_of_measurement || (id.endsWith("_kw") ? "kW" : "W")).toLowerCase();
    return eenheid === "kw" ? v * 1000 : v;
  }

  _f(v, d = 0) {
    return v == null ? "–" : v.toLocaleString("nl-NL", { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  _lampStatus(ids) {
    const st = ids.map((id) => this._s(id)).filter(Boolean);
    if (!st.length || st.every((s) => ONBEKEND.includes(s.state))) return { status: "onbekend", b: 0 };
    const aan = st.filter((s) => s.state === "on");
    if (!aan.length) return { status: st.some((s) => ONBEKEND.includes(s.state)) ? "onbekend" : "uit", b: 0 };
    const b = aan.map((s) => (s.attributes.brightness ?? 255) / 255);
    return { status: "aan", b: b.reduce((a, c) => a + c, 0) / b.length };
  }

  _groepIds(g) {
    return g.bediening ? [g.bediening] : g.lampen || [];
  }

  _avond() {
    if (this._tijd !== "auto") return this._tijd === "avond";
    const zon = this._s("sun.sun");
    return zon ? zon.state === "below_horizon" : new Date().getHours() >= 18;
  }

  _schakel(id, aan, extra = {}) {
    const st = this._s(id);
    if (!st || ONBEKEND.includes(st.state)) return; // nooit blind schakelen
    this._hass.callService("light", aan ? "turn_on" : "turn_off", { entity_id: id, ...extra });
  }

  _cfg(k) {
    return (this._config.entities || {})[k];
  }

  // mdi-icoon via HA's eigen <ha-icon>; buiten HA (test) een emoji
  _icoon(icon, reserve = "💡") {
    return customElements.get("ha-icon") ? `<ha-icon icon="${icon}"></ha-icon>` : reserve;
  }

  // HA's eigen detailvenster (met geschiedenis en alle instellingen)
  _meerInfo(id) {
    if (!id) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: id }, bubbles: true, composed: true }));
  }

  _naam(id) {
    return this._s(id)?.attributes.friendly_name || id.split(".")[1].replace(/_/g, " ");
  }

  // tik = schakelen, vasthouden (0,5 s) = details
  _tikHoud(el, tik, houd) {
    let t = null;
    let lang = false;
    el.addEventListener("pointerdown", () => {
      lang = false;
      t = setTimeout(() => { lang = true; houd(); }, 500);
    });
    const stop = () => clearTimeout(t);
    el.addEventListener("pointerup", stop);
    el.addEventListener("pointerleave", stop);
    el.addEventListener("contextmenu", (e) => { e.preventDefault(); });
    el.addEventListener("click", (e) => { e.stopPropagation(); if (!lang) tik(); });
  }

  _alleLampen() {
    const ids = [];
    for (const k of this._data.kamers) for (const id of k.lampen) if (!ids.includes(id)) ids.push(id);
    return ids;
  }

  // ------------------------------------------------------------ opbouw
  _bouw() {
    const d = this._data;
    const view = d.weergaven.find((v) => v.id === this._view) || d.weergaven[0];
    const p = this._config.pad;
    const knop = (id, naam, actief, attr) => `<button ${attr}="${id}" class="${actief ? "actief" : ""}">${naam}</button>`;
    this.shadowRoot.innerHTML = `
<style>
  :host { --bg:#121417; --panel:#1b1e23; --panel2:#23272e; --tekst:#e8eaed; --sub:#8b919a;
          --accent:#2ec4a6; --warm:#ffb648; --rood:#ff6b5b; --blauw:#5aa9ff; color:var(--tekst);
          font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif); }
  ha-card { background:var(--bg); color:var(--tekst); border-radius:18px; padding:14px; overflow:hidden; }
  .kop { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .kop .titel b { font-size:20px; display:block; } .kop .titel span { color:var(--sub); font-size:12px; }
  .kop .ruimte { flex:1; }
  .chip { background:var(--panel); border:1px solid #2a2f37; border-radius:12px; padding:6px 12px; font-size:13px;
          display:flex; gap:8px; align-items:center; white-space:nowrap; }
  .chip .groen { color:var(--accent); } .live::before { content:""; width:8px; height:8px; border-radius:50%;
          background:var(--accent); display:inline-block; box-shadow:0 0 6px var(--accent); }
  .tegels { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:12px 0; }
  .tegel { background:var(--panel); border:1px solid #2a2f37; border-radius:14px; padding:10px 14px; }
  .tegel .l { font-size:12px; color:var(--sub); } .tegel .w { font-size:24px; font-weight:600; }
  .tegel .w small { font-size:13px; font-weight:400; color:var(--sub); } .tegel .s { font-size:12px; }
  .hoofd { display:grid; grid-template-columns: 1fr 300px; gap:12px; }
  @media (max-width: 900px) { .hoofd { grid-template-columns: 1fr; } }
  .stage { position:relative; border-radius:16px; overflow:hidden; background:#0b0c0e; }
  .beeld { position:relative; aspect-ratio:${d.beeld.breedte} / ${d.beeld.hoogte}; }
  .beeld > img { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
  .beeld > img.licht { mix-blend-mode:screen; opacity:0; transition:opacity .5s; pointer-events:none; }
  .seg { position:absolute; top:10px; right:10px; display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; z-index:3; }
  .seg div { display:flex; background:rgba(20,22,26,.85); border:1px solid #2f343c; border-radius:12px; padding:3px; }
  .seg button { background:none; border:0; color:var(--sub); padding:5px 10px; border-radius:9px; font:inherit;
                font-size:12px; cursor:pointer; } .seg button.actief { background:#3a404a; color:var(--tekst); }
  .hot { position:absolute; transform:translate(-50%,-50%); width:34px; height:34px; border-radius:50%; z-index:2;
         background:rgba(20,22,26,.7); border:1.5px solid rgba(255,255,255,.6); display:flex; align-items:center;
         justify-content:center; cursor:pointer; font-size:15px; touch-action:manipulation; }
  .hot.aan { background:rgba(255,182,72,.95); box-shadow:0 0 16px rgba(255,182,72,.9); border-color:#fff; }
  .hot.onbekend { opacity:.55; border-style:dashed; }
  .label { position:absolute; transform:translate(-50%,-50%); z-index:2; background:rgba(20,22,26,.82);
           border:1px solid #39404a; border-radius:12px; padding:4px 10px 4px 8px; font-size:12px; display:flex;
           gap:6px; align-items:center; white-space:nowrap; pointer-events:none; }
  .label b { font-size:14px; } .label small { color:var(--sub); display:block; font-size:10px; }
  .nuthuis { position:absolute; left:10px; top:58px; width:230px; z-index:3; background:rgba(20,22,26,.88);
             border:1px solid #2f343c; border-radius:14px; padding:10px; }
  .nuthuis h4 { margin:0 0 8px; font-size:13px; display:flex; justify-content:space-between; }
  .nuthuis h4 span { color:var(--sub); font-weight:400; }
  .melding { border:1px solid #3a3f47; border-radius:10px; padding:6px 8px; margin-top:6px; font-size:12px;
             display:flex; gap:8px; } .melding b { display:block; font-size:13px; } .melding span { color:var(--sub); }
  .melding.warm { border-color:#7a5a2a; } .melding.rood { border-color:#7a3a33; } .melding.groen { border-color:#2b6b5f; }
  .paneel { background:var(--panel); border:1px solid #2a2f37; border-radius:16px; padding:12px; max-height:640px;
            overflow:auto; } .paneel h3 { margin:0; font-size:18px; } .paneel .sub { color:var(--sub); font-size:12px; }
  .kamers { display:flex; gap:6px; flex-wrap:wrap; margin:10px 0; }
  .kamers button { background:var(--panel2); border:0; color:var(--sub); padding:5px 10px; border-radius:10px;
                   font:inherit; font-size:12px; cursor:pointer; } .kamers button.actief { background:#3a404a; color:var(--tekst); }
  .rij { background:var(--panel2); border-radius:12px; padding:10px 12px; margin-top:8px; }
  .rij .boven { display:flex; align-items:center; gap:10px; } .rij .naam { flex:1; } .rij .naam small { display:block; color:var(--sub); }
  .tgl { width:42px; height:24px; border-radius:12px; background:#3a3f47; position:relative; cursor:pointer; border:0; }
  .tgl::after { content:""; position:absolute; top:3px; left:3px; width:18px; height:18px; border-radius:50%; background:#cfd3d8; transition:left .2s; }
  .tgl.aan { background:var(--warm); } .tgl.aan::after { left:21px; background:#fff; } .tgl:disabled { opacity:.35; }
  .rij input[type=range] { width:100%; margin-top:8px; accent-color:var(--warm); }
  .voet { display:flex; gap:8px; justify-content:center; margin-top:12px; flex-wrap:wrap; }
  .persoon { display:flex; align-items:center; gap:8px; background:var(--panel); border:1px solid #2a2f37; border-radius:12px; padding:5px 12px 5px 6px; font-size:12px; }
  .persoon .av { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:600; background:#3a404a; }
  .persoon.thuis .av { background:#e9a23b; color:#2b1a00; } .persoon span { color:var(--sub); display:block; }
  .persoon.thuis span { color:var(--accent); } .persoon.alarm { border-color:#7a3a33; }
  @media (max-width: 700px) {
    ha-card { padding:10px; }
    .tegels { grid-template-columns:repeat(2,1fr); } .tegel .w { font-size:20px; }
    .stage { display:flex; flex-direction:column; } .seg { order:-1; }
    .seg { position:static; justify-content:flex-start; padding:8px; overflow-x:auto; flex-wrap:nowrap; }
    .seg div { flex-shrink:0; }
    .nuthuis { position:static; width:auto; margin:8px; }
    .hot { width:30px; height:30px; font-size:13px; }
    .label { font-size:10px; padding:2px 6px; } .label b { font-size:11px; } .label small { display:none; }
    .kop .titel span { display:none; } .chip.live { display:none; }
  }
  #drie { position:absolute; inset:0; z-index:2; display:none; background:#121417; }
  ha-icon { --mdc-icon-size:18px; }
  .klik { cursor:pointer; transition:transform .12s, border-color .2s; }
  .klik:hover { border-color:#3d4450; } .klik:active { transform:scale(.97); }
  .tegel .pijl { float:right; color:var(--sub); font-size:12px; }
  .label.klik { pointer-events:auto; }
  .chip.lampen b { color:var(--warm); }
  .pop { position:fixed; inset:0; z-index:20; background:rgba(5,6,8,.55); display:flex; align-items:center;
         justify-content:center; padding:16px; backdrop-filter:blur(3px); }
  .pop[hidden] { display:none; }
  .vel { background:var(--panel); border:1px solid #2f343c; border-radius:20px; width:min(420px,100%);
         max-height:90%; overflow:auto; padding:16px; box-shadow:0 20px 60px rgba(0,0,0,.6); }
  .vel .velkop { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
  .vel .velkop h3 { margin:0; font-size:18px; flex:1; } .vel .velkop small { display:block; color:var(--sub); font-weight:400; font-size:12px; }
  .vel .dicht { background:var(--panel2); border:0; color:var(--tekst); width:32px; height:32px; border-radius:50%; cursor:pointer; font-size:16px; }
  .groot { display:flex; align-items:center; gap:12px; background:var(--panel2); border-radius:14px; padding:14px; margin-bottom:10px; }
  .groot .wrd { font-size:28px; font-weight:600; } .groot .wrd small { font-size:13px; color:var(--sub); font-weight:400; }
  .knoppen { display:grid; grid-template-columns:repeat(auto-fit,minmax(80px,1fr)); gap:8px; margin:10px 0; }
  .knoppen button, .kn { background:var(--panel2); border:1px solid #333944; color:var(--tekst); border-radius:12px;
         padding:10px 8px; font:inherit; font-size:13px; cursor:pointer; display:flex; flex-direction:column;
         align-items:center; gap:4px; }
  .knoppen button:active, .kn:active { transform:scale(.96); }
  .knoppen button.actief { background:var(--accent); color:#06231d; border-color:var(--accent); }
  .knoppen button:disabled { opacity:.35; cursor:default; }
  .kn.rood { border-color:#7a3a33; color:#ffb4aa; } .kn.breed { width:100%; flex-direction:row; justify-content:center; margin-top:10px; }
  .regel { display:flex; justify-content:space-between; gap:10px; padding:7px 2px; border-bottom:1px solid #2a2f37; font-size:13px; }
  .regel span:first-child { color:var(--sub); } .regel:last-child { border-bottom:0; }
  .vel h4 { margin:14px 0 6px; font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--sub); }
  .schuif { width:100%; accent-color:var(--warm); height:28px; }
  .schuif.kt { accent-color:#ffd9a0; background:linear-gradient(90deg,#ffb35c,#fff4e0,#cfe3ff); border-radius:8px; height:10px; -webkit-appearance:none; appearance:none; }
  .kleuren { display:flex; gap:8px; flex-wrap:wrap; margin-top:6px; }
  .kleuren button { width:34px; height:34px; border-radius:50%; border:2px solid #fff3; cursor:pointer; }
  .hot.scene { background:rgba(46,196,166,.25); border-color:var(--accent); }
  .scenes { display:flex; gap:6px; flex-wrap:wrap; margin:4px 0 8px; }
  .alles-uit { margin-left:auto; background:none; border:1px solid #3a3f47; color:var(--sub); border-radius:10px; padding:4px 10px; font:inherit; font-size:12px; cursor:pointer; }
  .stage.drie .hot { display:none; }
</style>
<ha-card>
  <div class="kop">
    <div class="chip">🏠</div>
    <div class="titel"><b>${this._config.titel || "Thuis"}</b><span class="datum"></span></div>
    <div class="ruimte"></div>
    <div class="chip lampen klik"></div>
    <div class="chip weer klik"></div>
    <div class="chip goedkoop"></div>
    <div class="chip"><span class="klok"></span></div>
    <div class="chip live"><span class="livetxt">Live</span></div>
  </div>
  <div class="tegels"></div>
  <div class="hoofd">
    <div class="stage ${this._view === "3d" ? "drie" : ""}">
     <div class="beeld">
      <img class="basis" alt="">
      ${(view.groepen || []).filter((g) => g.render).map((g) => `<img class="licht" data-g="${g.id}" src="${p}/renders/${g.render}" alt="">`).join("")}
      ${(view.groepen || []).filter((g) => g.x != null).map((g) => `<div class="hot ${g.type === "scene" ? "scene" : ""}" data-g="${g.id}" title="${g.naam}" style="left:${g.x}%;top:${g.y}%">${this._icoon(g.icoon || "mdi:lightbulb", g.type === "scene" ? "🔊" : "💡")}</div>`).join("")}
      <div class="labels"></div>
      <div id="drie"></div>
     </div>
      <div class="nuthuis"><h4>Nu thuis <span class="aantal"></span></h4><div class="lijst"></div></div>
      <div class="seg">
        <div>${d.weergaven.map((v) => knop(v.id, v.naam, v.id === this._view, "data-view")).join("")}${knop("3d", "3D", this._view === "3d", "data-view")}</div>
        <div>${[["auto", "Auto"], ["dag", "Dag"], ["avond", "Avond"]].map(([k, n]) => knop(k, n, this._tijd === k, "data-tijd")).join("")}</div>
        <div>${knop("labels", "Energie", this._labels, "data-labels")}</div>
      </div>
    </div>
    <div class="paneel">
      <div style="display:flex;align-items:center;gap:8px"><h3 class="kamernaam"></h3><button class="alles-uit" data-actie="kamer-uit">Alles uit</button></div>
      <div class="sub kamersub"></div>
      ${(d.scenes || []).length ? `<div class="scenes">${d.scenes.map((sc) => `<button class="kn" data-scene="${sc.id}" style="flex-direction:row;padding:6px 10px">${this._icoon(sc.icoon, "🎵")} ${sc.naam}</button>`).join("")}</div>` : ""}
      <div class="kamers">${d.kamers.map((k) => knop(k.id, k.naam, k.id === this._kamer, "data-kamer")).join("")}</div>
      <div class="rijen"></div>
    </div>
  </div>
  <div class="voet"></div>
  <div class="pop" hidden><div class="vel"></div></div>
</ha-card>`;
    const r = this.shadowRoot;
    r.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => {
      this._view = b.dataset.view;
      // kamerpaneel meenemen naar een kamer op deze verdieping
      const nieuw = d.weergaven.find((v) => v.id === this._view);
      const k = (nieuw?.groepen || []).map((g) => g.kamer).find((id) => d.kamers.some((x) => x.id === id));
      if (k) this._kamer = k;
      this._bouw();
      this._update();
    }));
    r.querySelectorAll("[data-tijd]").forEach((b) => b.addEventListener("click", () => {
      this._tijd = b.dataset.tijd;
      r.querySelectorAll("[data-tijd]").forEach((x) => x.classList.toggle("actief", x === b));
      this._update();
    }));
    r.querySelector("[data-labels]").addEventListener("click", (e) => {
      this._labels = !this._labels;
      e.target.classList.toggle("actief", this._labels);
      this._update();
    });
    r.querySelectorAll("[data-kamer]").forEach((b) => b.addEventListener("click", () => {
      this._kamer = b.dataset.kamer;
      r.querySelectorAll("[data-kamer]").forEach((x) => x.classList.toggle("actief", x === b));
      this._bouwRijen();
      this._update();
    }));
    r.querySelectorAll(".hot").forEach((h) => {
      const g = view.groepen.find((x) => x.id === h.dataset.g);
      const naarKamer = () => {
        if (!g.kamer || !d.kamers.some((k) => k.id === g.kamer)) return;
        this._kamer = g.kamer;
        r.querySelectorAll("[data-kamer]").forEach((x) => x.classList.toggle("actief", x.dataset.kamer === g.kamer));
        this._bouwRijen();
      };
      if (g.type === "scene") {
        h.addEventListener("click", () => this._open("scene", g));
        return;
      }
      this._tikHoud(h, () => {
        const st = this._lampStatus(this._groepIds(g));
        if (st.status === "onbekend") return;
        this._groepIds(g).forEach((id) => this._schakel(id, st.status !== "aan"));
        naarKamer();
      }, () => this._open("lamp", g));
    });
    // klikbare onderdelen
    r.querySelector(".chip.lampen").addEventListener("click", () => this._open("aan"));
    r.querySelector(".chip.weer").addEventListener("click", () => this._meerInfo(this._cfg("weer") || "weather.forecast_thuis"));
    r.querySelector("[data-actie=kamer-uit]").addEventListener("click", () => {
      const k = d.kamers.find((x) => x.id === this._kamer);
      (k?.lampen || []).filter((id) => this._s(id)?.state === "on").forEach((id) => this._schakel(id, false));
    });
    r.querySelectorAll("[data-scene]").forEach((b) => b.addEventListener("click", () => this._open("scene", d.scenes.find((x) => x.id === b.dataset.scene))));
    const actie = (a) => (a === "laadpaal" ? this._open("laadpaal") : this._meerInfo(this._cfg(a)));
    for (const sel of [".tegels", ".labels"]) {
      r.querySelector(sel).addEventListener("click", (e) => {
        const el = e.target.closest("[data-actie]");
        if (el) actie(el.dataset.actie);
      });
    }
    for (const sel of [".voet", ".nuthuis"]) {
      r.querySelector(sel).addEventListener("click", (e) => {
        const el = e.target.closest("[data-ent]");
        if (el) this._meerInfo(el.dataset.ent);
      });
    }
    const pop = r.querySelector(".pop");
    pop.addEventListener("click", (e) => { if (e.target === pop) this._sluit(); });
    if (this._pop) this._tekenPop();
    this._bouwRijen();
    if (this._view === "3d") this._start3D();
  }

  _bouwRijen() {
    const kamer = this._data.kamers.find((k) => k.id === this._kamer);
    const r = this.shadowRoot;
    if (!kamer) return;
    r.querySelector(".kamernaam").textContent = kamer.naam;
    r.querySelector(".rijen").innerHTML = kamer.lampen
      .map((id) => `<div class="rij" data-id="${id}"><div class="boven"><span>💡</span><div class="naam"><span class="n"></span><small class="st"></small></div><button class="tgl"></button></div><input type="range" min="1" max="100"></div>`)
      .join("");
    r.querySelectorAll(".rij").forEach((rij) => {
      const id = rij.dataset.id;
      rij.querySelector(".tgl").addEventListener("click", () => this._schakel(id, this._s(id)?.state !== "on"));
      rij.querySelector(".naam").style.cursor = "pointer";
      rij.querySelector(".naam").addEventListener("click", () => this._open("lamp", { id, naam: this._naam(id), bediening: id, lampen: [] }));
      const slider = rij.querySelector("input");
      slider.addEventListener("change", () => this._schakel(id, true, { brightness_pct: Number(slider.value) }));
    });
    if (this._hass) this._updateRijen();
  }

  // ------------------------------------------------------------ live
  _updateKlok() {
    const nu = new Date();
    const r = this.shadowRoot;
    const k = r.querySelector(".klok");
    if (k) k.textContent = nu.toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });
    const d = r.querySelector(".datum");
    if (d) d.textContent = nu.toLocaleDateString("nl-NL", { weekday: "long", day: "numeric", month: "long" });
  }

  _update() {
    const r = this.shadowRoot;
    if (!r || !this._data || !this._hass) return;
    const p = this._config.pad;
    const view = this._data.weergaven.find((v) => v.id === this._view);
    this._updateKlok();
    const live = r.querySelector(".livetxt");
    if (live) live.textContent = this._hass.connected === false ? "Offline" : "Live";

    // weer
    const w = this._s(this._cfg("weer") || "weather.forecast_thuis");
    r.querySelector(".weer").innerHTML = w && !ONBEKEND.includes(w.state)
      ? `☀︎ <b>${this._f(w.attributes.temperature)}°C</b> ${WEER_NL[w.state] || w.state} · 💧 ${this._f(w.attributes.humidity)}%`
      : "Weer onbekend";

    // goedkoopste blok (als de prijssensor een lijst met prijzen heeft)
    const blok = this._goedkoopsteBlok();
    const gk = r.querySelector(".goedkoop");
    gk.style.display = blok ? "" : "none";
    if (blok) gk.innerHTML = `€ <span>Goedkoopst<br><b class="groen">${blok}</b></span>`;

    this._updateTegels();
    const aanIds = this._alleLampen().filter((id) => this._s(id)?.state === "on");
    r.querySelector(".chip.lampen").innerHTML = `${this._icoon("mdi:lightbulb-group", "💡")} <b>${aanIds.length}</b> aan`;
    if (this._pop && !this._sleept) this._tekenPop();
    if (view) {
      const basis = r.querySelector("img.basis");
      const src = `${p}/renders/${this._avond() ? view.basis : view.dag}`;
      if (basis && !basis.src.endsWith(src)) basis.src = src;
      for (const g of view.groepen || []) {
        const st = this._lampStatus(this._groepIds(g));
        const img = r.querySelector(`img.licht[data-g="${g.id}"]`);
        if (img) img.style.opacity = st.status === "aan" ? (0.35 + 0.65 * st.b).toFixed(2) : "0";
        const h = r.querySelector(`.hot[data-g="${g.id}"]`);
        if (h) {
          h.classList.toggle("aan", st.status === "aan");
          h.classList.toggle("onbekend", st.status === "onbekend");
          h.title = `${g.naam}: ${st.status}`;
        }
      }
      this._updateLabels(view);
    }
    if (this._three) {
      // in 3D alle groepen van alle weergaven kleuren
      for (const v of this._data.weergaven) {
        for (const g of v.groepen || []) this._three.zet(g.id, this._lampStatus(this._groepIds(g)));
      }
    }
    this._updateRijen();
    this._updateNuThuis();
    this._updateVoet();
  }

  _goedkoopsteBlok() {
    const s = this._s(this._cfg("prijs"));
    const lijst = s && (s.attributes.prices || s.attributes.forecast || s.attributes.today);
    if (!Array.isArray(lijst) || !lijst.length) return null;
    const nu = Date.now();
    const items = lijst
      .map((x) => ({ t: new Date(x.from || x.start || x.datetime || x.time).getTime(), p: parseFloat(x.price ?? x.value ?? x.total) }))
      .filter((x) => !isNaN(x.t) && !isNaN(x.p) && x.t >= nu - 3600e3 && x.t <= nu + 8 * 3600e3);
    if (!items.length) return null;
    const best = items.reduce((a, b) => (b.p < a.p ? b : a));
    const uur = (t) => new Date(t).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });
    return `${uur(best.t)}–${uur(best.t + 3600e3)} · € ${this._f(best.p, 3)}`;
  }

  _updateTegels() {
    const net = this._watt(this._cfg("net_nu"));
    const zon = this._watt(this._cfg("zon_nu"));
    const huis = net != null && zon != null ? net + zon : null;
    const laad = this._s(this._cfg("laadpaal_status"));
    const tegel = (l, w, eenheid, s, kleur, actie) =>
      `<div class="tegel klik" data-actie="${actie}"><div class="l">${l}<span class="pijl">›</span></div><div class="w">${w} <small>${eenheid}</small></div><div class="s" style="color:${kleur}">${s}</div></div>`;
    this.shadowRoot.querySelector(".tegels").innerHTML = [
      tegel("Net nu", this._f(net == null ? null : Math.abs(net)), "W", net == null ? "onbekend" : net < 0 ? "teruglevering" : "afname", net != null && net < 0 ? "var(--accent)" : "var(--blauw)", "net_nu"),
      tegel("Verbruik huis", this._f(huis), "W", `vandaag ${this._f(this._num(this._cfg("verbruik_vandaag")), 1)} kWh`, "var(--sub)", "verbruik_vandaag"),
      tegel("Zon nu", this._f(zon), "W", `${this._f(this._num(this._cfg("zon_vandaag")), 1)} kWh vandaag`, "var(--warm)", "zon_nu"),
      tegel("Laadpaal", laad && !ONBEKEND.includes(laad.state) ? LAADPAAL_NL[laad.state] || laad.state : "onbekend", "", `sessie ${this._f(this._num(this._cfg("laadpaal_sessie")), 1)} kWh`, "var(--sub)", "laadpaal"),
      tegel("Stroomprijs", this._f(this._num(this._cfg("prijs")), 3), "€/kWh", "", "var(--sub)", "prijs"),
    ].join("");
  }

  _updateLabels(view) {
    const el = this.shadowRoot.querySelector(".labels");
    if (!el) return;
    if (!this._labels || this._view === "3d") {
      el.innerHTML = "";
      return;
    }
    const net = this._watt(this._cfg("net_nu"));
    const zon = this._watt(this._cfg("zon_nu"));
    const waarden = {
      zon: ["☀︎", `${this._f(zon)} W`, "zonnepanelen"],
      net: ["⚡", `${this._f(net == null ? null : Math.abs(net))} W`, net != null && net < 0 ? "naar het net" : "van het net"],
      huis: ["🏠", `${this._f(net != null && zon != null ? net + zon : null)} W`, "verbruik huis"],
      laadpaal: ["🔌", LAADPAAL_NL[this._s(this._cfg("laadpaal_status"))?.state] || this._s(this._cfg("laadpaal_status"))?.state || "–", "laadpaal"],
    };
    el.innerHTML = (view.labels || [])
      .filter((l) => waarden[l.type])
      .map((l) => {
        const [i, w, s] = waarden[l.type];
        return `<div class="label klik" data-actie="${{ zon: "zon_nu", net: "net_nu", huis: "verbruik_vandaag", laadpaal: "laadpaal" }[l.type]}" style="left:${l.x}%;top:${l.y}%">${i}<div><b>${w}</b><small>${s}</small></div></div>`;
      })
      .join("");
  }

  _updateRijen() {
    const r = this.shadowRoot;
    let aan = 0;
    r.querySelectorAll(".rij").forEach((rij) => {
      const s = this._s(rij.dataset.id);
      const onb = !s || ONBEKEND.includes(s.state);
      const isAan = s?.state === "on";
      if (isAan) aan++;
      rij.querySelector(".n").textContent = s?.attributes.friendly_name || rij.dataset.id;
      rij.querySelector(".st").textContent = onb ? "Onbekend (niet bereikbaar)" : isAan ? `Aan · ${Math.round(((s.attributes.brightness ?? 255) / 255) * 100)}%` : "Uit";
      const t = rij.querySelector(".tgl");
      t.classList.toggle("aan", isAan);
      t.disabled = onb;
      const sl = rij.querySelector("input");
      sl.style.display = isAan && s.attributes.brightness != null ? "" : "none";
      if (isAan && document.activeElement !== sl) sl.value = Math.round(((s.attributes.brightness ?? 255) / 255) * 100);
    });
    const kamer = this._data.kamers.find((k) => k.id === this._kamer);
    const sub = r.querySelector(".kamersub");
    if (kamer && sub) sub.textContent = `${kamer.verdieping} · ${kamer.lampen.length} lampen, ${aan} aan`;
  }

  _updateNuThuis() {
    const regels = this._config.meldingen || [];
    const actief = regels.filter((m) => {
      const s = this._s(m.entity);
      if (!s) return false;
      return (m.states || ["on"]).includes(s.state);
    });
    const r = this.shadowRoot;
    const box = r.querySelector(".nuthuis");
    if (!box) return;
    box.style.display = actief.length ? "" : "none";
    r.querySelector(".nuthuis .aantal").textContent = `${actief.length} ${actief.length === 1 ? "ding" : "dingen"}`;
    r.querySelector(".nuthuis .lijst").innerHTML = actief
      .map((m) => `<div class="melding klik ${m.kleur || "warm"}" data-ent="${m.entity}"><div>${m.icoon || "⚠︎"}</div><div><b>${m.titel}</b><span>${m.sub || ""}</span></div></div>`)
      .join("");
  }

  _updateVoet() {
    const r = this.shadowRoot;
    // geen lijst ingesteld: alle person.* uit Home Assistant
    const ids = this._config.personen || Object.keys(this._hass.states).filter((id) => id.startsWith("person.")).sort();
    const mensen = ids.map((id) => {
      const s = this._s(id);
      const naam = s?.attributes.friendly_name || id.split(".")[1];
      const thuis = s?.state === "home";
      const st = !s || ONBEKEND.includes(s.state) ? "onbekend" : thuis ? "Thuis" : "Weg";
      return `<div class="persoon klik ${thuis ? "thuis" : ""}" data-ent="${id}"><div class="av">${naam[0].toUpperCase()}</div><div>${naam}<span>${st}</span></div></div>`;
    });
    const deuren = (this._config.deuren || []).map((d) => {
      const s = this._s(d.entity);
      const st = !s || ONBEKEND.includes(s.state) ? "onbekend" : s.state === "on" ? "open" : "dicht";
      return `<div class="persoon klik ${st === "open" ? "alarm" : ""}" data-ent="${d.entity}"><div class="av">🚪</div><div>${d.naam}<span>${st}</span></div></div>`;
    });
    r.querySelector(".voet").innerHTML = mensen.concat(deuren).join("");
  }

  // ------------------------------------------------------------ pop-ups
  _open(type, arg) {
    this._pop = { type, arg };
    this._tekenPop();
  }

  _sluit() {
    this._pop = null;
    const p = this.shadowRoot.querySelector(".pop");
    if (p) p.hidden = true;
  }

  _tekenPop() {
    const pop = this.shadowRoot.querySelector(".pop");
    if (!pop || !this._pop || !this._hass) return;
    const vel = pop.querySelector(".vel");
    const { type, arg } = this._pop;
    const kop = (icoon, titel, sub) =>
      `<div class="velkop">${icoon}<h3>${titel}<small>${sub || ""}</small></h3><button class="dicht" aria-label="Sluiten">✕</button></div>`;
    let html = "";
    if (type === "lamp") html = this._popLamp(arg, kop);
    else if (type === "laadpaal") html = this._popLaadpaal(kop);
    else if (type === "aan") html = this._popAan(kop);
    else if (type === "scene") {
      html = kop(this._icoon(arg.icoon, "🎵"), arg.naam, "Scène")
        + `<div class="knoppen"><button data-sc="${arg.aan}">${this._icoon("mdi:play", "▶")}Aan</button>`
        + `<button data-sc="${arg.uit}">${this._icoon("mdi:stop", "■")}Uit</button></div>`;
    }
    const scroll = vel.scrollTop;
    vel.innerHTML = html;
    vel.scrollTop = scroll;
    pop.hidden = false;
    this._bindPop(vel);
  }

  _schakelaar(id, aan, onb, attr = "data-tgl") {
    return `<button class="tgl ${aan ? "aan" : ""}" ${attr}="${id}" ${onb ? "disabled" : ""}></button>`;
  }

  _rijLamp(id) {
    const s = this._s(id);
    const onb = !s || ONBEKEND.includes(s.state);
    const aan = s?.state === "on";
    const st = onb ? "Onbekend" : aan ? `Aan · ${Math.round(((s.attributes.brightness ?? 255) / 255) * 100)}%` : "Uit";
    return `<div class="rij"><div class="boven"><span>💡</span><div class="naam">${this._naam(id)}<small>${st}</small></div>${this._schakelaar(id, aan, onb)}</div></div>`;
  }

  _popLamp(g, kop) {
    const id = g.bediening || (g.lampen || [])[0];
    const s = this._s(id);
    const onb = !s || ONBEKEND.includes(s.state);
    const aan = s?.state === "on";
    const pct = aan ? Math.round(((s.attributes.brightness ?? 255) / 255) * 100) : 0;
    const modes = s?.attributes.supported_color_modes || [];
    const dimbaar = modes.some((m) => m !== "onoff") || s?.attributes.brightness != null;
    const kt = modes.includes("color_temp");
    const kleur = modes.some((m) => ["hs", "rgb", "rgbw", "rgbww", "xy"].includes(m));
    const minK = s?.attributes.min_color_temp_kelvin || 2200;
    const maxK = s?.attributes.max_color_temp_kelvin || 6500;
    const curK = s?.attributes.color_temp_kelvin || 2700;
    const kleuren = [[30, 75], [0, 85], [330, 70], [285, 70], [225, 85], [185, 75], [120, 70], [52, 70]];
    const leden = (g.lampen || []).filter((x) => x !== id);
    return kop(this._icoon(g.icoon || "mdi:lightbulb"), g.naam || this._naam(id), onb ? "Niet bereikbaar" : aan ? "Aan" : "Uit")
      + `<div class="groot"><div class="wrd">${onb ? "Onbekend" : aan ? `${pct}<small> %</small>` : "Uit"}</div><div style="margin-left:auto">${this._schakelaar(id, aan, onb)}</div></div>`
      + (dimbaar && !onb ? `<h4>Helderheid</h4><input type="range" class="schuif" min="1" max="100" value="${pct || 50}" data-dim="${id}">` : "")
      + (kt && !onb ? `<h4>Kleurtemperatuur</h4><input type="range" class="schuif kt" min="${minK}" max="${maxK}" value="${curK}" data-kt="${id}">` : "")
      + (kleur && !onb ? `<h4>Kleur</h4><div class="kleuren">${kleuren.map(([h, sat]) => `<button data-kleur="${id}" data-h="${h}" data-s="${sat}" style="background:hsl(${h},${sat}%,55%)"></button>`).join("")}</div>` : "")
      + (leden.length ? `<h4>Losse lampen</h4>${leden.map((x) => this._rijLamp(x)).join("")}` : "")
      + `<button class="kn breed" data-meer="${id}">${this._icoon("mdi:cog", "⚙︎")} Meer opties en geschiedenis</button>`;
  }

  _popAan(kop) {
    const aan = this._alleLampen().filter((id) => this._s(id)?.state === "on");
    return kop(this._icoon("mdi:lightbulb-group", "💡"), "Lampen die aan zijn", `${aan.length} van ${this._alleLampen().length}`)
      + (aan.length ? aan.map((id) => this._rijLamp(id)).join("") : `<div class="groot">Alle lampen zijn uit.</div>`)
      + (aan.length ? `<button class="kn breed rood" data-alles-uit>${this._icoon("mdi:power", "⏻")} Alles uit (${aan.length})</button>` : "");
  }

  _laadpaalInfo() {
    const statusId = this._cfg("laadpaal_status") || "";
    const cfg = this._config.laadpaal || {};
    const prefix = cfg.prefix || (statusId.split(".")[1] || "").replace(/_status$/, "");
    return { statusId, cfg, prefix, charger: cfg.charger_id || prefix.toUpperCase() };
  }

  _popLaadpaal(kop) {
    const { statusId, cfg, prefix } = this._laadpaalInfo();
    const st = this._s(statusId);
    const onb = !st || ONBEKEND.includes(st.state);
    const status = st?.state;
    const ents = prefix ? Object.keys(this._hass.states).filter((e) => (e.split(".")[1] || "").startsWith(prefix + "_")) : [];
    const vermogenId = cfg.vermogen || ents.find((e) => e.startsWith("sensor.") && /(vermogen|power)$/.test(e));
    const vermogen = this._watt(vermogenId);
    const geenAuto = status === "disconnected";
    const knop = (cmd, icoon, reserve, tekst, actief) =>
      `<button data-easee="${cmd}" ${onb || geenAuto ? "disabled" : ""} class="${actief ? "actief" : ""}">${this._icoon(icoon, reserve)}${tekst}</button>`;
    const bestuurder = this._s(cfg.bestuurder || "input_select.laadpaal_bestuurder");
    const maand = (cfg.maand || ["input_number.laadkwh_mark", "input_number.laadkwh_sophie"]).filter((id) => this._s(id));
    const schakelaars = ents.filter((e) => e.startsWith("switch."));
    const sensoren = ents.filter((e) => e.startsWith("sensor.") && e !== statusId).slice(0, 12);
    const regel = (id) => {
      const s = this._s(id);
      const w = !s || ONBEKEND.includes(s.state) ? "onbekend" : `${LAADPAAL_NL[s.state] || s.state} ${s.attributes.unit_of_measurement || ""}`;
      return `<div class="regel"><span>${this._naam(id)}</span><span>${w}</span></div>`;
    };
    return kop(this._icoon("mdi:ev-station", "🔌"), "Laadpaal", "Easee op de oprit")
      + `<div class="groot">${this._icoon("mdi:car-electric", "🚗")}<div class="wrd">${onb ? "Onbekend" : LAADPAAL_NL[status] || status}<br><small>${vermogen != null ? `${this._f(vermogen / 1000, 1)} kW · ` : ""}sessie ${this._f(this._num(this._cfg("laadpaal_sessie")), 1)} kWh</small></div></div>`
      + `<div class="knoppen">${knop("start", "mdi:play", "▶", "Start", false)}${knop("pause", "mdi:pause", "❚❚", "Pauze", status === "paused")}${knop("resume", "mdi:play-pause", "▶❚", "Hervat", false)}${knop("stop", "mdi:stop", "■", "Stop", false)}</div>`
      + (geenAuto ? `<div class="sub" style="text-align:center">Geen auto aangesloten.</div>` : "")
      + (bestuurder ? `<h4>Wie laadt er?</h4><div class="knoppen">${(bestuurder.attributes.options || []).map((o) => `<button data-select="${bestuurder.entity_id}" data-optie="${o}" class="${bestuurder.state === o ? "actief" : ""}">${o}</button>`).join("")}</div>` : "")
      + (maand.length ? `<h4>Deze maand geladen</h4>${maand.map(regel).join("")}` : "")
      + (schakelaars.length ? `<h4>Instellingen</h4>${schakelaars.map((id) => { const s = this._s(id); const onb2 = !s || ONBEKEND.includes(s.state); return `<div class="regel"><span>${this._naam(id)}</span>${this._schakelaar(id, s?.state === "on", onb2, "data-switch")}</div>`; }).join("")}` : "")
      + (sensoren.length ? `<h4>Details</h4>${sensoren.map(regel).join("")}` : "")
      + `<button class="kn breed" data-meer="${statusId}">${this._icoon("mdi:chart-line", "📈")} Geschiedenis</button>`;
  }

  _bindPop(vel) {
    const h = this._hass;
    const q = (sel, fn, ev = "click") => vel.querySelectorAll(sel).forEach((el) => el.addEventListener(ev, (e) => fn(el, e)));
    q(".dicht", () => this._sluit());
    q("[data-tgl]", (el) => this._schakel(el.dataset.tgl, this._s(el.dataset.tgl)?.state !== "on"));
    q("[data-switch]", (el) => h.callService("switch", "toggle", { entity_id: el.dataset.switch }));
    q("[data-sc]", (el) => { h.callService("scene", "turn_on", { entity_id: el.dataset.sc }); this._sluit(); });
    q("[data-meer]", (el) => { this._sluit(); this._meerInfo(el.dataset.meer); });
    q("[data-alles-uit]", () => this._alleLampen().filter((id) => this._s(id)?.state === "on").forEach((id) => this._schakel(id, false)));
    q("[data-select]", (el) => h.callService("input_select", "select_option", { entity_id: el.dataset.select, option: el.dataset.optie }));
    q("[data-easee]", (el) => h.callService("easee", "action_command", { charger_id: this._laadpaalInfo().charger, action_command: el.dataset.easee }));
    q("[data-kleur]", (el) => this._schakel(el.dataset.kleur, true, { hs_color: [Number(el.dataset.h), Number(el.dataset.s)] }));
    for (const [attr, sleutel] of [["data-dim", "brightness_pct"], ["data-kt", "color_temp_kelvin"]]) {
      q(`[${attr}]`, () => { this._sleept = true; }, "input");
      q(`[${attr}]`, (el) => {
        this._sleept = false;
        this._schakel(el.getAttribute(attr), true, { [sleutel]: Number(el.value) });
      }, "change");
    }
  }

  // ------------------------------------------------------------ 3D
  async _start3D() {
    const host = this.shadowRoot.querySelector("#drie");
    host.style.display = "block";
    const p = this._config.pad;
    const THREE = await import(`${p}/vendor/three.module.js`);
    const { GLTFLoader } = await import(`${p}/vendor/addons/loaders/GLTFLoader.js`);
    const { OrbitControls } = await import(`${p}/vendor/addons/controls/OrbitControls.js`);
    const w = host.clientWidth;
    const h = host.clientHeight;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h);
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x121417);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 2));
    const zon = new THREE.DirectionalLight(0xffffff, 1.2);
    zon.position.set(10, 20, 10);
    scene.add(zon);
    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 500);
    const controls = new OrbitControls(camera, renderer.domElement);
    const root = (await new GLTFLoader().loadAsync(`${p}/huis.glb`)).scene;
    scene.add(root);
    root.traverse((o) => {
      if (/_daken$|_terrein$/.test(o.name)) o.visible = false;
    });
    [1, 2, 3].map((i) => root.getObjectByName(`verdieping_${i}`)).filter(Boolean).forEach((f, i) => (f.position.y += i * 3));
    const box = new THREE.Box3().setFromObject(root);
    const c = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3()).length();
    camera.position.set(c.x + size * 0.5, c.y + size * 0.45, c.z + size * 0.5);
    controls.target.copy(c);
    controls.update();
    const mats = {};
    root.traverse((o) => {
      const g = o.userData?.groep;
      if (o.isMesh && g) {
        o.material = o.material.clone();
        (mats[g] = mats[g] || []).push(o.material);
      }
    });
    this._three = {
      zet: (id, st) => (mats[id] || []).forEach((m) => {
        const aan = st.status === "aan";
        m.color.set(st.status === "onbekend" ? 0x777777 : aan ? 0xffc864 : 0x333333);
        if (m.emissive) {
          m.emissive.set(aan ? 0xffb040 : 0x000000);
          m.emissiveIntensity = aan ? 0.4 + st.b : 0;
        }
      }),
    };
    const loop = () => {
      if (!this.isConnected || this._view !== "3d") {
        renderer.dispose();
        this._three = null;
        return;
      }
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(loop);
    };
    loop();
    this._update();
  }
}

customElements.define("huis-dashboard-card", HuisDashboardCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "huis-dashboard-card", name: "Huis dashboard", description: "Fotorealistisch huis met lampen, energie en meldingen" });
