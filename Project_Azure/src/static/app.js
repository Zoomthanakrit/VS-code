// Match Story - replays a synthetic match with live stats and personalized, fact-checked AI cards.

const $ = (id) => document.getElementById(id);
const SVG = "http://www.w3.org/2000/svg";
const END_T = 91 * 60;

const TEXT = {
  en: { speed: "Speed", legend: "dots = players · line = pass · circle = shot · ⚡ = sprint over 32 km/h", feed: "Story so far",
        playersTitle: "Player stats so far", physicalNote: "Distance, sprints and top speed are synthetic tracking data.",
        cols: ["#", "Player", "Pos", "Passes", "Pass %", "Shots", "Goals", "xG", "Ball wins", "Pressures", "Km", "Sprints", "Top km/h"],
        replayLive: "Replay a moment", replayFull: "Full time: replay the key moments", replayBanner: "REPLAY",
        thinking: "AI commentator is writing…", recap: "Match recap", you: "Your view", mode: "Mode",
        language: "Language", team: "Favorite team", player: "Favorite player", focus: "Focus", stats: "Match stats",
        momentum: "Momentum (xG per 15 min)", playercard: "Player card", passes: "Passes", shots: "Shots",
        goals: "Goals", pressures: "Pressures", foryou: "★ For you", checked: "fact-checked", headlineOnly: "headline only",
        none: "None", zones: "Zones", wholeMatch: "Whole match", last10: "Last 10 min", off: "Off",
        pulse: "Match Pulse", pulseSub: "last 5 minutes", control: "Control (who keeps the ball)",
        chaos: "Chaos (how often the ball changes teams)", inControl: "in control", balanced: "Balanced",
        calm: "Calm", normal: "Normal", chaotic: "Chaotic", ballChanges: "changes of possession",
        agents: "AI agent team (live)", agentEmpty: "Press ▶ to watch the agents work.",
        askTitle: "Ask the Match", askBtn: "Ask", askPlaceholder: "Ask anything about this match…",
        askThinking: "The Q&A agent is looking up the stats…", askLooked: "Looked up", askNoTools: "no tools used",
        askFail: "Sorry, something went wrong. Please try again.",
        askChips: ["Who is in control right now?", "How is Ali Demir playing?", "Which team creates better chances?",
                   "What changed in the last 10 minutes?"],
        thirds: "Where each team plays (passes by third)", defend: "Defend", middle: "Middle", attack: "Attack",
        zoneNames: ["1st third", "2nd third", "3rd third"], attacks: "attacks",
        statLabels: { possession_pct: "Possession %", shots: "Shots", shots_on_target: "On target", xg: "xG",
                      pass_accuracy_pct: "Pass accuracy %", pressures: "Pressures", tackles_won: "Tackles won" },
        kinds: { goal: "Goal", big_chance_missed: "Big chance", great_save: "Great save", yellow_card: "Yellow card",
                 pressing_spell: "Pressing", momentum_swing: "Momentum", fastest_shot: "Fastest shot" } },
  th: { speed: "ความเร็ว", legend: "จุด = นักเตะ · เส้น = ส่งบอล · วงกลม = ยิง · ⚡ = สปรินต์เกิน 32 กม./ชม.", feed: "เรื่องราวของเกม",
        playersTitle: "สถิตินักเตะจนถึงตอนนี้", physicalNote: "ระยะวิ่ง สปรินต์ และความเร็วสูงสุด เป็นข้อมูลติดตามแบบจำลอง",
        cols: ["#", "นักเตะ", "ตำแหน่ง", "ส่งบอล", "สำเร็จ %", "ยิง", "ประตู", "xG", "แย่งบอล", "เพรส", "กม.", "สปรินต์", "เร็วสุด"],
        replayLive: "ดูรีเพลย์", replayFull: "จบเกม: ดูรีเพลย์จังหวะสำคัญ", replayBanner: "รีเพลย์",
        thinking: "AI กำลังเขียนบทบรรยาย…", recap: "สรุปเกม", you: "มุมมองของคุณ", mode: "โหมด",
        language: "ภาษา", team: "ทีมโปรด", player: "นักเตะคนโปรด", focus: "สนใจเรื่อง", stats: "สถิติการแข่งขัน",
        momentum: "โมเมนตัม (xG ทุก 15 นาที)", playercard: "การ์ดนักเตะ", passes: "ส่งบอล", shots: "ยิง",
        goals: "ประตู", pressures: "เพรส", foryou: "★ สำหรับคุณ", checked: "ตรวจสอบตัวเลขแล้ว", headlineOnly: "หัวข้อเท่านั้น",
        none: "ไม่มี", zones: "โซน", wholeMatch: "ทั้งเกม", last10: "10 นาทีล่าสุด", off: "ปิด",
        pulse: "ชีพจรเกม", pulseSub: "5 นาทีล่าสุด", control: "การควบคุมเกม (ใครครองบอลได้)",
        chaos: "ความวุ่นวาย (บอลเปลี่ยนฝั่งบ่อยแค่ไหน)", inControl: "คุมเกม", balanced: "สูสี",
        calm: "นิ่ง", normal: "ปกติ", chaotic: "วุ่นวาย", ballChanges: "ครั้งที่เปลี่ยนการครองบอล",
        agents: "ทีมเอเจนต์ AI (สด)", agentEmpty: "กด ▶ เพื่อดูเอเจนต์ทำงาน",
        askTitle: "ถามเกมนี้", askBtn: "ถาม", askPlaceholder: "ถามอะไรก็ได้เกี่ยวกับเกมนี้…",
        askThinking: "เอเจนต์ถาม-ตอบกำลังค้นสถิติ…", askLooked: "ค้นข้อมูลจาก", askNoTools: "ไม่ได้ใช้เครื่องมือ",
        askFail: "ขออภัย เกิดข้อผิดพลาด กรุณาลองใหม่",
        askChips: ["ตอนนี้ทีมไหนคุมเกม?", "Ali Demir เล่นเป็นยังไงบ้าง?", "ทีมไหนสร้างโอกาสได้ดีกว่า?",
                   "10 นาทีล่าสุดมีอะไรเปลี่ยนไป?"],
        thirds: "แต่ละทีมเล่นโซนไหน (ส่งบอลแยกตามโซน)", defend: "แดนรับ", middle: "แดนกลาง", attack: "แดนรุก",
        zoneNames: ["โซน 1", "โซน 2", "โซน 3"], attacks: "บุก",
        statLabels: { possession_pct: "ครองบอล %", shots: "ยิง", shots_on_target: "ยิงตรงกรอบ", xg: "xG",
                      pass_accuracy_pct: "ส่งบอลสำเร็จ %", pressures: "เพรส", tackles_won: "แย่งบอลสำเร็จ" },
        kinds: { goal: "ประตู", big_chance_missed: "โอกาสทอง", great_save: "เซฟสวย", yellow_card: "ใบเหลือง",
                 pressing_spell: "เพรสหนัก", momentum_swing: "โมเมนตัม", fastest_shot: "ยิงแรงสุด" } },
};

const S = {
  t: 0, playing: false, speed: 18, match: null, events: [], overlays: new Map(), shown: new Set(),
  physical: [], playerStats: [], tableSide: "home", sortCol: 10, sortDesc: true, replay: null,
  queue: [], cardTimer: null, lastMinute: -1, loadingOverlays: false, overlaysFor: -1, profileVersion: 0,
};

const key = (o) => `${o.t}|${o.kind}|${o.player || o.team}`;
const fmt = (t) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
const T = () => TEXT[$("lang").value] || TEXT.en;
const sideOf = (team) => (team === S.match.away_team ? "away" : "home");

function profileQuery() {
  const p = new URLSearchParams({ mode: $("mode").value, lang: $("lang").value });
  if ($("team").value) p.set("team", $("team").value);
  if ($("player").value) p.set("player", $("player").value);
  if ($("focus").value) p.set("focus", $("focus").value);
  return p;
}

// ---------- Start ----------
async function start() {
  S.match = await (await fetch("/api/match")).json();
  S.events = (await (await fetch("/api/events")).json()).map((e) => ({ ...e, t: e.minute * 60 + e.second }));
  S.physical = await (await fetch("/api/physical")).json();
  $("aiStatus").textContent = `· AI ${S.match.ai}`;
  buildPlayers();
  $("tabHome").textContent = S.match.home_team;
  $("tabAway").textContent = S.match.away_team;
  $("tabHome").onclick = () => { S.tableSide = "home"; renderPlayerTable(); };
  $("tabAway").onclick = () => { S.tableSide = "away"; renderPlayerTable(); };
  for (const id of ["homeName", "legHome"]) $(id).textContent = S.match.home_team;
  for (const id of ["awayName", "legAway"]) $(id).textContent = S.match.away_team;
  fillPickers();
  applyLanguage();

  $("playBtn").onclick = () => { S.playing = !S.playing; $("playBtn").textContent = S.playing ? "⏸" : "▶"; };
  $("speed").onchange = (e) => { if (!S.replay) S.speed = Number(e.target.value); };
  $("slider").oninput = (e) => seek(Number(e.target.value));
  $("zoneMode").onchange = () => renderZones(S.zones);
  $("askForm").onsubmit = (e) => { e.preventDefault(); askQuestion(); };
  for (const id of ["mode", "lang", "team", "player", "focus"]) $(id).onchange = profileChanged;

  setInterval(tick, 100);
  update();
}

function fillPickers() {
  const team = $("team"), player = $("player");
  team.innerHTML = player.innerHTML = "";
  team.add(new Option("—", ""));
  team.add(new Option(S.match.home_team, S.match.home_team));
  team.add(new Option(S.match.away_team, S.match.away_team));
  player.add(new Option("—", ""));
  for (const [side, name] of [["home", S.match.home_team], ["away", S.match.away_team]]) {
    const group = document.createElement("optgroup");
    group.label = name;
    for (const p of S.match.lineups[side]) group.append(new Option(`${p.number}. ${p.name} (${p.position})`, p.name));
    player.append(group);
  }
}

function applyLanguage() {
  const tx = T();
  document.documentElement.lang = $("lang").value;
  document.querySelectorAll("[data-i18n]").forEach((el) => { if (tx[el.dataset.i18n]) el.textContent = tx[el.dataset.i18n]; });
  $("cardForYou").textContent = tx.foryou;
  $("askInput").placeholder = tx.askPlaceholder;
  const chips = $("askChips");
  chips.innerHTML = "";
  for (const q of tx.askChips) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.textContent = q;
    b.onclick = () => { $("askInput").value = q; askQuestion(); };
    chips.append(b);
  }
}

// ---------- Ask the Match (Q&A agent) ----------
async function askQuestion() {
  const tx = T();
  const question = $("askInput").value.trim();
  if (!question) return;
  const minute = S.t >= 90 * 60 ? 999 : Math.floor(S.t / 60) + 1;
  $("askAnswer").classList.remove("hidden");
  $("askQ").textContent = `“${question}”  ·  ${fmt(S.t)}`;
  $("askA").textContent = tx.askThinking;
  $("askCheck").textContent = "";
  $("askCheck").classList.remove("ok");
  $("askTools").textContent = "";
  $("askBtn").disabled = true;
  try {
    const res = await fetch("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, minute, mode: $("mode").value, lang: $("lang").value }),
    });
    const r = await res.json();
    if (!res.ok) throw new Error(r.detail || res.status);
    $("askA").textContent = r.answer;
    $("askCheck").textContent = r.grounded ? tx.checked : tx.headlineOnly;
    $("askCheck").classList.toggle("ok", r.grounded);
    const tools = [...new Set(r.tools.map((x) => x.tool.replaceAll("_", " ")))];
    $("askTools").textContent = `  ${tx.askLooked}: ${tools.length ? tools.join(", ") : tx.askNoTools}` +
      (r.cached ? "" : ` · ${r.seconds} s`);
    S.qaLog = S.qaLog || [];
    S.qaLog.push({ t: S.t, agent: "qa",
      text: `Answered "${question}" using ${tools.length ? tools.join(", ") : "no tools"}${r.cached ? " (from cache)" : ` in ${r.seconds} s`}` });
    S.qaLog.push({ t: S.t, agent: "factchecker", ok: r.grounded,
      text: r.grounded ? `Checked ${r.numbers_checked} number${r.numbers_checked === 1 ? "" : "s"} in the answer: all came from the tools`
                       : "Could not verify the numbers, so the agent refused to guess" });
    S.logCount = -1;
    renderAgentLog();
  } catch (err) {
    console.error(err);
    $("askA").textContent = tx.askFail;
  } finally {
    $("askBtn").disabled = false;
  }
}

// ---------- Clock ----------
function tick() {
  if (!S.playing) return;
  S.t = Math.min(END_T, S.t + S.speed * 0.1);
  if (S.t >= END_T) { S.playing = false; $("playBtn").textContent = "▶"; }
  if (S.replay && S.t >= S.replay.end) finishReplay();
  update();
}

// ---------- Replays ----------
const REPLAY_KINDS = ["goal", "big_chance_missed", "great_save"];

function startReplay(o) {
  if (S.replay) return;
  S.replay = { end: o.t + 10, back: S.t, wasPlaying: S.playing };
  $("replayBanner").textContent = `⟲ ${T().replayBanner} · ${o.show_at}`;
  $("replayBanner").classList.remove("hidden");
  seek(Math.max(0, o.t - 12));
  S.speed = 6; // slow motion
  S.playing = true;
  $("playBtn").textContent = "⏸";
}

function finishReplay() {
  const r = S.replay;
  S.playing = false;
  setTimeout(() => {
    S.replay = null;
    S.speed = Number($("speed").value);
    $("replayBanner").classList.add("hidden");
    seek(r.back);
    S.playing = r.wasPlaying && r.back < END_T;
    $("playBtn").textContent = S.playing ? "⏸" : "▶";
  }, 1500);
}

function renderReplays() {
  const items = [...S.overlays.values()]
    .filter((o) => REPLAY_KINDS.includes(o.kind) && o.t <= (S.replay ? S.replay.back : S.t))
    .sort((a, b) => a.t - b.t);
  const box = $("replays");
  box.classList.toggle("hidden", items.length === 0);
  const tx = T();
  const full = (S.replay ? S.replay.back : S.t) >= 90 * 60;
  box.classList.toggle("full", full);
  $("replaysHead").textContent = full ? tx.replayFull : tx.replayLive;
  const list = $("replayList");
  const sig = items.map(key).join(",") + full + $("lang").value;
  if (list.dataset.sig === sig) return;
  list.dataset.sig = sig;
  list.innerHTML = "";
  for (const o of items) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `replay-btn ${sideOf(o.team)}`;
    b.textContent = `▶ ${o.show_at} ${tx.kinds[o.kind] || o.kind}${o.player ? " · " + o.player : ""}`;
    b.onclick = () => startReplay(o);
    list.append(b);
  }
}

function seek(t) {
  S.t = t;
  S.queue = [];
  hideCard();
  S.shown = new Set([...S.overlays.values()].filter((o) => showT(o) <= t).map(key)); // jump: no pop-ups for the past
  S.logCount = -1;
  renderFeed();
  update();
}

function update() {
  $("clock").textContent = fmt(S.t);
  $("slider").value = Math.floor(S.t);
  drawPitch();
  const minute = Math.floor(S.t / 60);
  if (minute !== S.lastMinute) {
    S.lastMinute = minute;
    loadState(minute);
  }
  loadOverlays(minute);
  queueDueCards();
  renderAgentLog();
  renderReplays();
}

// ---------- Agent team log ----------
const AGENTS = {
  stats: { icon: "🧮", en: "Stats agent", th: "เอเจนต์สถิติ" },
  commentator: { icon: "🎙️", en: "Commentator", th: "ผู้บรรยาย" },
  factchecker: { icon: "✅", en: "Fact-checker", th: "ผู้ตรวจข้อเท็จจริง" },
  director: { icon: "🎬", en: "Director", th: "ผู้กำกับ" },
  qa: { icon: "💬", en: "Q&A agent", th: "เอเจนต์ถาม-ตอบ" },
};

function renderAgentLog() {
  const visible = [...(S.agentLog || []), ...(S.qaLog || [])].filter((l) => l.t <= S.t).sort((a, b) => a.t - b.t);
  if (visible.length === S.logCount) return; // nothing new
  S.logCount = visible.length;
  const lang = $("lang").value;
  const list = $("agentLog");
  list.innerHTML = "";
  for (const l of visible.slice(-10).reverse()) {
    const a = AGENTS[l.agent] || { icon: "•", en: l.agent, th: l.agent };
    const li = document.createElement("li");
    li.className = `log ${l.agent}${l.ok === false ? " bad" : ""}${l.popup === false ? " skip" : ""}`;
    li.innerHTML = `<span class="t"></span><span class="who"></span><span class="what"></span>`;
    li.querySelector(".t").textContent = fmt(l.t);
    li.querySelector(".who").textContent = `${a.icon} ${a[lang] || a.en}`;
    li.querySelector(".what").textContent = l.text;
    list.append(li);
  }
  $("agentEmpty").classList.toggle("hidden", visible.length > 0);
}

// ---------- Stats ----------
async function loadState(minute) {
  const s = await (await fetch(`/api/state?minute=${minute + 1}`)).json();
  if (minute !== S.lastMinute) return; // a newer minute is already loading
  $("score").textContent = `${s.match.score_home} - ${s.match.score_away}`;
  renderStats(s.team_stats);
  renderMomentum(s.timeline);
  S.zones = s.zones;
  renderZones(s.zones);
  renderPulse(s.pulse);
  S.playerStats = s.player_stats || [];
  renderPlayerTable();
}

// ---------- Player stats table (events + synthetic tracking) ----------
function renderPlayerTable() {
  const tx = T();
  $("tabHome").classList.toggle("active", S.tableSide === "home");
  $("tabAway").classList.toggle("active", S.tableSide === "away");
  const minute = Math.floor(S.t / 60);
  const phys = {};
  for (const r of S.physical) {
    if (r.minute > minute) continue;
    const p = (phys[r.player] = phys[r.player] || { m: 0, sprints: 0, top: 0 });
    p.m += r.distance_m;
    p.sprints += r.sprints;
    p.top = Math.max(p.top, r.top_speed_kmh);
  }
  const rows = S.match.lineups[S.tableSide].map((pl) => {
    const st = S.playerStats.find((x) => x.player === pl.name) || {};
    const ph = phys[pl.name] || { m: 0, sprints: 0, top: 0 };
    return [pl.number, pl.name, pl.position, st.passes || 0, st.pass_accuracy_pct ?? "–", st.shots || 0, st.goals || 0,
            st.xg || 0, st.ball_wins || 0, st.pressures || 0, Number((ph.m / 1000).toFixed(1)), ph.sprints, ph.top || "–"];
  });
  const c = S.sortCol;
  rows.sort((a, b) => {
    const x = typeof a[c] === "number" ? a[c] : -1, y = typeof b[c] === "number" ? b[c] : -1;
    if (c === 1 || c === 2) return S.sortDesc ? String(b[c]).localeCompare(a[c]) : String(a[c]).localeCompare(b[c]);
    return S.sortDesc ? y - x : x - y;
  });
  const head = $("playersHead");
  head.innerHTML = "";
  tx.cols.forEach((label, i) => {
    const th = document.createElement("th");
    th.textContent = label + (i === c ? (S.sortDesc ? " ▼" : " ▲") : "");
    th.className = i === 1 || i === 2 ? "l" : "";
    th.onclick = () => { S.sortDesc = S.sortCol === i ? !S.sortDesc : true; S.sortCol = i; renderPlayerTable(); };
    head.append(th);
  });
  const body = $("playersBody");
  body.innerHTML = "";
  for (const r of rows) {
    const tr = document.createElement("tr");
    if (r[1] === $("player").value) tr.className = "fav";
    r.forEach((v, i) => {
      const td = document.createElement("td");
      td.textContent = i === 10 ? v.toFixed(1) : v;
      if (i === 1 || i === 2) td.className = "l";
      tr.append(td);
    });
    body.append(tr);
  }
}

// ---------- Match Pulse: control vs chaos (last 5 minutes) ----------
function renderPulse(p) {
  if (!p) return;
  const tx = T();
  $("pulseWindow").textContent = `${p.from_minute}'–${p.to_minute}'`;
  $("ctrlHome").style.flex = String(p.home_control_pct || 0.0001);
  $("ctrlAway").style.flex = String(p.away_control_pct || 0.0001);
  $("ctrlHomeVal").textContent = `${S.match.home_team.split(" ")[0]} ${p.home_control_pct}%`;
  $("ctrlAwayVal").textContent = `${p.away_control_pct}% ${S.match.away_team.split(" ")[0]}`;
  const lead = p.home_control_pct >= 58 ? S.match.home_team : p.away_control_pct >= 58 ? S.match.away_team : null;
  $("ctrlWord").textContent = lead ? `${lead} ${tx.inControl}` : tx.balanced;
  $("chaosFill").style.width = `${p.chaos}%`;
  $("chaosVal").textContent = `${p.chaos}/100`;
  $("chaosWord").textContent = p.chaos >= 65 ? tx.chaotic : p.chaos >= 35 ? tx.normal : tx.calm;
  $("chaosHint").textContent = `${p.ball_changes} ${tx.ballChanges}`;
}

// ---------- Zones: thirds of the pitch ----------
function renderZones(z) {
  const tx = T();
  const layer = $("zoneLayer");
  layer.innerHTML = "";
  $("direction").textContent = `◀ ${S.match.away_team} ${tx.attacks}   ·   ${S.match.home_team} ${tx.attacks} ▶`;
  renderThirds(z);
  const mode = $("zoneMode").value;
  if (!z || mode === "off") return;
  const t = z[mode];
  const parts = [
    [0, t.home_third_pct, tx.zoneNames[0]], [35, t.middle_third_pct, tx.zoneNames[1]], [70, t.away_third_pct, tx.zoneNames[2]],
  ];
  for (const [x, pct, label] of parts) {
    const rect = document.createElementNS(SVG, "rect");
    Object.entries({ x, y: 0, width: 35, height: 68, class: "zone", "fill-opacity": (0.03 + (pct / 100) * 0.4).toFixed(3) })
      .forEach(([k, v]) => rect.setAttribute(k, v));
    layer.append(rect);
    const big = document.createElementNS(SVG, "text");
    Object.entries({ x: x + 17.5, y: 9, class: "zone-pct", "text-anchor": "middle" }).forEach(([k, v]) => big.setAttribute(k, v));
    big.textContent = `${pct}%`;
    const small = document.createElementNS(SVG, "text");
    Object.entries({ x: x + 17.5, y: 13, class: "zone-label", "text-anchor": "middle" }).forEach(([k, v]) => small.setAttribute(k, v));
    small.textContent = label;
    layer.append(big, small);
  }
  for (const x of [35, 70]) {
    const line = document.createElementNS(SVG, "line");
    Object.entries({ x1: x, x2: x, y1: 0, y2: 68, class: "zone-line" }).forEach(([k, v]) => line.setAttribute(k, v));
    layer.append(line);
  }
}

function renderThirds(z) {
  const tx = T();
  const box = $("thirds");
  box.innerHTML = "";
  if (!z) return;
  for (const t of z.by_team) {
    const row = document.createElement("div");
    row.className = `thirds-row ${t.team_side}`;
    row.innerHTML = `<div class="thirds-team"></div>
      <div class="thirds-bar"><span class="s1"></span><span class="s2"></span><span class="s3"></span></div>
      <div class="thirds-labels"><span></span><span></span><span></span></div>`;
    row.querySelector(".thirds-team").textContent = t.team;
    const values = [t.defensive_third_pct, t.middle_third_pct, t.attacking_third_pct];
    const names = [tx.defend, tx.middle, tx.attack];
    row.querySelectorAll(".thirds-bar span").forEach((el, i) => { el.style.flex = String(values[i] || 0.0001); });
    row.querySelectorAll(".thirds-labels span").forEach((el, i) => { el.textContent = `${names[i]} ${values[i]}%`; });
    box.append(row);
  }
}

function renderStats(teamStats) {
  const home = teamStats.find((x) => x.team_side === "home") || {};
  const away = teamStats.find((x) => x.team_side === "away") || {};
  const box = $("stats");
  box.innerHTML = "";
  for (const [k, label] of Object.entries(T().statLabels)) {
    const h = Number(home[k] ?? 0), a = Number(away[k] ?? 0);
    const total = h + a || 1;
    const row = document.createElement("div");
    row.innerHTML = `<div class="stat-row"><span class="v"></span><span class="stat-mid"></span><span class="v r"></span></div>
      <div class="split"><span class="h"></span><span class="a"></span></div>`;
    const [hv, mid, av] = row.querySelectorAll(".stat-row span");
    hv.textContent = home[k] ?? 0; mid.textContent = label; av.textContent = away[k] ?? 0;
    row.querySelector(".h").style.flex = String(h / total || 0.0001);
    row.querySelector(".a").style.flex = String(a / total || 0.0001);
    box.append(row);
  }
}

function renderMomentum(timeline) {
  const svg = $("momentum");
  svg.innerHTML = "";
  const W = 300, H = 140, mid = 66, left = 34, slot = (W - left) / 6;
  const maxXg = Math.max(0.5, ...timeline.flatMap((b) => [b.home_xg, b.away_xg]));
  const scale = (v) => (v / maxXg) * 52;
  const el = (name, attrs, parent = svg) => {
    const n = document.createElementNS(SVG, name);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    parent.append(n);
    return n;
  };
  el("line", { x1: left, x2: W, y1: mid, y2: mid, class: "axis" });
  el("text", { x: 0, y: mid - 40 }).textContent = S.match.home_team.split(" ")[0];
  el("text", { x: 0, y: mid + 48 }).textContent = S.match.away_team.split(" ")[0];
  for (let i = 0; i < 6; i++) {
    const b = timeline.find((x) => x.from_minute === i * 15);
    const x = left + i * slot + slot * 0.25, w = slot * 0.5;
    el("text", { x: left + i * slot + slot / 2, y: H - 2, "text-anchor": "middle" }).textContent = `${i * 15}'`;
    if (!b) continue;
    const hh = scale(b.home_xg), ah = scale(b.away_xg);
    if (hh > 0) el("rect", { x, y: mid - 1 - hh, width: w, height: hh, rx: 2, class: "bar-h" });
    if (ah > 0) el("rect", { x, y: mid + 1, width: w, height: ah, rx: 2, class: "bar-a" });
    const hit = el("rect", { x: left + i * slot, y: 0, width: slot, height: H - 14, class: "hit" });
    hit.onmousemove = (e) => showTip(e, `${b.from_minute}'–${b.to_minute}' · ${S.match.home_team} xG ${b.home_xg} · ${S.match.away_team} xG ${b.away_xg}`);
    hit.onmouseleave = () => $("tip").classList.add("hidden");
  }
}

function showTip(e, text) {
  const tip = $("tip"), box = $("momentum").getBoundingClientRect();
  tip.textContent = text;
  tip.classList.remove("hidden");
  const x = Math.min(e.clientX - box.left + 10, box.width - tip.offsetWidth - 4);
  tip.style.left = `${Math.max(0, x)}px`;
  tip.style.top = `${e.clientY - box.top - 34}px`;
}

// ---------- Players on the pitch (Football Manager style) ----------
// Each team stands in a 4-3-3 shape. The whole team slides with the ball, and the players
// involved in the latest actions move to where the action happened.
const SHAPE = [[6, 34], [22, 58], [20, 42], [20, 26], [22, 10], [38, 34], [46, 50], [46, 18], [64, 56], [68, 34], [64, 12]];

function buildPlayers() {
  const layer = $("playerLayer");
  layer.innerHTML = "";
  S.players = {};
  for (const side of ["home", "away"]) {
    S.match.lineups[side].forEach((p, i) => {
      const g = document.createElementNS(SVG, "g");
      g.setAttribute("class", `pl ${side}`);
      g.innerHTML = `<circle r="1.7"></circle><text class="num" text-anchor="middle" dy="0.6"></text>
        <text class="tag" text-anchor="middle" y="-2.6"></text>`;
      g.querySelector(".num").textContent = p.number;
      const title = document.createElementNS(SVG, "title");
      title.textContent = `${p.number}. ${p.name} (${p.position})`;
      g.append(title);
      layer.append(g);
      S.players[p.name] = { g, side, index: i, name: p.name, x: 0, y: 0 };
    });
  }
}

function placePlayers(recent) {
  if (!S.players) return;
  const flip = (e, x, y) => (e.team_side === "away" ? [105 - x, 68 - y] : [x, y]);
  const last = recent.filter((e) => e.x != null).slice(-3);
  let ball = [52.5, 34];
  const special = {};
  for (const e of last) {
    const [x, y] = flip(e, e.x, e.y);
    ball = [x, y];
    if (e.player) special[e.player] = [x, y];
    if (e.type === "pass" && e.outcome === "complete" && e.recipient) {
      const [ex, ey] = flip(e, e.end_x, e.end_y);
      special[e.recipient] = [ex, ey];
      ball = [ex, ey];
    }
  }
  const dx = (ball[0] - 52.5) * 0.5, dy = (ball[1] - 34) * 0.2;
  const minute = Math.floor(S.t / 60);
  const fast = S.speedTags && S.speedTags[minute] ? S.speedTags[minute] : {};
  const fav = $("player").value;
  const carrier = last.length ? (last[last.length - 1].recipient || last[last.length - 1].player) : null;
  for (const p of Object.values(S.players)) {
    let [x, y] = SHAPE[p.index];
    if (p.side === "away") { x = 105 - x; y = 68 - y + (p.index ? 4 : 0); } // small offset so shirts don't overlap
    if (p.index === 0) { x += dx * 0.15; } else { x += dx; y += dy; }
    if (special[p.name]) [x, y] = special[p.name];
    x = Math.min(103.5, Math.max(1.5, x));
    y = Math.min(66.5, Math.max(1.5, y));
    p.g.style.transform = `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
    p.g.classList.toggle("carrier", p.name === carrier);
    p.g.classList.toggle("fav", p.name === fav);
    const tag = p.g.querySelector(".tag");
    tag.textContent = fast[p.name] ? `⚡${fast[p.name]}` : p.name === carrier ? p.name.split(" ").slice(-1)[0] : "";
  }
  const b = $("ballLayer");
  b.innerHTML = `<circle class="ball" r="0.9" cx="${ball[0].toFixed(2)}" cy="${ball[1].toFixed(2)}"></circle>`;
}

// ---------- Pitch ----------
function drawPitch() {
  if (!S.speedTags) {
    S.speedTags = {};
    for (const r of S.physical) {
      if (r.top_speed_kmh >= 32) (S.speedTags[r.minute] = S.speedTags[r.minute] || {})[r.player] = r.top_speed_kmh;
    }
  }
  const layer = $("eventLayer");
  layer.innerHTML = "";
  const recent = S.events.filter((e) => e.t <= S.t && e.t > S.t - 20);
  placePlayers(recent);
  const flip = (e, x, y) => (e.team_side === "away" ? [105 - x, 68 - y] : [x, y]);
  let ball = null;
  for (const e of recent) {
    if (e.x == null) continue;
    const color = e.team_side === "away" ? "var(--away)" : "var(--home)";
    const [x, y] = flip(e, e.x, e.y);
    if (e.type === "pass") {
      const [ex, ey] = flip(e, e.end_x, e.end_y);
      const line = document.createElementNS(SVG, "line");
      Object.entries({ x1: x, y1: y, x2: ex, y2: ey, stroke: color, class: `ev-pass ${e.outcome === "complete" ? "" : "fail"}` })
        .forEach(([k, v]) => line.setAttribute(k, v));
      layer.append(line);
      ball = [ex, ey];
    } else if (e.type === "shot") {
      const c = document.createElementNS(SVG, "circle");
      Object.entries({ cx: x, cy: y, r: 1.3, fill: color, class: "ev-shot" }).forEach(([k, v]) => c.setAttribute(k, v));
      layer.append(c);
      if (e.outcome === "goal") {
        const ring = document.createElementNS(SVG, "circle");
        Object.entries({ cx: x, cy: y, r: 2.6, class: "ev-goal" }).forEach(([k, v]) => ring.setAttribute(k, v));
        layer.append(ring);
      }
      ball = [x, y];
    } else {
      ball = [x, y];
    }
  }
}

// ---------- AI overlays ----------
async function loadOverlays(minute) {
  if (S.loadingOverlays || minute === S.overlaysFor) return;
  S.loadingOverlays = true;
  const version = S.profileVersion;
  const asked = minute >= 90 ? 999 : minute + 1;
  $("pending").classList.remove("hidden");
  try {
    const q = profileQuery();
    q.set("minute", asked);
    const data = await (await fetch(`/api/overlays?${q}`)).json();
    if (version !== S.profileVersion) return; // viewer changed settings while we waited
    S.overlaysFor = minute;
    for (const o of data.overlays) {
      const isNew = !S.overlays.has(key(o));
      S.overlays.set(key(o), o); // always keep the Director's latest decision
      if (isNew && showT(o) < S.t - 120) S.shown.add(key(o)); // too old to pop up: straight into the feed
    }
    S.agentLog = data.agent_log || [];
    S.logCount = -1;
    renderFeed();
    renderPlayerCard(data.player_card);
    if (data.recap) {
      $("recap").classList.remove("hidden");
      $("recapHeadline").textContent = data.recap.headline;
      $("recapText").textContent = data.recap.text;
    }
  } catch (err) {
    console.error(err);
  } finally {
    S.loadingOverlays = false;
    $("pending").classList.add("hidden");
  }
}

// The Director agent decides when a card goes on screen (show_t) and whether it pops up at all.
const showT = (o) => (o.show_t ?? o.t);

function queueDueCards() {
  const due = [...S.overlays.values()].filter((o) => showT(o) <= S.t && !S.shown.has(key(o))).sort((a, b) => showT(a) - showT(b));
  for (const o of due) {
    S.shown.add(key(o));
    if (o.popup !== false) S.queue.push(o); // skipped pop-ups still go into the story list
  }
  if (due.length) renderFeed();
  if (!S.cardTimer && S.queue.length) showCard(S.queue.shift());
}

function showCard(o) {
  const tx = T();
  const card = $("card");
  card.classList.remove("hidden", "away");
  void card.offsetWidth; // restart the animation
  if (sideOf(o.team) === "away") card.classList.add("away");
  $("cardKind").textContent = tx.kinds[o.kind] || o.kind;
  $("cardTime").textContent = o.show_at;
  $("cardForYou").classList.toggle("hidden", !o.for_you);
  const check = $("cardCheck");
  check.textContent = o.text ? tx.checked : tx.headlineOnly;
  check.classList.toggle("ok", Boolean(o.grounded && o.text));
  $("cardHeadline").textContent = o.headline;
  $("cardText").textContent = o.text;
  S.cardTimer = setTimeout(() => { hideCard(); queueDueCards(); }, o.kind === "goal" ? 9000 : 7000);
}

function hideCard() {
  clearTimeout(S.cardTimer);
  S.cardTimer = null;
  $("card").classList.add("hidden");
}

function renderFeed() {
  const feed = $("feed");
  feed.innerHTML = "";
  const tx = T();
  const items = [...S.overlays.values()].filter((o) => S.shown.has(key(o))).sort((a, b) => a.t - b.t);
  for (const o of items) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="t"></span><span class="bar"></span><div><div class="h"></div><div class="x"></div></div>`;
    li.querySelector(".t").textContent = o.show_at;
    if (sideOf(o.team) === "away") li.querySelector(".bar").classList.add("away");
    li.querySelector(".h").textContent = `${o.for_you ? "★ " : ""}${tx.kinds[o.kind] || o.kind} · ${o.headline}`;
    li.querySelector(".x").textContent = o.text;
    li.querySelector(".h").dir = li.querySelector(".x").dir = "auto"; // right-to-left for Arabic
    feed.append(li);
  }
}

function renderPlayerCard(rows) {
  const panel = $("playerPanel");
  if (!rows || !$("player").value) { panel.classList.add("hidden"); return; }
  panel.classList.remove("hidden");
  $("playerName").textContent = $("player").value;
  const body = $("playerRows");
  body.innerHTML = "";
  for (const r of rows) {
    const tr = document.createElement("tr");
    for (const v of [r.minute, r.passes, r.shots, r.xg, r.goals, r.pressures]) {
      const td = document.createElement("td");
      td.textContent = v;
      tr.append(td);
    }
    body.append(tr);
  }
}

function profileChanged() {
  S.profileVersion++;
  S.overlays.clear();
  S.shown.clear();
  S.queue = [];
  S.overlaysFor = -1;
  hideCard();
  $("recap").classList.add("hidden");
  applyLanguage();
  renderFeed();
  S.agentLog = [];
  S.logCount = -1;
  S.lastMinute = -1; // refresh stat labels in the new language
  $("replayList").dataset.sig = "";
  update();
}

start();
