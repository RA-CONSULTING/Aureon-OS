/* Aureon Watch — voice-first, thin client.
   mic -> browser STT -> existing /api SSE -> tokens -> browser TTS.
   No PC load; the data centre is a black box. Same-origin, no CORS. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const api = (p, opt) => fetch(p, opt).then((r) => r.ok ? r.json() : Promise.reject(r.status));

  const QUICK = [
    "What is the current system status?",
    "What is the organism doing right now?",
    "Summarise Aureon's latest research.",
    "How does Aureon ground and gate an answer?",
    "What can this platform do for me today?",
  ];
  const TRADING_PROMPT =
    "Give me a strictly read-only summary of the current trading state and any open " +
    "positions or exposure. Do not take, propose, or prepare any action — reporting only.";

  // ── screen deck + dots ──────────────────────────────────────────────────
  const deck = $("deck");
  const screens = [...document.querySelectorAll(".screen")];
  const dotsWrap = $("dots");
  screens.forEach((s, i) => {
    const b = document.createElement("b");
    b.title = s.getAttribute("aria-label") || s.dataset.screen;
    b.addEventListener("click", () => s.scrollIntoView({ behavior: "smooth" }));
    dotsWrap.appendChild(b);
  });
  const dots = [...dotsWrap.children];
  const loaded = {};
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        const i = screens.indexOf(e.target);
        dots.forEach((d, j) => d.classList.toggle("on", j === i));
        const name = e.target.dataset.screen;
        if (!loaded[name]) { loaded[name] = true; onEnter(name); }
      }
    });
  }, { root: deck, threshold: 0.6 });
  screens.forEach((s) => io.observe(s));

  function onEnter(name) {
    if (name === "pulse" || name === "organism") refreshPulse();
    if (name === "systems") loadSystems();
    if (name === "approvals") loadApprovals();
  }

  // ── APPROVALS (the director's desk — one-tap approve/reject, records only) ─
  function loadApprovals() {
    api("/api/approvals").then((d) => {
      const pend = (d && d.pending) || [];
      if (!pend.length) { $("appr-list").innerHTML = '<div class="muted">desk clear</div>'; return; }
      $("appr-list").innerHTML = pend.map((it) =>
        `<div class="item" data-id="${esc(it.id)}"><div class="t">${esc(it.kind)} · risk ${esc(it.risk)}</div>` +
        `<div class="s">${esc(it.summary || "")}</div>` +
        `<div class="apr-btns"><button class="ok" data-d="approve">Approve</button>` +
        `<button class="no" data-d="reject">Reject</button></div></div>`).join("");
      $("appr-list").querySelectorAll(".item").forEach((el) => {
        el.querySelectorAll("button").forEach((b) =>
          b.addEventListener("click", () => decideApproval(el.getAttribute("data-id"), b.getAttribute("data-d"))));
      });
    }).catch(() => { $("appr-list").innerHTML = '<div class="muted">approvals unavailable</div>'; });
  }

  function decideApproval(id, decision) {
    api("/api/approvals/" + id, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    }).then(() => loadApprovals()).catch(() => { /* stays pending */ });
  }

  // ── line-up ─────────────────────────────────────────────────────────────
  api("/healthz").then((d) => {
    $("lineup").textContent = "· " + ((d.providers || []).map((p) => p.name).join(" · ") || "offline");
  }).catch(() => { $("lineup").textContent = "· offline"; });

  // ── voice: speech-to-text + text-to-speech ───────────────────────────────
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const canTTS = "speechSynthesis" in window;
  let rec = null, listening = false, busy = false;
  const orb = $("mic"), orbLabel = $("orb-label");

  function speak(text) {
    if (!canTTS || !$("t-tts").checked || !text) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text.slice(0, 600));
      u.rate = 1.02; u.pitch = 1.0;
      window.speechSynthesis.speak(u);
    } catch (_) { /* TTS optional */ }
  }

  function setOrb(state) {
    orb.classList.toggle("listening", state === "listening");
    orb.classList.toggle("busy", state === "busy");
    orbLabel.textContent =
      state === "listening" ? "Listening…" : state === "busy" ? "Thinking…" : "Tap to speak";
  }

  function extractPrompt(transcript) {
    const t = transcript.trim();
    const m = t.match(/\b(?:hey\s+)?aureon\b[,:]?\s*(.*)$/i);
    if (m) return m[1].trim();          // wake-word: take what follows "Aureon"
    return $("t-wake").checked ? "" : t; // hands-free requires the wake word; tap-to-talk takes all
  }

  function startListen() {
    if (!SR) { $("prompt").focus(); return; }
    if (listening) { stopListen(); return; }
    try {
      rec = new SR();
      rec.lang = "en-GB"; rec.interimResults = false; rec.maxAlternatives = 1;
      rec.continuous = false;
      rec.onstart = () => { listening = true; setOrb("listening"); };
      rec.onerror = () => { listening = false; if (!busy) setOrb("idle"); };
      rec.onend = () => { listening = false; if (!busy) setOrb("idle"); };
      rec.onresult = (ev) => {
        const said = ev.results[ev.results.length - 1][0].transcript || "";
        const q = extractPrompt(said);
        if (q) ask(q);
      };
      rec.start();
    } catch (_) { $("prompt").focus(); }
  }
  function stopListen() { try { rec && rec.stop(); } catch (_) {} listening = false; setOrb(busy ? "busy" : "idle"); }
  orb.addEventListener("click", startListen);

  // hide voice hint if unsupported
  if (!SR) { orbLabel.textContent = "Type below"; $("t-wake").parentElement.style.opacity = ".4"; }

  // ── ASK: stream over SSE (reuses the operator/cognition event contract) ───
  const chipsWrap = $("chips"), answerEl = $("answer"), verdictEl = $("verdict");
  let es = null;

  function ask(q) {
    q = (q || "").trim(); if (!q || busy) return;
    if (es) { try { es.close(); } catch (_) {} }
    busy = true; setOrb("busy");
    if (canTTS) { try { window.speechSynthesis.cancel(); } catch (_) {} }
    verdictEl.textContent = ""; verdictEl.className = "verdict";
    answerEl.textContent = ""; chipsWrap.innerHTML = "";
    $("send").disabled = true;

    const cog = $("t-cog").checked;
    const steps = cog ? ["grounding", "tool", "veto"] : ["ground", "fan_out", "consensus", "veto"];
    const chipEls = {};
    steps.forEach((p) => {
      const c = document.createElement("span"); c.className = "chip"; c.textContent = p;
      chipsWrap.appendChild(c); chipEls[p] = c;
    });

    let answer = "";
    const base = cog ? "/api/cognition/stream" : "/api/operator/stream";
    es = new EventSource(base + "?prompt=" + encodeURIComponent(q));
    es.addEventListener("phase", (e) => {
      const d = JSON.parse(e.data);
      const c = chipEls[d.phase]; if (!c) return; c.classList.add("on");
      if (d.phase === "fan_out" && d.detail) c.textContent = "fan " + d.detail.n_ok + "/" + d.detail.n_total;
      if (d.phase === "consensus" && d.detail) c.textContent = Math.round((d.detail.agreement || 0) * 100) + "%";
    });
    es.addEventListener("grounding", (e) => {
      const d = (JSON.parse(e.data).detail) || {}; const c = chipEls.grounding;
      if (c) { c.classList.add("on"); c.textContent = (d.source_count || 0) + " src"; }
    });
    es.addEventListener("tool", (e) => {
      const d = (JSON.parse(e.data).detail) || {}; const c = chipEls.tool;
      if (c) { c.classList.add("on"); c.textContent = "🔧 " + (d.tool || "tool"); }
    });
    es.addEventListener("veto", (e) => {
      const d = (JSON.parse(e.data).detail) || {}; const c = chipEls.veto;
      if (c) { c.classList.add("on"); c.textContent = "veto " + (d.verdict || ""); }
    });
    es.addEventListener("token", (e) => {
      answer += JSON.parse(e.data).text; answerEl.textContent = answer;
      answerEl.scrollTop = answerEl.scrollHeight;
    });
    es.addEventListener("complete", (e) => {
      const d = (JSON.parse(e.data).response) || {};
      verdictEl.className = "verdict" + (d.blocked ? " veto" : "");
      verdictEl.textContent = "🦗 " + (d.conscience_verdict || "—") +
        (d.grounding ? " · " + (d.grounding.source_count || 0) + " src" : "");
      finishAsk(); speak(answer);
    });
    es.onerror = () => { if (!answer) answerEl.textContent = "[stream unavailable]"; finishAsk(); };
  }
  function finishAsk() {
    if (es) { try { es.close(); } catch (_) {} es = null; }
    busy = false; $("send").disabled = false; setOrb("idle");
    if ($("t-wake").checked && SR) setTimeout(startListen, 700); // hands-free re-arm
  }

  $("askform").addEventListener("submit", (e) => {
    e.preventDefault(); const v = $("prompt").value; $("prompt").value = "";
    if (v.trim()) { document.getElementById("s-ask").scrollIntoView(); ask(v); }
  });

  // ── PULSE + ORGANISM (one composed read-only call) ────────────────────────
  let pulseTimer = null;
  function refreshPulse() {
    api("/api/pulse").then(renderPulse).catch(() => {
      $("p-status").textContent = "offline"; $("o-cov").textContent = "—";
    });
    clearTimeout(pulseTimer); pulseTimer = setTimeout(refreshPulse, 20000);
  }
  function renderPulse(d) {
    const st = (d.status || {});
    const label = st.status || (d.ok ? "ok" : "down");
    $("p-status").textContent = label;
    $("live-dot").className = "dot" + (label === "healthy" ? "" : label === "critical" ? " veto" : " warn");
    const rows = [];
    rows.push(["providers", (d.providers || []).map((p) => p.name).join(", ") || "—"]);
    if (st.domains_reachable != null) rows.push(["domains", st.domains_reachable + "/" + st.domains_total]);
    const org = d.organism || {};
    rows.push(["organism", org.available ? "live" : "resting"]);
    const my = (org.mycelium && org.mycelium.connected_systems) || [];
    rows.push(["mycelium", my.length + " systems"]);
    rows.push(["pulses", (org.recent_pulses || []).length + " recent"]);
    $("p-body").innerHTML = rows.map(([k, v]) =>
      `<div class="row"><b>${esc(k)}</b><span>${esc(v)}</span></div>`).join("");
    renderOrganism(org);
  }
  function renderOrganism(org) {
    const con = org.connectome || {};
    // coverage: prefer an explicit coverage-like field, else connected count
    let cov = "—";
    for (const k of Object.keys(con)) {
      if (/coverage|wired|percent|ratio/i.test(k) && typeof con[k] === "number") {
        cov = con[k] <= 1 ? Math.round(con[k] * 100) + "%" : con[k]; break;
      }
    }
    if (cov === "—") { const my = (org.mycelium && org.mycelium.connected_systems) || []; cov = my.length || "—"; }
    $("o-cov").textContent = cov;
    const rows = [];
    for (const [k, v] of Object.entries(con)) {
      if (typeof v === "number" || typeof v === "string") rows.push([k, v]);
    }
    (org.recent_pulses || []).slice(0, 3).forEach((p, i) =>
      rows.push(["pulse " + (i + 1), (p && (p.summary || p.title || p.kind || p.event)) || "…"]));
    $("o-body").innerHTML = rows.length
      ? rows.map(([k, v]) => `<div class="row"><b>${esc(k)}</b><span>${esc(v)}</span></div>`).join("")
      : '<div class="muted">organism resting</div>';
  }

  // ── SYSTEMS (catalog: what Aureon can do) ─────────────────────────────────
  function loadSystems() {
    api("/api/catalog").then((d) => {
      const cats = d.categories || {};
      const entries = Object.entries(cats);
      $("sys-sub").textContent = (d.total_systems || "?") + " systems · " + entries.length + " categories";
      $("sys-list").innerHTML = entries.map(([name, c]) => {
        const sys = (c.systems || []).slice(0, 8).map((s) => esc(s.name)).join(", ");
        return `<div class="item" data-cat="${esc(name)}"><div class="t">${esc(c.icon || "")} ${esc(name)}` +
          ` · ${c.system_count || (c.systems || []).length}</div>` +
          `<div class="s" hidden>${sys || esc(c.description || "")}</div></div>`;
      }).join("") || '<div class="muted">no catalog</div>';
      $("sys-list").querySelectorAll(".item").forEach((it) =>
        it.addEventListener("click", () => {
          const s = it.querySelector(".s"); if (s) s.hidden = !s.hidden;
        }));
    }).catch(() => { $("sys-list").innerHTML = '<div class="muted">catalog unavailable</div>'; });
  }

  // ── TRADING (read-only, via gated cognition) ──────────────────────────────
  function readTrading() {
    $("tr-body").innerHTML = '<div class="muted">reading state…</div>';
    api("/api/cognition/reason", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: TRADING_PROMPT }),
    }).then((d) => {
      $("tr-body").textContent = (d && d.text) || "no state returned";
      speak(d && d.text);
    }).catch(() => { $("tr-body").innerHTML = '<div class="muted">state unavailable</div>'; });
  }

  // ── QUICK prompts ─────────────────────────────────────────────────────────
  $("quick").innerHTML = QUICK.map((q, i) => `<button class="q" data-q="${i}">${esc(q)}</button>`).join("");
  $("quick").querySelectorAll(".q").forEach((b) =>
    b.addEventListener("click", () => {
      document.getElementById("s-ask").scrollIntoView({ behavior: "smooth" });
      setTimeout(() => ask(QUICK[+b.dataset.q]), 400);
    }));

  // refresh buttons
  document.querySelectorAll("[data-refresh]").forEach((b) =>
    b.addEventListener("click", () => {
      const w = b.dataset.refresh;
      if (w === "systems") loadSystems();
      else if (w === "trading") readTrading();
      else refreshPulse();
    }));

  // ── PWA + connectivity ────────────────────────────────────────────────────
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () =>
      navigator.serviceWorker.register("/watch/sw.js", { scope: "/watch/" }).catch(() => {}));
  }
  const off = $("offline");
  const setNet = () => { off.hidden = navigator.onLine; };
  window.addEventListener("online", setNet); window.addEventListener("offline", setNet); setNet();
})();
