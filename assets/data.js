/* =============================================================================
   Module Hub — content map
   -----------------------------------------------------------------------------
   All content below is built from PUBLIC information only (Vanderlande website,
   product pages, trade press and public YouTube). No restricted/internal
   documentation is included. Replace the placeholder PDF links and the public
   summaries with controlled documents when the app runs on the internal network.

   Add a module here -> it works everywhere (directory, scanning, QR label).
   ========================================================================== */

const SITE = {
  name: "Vanderlande Module Hub",
  subtitle: "Site operations — manuals, video & live health",
  // Demo site. Rename freely.
  location: "Demo Distribution Centre",
};

/* Shared, reusable public reference content (rendered in the in-app reader).
   Marked clearly as public so nobody mistakes it for the controlled manual. */
const PUBLIC_NOTE =
  "Public reference only — sourced from Vanderlande public materials. " +
  "The controlled service manual must be linked here when hosted on the internal network.";

const MODULES = {
  /* ----------------------------- POSISORTER ------------------------------ */
  "POSI-DRV-014": {
    system: "POSISORTER",
    name: "POSISORTER Drive Unit",
    location: "Hall 2 · Sortation Line A · Drive 014",
    status: "operational",
    summary:
      "Main drive station of a POSISORTER sliding-shoe sorter. Positive, " +
      "high-capacity sortation of cartons, totes, trays and bags at over " +
      "10,000 items per hour.",
    specs: {
      "Sorter type": "Sliding-shoe (positive) sorter",
      "Throughput": "> 10,000 items/hour",
      "Sort accuracy": "≈ 1 missort per 10,000 items",
      "Max product size": "1,500 × 900 mm",
      "Handles": "Cartons, totes, trays, bags",
      "Sortation": "Single- or dual-sided",
    },
    resources: [
      { type: "guide", title: "POSISORTER — overview & operating principle",
        sub: "Public reference · how the sorter works", key: "posi_overview" },
      { type: "guide", title: "Shoe replacement (plug-and-play carrier)",
        sub: "Public reference · ~60 s per shoe", key: "posi_shoe" },
      { type: "pdf", title: "Drive Unit Maintenance Manual",
        sub: "Controlled document — link on internal network", url: "#" },
      { type: "pdf", title: "Lubrication & chain tension schedule",
        sub: "Controlled document — link on internal network", url: "#" },
    ],
    videos: [
      { title: "Vanderlande POSISORTER", id: "YXuxRv06C_c", sub: "Product overview" },
      { title: "POSISORTER shoe replacement", id: "oRTRjaXLxq0", sub: "Maintenance demo" },
    ],
    health: { temp: 47, tempMax: 75, throughput: 9200, tpMax: 10000,
              vibration: 2.1, pressure: null, baseUptime: 99.4, pneumatic: false },
  },

  "POSI-CAR-031": {
    system: "POSISORTER",
    name: "POSISORTER Slat & Shoe Carrier Bed",
    location: "Hall 2 · Sortation Line A · Carrier 031",
    status: "attention",
    summary:
      "Full-width carrier bed where divert shoes slide diagonally across the " +
      "slats to push product gently into the outfeed spurs. Patented " +
      "plug-and-play carriers allow a shoe to be changed in under 60 seconds.",
    specs: {
      "Carrier": "Full-width slat carrier",
      "Divert action": "Diagonal shoe slide",
      "Shoe change": "< 60 s (plug-and-play)",
      "Energy": "≈ 20% more efficient vs. traditional",
      "Noise": "≈ 3 dB lower",
    },
    resources: [
      { type: "guide", title: "Shoe replacement (plug-and-play carrier)",
        sub: "Public reference · ~60 s per shoe", key: "posi_shoe" },
      { type: "guide", title: "Slat & shoe inspection — what to check",
        sub: "Public reference · wear & alignment", key: "posi_slat" },
      { type: "pdf", title: "Carrier Bed Service Guide",
        sub: "Controlled document — link on internal network", url: "#" },
      { type: "pdf", title: "Fault code reference",
        sub: "Controlled document — link on internal network", url: "#" },
    ],
    videos: [
      { title: "Shoe Sorter — POSISORTER", id: "HrdZsPUkCjQ", sub: "Operating principle" },
      { title: "POSISORTER shoe replacement", id: "oRTRjaXLxq0", sub: "Maintenance demo" },
    ],
    health: { temp: 58, tempMax: 75, throughput: 8600, tpMax: 10000,
              vibration: 4.8, pressure: null, baseUptime: 97.1, pneumatic: false },
  },

  "POSI-DIV-052": {
    system: "POSISORTER",
    name: "POSISORTER Divert / Outfeed Spur",
    location: "Hall 2 · Sortation Line A · Spur 052",
    status: "operational",
    summary:
      "Outfeed spur where sorted product leaves the main line. Divert switches " +
      "may be electric or pneumatic; rubber isolators keep operation quiet and " +
      "maintenance simple.",
    specs: {
      "Divert switch": "Electric / pneumatic",
      "Isolators": "Rubber (quiet running)",
      "Product flow": "Diagonal divert to spur",
      "Max product size": "1,500 × 900 mm",
    },
    resources: [
      { type: "guide", title: "POSISORTER — overview & operating principle",
        sub: "Public reference · how the sorter works", key: "posi_overview" },
      { type: "pdf", title: "Divert Mechanism Service Guide",
        sub: "Controlled document — link on internal network", url: "#" },
      { type: "pdf", title: "Pneumatic system check (if fitted)",
        sub: "Controlled document — link on internal network", url: "#" },
    ],
    videos: [
      { title: "Vanderlande POSISORTER", id: "YXuxRv06C_c", sub: "Product overview" },
    ],
    health: { temp: 41, tempMax: 75, throughput: 9000, tpMax: 10000,
              vibration: 1.7, pressure: 6.2, baseUptime: 99.8, pneumatic: true },
  },

  "POSI-INF-003": {
    system: "POSISORTER",
    name: "POSISORTER Infeed & Induction",
    location: "Hall 2 · Sortation Line A · Infeed 003",
    status: "operational",
    summary:
      "Induction zone that gaps, aligns and meters product onto the sorter. " +
      "Photocells and scanners identify each item and pass the data to the " +
      "control system to trigger the correct divert.",
    specs: {
      "Function": "Gapping, alignment, induction",
      "Identification": "Photocells + barcode scanning",
      "Feeds": "POSISORTER main line",
      "Handles": "Cartons, totes, trays, bags",
    },
    resources: [
      { type: "guide", title: "POSISORTER — overview & operating principle",
        sub: "Public reference · how the sorter works", key: "posi_overview" },
      { type: "guide", title: "Photocell & scanner — what to check",
        sub: "Public reference · alignment & cleaning", key: "scan_check" },
      { type: "pdf", title: "Induction & Scanning Service Guide",
        sub: "Controlled document — link on internal network", url: "#" },
    ],
    videos: [
      { title: "Line sorter — unboxing insights", id: "vDqDHQNLFSI", sub: "How line sorting works" },
    ],
    health: { temp: 39, tempMax: 70, throughput: 9300, tpMax: 10000,
              vibration: 1.2, pressure: null, baseUptime: 99.9, pneumatic: false },
  },

  /* -------------------------------- SPOX --------------------------------- */
  "SPOX-SRT-007": {
    system: "SPOX",
    name: "SPOX Line Sorter Section",
    location: "Hall 4 · Sortation Line B · Section 007",
    status: "operational",
    summary:
      "SPOX next-generation line sorter section. A closed-deck carrier and a " +
      "parallel-sort strategy handle a mixed flow of small and regular parcels " +
      "— from 5 mm-high envelopes and polybags to bulky boxes.",
    specs: {
      "Sorter type": "Line sorter (closed-deck carrier)",
      "Throughput": "up to 10,000 items/hour",
      "Min product height": "5 mm",
      "Handles": "Envelopes, polybags, boxes (mixed flow)",
      "Sort strategy": "Parallel sort, dynamic shoe placement",
      "Outfeeds": "Single-file, buffer slide, direct drop",
    },
    resources: [
      { type: "guide", title: "SPOX — overview & what's new",
        sub: "Public reference · closed-deck, parallel sort", key: "spox_overview" },
      { type: "guide", title: "Dynamic shoe placement explained",
        sub: "Public reference · drift-free, slip-free handling", key: "spox_shoe" },
      { type: "pdf", title: "SPOX Section Service Manual",
        sub: "Controlled document — link on internal network", url: "#" },
    ],
    videos: [
      { title: "Sorting Insight 4: SPOX", id: "Ccd_TpI861g", sub: "High capacity, same footprint" },
      { title: "Line sorter — unboxing insights", id: "vDqDHQNLFSI", sub: "How line sorting works" },
    ],
    health: { temp: 44, tempMax: 75, throughput: 9600, tpMax: 10000,
              vibration: 1.9, pressure: null, baseUptime: 99.6, pneumatic: false },
  },

  "SPOX-CAR-018": {
    system: "SPOX",
    name: "SPOX Intelligent Carrier",
    location: "Hall 4 · Sortation Line B · Carrier 018",
    status: "attention",
    summary:
      "Intelligent SPOX carrier that monitors its own health. Worn components " +
      "are designed to be refurbished and reintegrated into the system, " +
      "reducing waste and total cost of ownership.",
    specs: {
      "Carrier": "Closed-deck, self-monitoring",
      "Health data": "On-board condition monitoring",
      "Sustainability": "Refurbish & reintegrate components",
      "Benefit": "No parcel drift, slip-free heavy items",
    },
    resources: [
      { type: "guide", title: "SPOX — overview & what's new",
        sub: "Public reference · closed-deck, parallel sort", key: "spox_overview" },
      { type: "guide", title: "Dynamic shoe placement explained",
        sub: "Public reference · drift-free, slip-free handling", key: "spox_shoe" },
      { type: "pdf", title: "Carrier Refurbishment Procedure",
        sub: "Controlled document — link on internal network", url: "#" },
    ],
    videos: [
      { title: "Sorting Insight 4: SPOX", id: "Ccd_TpI861g", sub: "High capacity, same footprint" },
    ],
    health: { temp: 61, tempMax: 75, throughput: 8800, tpMax: 10000,
              vibration: 5.3, pressure: null, baseUptime: 96.4, pneumatic: false },
  },
};

/* In-app reader content for the "guide" resources (public references). */
const GUIDES = {
  posi_overview: {
    title: "POSISORTER — overview & operating principle",
    note: PUBLIC_NOTE,
    body: [
      ["h", "What it is"],
      ["p", "The POSISORTER is a sliding-shoe (positive) sorter that combines high-capacity conveyance with careful product handling. Divert shoes slide across the full-width carriers, pushing each parcel gently into the output spur in a diagonal movement."],
      ["h", "Key figures"],
      ["ul", [
        "Throughput of more than 10,000 items per hour",
        "Sort accuracy of about one missort per 10,000 items",
        "Handles products up to 1,500 × 900 mm",
        "Suitable for cartons, totes, trays and bags",
        "Available single- or dual-sided",
      ]],
      ["h", "Why operators like it"],
      ["ul", [
        "Patented plug-and-play carrier — a shoe can be changed in under 60 seconds",
        "About 20% more energy efficient than traditional sorting methods",
        "Around 3 dB quieter in operation",
      ]],
    ],
  },
  posi_shoe: {
    title: "Shoe replacement (plug-and-play carrier)",
    note: PUBLIC_NOTE,
    body: [
      ["p", "POSISORTER uses a patented plug-and-play carrier design so a worn or damaged divert shoe can be replaced in less than 60 seconds, minimising downtime."],
      ["h", "General principle (public)"],
      ["ul", [
        "Isolate and lock out the sorter before any work on the carrier bed",
        "Locate the carrier with the worn shoe; the plug-and-play design releases without special tools",
        "Fit the replacement shoe and confirm it seats and slides freely",
        "Release lock-out and run a test divert before returning to production",
      ]],
      ["p", "Always follow the controlled lock-out/tag-out and service procedure for the exact steps and torque values."],
    ],
  },
  posi_slat: {
    title: "Slat & shoe inspection — what to check",
    note: PUBLIC_NOTE,
    body: [
      ["p", "The slats form the carrying surface and each carries a sliding shoe. Keeping them clean and correctly aligned keeps diverts accurate and reduces wear."],
      ["ul", [
        "Shoes and slats kept clean and free of debris",
        "No cracked, chipped or excessively worn shoes",
        "Even shoe travel across the slats — no binding",
        "Drive/roller chain tension and lubrication within spec",
        "Listen for unusual noise or vibration during a test run",
      ]],
    ],
  },
  spox_overview: {
    title: "SPOX — overview & what's new",
    note: PUBLIC_NOTE,
    body: [
      ["h", "What it is"],
      ["p", "SPOX is Vanderlande's next-generation line sorter. It handles a mixed flow of small and regular parcels in a single system, from ultra-flat envelopes and polybags down to 5 mm high, up to bulky boxes."],
      ["h", "Key innovations"],
      ["ul", [
        "Closed-deck carrier for improved conveyability",
        "Dynamic shoe placement to eliminate parcel drift",
        "Intelligent carriers that monitor their own health",
        "Parallel-sort strategy — no item rotation or gaps on the conveyor",
        "Greater accuracy and throughput at slower speeds, smaller footprint",
      ]],
      ["h", "Capacity & flexibility"],
      ["ul", [
        "Up to 10,000 items per hour (based on an average parcel size)",
        "Outfeeds can be single-file, buffer slide or direct drop, and adjusted as layouts change",
        "Designed for sustainability — worn components can be refurbished and reintegrated",
      ]],
    ],
  },
  spox_shoe: {
    title: "Dynamic shoe placement explained",
    note: PUBLIC_NOTE,
    body: [
      ["p", "SPOX uses dynamic shoe placement: the number and position of shoes engaging each parcel is adapted to the item. This eliminates parcel drift and gives slip-free handling of heavier items, enabling accurate sorting at lower speeds."],
      ["ul", [
        "Shoes engage where the parcel actually is — no drift",
        "Heavier items handled slip-free",
        "Parallel sorting avoids rotating items or leaving gaps",
      ]],
    ],
  },
  scan_check: {
    title: "Photocell & scanner — what to check",
    note: PUBLIC_NOTE,
    body: [
      ["p", "As an item enters the sorter, sensors and scanners identify it and relay the information to the control system, which triggers the correct divert. Clean, well-aligned sensors are essential for sort accuracy."],
      ["ul", [
        "Photocell lenses clean and free of dust/condensation",
        "Emitter and receiver correctly aligned",
        "Scanner window clean; read-rate within expected range",
        "No loose cabling or connectors at the sensor",
      ]],
    ],
  },
};
