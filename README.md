# Module Hub

A lightweight web app for Vanderlande sites. Scan the QR label on a module to
open its **instruction manuals**, **training videos** and **live module health**.

> **MVP / demo.** All content here comes from **public** Vanderlande materials
> (website, trade press, public YouTube). No restricted or internal documents
> are included. The Health tab shows **simulated** data — wire it to the real
> site control system (PLC / SCADA / maintenance API) before production use.

## What it does

- **Directory** of modules grouped by system (POSISORTER, SPOX), with search.
- **Module page** with three tabs:
  - **Manuals** — in-app reference guides (public info) plus placeholders for the
    controlled PDFs you link on the internal network.
  - **Videos** — embedded public Vanderlande training/overview videos.
  - **Health** — a simulated live dashboard (throughput, uptime, drive
    temperature, vibration, air pressure, recent events).
- **QR scanning** — tap **Scan QR** to open the camera and jump straight to a
  module. Uses the native `BarcodeDetector` where available, with a `jsQR`
  fallback so it works across browsers.
- **QR labels** — generate and print a QR label for any module from its page.

## Run it locally

Just open `index.html` in a browser — everything (QR generate + scan) is
vendored, so it works offline.

> 📷 **Camera note:** browsers only allow the camera on a **secure context**
> (HTTPS, or `http://localhost`). Opening the file directly (`file://`) shows the
> app but the live scanner may be blocked. Use the hosted URL (below) or a local
> server (`python3 -m http.server`) to test scanning.

## Hosting (GitHub Pages — free)

A workflow is included at `.github/workflows/deploy.yml`.

1. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push to `main` (or this feature branch) — the site deploys automatically.
3. Your site URL appears in the workflow run and on the Pages settings screen,
   e.g. `https://<owner>.github.io/<repo>/`.

Because Pages serves over HTTPS, the camera scanner works there.

## Project structure

```
index.html          App shell (markup only)
assets/
  styles.css        Styling (clean iOS/Material blend, light + dark)
  app.js            Routing, rendering, live health, QR generate + scan
  data.js           Module content map  <- add/edit modules here
vendor/
  qrcode.js         QR generator (qrcode-generator, MIT)
  jsQR.js           QR decoder for the camera (jsQR, MIT)
```

## Add or edit a module

Everything is driven by `assets/data.js`. Add an entry to `MODULES` and it
appears in the directory, becomes scannable, and gets a printable QR label
automatically. In-app reference guides live in `GUIDES`.

## Roadmap

- Replace public guides/placeholders with controlled PDFs (internal hosting).
- Connect the Health tab to a real PLC/SCADA/maintenance data feed.
- Bulk QR-label generation for a whole site.
- Optional: offline PWA install, authentication, multi-language.
