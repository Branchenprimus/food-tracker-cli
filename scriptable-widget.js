// Food Tracker • Scriptable Widget (Large)
// - Fetches JSON from /v1/widget/today (Bearer token optional)
// - Caches last successful response locally
// - If offline, uses cached response and shows a stale indicator
//
// Setup:
// 1) Install Scriptable on iPhone
// 2) Create a new Script and paste this code
// 3) Run once inside Scriptable (not as widget) to configure HOST/TOKEN
// 4) Add Scriptable widget (Large) and select this script
//
// Notes:
// - iOS controls refresh frequency. You can manually refresh by running the script.

//////////////////////////////
// USER CONFIG (edit here)
//////////////////////////////
const CONFIG = {
  // If true, read HOST/TOKEN from Keychain; otherwise use values below.
  useKeychain: true,

  // Used only when useKeychain=false:
  host: "http://192.168.178.38:8787",
  token: "",

  // Targets (edit to your goals)
  targets: {
    kcal: 2500,
    protein_g: 160,
    carbs_g: 260,
    fat_g: 80,
  },

  // Networking
  timeoutSeconds: 3,

  // Local cache file name
  cacheFile: "foodtracker_widget_today_cache.json",

  // Theme
  darkBackground: new Color("#111315"),
  cardBackground: new Color("#171A1E"),

  // Progress colors (bars)
  colors: {
    kcal: new Color("#F2C94C"),
    protein: new Color("#4F7DFF"), // blue/indigo
    carbs: new Color("#2DD4BF"),   // green/teal
    fat: new Color("#F97316"),     // orange/red
    mutedText: new Color("#8C93A1"),
    text: new Color("#E9EEF7"),
    stale: new Color("#9CA3AF"),
    divider: new Color("#2A2F38"),
  },

  // Sizing
  padding: 14,
  bar: {
    width: 300,   // will be scaled by device; used as draw width
    height: 10,
    radius: 5,
  },
};

//////////////////////////////
// KEYCHAIN KEYS
//////////////////////////////
const KC_HOST = "foodtracker_widget_host";
const KC_TOKEN = "foodtracker_widget_token";

//////////////////////////////
// MAIN
//////////////////////////////
const { data, isStale, usedCache } = await fetchDataWithFallback();
const widget = await buildWidget(data, { isStale, usedCache });

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  // Preview in-app
  await widget.presentLarge();
}
Script.complete();

//////////////////////////////
// HELPERS
//////////////////////////////

function clamp01(x) {
  if (x < 0) return 0;
  if (x > 1) return 1;
  return x;
}

function fmtInt(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
  return Math.round(Number(n)).toString();
}

function fmt1(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
  const x = Number(n);
  const rounded = Math.round(x * 10) / 10;
  return (Math.abs(rounded - Math.round(rounded)) < 1e-9) ? Math.round(rounded).toString() : rounded.toString();
}

function isoDateToDisplay(isoDate) {
  // isoDate: YYYY-MM-DD
  if (!isoDate || typeof isoDate !== "string") return "Today";
  const parts = isoDate.split("-");
  if (parts.length !== 3) return isoDate;
  const [y, m, d] = parts.map((p) => Number(p));
  const dt = new Date(Date.UTC(y, m - 1, d));
  // Localized short date
  return dt.toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "2-digit" });
}

function nowISO() {
  return new Date().toISOString();
}

function getFileManager() {
  return FileManager.local();
}

function cachePath() {
  const fm = getFileManager();
  return fm.joinPath(fm.documentsDirectory(), CONFIG.cacheFile);
}

async function readCacheFile() {
  const fm = getFileManager();
  const p = cachePath();
  if (!fm.fileExists(p)) return null;
  try {
    const raw = fm.readString(p);
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

async function writeCacheFile(obj) {
  const fm = getFileManager();
  const p = cachePath();
  try {
    fm.writeString(p, JSON.stringify(obj));
  } catch (e) {
    // ignore write failures
  }
}

function getHostAndToken() {
  let host = CONFIG.host;
  let token = CONFIG.token;

  if (CONFIG.useKeychain) {
    if (Keychain.contains(KC_HOST)) host = Keychain.get(KC_HOST);
    if (Keychain.contains(KC_TOKEN)) token = Keychain.get(KC_TOKEN);
  }

  return { host, token };
}

async function maybeSetupKeychainIfMissing() {
  if (!CONFIG.useKeychain) return;

  const hasHost = Keychain.contains(KC_HOST);
  const hasToken = Keychain.contains(KC_TOKEN);

  if (hasHost && hasToken) return;

  // Only prompt when run in app (not in widget)
  if (config.runsInWidget) return;

  const a = new Alert();
  a.title = "Food Tracker Widget Setup";
  a.message =
    "Host/TOKEN not found in Keychain.\n\n" +
    "Press Setup to enter:\n" +
    "- HOST (e.g. http://192.168.178.38:8787)\n" +
    "- TOKEN (optional)\n\n" +
    "You can rerun this script later to update.";
  a.addAction("Setup");
  a.addCancelAction("Cancel");

  const r = await a.present();
  if (r === -1) return;

  const a2 = new Alert();
  a2.title = "Enter HOST";
  a2.addTextField("HOST", "http://192.168.178.38:8787");
  a2.addAction("Next");
  await a2.present();
  const host = a2.textFieldValue(0).trim();

  const a3 = new Alert();
  a3.title = "Enter TOKEN (optional)";
  a3.addTextField("TOKEN", "");
  a3.addAction("Save");
  await a3.present();
  const token = a3.textFieldValue(0).trim();

  if (host) Keychain.set(KC_HOST, host);
  Keychain.set(KC_TOKEN, token);

  const ok = new Alert();
  ok.title = "Saved";
  ok.message = "Host/TOKEN saved to Keychain.";
  ok.addAction("OK");
  await ok.present();
}

async function fetchDataWithFallback() {
  await maybeSetupKeychainIfMissing();

  const { host, token } = getHostAndToken();
  const url = `${host.replace(/\/$/, "")}/v1/widget/today`;

  // Try network first
  try {
    const req = new Request(url);
    req.method = "GET";
    req.timeoutInterval = CONFIG.timeoutSeconds;

    if (token && token.length > 0) {
      req.headers = { Authorization: `Bearer ${token}` };
    }

    const json = await req.loadJSON();

    // Basic validation
    if (!json || !json.day || typeof json.day.total_kcal === "undefined") {
      throw new Error("Invalid JSON structure");
    }

    // Write cache with a fetched timestamp (separate from generated_at)
    const cachedObj = {
      fetched_at: nowISO(),
      source_url: url,
      payload: json,
    };
    await writeCacheFile(cachedObj);

    return { data: json, isStale: false, usedCache: false };
  } catch (e) {
    // Network failed: try cache
    const cached = await readCacheFile();
    if (cached && cached.payload) {
      // mark stale; include fetched_at for display
      const stalePayload = cached.payload;
      stalePayload.__stale = true;
      stalePayload.__cached_fetched_at = cached.fetched_at || null;
      return { data: stalePayload, isStale: true, usedCache: true };
    }

    // No cache available: show empty widget with error
    const fallback = {
      generated_at: null,
      timezone: "Europe/Berlin",
      day: {
        date: null,
        total_kcal: 0,
        total_protein: 0,
        total_carbs: 0,
        total_fat: 0,
        entry_count: 0,
      },
      week: { total_kcal: 0, days_tracked: 0 },
      streak: 0,
      __error: "No data (offline and no cache)",
      __stale: true,
      __cached_fetched_at: null,
    };
    return { data: fallback, isStale: true, usedCache: false };
  }
}

function createProgress(width, height, percent, fillColor, bgColor, radius) {
  const p = clamp01(percent);

  const dc = new DrawContext();
  dc.opaque = false;
  dc.respectScreenScale = true;
  dc.size = new Size(width, height);

  const r = radius ?? Math.floor(height / 2);

  // Background track
  const trackRect = new Rect(0, 0, width, height);
  dc.setFillColor(bgColor);
  dc.fillRoundedRect(trackRect, r, r);

  // Fill
  const fillW = Math.max(0, Math.floor(width * p));
  if (fillW > 0) {
    const fillRect = new Rect(0, 0, fillW, height);
    dc.setFillColor(fillColor);
    dc.fillRoundedRect(fillRect, r, r);
  }

  return dc.getImage();
}

function addDivider(w) {
  const line = w.addStack();
  line.size = new Size(0, 1);
  line.backgroundColor = CONFIG.colors.divider;
  w.addSpacer(10);
}

async function buildWidget(data, meta) {
  const w = new ListWidget();
  w.backgroundColor = CONFIG.darkBackground;
  w.setPadding(CONFIG.padding, CONFIG.padding, CONFIG.padding, CONFIG.padding);

  // If you want a subtle card background feel, wrap everything in a stack
  const card = w.addStack();
  card.layoutVertically();
  card.backgroundColor = CONFIG.cardBackground;
  card.cornerRadius = 16;
  card.setPadding(12, 12, 12, 12);

  // Header row: Today + streak + stale indicator
  const header = card.addStack();
  header.layoutHorizontally();
  header.centerAlignContent();

  const left = header.addStack();
  left.layoutVertically();

  const dateLabel = left.addText("Today");
  dateLabel.font = Font.systemFont(12);
  dateLabel.textColor = CONFIG.colors.mutedText;

  const dateText = left.addText(isoDateToDisplay(data.day?.date));
  dateText.font = Font.semiboldSystemFont(16);
  dateText.textColor = CONFIG.colors.text;

  header.addSpacer();

  const right = header.addStack();
  right.layoutVertically();
  right.rightAlignContent();

  const streak = Number(data.streak ?? 0);
  const streakText = right.addText(`🔥 ${fmtInt(streak)}`);
  streakText.font = Font.semiboldSystemFont(14);
  streakText.textColor = CONFIG.colors.text;

  // Stale indicator
  if (meta.isStale) {
    const staleRow = right.addStack();
    staleRow.layoutHorizontally();
    staleRow.rightAlignContent();

    const warn = staleRow.addText("⚠︎ stale");
    warn.font = Font.boldSystemFont(11);
    warn.textColor = CONFIG.colors.stale;
  }

  card.addSpacer(12);

  // Calories big
  const kcalValue = Number(data.day?.total_kcal ?? 0);
  const kcalTarget = Number(CONFIG.targets.kcal ?? 2500);
  const kcalPct = kcalTarget > 0 ? (kcalValue / kcalTarget) : 0;

  const kcalRow = card.addStack();
  kcalRow.layoutHorizontally();
  kcalRow.centerAlignContent();

  const kcalLeft = kcalRow.addStack();
  kcalLeft.layoutVertically();

  const kcalLabel = kcalLeft.addText("Calories");
  kcalLabel.font = Font.systemFont(12);
  kcalLabel.textColor = CONFIG.colors.mutedText;

  const kcalBig = kcalLeft.addText(`${fmtInt(kcalValue)}`);
  kcalBig.font = Font.boldSystemFont(34);
  kcalBig.textColor = CONFIG.colors.text;

  const kcalSub = kcalLeft.addText(`${fmtInt(kcalTarget)} target • ${fmtInt(data.day?.entry_count ?? 0)} entries`);
  kcalSub.font = Font.systemFont(11);
  kcalSub.textColor = CONFIG.colors.mutedText;

  kcalRow.addSpacer();

  // Optional: show percent
  const pctBox = kcalRow.addStack();
  pctBox.layoutVertically();
  pctBox.rightAlignContent();
  const pctText = pctBox.addText(`${fmtInt(clamp01(kcalPct) * 100)}%`);
  pctText.font = Font.semiboldSystemFont(14);
  pctText.textColor = CONFIG.colors.text;

  card.addSpacer(8);

  // Calories progress bar
  const kcalBarImg = createProgress(
    CONFIG.bar.width,
    CONFIG.bar.height,
    kcalPct,
    CONFIG.colors.kcal,
    new Color("#0B0D10"),
    CONFIG.bar.radius
  );
  const kcalBar = card.addImage(kcalBarImg);
  kcalBar.imageSize = new Size(0, CONFIG.bar.height); // auto width
  kcalBar.resizable = true;

  card.addSpacer(14);

  // Macros section title
  const macroTitleRow = card.addStack();
  macroTitleRow.layoutHorizontally();
  const macroTitle = macroTitleRow.addText("Macros");
  macroTitle.font = Font.semiboldSystemFont(12);
  macroTitle.textColor = CONFIG.colors.mutedText;

  macroTitleRow.addSpacer();

  // Week + streak small info
  const weekInfo = macroTitleRow.addText(`Week: ${fmtInt(data.week?.total_kcal ?? 0)} kcal • ${fmtInt(data.week?.days_tracked ?? 0)} days`);
  weekInfo.font = Font.systemFont(11);
  weekInfo.textColor = CONFIG.colors.mutedText;

  card.addSpacer(10);

  // Macro rows
  const macros = [
    {
      key: "total_protein",
      label: "Protein",
      value: Number(data.day?.total_protein ?? 0),
      target: Number(CONFIG.targets.protein_g ?? 0),
      color: CONFIG.colors.protein,
    },
    {
      key: "total_carbs",
      label: "Carbs",
      value: Number(data.day?.total_carbs ?? 0),
      target: Number(CONFIG.targets.carbs_g ?? 0),
      color: CONFIG.colors.carbs,
    },
    {
      key: "total_fat",
      label: "Fat",
      value: Number(data.day?.total_fat ?? 0),
      target: Number(CONFIG.targets.fat_g ?? 0),
      color: CONFIG.colors.fat,
    },
  ];

  for (let i = 0; i < macros.length; i++) {
    const m = macros[i];
    const pct = m.target > 0 ? (m.value / m.target) : 0;

    const row = card.addStack();
    row.layoutHorizontally();
    row.centerAlignContent();

    const leftCol = row.addStack();
    leftCol.layoutVertically();
    leftCol.size = new Size(0, 0);

    const lbl = leftCol.addText(m.label);
    lbl.font = Font.systemFont(13);
    lbl.textColor = CONFIG.colors.text;

    const val = leftCol.addText(`${fmt1(m.value)}g / ${fmt1(m.target)}g`);
    val.font = Font.systemFont(11);
    val.textColor = CONFIG.colors.mutedText;

    row.addSpacer();

    // Progress bar (smaller)
    const barW = 140;
    const barH = 8;

    const barImg = createProgress(
      barW,
      barH,
      pct,
      m.color,
      new Color("#0B0D10"),
      Math.floor(barH / 2)
    );
    const img = row.addImage(barImg);
    img.imageSize = new Size(barW, barH);
    img.resizable = false;

    card.addSpacer(10);
  }

  // Footer (only if stale / error)
  if (meta.isStale) {
    card.addSpacer(6);

    const foot = card.addStack();
    foot.layoutHorizontally();

    const staleText = data.__cached_fetched_at
      ? `Using cached data • fetched ${new Date(data.__cached_fetched_at).toLocaleTimeString()}`
      : "Using cached data";
    const t = foot.addText(staleText);
    t.font = Font.italicSystemFont(10);
    t.textColor = CONFIG.colors.stale;

    foot.addSpacer();
  }

  if (data.__error) {
    card.addSpacer(6);
    const err = card.addText(String(data.__error));
    err.font = Font.italicSystemFont(10);
    err.textColor = CONFIG.colors.stale;
  }

  // Dim the entire widget if stale (subtle)
  if (meta.isStale) {
    // Scriptable doesn’t support opacity on widget background directly,
    // so we just mute the card background slightly by overlaying a darker color.
    card.backgroundColor = new Color("#14161A");
  }

  // Deep link on tap (optional): open your API URL
  // w.url = `${getHostAndToken().host.replace(/\/$/, "")}/v1/widget/today`;

  return w;
}
