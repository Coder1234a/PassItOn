/* PassItOn phone app. Plain JS, no build step.
   Juniors: Home (ask + shelves), Seniors (swipe deck), Market, Matches.
   Seniors: Questions (swipe deck), Requests, Pass it on, Me. */
"use strict";

// ---------- small helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const params = new URLSearchParams(location.search);

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  swipe: '<rect x="7" y="3" width="12" height="16" rx="3"/><path d="M4 7v11a3 3 0 0 0 3 3h8"/>',
  bag: '<path d="M5 8h14l-1.2 12.1a1 1 0 0 1-1 .9H7.2a1 1 0 0 1-1-.9z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
  heart: '<path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7a4.3 4.3 0 0 1 7.5 2.8C19.5 15.4 12 20 12 20z"/>',
  inbox: '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M6 5h12l2 8v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-6z"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.2a6.5 6.5 0 0 1 3.5 5.8"/>',
  plus: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  pen: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13.5" r="3.5"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a1 1 0 0 1 1-1h10"/>',
  spark: '<path d="M12 3c.5 4 2.5 6 6.5 6.5-4 .5-6 2.5-6.5 6.5-.5-4-2.5-6-6.5-6.5C9.5 9 11.5 7 12 3z"/><path d="M19 15c.2 1.5 1 2.3 2.5 2.5-1.5.2-2.3 1-2.5 2.5-.2-1.5-1-2.3-2.5-2.5 1.5-.2 2.3-1 2.5-2.5z"/>',
  thumb: '<path d="M7 11v9H4v-9z"/><path d="M7 11l4-7a2 2 0 0 1 2.7 2.3L13 10h5.5a2 2 0 0 1 2 2.4l-1.4 6.5a2 2 0 0 1-2 1.6H7"/>',
  chat: '<path d="M4 18.5V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H8z"/>',
};
const icon = (name, extra = "") =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${ICONS[name]}</svg>`;
const VERIFIED = '<svg class="verified" viewBox="0 0 24 24" aria-label="Verified VIT senior"><circle cx="12" cy="12" r="10" fill="#19C9B0"/><path d="m7.5 12.5 3 3 6-6.5" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';

function hue(name) {
  let h = 0;
  for (const ch of String(name)) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}
function avatar(name, cls = "av-m") {
  const h = hue(name);
  return `<span class="av ${cls}" style="background:linear-gradient(135deg,hsl(${h} 78% 60%),hsl(${(h + 45) % 360} 70% 42%))">${esc(String(name || "?").trim().charAt(0).toUpperCase())}</span>`;
}
function ago(ts) {
  const m = Math.max(1, Math.round((Date.now() / 1000 - ts) / 60));
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
}
const shortYear = (y) => String(y || "").replace(" year", " yr");
const priceText = (p) => (Number(p) > 0 ? `₹${Number(p).toLocaleString("en-IN")}` : "Free");

function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch (e) { /* private mode: the app still works, it just won't remember you */ }
  return null;
}

async function api(path, data) {
  const opts = data === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 25000);
  try {
    const res = await fetch(path, { ...opts, signal: ctrl.signal });
    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(json.error || "Something went wrong. Try again.");
    return json;
  } catch (e) {
    if (e.name === "AbortError") throw new Error("That took too long. Check your connection and try again.");
    if (e instanceof TypeError) throw new Error("Can't reach PassItOn. Check your connection.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

let toastTimer;
function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
}

// ---------- app state ----------
const S = {
  role: params.get("role") || store("pio_role"),
  me: params.get("me") || store("pio_me"),
  tab: null,
  data: null,
  live: { requests: [], questions: [], items: [], points: 0, me: {} },
  seenAccepted: null,
  seenRequests: null,
  deck: [], deckIdx: 0, deckFor: null, deckNeed: "", deckQuestion: "", deckInfo: null,
  qIdx: 0, qSkipped: new Set(),
  market: { q: "", cat: "All" },
  listing: null, photo: null,
  busy: false,
};
if (params.get("embed")) document.body.classList.add("embedded");

const JUNIOR_TABS = [["home", "Home", "home"], ["seniors", "Seniors", "swipe"], ["market", "Market", "bag"], ["matches", "Matches", "heart"]];
const SENIOR_TABS = [["questions", "Questions", "inbox"], ["requests", "Requests", "users"], ["sell", "Pass it on", "plus"], ["me", "Me", "user"]];
const NEEDS = [
  ["All", ""], ["FFCS", "FFCS slots timetable courses"], ["CAT & FAT", "exam CAT FAT preparation strategy"],
  ["DSA", "Data Structures and Algorithms recursion linked lists"], ["EG", "Engineering Graphics drafter projections"],
  ["Clubs", "clubs hackathons building projects"], ["Labs", "lab viva records experiments"],
  ["Internships", "internships resumes interview prep"],
];
const CATS = ["All", "Lab coat", "Calculator", "Hostel essentials", "Drafting / EG kit", "Textbook", "Cycle", "Electronics"];
const CAT_LABEL = { "Hostel essentials": "Hostel", "Drafting / EG kit": "EG kit", Textbook: "Books" };
const SUGGESTIONS = [
  "DSA CAT is on Thursday and recursion confuses me",
  "Which slots should I pick in my first FFCS?",
  "How do I start with hackathons?",
  "How do I apply for a semester exchange abroad?",
];

function seniorById(id) {
  return (S.data?.seniors || []).find((s) => String(s.id) === String(id));
}
function meName() {
  return S.role === "senior" ? seniorById(S.me)?.name || "Senior" : S.me || "You";
}

// ---------- boot ----------
async function boot() {
  try {
    S.data = await api("/api/bootstrap");
  } catch (e) {
    $("#view").innerHTML = `<div class="empty"><div class="big">📡</div><h2>Can't reach PassItOn</h2><p>${esc(e.message)}</p><button class="btn btn-primary" onclick="location.reload()">Try again</button></div>`;
    return;
  }
  if (S.role === "senior" && !seniorById(S.me)) S.role = null;
  if (!S.role || !S.me) return renderWelcome();
  startRole();
}

async function startRole() {
  document.body.classList.toggle("senior", S.role === "senior");
  S.tab = S.role === "senior" ? "questions" : "home";
  S.seenAccepted = null;
  S.seenRequests = null;
  renderChrome();
  showTour(false);
  await poll();
  go(S.tab);
  clearInterval(S.pollTimer);
  S.pollTimer = setInterval(poll, 3000);
}

function setRole(role, me) {
  S.role = role;
  S.me = String(me);
  store("pio_role", role);
  store("pio_me", S.me);
  startRole();
}

// ---------- welcome ----------
function renderWelcome() {
  document.body.classList.remove("senior");
  $("#topbar").hidden = true;
  $("#tabbar").hidden = true;
  const seniors = S.data.seniors.map((s) => `<button data-senior="${esc(s.id)}">${avatar(s.name, "av-s")}<span>${esc(s.name)}<small>${esc(shortYear(s.year))}, ${esc(s.branch)}</small></span></button>`).join("");
  $("#view").innerHTML = `
    <div class="welcome">
      <div class="logo">pass<i>it</i>on</div>
      <p class="tagline">Seniors who've been through it, one swipe away.</p>
      <button class="choice j" id="pick-junior"><span class="emoji">🎒</span><h2>I'm a junior</h2><p>Get answers, find a senior, grab their old stuff</p></button>
      <div id="junior-name" hidden>
        <input type="text" id="jname" maxlength="30" placeholder="Your first name" autocomplete="given-name">
        <button class="btn btn-primary btn-block" id="go-junior" style="margin-top:10px">Start</button>
      </div>
      <button class="choice s" id="pick-senior"><span class="emoji">🎓</span><h2>I'm a senior</h2><p>Answer questions, mentor juniors, pass things on</p></button>
      <div id="senior-who" hidden><div class="who-grid">${seniors}</div></div>
      <p class="fineprint">Demo build with sample seniors, tips and listings.</p>
    </div>`;
  $("#pick-junior").onclick = () => { $("#junior-name").hidden = false; $("#senior-who").hidden = true; $("#jname").focus(); };
  $("#pick-senior").onclick = () => { $("#senior-who").hidden = false; $("#junior-name").hidden = true; };
  const startJunior = async () => {
    const name = $("#jname").value.trim().replace(/\s+/g, " ");
    if (!name) { toast("Add your first name so seniors know who's asking"); $("#jname").focus(); return; }
    try {
      const v = await api("/api/check_name", { name });
      if (!v.allowed) { toast(v.message); $("#jname").focus(); return; }
    } catch (e) { /* server unreachable: let them in, the server checks again later */ }
    setRole("junior", name);
  };
  $("#go-junior").onclick = startJunior;
  $("#jname").onkeydown = (e) => { if (e.key === "Enter") startJunior(); };
  $("#senior-who").onclick = (e) => { const b = e.target.closest("[data-senior]"); if (b) setRole("senior", b.dataset.senior); };
}

// ---------- chrome: top bar + tab bar ----------
function renderChrome() {
  const tabs = S.role === "senior" ? SENIOR_TABS : JUNIOR_TABS;
  $("#topbar").hidden = false;
  $("#tabbar").hidden = false;
  $("#topbar").innerHTML = `<div class="wordmark">pass<i>it</i>on</div>
    <button class="role-pill" id="who" aria-label="Account">${S.role === "senior" ? "Senior" : "Junior"} ${avatar(meName(), "av-s")}</button>`;
  $("#tabbar").innerHTML = tabs.map(([id, label, ic]) => `<button class="tab" data-tab="${id}">${icon(ic)}<span>${label}</span><span class="badge" data-badge="${id}" hidden></span></button>`).join("");
  $("#tabbar").onclick = (e) => { const b = e.target.closest("[data-tab]"); if (b) go(b.dataset.tab); };
  $("#who").onclick = openAccount;
}

function go(tab) {
  S.tab = tab;
  document.querySelectorAll(".tab").forEach((t) => t.setAttribute("aria-current", t.dataset.tab === tab ? "page" : "false"));
  const view = $("#view");
  view.scrollTop = 0;
  ({ home: viewHome, seniors: viewSeniors, market: viewMarket, matches: viewMatches,
     questions: viewQuestions, requests: viewRequests, sell: viewSell, me: viewMe })[tab]();
}

function openAccount() {
  openSheet(`<div class="sheet-h"><h2>${esc(meName())}</h2>${closeBtn()}</div>
    <button class="btn btn-ghost btn-block" id="replay" style="margin-bottom:10px">How PassItOn works</button>
    <button class="btn btn-ghost btn-block" id="switch">Switch to ${S.role === "senior" ? "junior" : "senior"} mode</button>
    <button class="btn btn-ghost btn-block" id="reset" style="margin-top:10px">Reset demo data</button>`);
  $("#replay").onclick = () => { closeSheet(); showTour(true); };
  $("#switch").onclick = () => { closeSheet(); store("pio_role", null); store("pio_me", null); S.role = null; clearInterval(S.pollTimer); renderWelcome(); };
  $("#reset").onclick = async () => {
    await api("/api/reset", {});
    S.data = await api("/api/bootstrap");
    S.qSkipped.clear();
    closeSheet();
    toast("Demo data reset");
    startRole();
  };
}

// ---------- bottom sheet & overlay ----------
const closeBtn = () => `<button class="x" data-close aria-label="Close">${icon("x")}</button>`;
function openSheet(html, tall = false) {
  const sh = $("#sheet");
  sh.innerHTML = `<div class="grab"></div>${html}`;
  sh.classList.toggle("tall", tall);
  sh.hidden = false;
  $("#sheet-backdrop").hidden = false;
  sh.onclick = (e) => { if (e.target.closest("[data-close]")) closeSheet(); };
  $("#sheet-backdrop").onclick = closeSheet;
  return sh;
}
function closeSheet() {
  $("#sheet").hidden = true;
  $("#sheet-backdrop").hidden = true;
  $("#sheet").innerHTML = "";
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { if (!$("#overlay").hidden) $("#overlay").hidden = true; else closeSheet(); }
  const typing = /INPUT|TEXTAREA/.test(document.activeElement?.tagName || "");
  if (!typing && $("#sheet").hidden && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
    const deck = $(".deck");
    if (deck && deck._fly) deck._fly(e.key === "ArrowRight" ? 1 : -1);
  }
});

// ---------- swipe engine ----------
/* Renders up to 3 stacked cards. Drag the top card, or use the buttons.
   onSwipe(item, dir) is called with dir = 1 (right) or -1 (left). */
function mountDeck(el, items, startIdx, renderCard, onSwipe, onEmpty) {
  let idx = startIdx;
  let locked = false;
  function draw() {
    const visible = items.slice(idx, idx + 3).reverse();
    if (!visible.length) { el.innerHTML = ""; onEmpty(); return; }
    el.innerHTML = visible.map((it) => `<article class="card" tabindex="-1">${renderCard(it)}</article>`).join("");
    attach(el.lastElementChild);
  }
  function fly(dir) {
    const card = el.lastElementChild;
    if (!card || locked) return;
    locked = true;
    const item = items[idx];
    card.style.transition = "transform 0.3s ease-in";
    card.style.transform = `translateX(${dir * 140}%) rotate(${dir * 22}deg)`;
    const stamp = card.querySelector(dir > 0 ? ".stamp.yes" : ".stamp.no");
    if (stamp) stamp.style.opacity = 1;
    setTimeout(() => { idx += 1; locked = false; draw(); onSwipe(item, dir, idx); }, 260);
  }
  function attach(card) {
    let x0 = null, y0 = 0, dx = 0;
    const yes = card.querySelector(".stamp.yes"), no = card.querySelector(".stamp.no");
    card.addEventListener("pointerdown", (e) => {
      if (e.target.closest("button")) return;
      x0 = e.clientX; y0 = e.clientY; dx = 0;
      card.setPointerCapture(e.pointerId);
      card.classList.add("dragging");
    });
    card.addEventListener("pointermove", (e) => {
      if (x0 === null) return;
      dx = e.clientX - x0;
      const dy = (e.clientY - y0) * 0.2;
      card.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx / 14}deg)`;
      if (yes) yes.style.opacity = Math.max(0, Math.min(1, dx / 90));
      if (no) no.style.opacity = Math.max(0, Math.min(1, -dx / 90));
    });
    const end = () => {
      if (x0 === null) return;
      x0 = null;
      card.classList.remove("dragging");
      if (Math.abs(dx) > 95) { fly(dx > 0 ? 1 : -1); return; }
      card.style.transform = "";
      if (yes) yes.style.opacity = 0;
      if (no) no.style.opacity = 0;
    };
    card.addEventListener("pointerup", end);
    card.addEventListener("pointercancel", end);
  }
  el._fly = fly;
  el._undo = () => { if (idx > 0 && !locked) { idx -= 1; draw(); } return idx; };
  draw();
}

// =====================================================================
// JUNIOR
// =====================================================================
function posterClass(row) { return "p-" + String(row).split(" ")[0]; }

async function viewHome() {
  try { S.data = await api("/api/bootstrap"); } catch (e) { /* keep the last copy */ }
  const tips = S.data.tips;
  const shelves = S.data.rows.map((row) => {
    const list = tips.filter((t) => t.row === row).sort((a, b) => b.helpful - a.helpful || b.id - a.id).slice(0, 10);
    if (!list.length) return "";
    return `<div class="row-title"><h2>${esc(row)}</h2><button class="link" data-need="${esc(row)}">Seniors for this</button></div>
      <div class="shelf">${list.map((t) => `<button class="poster ${posterClass(row)}" data-tip="${esc(t.id)}">
        <h3>${esc(t.question)}</h3><span class="by">${esc(t.senior_name)}, ${esc(shortYear(t.senior_year))}${t.helpful ? ` · 👍 ${t.helpful}` : ""}</span></button>`).join("")}</div>`;
  }).join("");
  const free = S.data.items.filter((i) => !Number(i.price)).slice(0, 8);
  const top = [...S.data.seniors].sort((a, b) => b.rating - a.rating).slice(0, 8);
  $("#view").innerHTML = `
    <div class="pad">
      <h1 class="hello">Hey ${esc(S.me)} 👋</h1>
      <p class="sub">What do you need help with?</p>
      <button class="askbar" id="ask-open">${icon("search")}<span>Ask seniors anything…</span></button>
    </div>
    <div class="row-title"><h2>Seniors around this week</h2><button class="link" data-goto="seniors">Swipe all</button></div>
    <div class="faces">${top.map((s) => `<button class="face" data-senior="${esc(s.id)}">${avatar(s.name)}${esc(s.name)}</button>`).join("")}</div>
    ${shelves}
    <div class="row-title"><h2>Free from seniors</h2><button class="link" data-goto="market">See market</button></div>
    <div class="shelf">${free.map(productCard).map((h) => h.replace('class="product"', 'class="product mini"')).join("")}</div>`;
  const v = $("#view");
  $("#ask-open").onclick = () => openAsk();
  v.onclick = (e) => {
    const t = e.target.closest("[data-tip]"); if (t) return openTip(t.dataset.tip);
    const n = e.target.closest("[data-need]"); if (n) return openDeckForNeed(n.dataset.need, n.dataset.need);
    const g = e.target.closest("[data-goto]"); if (g) return go(g.dataset.goto);
    const s = e.target.closest("[data-senior]"); if (s) return openSeniorSheet(s.dataset.senior);
    const p = e.target.closest("[data-item]"); if (p) return openItem(p.dataset.item);
  };
}

function openTip(id) {
  const t = S.data.tips.find((x) => String(x.id) === String(id));
  if (!t) return;
  const s = S.data.seniors.find((x) => x.name === t.senior_name);
  openSheet(`<div class="sheet-h"><h2>${esc(t.question)}</h2>${closeBtn()}</div>
    ${answerCard(t.answer, [t])}
    ${s ? `<button class="btn btn-primary btn-block" style="margin-top:16px" id="ask-this">Ask ${esc(s.name)} in person</button>` : ""}`);
  bindHelpful();
  if (s) $("#ask-this").onclick = () => sendRequest(s, t.question, null, true);
}

function answerCard(text, sources, trace) {
  const src = sources[0] || {};
  return `<div class="answer">
    <div class="who">${avatar(src.senior_name || "S", "av-s")}<span><b>${esc(src.senior_name || "Seniors")}</b>${esc(src.senior_year || "")}${src.course ? `, ${esc(src.course)}` : ""}</span></div>
    <p>${esc(text)}</p>
    <div class="answer-foot">
      <button class="pill-btn" data-helpful="${esc(src.id)}" aria-pressed="false">${icon("thumb", 'width="16" height="16"')}<span>Helpful${src.helpful ? ` · ${src.helpful}` : ""}</span></button>
      ${trace ? `<button class="link" data-trace>${icon("spark", 'width="16" height="16" style="vertical-align:-3px"')} How the AI got this</button>` : ""}
    </div></div>`;
}
function bindHelpful() {
  const b = $("#sheet [data-helpful]");
  if (!b) return;
  b.onclick = async () => {
    if (b.getAttribute("aria-pressed") === "true") return;
    b.setAttribute("aria-pressed", "true");
    try {
      const r = await api("/api/helpful", { tip_id: Number(b.dataset.helpful) });
      b.querySelector("span").textContent = `Helpful · ${r.helpful}`;
    } catch (e) { toast(e.message); }
  };
}

// ----- ask flow -----
function openAsk(prefill = "") {
  openSheet(`<div class="sheet-h"><h2>Ask seniors</h2>${closeBtn()}</div>
    <textarea id="q" rows="3" maxlength="500" placeholder="e.g. My DSA CAT is on Thursday and recursion makes no sense">${esc(prefill)}</textarea>
    <button class="btn btn-primary btn-block" id="q-go" style="margin-top:12px">Ask</button>
    <div id="q-out"><div class="suggest">${SUGGESTIONS.map((s) => `<button data-s="${esc(s)}">${esc(s)}</button>`).join("")}</div></div>`, true);
  const q = $("#q");
  setTimeout(() => q.focus(), 300);
  $("#q-out").onclick = (e) => { const b = e.target.closest("[data-s]"); if (b) { q.value = b.dataset.s; runAsk(); } };
  $("#q-go").onclick = runAsk;
  q.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runAsk(); } };
}

async function runAsk() {
  const q = $("#q"), out = $("#q-out"), btn = $("#q-go");
  const question = q.value.trim();
  if (question.length < 4) { toast("Type a full question first"); q.focus(); return; }
  if (S.busy) return;
  S.busy = true;
  btn.disabled = true;
  out.innerHTML = `<div class="loading"><span class="dots"><i></i><i></i><i></i></span>Checking ${S.data.tips.length} senior tips…</div>`;
  try {
    const r = await api("/api/ask", { question, me: S.me });
    if (!$("#q-out")) return; // sheet was closed while waiting
    if (r.status === "blocked") {
      const heading = { off_topic: "That's outside PassItOn", leisure: "That's outside PassItOn",
        too_short: "Add a bit more detail", vulgar: "Let's keep it respectful" }[r.category] || "Can't help with that one";
      const serious = ["academic_integrity", "cheating", "vulgar"].includes(r.category);
      out.innerHTML = `<div class="notice ${serious ? "bad" : ""}"><b>${heading}</b><p style="margin:6px 0 0">${esc(r.message)}</p></div>`;
      return;
    }
    const deckBtn = `<button class="btn ${r.answer.confident ? "btn-ghost" : "btn-primary"} btn-block" style="margin-top:14px" id="to-deck">${r.answer.confident ? "Still stuck? Swipe seniors who can help" : "Swipe seniors who can help"}</button>`;
    if (r.answer.confident) {
      out.innerHTML = answerCard(r.answer.text, r.answer.sources, r.trace) + deckBtn;
    } else {
      out.innerHTML = `<div class="notice"><b>No senior has answered this yet</b><p style="margin:6px 0 0">We won't guess. Your question is now in the seniors' inbox, and you can pick someone to ask right away.</p></div>
        ${deckBtn}<button class="link" data-trace style="margin-top:14px">${icon("spark", 'width="16" height="16" style="vertical-align:-3px"')} How the AI decided</button>`;
    }
    bindHelpful();
    out.querySelectorAll("[data-trace]").forEach((b) => (b.onclick = () => openTrace(r.trace, () => openAskResult(r))));
    $("#to-deck").onclick = () => { closeSheet(); showDeck(r.deck, r.question, r.question, r.info); };
    S.lastAsk = r;
  } catch (e) {
    out.innerHTML = `<div class="notice bad">${esc(e.message)}</div>`;
  } finally {
    S.busy = false;
    if ($("#q-go")) $("#q-go").disabled = false;
  }
}
function openAskResult(r) {
  openAsk(r.question);
  runAsk();
}

function openTrace(steps, back) {
  const names = { Safety: "Safety agent", Intake: "Intake agent", Ask: "Ask agent", Match: "Match agent", Coordination: "Coordination agent", Listing: "Listing agent" };
  openSheet(`<div class="sheet-h"><h2>How the AI got this</h2>${closeBtn()}</div>
    <ol class="steps">${(steps || []).map((s) => `<li><b>${esc(names[s.agent] || s.agent)}</b><span>${esc(s.action)}${s.detail ? ` — ${esc(s.detail)}` : ""}</span></li>`).join("")}</ol>
    ${back ? '<button class="btn btn-ghost btn-block" id="trace-back">Back</button>' : ""}`);
  if (back) $("#trace-back").onclick = back;
}

// ----- seniors deck (Tinder) -----
async function openDeckForNeed(label, needKey) {
  const need = (NEEDS.find(([l]) => l === needKey) || [null, needKey])[1];
  try {
    const deck = await api(`/api/deck?need=${encodeURIComponent(need)}`);
    showDeck(deck, label, "", null);
  } catch (e) { toast(e.message); }
}
function showDeck(deck, label, question, info) {
  S.deck = deck; S.deckIdx = 0; S.deckFor = label; S.deckQuestion = question; S.deckInfo = info;
  go("seniors");
}

async function viewSeniors() {
  if (!S.deck.length && !S.deckFor) {
    try { S.deck = await api("/api/deck"); } catch (e) { toast(e.message); }
  }
  const chips = NEEDS.map(([l]) => `<button class="chip" data-need="${esc(l)}" aria-pressed="${(S.deckFor || "All") === l}">${esc(l)}</button>`).join("");
  const forBar = S.deckQuestion
    ? `<div class="deck-for">${icon("search", 'width="18" height="18"')}<span>For: ${esc(S.deckQuestion)}</span><button class="x" id="clear-for" aria-label="Clear">${icon("x")}</button></div>` : "";
  $("#view").innerHTML = `${S.deckQuestion ? "" : `<div class="chips" style="padding-top:6px">${chips}</div>`}
    <div class="deck-wrap">${forBar}<div class="deck" id="deck"></div>
      <div class="deck-actions" id="deck-actions">
        <button class="round" id="d-no" aria-label="Skip">${icon("x", 'style="color:#FF6B81"')}</button>
        <button class="round small" id="d-undo" aria-label="Undo">${icon("undo", 'style="color:#FFC85C"')}</button>
        <button class="round yes" id="d-yes" aria-label="Ask for help">${icon("heart", 'fill="#fff" stroke="#fff"')}</button>
      </div></div>`;
  const v = $("#view");
  v.onclick = async (e) => {
    const c = e.target.closest("[data-need]");
    if (c) { const n = c.dataset.need; if (n === "All") { S.deckFor = null; S.deck = []; go("seniors"); } else openDeckForNeed(n, n); }
  };
  if ($("#clear-for")) $("#clear-for").onclick = () => { S.deckFor = null; S.deckQuestion = ""; S.deck = []; go("seniors"); };
  const deckEl = $("#deck");
  mountDeck(deckEl, S.deck, S.deckIdx, seniorCard, (s, dir, idx) => {
    S.deckIdx = idx;
    if (dir > 0) sendRequest(s, S.deckQuestion, S.deckInfo, false);
  }, () => {
    $("#deck-actions").hidden = true;
    deckEl.outerHTML = `<div class="empty"><div class="big">✨</div><h2>${S.deckQuestion ? "That's everyone who can help" : `That's everyone${S.deckFor && S.deckFor !== "All" ? ` for ${esc(S.deckFor)}` : ""}`}</h2>
      <p>Your requests are in Matches. Try another topic, or ask a question.</p>
      <button class="btn btn-primary" id="again">Ask a question</button></div>`;
    $("#again").onclick = () => openAsk();
  });
  $("#d-no").onclick = () => deckEl._fly && deckEl._fly(-1);
  $("#d-yes").onclick = () => deckEl._fly && deckEl._fly(1);
  $("#d-undo").onclick = () => { if (deckEl._undo) S.deckIdx = deckEl._undo(); };
  swipeHint(deckEl, "Swipe right to ask", "Swipe left to skip");
}

function seniorCard(s) {
  const h = hue(s.name);
  const why = (s.reasons || []).slice(0, 2).join(" · ");
  return `<div class="card-art" style="background:linear-gradient(160deg,hsl(${h} 80% 62%),hsl(${(h + 50) % 360} 70% 38%))"></div>
    <div class="card-letter">${esc(s.name.charAt(0))}</div>
    <div class="stamp yes">ASK</div><div class="stamp no">NOPE</div>
    <div class="card-info">
      <div class="card-name">${esc(s.name)} ${VERIFIED}</div>
      <div class="card-meta">${esc(shortYear(s.year))}, ${esc(s.branch)}</div>
      <div class="card-tags">${s.strengths.slice(0, 3).map((x) => `<span class="tag">${esc(x)}</span>`).join("")}</div>
      ${why ? `<div class="card-why">${esc(why.charAt(0).toUpperCase() + why.slice(1))}</div>` : ""}
      <div class="card-stats"><span>⭐ <b>${esc(s.rating)}</b></span><span>💬 <b>${Math.round(s.response_rate * 100)}%</b> reply</span>${s.next_free ? `<span>🕒 <b>${esc(s.next_free)}</b></span>` : ""}</div>
    </div>`;
}

function openSeniorSheet(id) {
  const s = seniorById(id);
  if (!s) return;
  openSheet(`<div class="sheet-h"><h2>${esc(s.name)}</h2>${closeBtn()}</div>
    <div class="deck" style="height:420px;margin-top:0"><article class="card">${seniorCard(s)}</article></div>
    <button class="btn btn-primary btn-block" style="margin-top:14px" id="ask-s">Ask ${esc(s.name)} for help</button>`);
  $("#ask-s").onclick = () => sendRequest(s, "", null, true);
}

async function sendRequest(s, question, info, closeAfter) {
  try {
    await api("/api/request", { me: S.me, senior_id: s.id, question, info });
    toast(`Asked ${s.name}. You'll see it in Matches when they say yes.`);
    if (closeAfter) closeSheet();
    poll();
  } catch (e) { toast(e.message); }
}

// ----- market (Amazon) -----
function productCard(i) {
  const seller = seniorById(i.seller_id);
  return `<button class="product" data-item="${esc(i.id)}">
    <div class="tile">${esc(i.emoji)}<span class="cond">${esc(i.condition)}</span>${i.fresh ? '<span class="new-pill">New</span>' : ""}</div>
    <div class="body"><div class="title">${esc(i.title)}</div>
      <div class="price ${Number(i.price) ? "" : "free"}">${priceText(i.price)}</div>
      <div class="seller">${seller ? `${esc(seller.name)}, ${esc(shortYear(seller.year))}` : "A senior"}</div></div></button>`;
}

async function viewMarket() {
  try { S.data = await api("/api/bootstrap"); } catch (e) { /* use the last copy */ }
  $("#view").innerHTML = `
    <div class="search">${icon("search")}<input type="text" id="m-q" placeholder="Search lab coats, calculators, cycles…" value="${esc(S.market.q)}" aria-label="Search the market"></div>
    <div class="chips">${CATS.map((c) => `<button class="chip" data-cat="${esc(c)}" aria-pressed="${S.market.cat === c}">${esc(CAT_LABEL[c] || c)}</button>`).join("")}</div>
    <div id="m-grid"></div>`;
  const draw = () => {
    const q = S.market.q.toLowerCase().trim();
    const list = S.data.items.filter((i) => (S.market.cat === "All" || i.category === S.market.cat)
      && (!q || `${i.title} ${i.category} ${i.course || ""} ${i.description}`.toLowerCase().includes(q)));
    $("#m-grid").innerHTML = list.length
      ? `<div class="grid">${list.map(productCard).join("")}</div>`
      : `<div class="empty"><div class="big">🔎</div><h2>Nothing like that yet</h2><p>Seniors list new things every week. Try another search, or ask a senior directly.</p></div>`;
  };
  draw();
  $("#m-q").oninput = (e) => { S.market.q = e.target.value; draw(); };
  $("#view").onclick = (e) => {
    const c = e.target.closest("[data-cat]");
    if (c) { S.market.cat = c.dataset.cat; document.querySelectorAll("[data-cat]").forEach((b) => b.setAttribute("aria-pressed", b === c)); draw(); return; }
    const p = e.target.closest("[data-item]"); if (p) openItem(p.dataset.item);
  };
}

function openItem(id) {
  const i = S.data.items.find((x) => String(x.id) === String(id));
  if (!i) return;
  const s = seniorById(i.seller_id);
  openSheet(`<div class="sheet-h"><h2>${esc(i.title)}</h2>${closeBtn()}</div>
    <div class="big-tile">${esc(i.emoji)}</div>
    <div class="price ${Number(i.price) ? "" : "free"}" style="font-size:30px;margin-top:14px">${priceText(i.price)}</div>
    <p style="color:var(--soft);margin:6px 0 0">${esc(i.description)}</p>
    <dl class="kv"><dt>Condition</dt><dd>${esc(i.condition)}</dd>${i.course ? `<dt>For</dt><dd>${esc(i.course)}</dd>` : ""}
      <dt>Pick up</dt><dd>${esc(s?.spot || "On campus")}</dd></dl>
    ${s ? `<div class="item-row">${avatar(s.name)}<div class="grow"><div class="t">${esc(s.name)} ${VERIFIED.replace('class="verified"', 'class="verified" style="width:16px;height:16px;vertical-align:-3px"')}</div><div class="d">${esc(shortYear(s.year))}, ${esc(s.branch)} · ⭐ ${esc(s.rating)}</div></div></div>` : ""}
    <button class="btn btn-primary btn-block" style="margin-top:16px" id="want">${Number(i.price) ? "Request to buy" : "Request it"}</button>`);
  $("#want").onclick = async () => {
    try {
      await api("/api/item_request", { me: S.me, item_id: i.id });
      closeSheet();
      toast(`Requested. ${s ? s.name : "The senior"} will confirm pick-up.`);
      poll();
    } catch (e) { toast(e.message); }
  };
}

// ----- matches -----
function viewMatches() {
  const reqs = [...S.live.requests].sort((a, b) => b.created - a.created);
  if (!reqs.length) {
    $("#view").innerHTML = `<div class="empty"><div class="big">💌</div><h2>No matches yet</h2><p>Swipe right on a senior to ask for help, or request something in the market.</p>
      <button class="btn btn-primary" id="to-swipe">Find a senior</button></div>`;
    $("#to-swipe").onclick = () => go("seniors");
    return;
  }
  const label = { pending: "Waiting", accepted: "Matched", declined: "Not this time" };
  const row = (r) => `<button class="item-row" data-req="${esc(r.id)}">${r.kind === "item" ? `<span class="av av-m" style="background:var(--plum-3)">${esc((S.data.items.find((i) => i.id === r.item_id) || {}).emoji || "📦")}</span>` : avatar(r.senior_name)}
    <div class="grow"><div class="t">${esc(r.senior_name)}</div><div class="d">${esc(r.kind === "item" ? r.question : r.question)}</div>
      ${r.status === "accepted" && r.when ? `<div class="d" style="color:var(--mint)">${esc(r.when)}, ${esc(r.spot)}</div>` : ""}</div>
    <span class="status st-${esc(r.status)}">${label[r.status]}</span></button>`;
  const matched = reqs.filter((r) => r.status === "accepted");
  const rest = reqs.filter((r) => r.status !== "accepted");
  $("#view").innerHTML = `${matched.length ? `<div class="section-h">Matched</div><div class="list">${matched.map(row).join("")}</div>` : ""}
    ${rest.length ? `<div class="section-h">Sent</div><div class="list">${rest.map(row).join("")}</div>` : ""}`;
  $("#view").onclick = (e) => {
    const b = e.target.closest("[data-req]");
    if (b) openPlan(S.live.requests.find((r) => String(r.id) === b.dataset.req));
  };
}

function openPlan(r) {
  if (!r) return;
  const msg = r.kind === "item" ? `Hi ${r.senior_name}! I'm ${S.me}, I requested your ${r.question} on PassItOn. When can I pick it up?` : r.message;
  openSheet(`<div class="sheet-h"><h2>${esc(r.senior_name)}</h2>${closeBtn()}</div>
    <span class="status st-${esc(r.status)}">${r.status === "accepted" ? "Matched" : r.status === "pending" ? "Waiting for a reply" : "Declined"}</span>
    <dl class="kv"><dt>About</dt><dd>${esc(r.question)}</dd>${r.when ? `<dt>When</dt><dd>${esc(r.when)}</dd>` : ""}${r.spot ? `<dt>Where</dt><dd>${esc(r.spot)}</dd>` : ""}</dl>
    ${r.warning ? `<div class="notice" style="margin-bottom:12px">${esc(r.warning)}</div>` : ""}
    <div class="msg">${esc(msg)}</div>
    <button class="btn btn-primary btn-block" style="margin-top:14px" id="copy-msg">${icon("copy", 'width="18" height="18"')} Copy message</button>
    ${r.wa_link ? `<a class="btn btn-ghost btn-block" style="margin-top:10px;text-decoration:none" href="${esc(r.wa_link)}" target="_blank" rel="noopener">${icon("chat", 'width="18" height="18"')} Open WhatsApp</a>` : ""}
    ${r.trace ? `<button class="link" data-trace style="margin-top:14px">${icon("spark", 'width="16" height="16" style="vertical-align:-3px"')} How the AI planned this</button>` : ""}`);
  $("#copy-msg").onclick = () => copyText(msg);
  const t = $("#sheet [data-trace]");
  if (t) t.onclick = () => openTrace(r.trace, () => openPlan(r));
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Message copied"); }
  catch (e) {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); toast("Message copied"); } catch (e2) { toast("Couldn't copy. Long-press the message instead."); }
    ta.remove();
  }
}

function showMatch(r) {
  const o = $("#overlay");
  o.innerHTML = `<h1>It's a match!</h1>
    <div class="pair">${avatar(S.me)}${avatar(r.senior_name)}</div>
    <p style="color:var(--soft);margin:0 0 6px">${esc(r.senior_name)} said yes to helping you.</p>
    <dl class="kv"><dt>When</dt><dd>${esc(r.when)}</dd><dt>Where</dt><dd>${esc(r.spot)}</dd></dl>
    <button class="btn btn-primary" id="m-open">Send your message</button>
    <button class="btn btn-ghost" id="m-close">Keep swiping</button>`;
  o.hidden = false;
  $("#m-open").onclick = () => { o.hidden = true; openPlan(r); };
  $("#m-close").onclick = () => { o.hidden = true; };
}

// =====================================================================
// SENIOR
// =====================================================================
function openQuestions() {
  return S.live.questions.filter((q) => !S.qSkipped.has(q.id));
}

function viewQuestions() {
  const qs = openQuestions();
  S.lastQSig = qs.map((q) => q.id).join(",");
  $("#view").innerHTML = `<div class="pad"><h1 class="hello">Juniors need you</h1>
      <p class="sub">${qs.length ? `${qs.length} question${qs.length > 1 ? "s" : ""} the AI couldn't answer yet` : "You're all caught up"}</p></div>
    <div class="deck-wrap"><div class="deck" id="qdeck"></div>
      <div class="deck-actions" id="q-actions">
        <button class="round" id="q-no" aria-label="Pass">${icon("x", 'style="color:#FF6B81"')}</button>
        <button class="round yes" id="q-yes" aria-label="Answer">${icon("pen", 'stroke="#fff"')}</button>
      </div></div>`;
  const el = $("#qdeck");
  mountDeck(el, qs, 0, (q) => `<div class="card-art"></div>
      <div class="stamp yes">ANSWER</div><div class="stamp no">PASS</div>
      <div class="qtext">“${esc(q.question)}”</div>
      <div class="card-info"><div class="card-tags"><span class="tag">${esc(q.course || "General")}</span></div>
        <div class="card-meta" style="margin-top:10px">${esc(q.asked_by)} asked ${esc(ago(q.created))}</div></div>`,
  (q, dir) => { if (dir > 0) openAnswer(q); else S.qSkipped.add(q.id); }, () => {
    $("#q-actions").hidden = true;
    el.outerHTML = `<div class="empty"><div class="big">🎉</div><h2>All caught up</h2><p>When the AI can't answer a junior, their question lands here.</p></div>`;
  });
  el.classList.add("qdeck");
  swipeHint(el, "Swipe right to answer", "Swipe left to pass");
  el.querySelectorAll(".card").forEach((c) => c.classList.add("qcard"));
  new MutationObserver(() => el.querySelectorAll(".card").forEach((c) => c.classList.add("qcard"))).observe(el, { childList: true });
  $("#q-no").onclick = () => el._fly && el._fly(-1);
  $("#q-yes").onclick = () => el._fly && el._fly(1);
}

function openAnswer(q) {
  openSheet(`<div class="sheet-h"><h2>Your answer</h2>${closeBtn()}</div>
    <p style="margin:0 0 12px;color:var(--soft)">“${esc(q.question)}”</p>
    <textarea id="adv" rows="6" maxlength="1500" placeholder="What would you tell your first-year self? Be specific: places, timings, what worked."></textarea>
    <button class="btn btn-primary btn-block" style="margin-top:12px" id="post">Post answer</button>
    <p style="font-size:14px;color:var(--muted);margin:10px 0 0">Your answer becomes a tip. Every junior who asks this later gets it instantly.</p>`, true);
  setTimeout(() => $("#adv")?.focus(), 300);
  // If they close without posting, the question goes back on the pile.
  const post = $("#post");
  post.onclick = async () => {
    const advice = $("#adv").value.trim();
    if (advice.length < 10) { toast("Write at least a sentence so juniors can use it"); return; }
    post.disabled = true;
    try {
      const r = await api("/api/answer", { question_id: q.id, senior_id: S.me, advice });
      closeSheet();
      toast(`Posted. +10 points (${r.points} total)`);
      await poll();
      if (S.tab === "questions") viewQuestions();
    } catch (e) { toast(e.message); post.disabled = false; }
  };
}

function viewRequests() {
  const mine = [...S.live.requests].sort((a, b) => b.created - a.created);
  const pending = mine.filter((r) => r.status === "pending");
  const done = mine.filter((r) => r.status !== "pending");
  const row = (r) => `<div class="item-row">${avatar(r.junior)}<div class="grow">
      <div class="t">${esc(r.junior)}${r.kind === "item" ? " wants your item" : ""}</div>
      <div class="d">${esc(r.question)}</div>
      ${r.kind === "meet" && r.when ? `<div class="d">Suggested: ${esc(r.when)}, ${esc(r.spot)}</div>` : ""}
      ${r.status === "pending" ? `<div class="row-actions"><button class="btn btn-ghost" data-decline="${esc(r.id)}">Decline</button><button class="btn btn-primary" data-accept="${esc(r.id)}">Accept</button></div>` : ""}
    </div>${r.status !== "pending" ? `<span class="status st-${esc(r.status)}">${r.status === "accepted" ? "Accepted" : "Declined"}</span>` : ""}</div>`;
  $("#view").innerHTML = mine.length
    ? `${pending.length ? `<div class="section-h">New</div><div class="list">${pending.map(row).join("")}</div>` : ""}
       ${done.length ? `<div class="section-h">Earlier</div><div class="list">${done.map(row).join("")}</div>` : ""}`
    : `<div class="empty"><div class="big">🙌</div><h2>No requests yet</h2><p>When a junior swipes right on you or wants something you listed, it shows up here.</p></div>`;
  $("#view").onclick = async (e) => {
    const a = e.target.closest("[data-accept]"), d = e.target.closest("[data-decline]");
    if (!a && !d) return;
    (a || d).disabled = true;
    try {
      await api("/api/respond", { request_id: (a || d).dataset[a ? "accept" : "decline"], accept: !!a });
      toast(a ? "Accepted. They'll get your meeting details. +15 points" : "Declined");
      await poll();
      viewRequests();
    } catch (err) { toast(err.message); }
  };
}

function viewSell() {
  S.listing = null;
  $("#view").innerHTML = `<div class="pad"><h1 class="hello">Pass it on</h1><p class="sub">Snap it, add a line, and juniors who need it get pinged.</p>
    <label class="photo-pick" style="margin-top:16px" id="pick">${icon("camera")}<span>Add a photo</span>
      <input type="file" accept="image/*" capture="environment" id="photo" hidden></label>
    <div class="field"><label for="what">What is it?</label><input type="text" id="what" maxlength="200" placeholder="e.g. Mini drafter, used one semester"></div>
    <div class="field"><label for="price">Price</label><div class="price-row"><input type="number" id="price" min="0" max="50000" inputmode="numeric" placeholder="0 = free"><button class="chip" id="free" aria-pressed="true">Free</button></div></div>
    <button class="btn btn-primary btn-block" style="margin-top:16px" id="make">Create listing</button>
    <div id="preview"></div></div>`;
  S.photo = null;
  $("#photo").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      S.photo = await shrink(f);
      $("#pick").insertAdjacentHTML("beforeend", `<img alt="Your photo" src="${S.photo}">`);
    } catch (err) { toast("Couldn't read that photo. Try another one."); }
  };
  $("#price").oninput = () => $("#free").setAttribute("aria-pressed", !Number($("#price").value));
  $("#free").onclick = () => { $("#price").value = ""; $("#free").setAttribute("aria-pressed", "true"); };
  $("#make").onclick = makeListing;
}

function shrink(file) {
  // Resize big phone photos to about 900px so they upload fast.
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, 900 / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(img.src);
      resolve(c.toDataURL("image/jpeg", 0.82));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

async function makeListing() {
  const text = $("#what").value.trim();
  if (!text && !S.photo) { toast("Add a photo or a line about it"); return; }
  const btn = $("#make");
  btn.disabled = true;
  $("#preview").innerHTML = `<div class="loading"><span class="dots"><i></i><i></i><i></i></span>Writing your listing…</div>`;
  try {
    const r = await api("/api/listing", { text, image: S.photo });
    S.listing = r;
    const it = r.item;
    $("#preview").innerHTML = `<div class="answer">
        <div style="font-size:13px;color:var(--muted)">Your listing</div>
        <h2 style="font-size:22px;margin-top:4px">${esc(it.title)}</h2>
        <p style="color:var(--soft);margin:6px 0 0">${esc(it.category)}, ${esc(it.condition)}${it.course ? ` · for ${esc(it.course)}` : ""}</p>
        ${it.description && it.description !== text ? `<p style="margin-top:8px">${esc(it.description)}</p>` : ""}</div>
      ${r.buyers.length ? `<div class="notice" style="background:rgba(61,220,151,.1);border-color:rgba(61,220,151,.35)"><b>${r.buyers.length} junior${r.buyers.length > 1 ? "s are" : " is"} looking for this</b>
        <p style="margin:6px 0 0">${r.buyers.map((b) => esc(b.junior_name)).join(", ")} will be pinged when you publish.</p></div>` : ""}
      <button class="btn btn-primary btn-block" style="margin-top:14px" id="publish">Publish to market</button>`;
    $("#publish").onclick = publish;
  } catch (e) {
    $("#preview").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`;
  } finally { btn.disabled = false; }
}

async function publish() {
  const b = $("#publish");
  b.disabled = true;
  try {
    await api("/api/publish", { senior_id: S.me, item: S.listing.item, price: Number($("#price").value) || 0 });
    toast("Published. +5 points");
    await poll();
    go("me");
  } catch (e) { toast(e.message); b.disabled = false; }
}

function viewMe() {
  const s = seniorById(S.me) || {};
  const live = S.live.me || {};
  const pts = S.live.points || 0;
  const goal = 100;
  $("#view").innerHTML = `<div class="profile">${avatar(s.name || "S")}<div><h1>${esc(s.name)}</h1>
      <div class="sub" style="margin:2px 0 0">${esc(shortYear(s.year))}, ${esc(s.branch)}</div>
      <div class="mentor">${VERIFIED.replace('class="verified"', 'style="width:16px;height:16px"')} Verified VIT mentor</div></div></div>
    <div class="stats"><div class="stat"><b>${esc(live.tips ?? s.tips ?? 0)}</b><span>Tips written</span></div>
      <div class="stat"><b>${esc(live.helped ?? 0)}</b><span>Juniors met</span></div>
      <div class="stat"><b>${pts}</b><span>Points</span></div></div>
    <div class="section-h">Next reward</div>
    <div class="card-box"><b>Free coffee at the campus café</b><div class="meter"><i style="width:${Math.min(100, (pts / goal) * 100)}%"></i></div>
      <div style="font-size:14px;color:var(--muted);margin-top:8px">${pts >= goal ? "Unlocked! Show this screen at the counter." : `${goal - pts} points to go. Answers +10, meet-ups +15, listings +5.`}</div></div>
    <div class="section-h">Your listings</div>
    ${S.live.items.length ? `<div class="grid" style="padding-top:0">${S.live.items.map(productCard).join("")}</div>` : `<p class="pad" style="color:var(--muted)">Nothing listed yet. Pass on a lab coat or calculator in a minute.</p>`}`;
}

// ---------- live updates ----------
async function poll() {
  if (!S.role || !S.me) return;
  try {
    const st = await api(`/api/state?role=${S.role}&me=${encodeURIComponent(S.me)}`);
    S.live = { requests: [], questions: [], items: [], points: 0, me: {}, ...st };
  } catch (e) { return; }
  if (S.role === "junior") {
    const accepted = S.live.requests.filter((r) => r.status === "accepted" && r.kind === "meet");
    if (S.seenAccepted === null) S.seenAccepted = new Set(accepted.map((r) => r.id));
    const fresh = accepted.find((r) => !S.seenAccepted.has(r.id));
    if (fresh) { S.seenAccepted.add(fresh.id); if ($("#overlay").hidden) showMatch(fresh); }
    S.live.requests.filter((r) => r.kind === "item" && r.status === "accepted" && !S.seenAccepted.has(r.id)).forEach((r) => {
      S.seenAccepted.add(r.id); toast(`${r.senior_name} is passing on the ${r.question}!`);
    });
    setBadge("matches", S.live.requests.filter((r) => r.status === "accepted").length);
    if (S.tab === "matches" && $("#sheet").hidden) viewMatches();
  } else {
    const pending = S.live.requests.filter((r) => r.status === "pending");
    if (S.seenRequests === null) S.seenRequests = new Set(pending.map((r) => r.id));
    const fresh = pending.filter((r) => !S.seenRequests.has(r.id));
    fresh.forEach((r) => S.seenRequests.add(r.id));
    if (fresh.length) toast(`${fresh[0].junior} wants your help`);
    setBadge("requests", pending.length);
    const qs = openQuestions();
    const sig = qs.map((q) => q.id).join(",");
    // A question arrived or was answered by someone else: redraw the deck, unless they're mid-swipe or typing.
    if (S.tab === "questions" && sig !== S.lastQSig && $("#sheet").hidden && !$("#qdeck .card.dragging")) viewQuestions();
    S.lastQSig = sig;
    setBadge("questions", qs.length);
    if (S.tab === "requests" && fresh.length && $("#sheet").hidden) viewRequests();
  }
}
function setBadge(tab, n) {
  const b = document.querySelector(`[data-badge="${tab}"]`);
  if (!b) return;
  b.hidden = !n;
  b.textContent = n > 9 ? "9+" : n;
}

boot();

// ---------- first-time tutorial ----------
const TOURS = {
  junior: [
    { art: "🙋", title: "Ask anything about VIT", text: "FFCS, CAT prep, clubs, hostel life. Answers come from seniors who've already been through it." },
    { art: "swipe", title: "Swipe right to ask a senior", text: "Right means “help me”, left means skip. When a senior says yes, it's a match, and we suggest a time and place." },
    { art: "🥼", title: "Grab what seniors pass on", text: "Lab coats, calculators, EG kits and hostel gear, mostly free. Request it and pick it up on campus." },
  ],
  senior: [
    { art: "✍️", title: "Answer once, help every junior", text: "Questions the AI couldn't answer land here. Your answer becomes a tip that juniors get instantly from then on." },
    { art: "swipe", title: "Say yes to juniors", text: "Juniors who swipe right on you show up in Requests. Accept, and they get a meeting time and place." },
    { art: "🎁", title: "Pass it on, earn points", text: "List your old stuff in seconds. Answers, meet-ups and listings earn points towards café rewards." },
  ],
};

function tourArt(art) {
  // The swipe slide gets a tiny animated card instead of an emoji.
  if (art !== "swipe") return `<div class="tour-art"><span>${art}</span></div>`;
  const label = S.role === "senior" ? "ANSWER" : "ASK";
  return `<div class="tour-art"><div class="mini-card"><b>${S.role === "senior" ? "?" : "A"}</b><i>${label}</i></div><span class="hand">👆</span></div>`;
}

function showTour(force) {
  const key = `pio_tour_${S.role}`;
  S.toured = S.toured || {};
  if (!force && (store(key) || S.toured[S.role])) return;
  S.toured[S.role] = true;
  const slides = TOURS[S.role];
  const el = $("#tour");
  el.innerHTML = `<button class="tour-skip" id="tour-skip">Skip</button>
    <div class="tour-track" id="tour-track">${slides.map((s) => `<section class="tour-slide">${tourArt(s.art)}<h1>${esc(s.title)}</h1><p>${esc(s.text)}</p></section>`).join("")}</div>
    <div class="tour-foot"><div class="tour-dots">${slides.map((_, i) => `<i data-dot="${i}"></i>`).join("")}</div>
      <button class="btn btn-primary btn-block" id="tour-next">Next</button></div>`;
  el.hidden = false;
  const track = $("#tour-track");
  const at = () => Math.round(track.scrollLeft / track.clientWidth);
  const sync = () => {
    const i = at();
    el.querySelectorAll("[data-dot]").forEach((d) => d.classList.toggle("on", Number(d.dataset.dot) === i));
    $("#tour-next").textContent = i === slides.length - 1 ? "Let's go" : "Next";
  };
  const done = () => {
    el.hidden = true; el.innerHTML = ""; store(key, "1");
    const next = S.afterTour; S.afterTour = null;
    if (next) next();
  };
  track.addEventListener("scroll", () => requestAnimationFrame(sync));
  $("#tour-next").onclick = () => {
    const i = at();
    if (i >= slides.length - 1) done();
    else track.scrollTo({ left: (i + 1) * track.clientWidth, behavior: "smooth" });
  };
  $("#tour-skip").onclick = done;
  sync();
  $("#tour-next").focus();
}

function swipeHint(deckEl, right, left) {
  // One-time hand animation over the deck; gone on the first touch.
  const key = `pio_hint_${S.role}`;
  S.hinted = S.hinted || {};
  if (store(key) || S.hinted[S.role] || !deckEl || !deckEl.querySelector(".card")) return;
  if (!$("#tour").hidden) { S.afterTour = () => swipeHint($(deckEl.id ? "#" + deckEl.id : ".deck"), right, left); return; }
  const hint = document.createElement("div");
  hint.className = "swipe-hint";
  hint.innerHTML = `<span class="hand">👆</span><p><b>${esc(right)}</b><br>${esc(left)}</p>`;
  deckEl.appendChild(hint);
  const gone = () => { hint.remove(); store(key, "1"); S.hinted[S.role] = true; };
  hint.addEventListener("pointerdown", gone);
  deckEl.addEventListener("pointerdown", gone, { once: true });
}
