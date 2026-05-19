(() => {
  "use strict";

  const state = {
    language: "en",
    messages: [],
    observers: [
      { id: "gemma", label: "Gemma Context Observer", status: "idle", notes: "Conversation context" },
      { id: "aureon", label: "Aureon Queen Observer", status: "linked", notes: "Supervisor and organism state" },
    ],
    lastSupervisor: null,
    flameballPlan: null,
  };

  const providerModels = {
    gemini: ["gemini-1.5-flash", "gemini-2.0-flash-exp"],
    openrouter: ["openrouter/free", "google/gemma-4-31b-it:free", "meta-llama/llama-3.1-8b-instruct:free"],
    aureon: ["aureon-brain", "aureon-queen", "aureon-council", "aureon-architect", "aureon-vault"],
    huggingface: ["Qwen/Qwen2.5-7B-Instruct", "HuggingFaceH4/zephyr-7b-beta", "microsoft/Phi-3-mini-4k-instruct"],
    grok: ["grok-2-latest"],
    openai: ["gpt-4o-mini", "gpt-4o"],
  };

  const $ = (id) => document.getElementById(id);

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function asList(value) {
    if (Array.isArray(value)) return value;
    if (value && typeof value === "object") return Object.values(value);
    return [];
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new Error(data?.error?.message || `${response.status} ${response.statusText}`);
    }
    return data;
  }

  async function postJson(url, body) {
    return fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  function setText(id, text) {
    const node = $(id);
    if (node) node.textContent = text;
  }

  function setHtml(id, html) {
    const node = $(id);
    if (node) node.innerHTML = html;
  }

  function setStatus(text, tone = "info") {
    const node = $("status");
    if (!node) return;
    node.textContent = text;
    node.dataset.tone = tone;
  }

  function selectedValue(id, fallback = "") {
    return $(id)?.value || fallback;
  }

  function updateModels() {
    const provider = selectedValue("provider", "aureon");
    const modelSelect = $("model");
    if (!modelSelect) return;
    modelSelect.innerHTML = "";
    for (const model of providerModels[provider] || ["default"]) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      modelSelect.appendChild(option);
    }
    updateActiveLabels();
  }

  function updateActiveLabels() {
    const provider = selectedValue("provider", "aureon");
    const model = selectedValue("model", "aureon-brain");
    const engine = selectedValue("assistantEngine", "standard");
    setText("activeModelLabel", `${provider} / ${model} / ${engine}`);
    const hint = {
      standard: "Standard chat through the selected provider.",
      codex: "Codex persona for software and repo work; provider still controls the chat route.",
      aureon: "Aureon local bridge through Phi, supervisor, and vault context.",
      flameball: "Aureon flAmeBall mode for local planning and guarded execution.",
      terminal: "Local terminal is guarded by MURGE_HOST_TERMINAL_ENABLED.",
      sandbox: "Docker sandbox is guarded by MURGE_SANDBOX_ENABLED.",
    }[engine] || "Choose an agent persona for this PC.";
    setText("assistantEngineHint", hint);
  }

  function appendMessage(role, text, extraClass = "") {
    const container = $("chatMessages");
    if (!container) return null;
    const node = document.createElement("div");
    node.className = `message ${role}${extraClass ? ` ${extraClass}` : ""}`;
    node.textContent = text;
    container.appendChild(node);
    container.scrollTop = container.scrollHeight;
    state.messages.push({ role, text, createdAt: new Date().toISOString() });
    return node;
  }

  function removeNode(node) {
    if (node?.parentNode) node.parentNode.removeChild(node);
  }

  function rolePrompt() {
    const role = selectedValue("role", "assistant");
    const route = selectedValue("swarmRoute", "direct");
    const supervisor = state.lastSupervisor;
    const gates = supervisor?.liveGates || {};
    return [
      `You are ${role} inside the Flameborn UI connected to Aureon.`,
      `Swarm route: ${route}.`,
      `Aureon supervisor: ${supervisor?.status || "unknown"}.`,
      `Trade path: ${gates.tradePathState || "unknown"}.`,
      "Do not create manual trading controls or bypass runtime gates.",
    ].join(" ");
  }

  async function sendChat() {
    const input = $("userInput");
    const message = input?.value.trim() || "";
    if (!message) return;
    const engine = selectedValue("assistantEngine", "standard");
    const provider = engine === "aureon" || engine === "flameball" || $("localAureonAssistant")?.checked
      ? "aureon"
      : selectedValue("provider", "aureon");
    const model = selectedValue("model", providerModels[provider]?.[0] || "aureon-brain");
    appendMessage("user", message);
    input.value = "";
    const loading = appendMessage("loading", "Aureon is routing the request...");
    setStatus("Sending through the selected local bridge...", "info");
    try {
      const endpoint = provider === "aureon" ? "/api/aureon/chat" : "/api/chat";
      const response = await postJson(endpoint, {
        provider,
        model,
        message,
        rolePrompt: rolePrompt(),
        accessMode: selectedValue("accessMode", "free"),
        temperature: Number(selectedValue("temperature", "0.7")),
        responseStyle: selectedValue("aureonResponseStyle", "safe"),
        swarmRoute: selectedValue("swarmRoute", "direct"),
      });
      removeNode(loading);
      appendMessage("assistant", response.reply || response.text || JSON.stringify(response, null, 2));
      setStatus(response.bridgeConnected === false ? "Local vault fallback used." : "Response received.", response.bridgeConnected === false ? "warn" : "ok");
      if ($("classroomMode")?.checked) {
        mirrorConversation(message, response.reply || "");
      }
    } catch (error) {
      removeNode(loading);
      appendMessage("assistant", `Route blocked or unavailable: ${error.message}`);
      setStatus(error.message, "warn");
    }
  }

  async function mirrorConversation(userText, assistantText) {
    try {
      await postJson("/api/classroom/observe", {
        depth: selectedValue("observerDepth", "standard"),
        conversation: {
          user: userText,
          assistant: assistantText,
          provider: selectedValue("provider", "aureon"),
          model: selectedValue("model", "aureon-brain"),
        },
      });
      await loadClassroomState();
    } catch {
      setText("streamStatus", "observer blocked");
    }
  }

  function renderSystems(payload) {
    const capabilities = payload?.capabilities || {};
    const systems = asList(capabilities.systems);
    const liveRows = asList(payload?.liveCapabilityRows);
    const artifactRows = asList(payload?.artifactRows);
    const detected = Number(capabilities.detected || 0);
    const total = Number(capabilities.total || systems.length || 0);
    const liveGate = payload?.liveGates?.tradePathState || "unknown";
    const liveHtml = liveRows.map((row) => `
      <div class="aureon-system-item system-live">
        <div class="aureon-system-top">
          <strong>${escapeHtml(row.label || row.id)}</strong>
          <span>${escapeHtml(row.status || "visible")}</span>
        </div>
        <p>${escapeHtml(row.endpoint || row.mode || row.id || "")}</p>
      </div>
    `).join("");
    const artifactHtml = artifactRows.map((row) => `
      <div class="aureon-system-item ${row.exists ? "system-live" : "system-missing"}">
        <div class="aureon-system-top">
          <strong>${escapeHtml(row.label || row.id)}</strong>
          <span>${escapeHtml(row.status || (row.exists ? "present" : "missing"))}</span>
        </div>
        <p>${escapeHtml(row.updatedAt || row.path || "")}</p>
      </div>
    `).join("");
    const systemHtml = systems.slice(0, 14).map((system) => `
      <div class="aureon-system-item ${system.exists ? "system-live" : "system-missing"}">
        <div class="aureon-system-top">
          <strong>${escapeHtml(system.label)}</strong>
          <span>${system.exists ? "wired" : "missing"}</span>
        </div>
        <p>${escapeHtml(system.purpose || system.relativePath)}</p>
      </div>
    `).join("");
    setHtml("aureonSystemsCard", `
      <div class="aureon-systems-summary">
        <strong>${detected}/${total} repo capabilities</strong>
        <span>trade path ${escapeHtml(liveGate)}</span>
      </div>
      <div class="aureon-systems-list">${liveHtml}${artifactHtml}${systemHtml}</div>
    `);
  }

  function renderFullCapabilityStress(report) {
    const summary = report?.summary || {};
    const rows = asList(report?.status_rows);
    const actions = asList(report?.next_repair_actions);
    const required = `${summary.required_status_pass_count ?? 0}/${summary.required_status_count ?? 0}`;
    const status = report?.status || "artifact_missing";
    const rowHtml = rows.slice(0, 14).map((row) => `
      <div class="aureon-system-item ${row.passed ? "system-live" : "system-missing"}">
        <div class="aureon-system-top">
          <strong>${escapeHtml(row.label || row.id)}</strong>
          <span>${escapeHtml(row.status || (row.passed ? "passing" : "attention"))}</span>
        </div>
        <p>${escapeHtml(row.passed ? row.id : row.next_action || row.blocker_id || row.id)}</p>
      </div>
    `).join("");
    const actionHtml = actions.slice(0, 4).map((action) => `
      <div class="aureon-system-item system-missing">
        <div class="aureon-system-top">
          <strong>${escapeHtml(action.id || action.status_row || "repair")}</strong>
          <span>${escapeHtml(action.severity || "attention")}</span>
        </div>
        <p>${escapeHtml(action.action || "")}</p>
      </div>
    `).join("");
    setHtml("fullCapabilityStressCard", `
      <div class="aureon-systems-summary">
        <strong>${escapeHtml(status)}</strong>
        <span>${escapeHtml(required)} proof rows</span>
      </div>
      <div class="aureon-systems-list">
        <div class="aureon-system-item ${summary.no_trading_gate_bypass ? "system-live" : "system-missing"}">
          <div class="aureon-system-top"><strong>No trading bypass</strong><span>${summary.no_trading_gate_bypass ? "visible" : "attention"}</span></div>
          <p>Live gate visibility ${summary.live_trade_gate_visibility ? "passing" : "needs proof"}; broker mutation remains runtime-owned.</p>
        </div>
        <div class="aureon-system-item ${summary.thoughtbus_receiving && summary.mycelium_receiving ? "system-live" : "system-missing"}">
          <div class="aureon-system-top"><strong>ThoughtBus + Mycelium</strong><span>${summary.thoughtbus_receiving && summary.mycelium_receiving ? "receiving" : "attention"}</span></div>
          <p>ThoughtBus ${summary.thoughtbus_receiving ? "yes" : "no"}; Mycelium ${summary.mycelium_receiving ? "yes" : "no"}.</p>
        </div>
        ${rowHtml || `<div class="empty-panel">Full capability stress artifact is not ready yet.</div>`}
        ${actionHtml}
      </div>
    `);
  }

  function renderSupervisor(supervisor) {
    state.lastSupervisor = supervisor;
    const gates = supervisor.liveGates || {};
    const gateSummary = [
      `intent ${gates.orderIntentPublishEnabled ? "on" : "off"}`,
      `executor ${gates.executorEnabled ? "on" : "off"}`,
      `live ${gates.liveEnabled ? "on" : "off"}`,
      `real orders ${gates.realOrdersDisabled ? "disabled" : "enabled"}`,
      `mutations ${gates.exchangeMutationsDisabled ? "disabled" : "enabled"}`,
    ].join(" | ");
    setText("providerStatus", `Supervisor ${supervisor.status}; ${gateSummary}`);
    const badge = document.querySelector(".system-badge strong");
    if (badge) badge.textContent = supervisor.supervisorConnected ? "Aureon linked" : "Aureon attention";
    const badgeStatus = document.querySelector(".system-badge span");
    if (badgeStatus) badgeStatus.textContent = supervisor.phiBridgeConnected ? "Phi bridge online" : "Core checking";
  }

  async function refreshAureon() {
    try {
      const [status, systems, supervisor, fullCapabilityStress] = await Promise.all([
        fetchJson("/api/aureon/status"),
        fetchJson("/api/aureon/systems"),
        fetchJson("/api/aureon/supervisor"),
        fetchJson("/api/aureon/full-capability-stress").catch((error) => ({
          status: "artifact_missing",
          summary: {},
          status_rows: [],
          next_repair_actions: [{ id: "artifact_missing", severity: "attention", action: error.message }],
        })),
      ]);
      renderSupervisor(supervisor);
      renderSystems(systems);
      renderFullCapabilityStress(fullCapabilityStress);
      renderDesktopStatus(status, supervisor);
      setStatus("Flameborn is connected to Aureon supervisor surfaces.", "ok");
    } catch (error) {
      setHtml("aureonSystemsCard", `<div class="empty-panel">Aureon supervisor unavailable: ${escapeHtml(error.message)}</div>`);
      setHtml("fullCapabilityStressCard", `<div class="empty-panel">Full launch proof unavailable: ${escapeHtml(error.message)}</div>`);
      setStatus(`Aureon supervisor unavailable: ${error.message}`, "warn");
    }
  }

  function renderDesktopStatus(status, supervisor) {
    const activation = status.activation || {};
    const blockers = asList(supervisor.blockers).slice(0, 6);
    setText("desktopModeLabel", activation.localOnly ? "Local-only mode" : "Remote bind attention");
    setHtml("desktopStatusCard", `
      <div class="aureon-systems-summary">
        <strong>${escapeHtml(supervisor.status || "checking")}</strong>
        <span>${activation.noTradingGateBypass ? "no trading bypass" : "attention"}</span>
      </div>
      <div class="aureon-systems-list">
        <div class="aureon-system-item ${activation.hostTerminalEnabled ? "system-live" : "system-missing"}">
          <div class="aureon-system-top"><strong>Host terminal</strong><span>${activation.hostTerminalEnabled ? "enabled" : "guarded off"}</span></div>
          <p>MURGE_HOST_TERMINAL_ENABLED</p>
        </div>
        <div class="aureon-system-item ${activation.sandboxEnabled ? "system-live" : "system-missing"}">
          <div class="aureon-system-top"><strong>Docker sandbox</strong><span>${activation.sandboxEnabled ? "enabled" : "guarded off"}</span></div>
          <p>MURGE_SANDBOX_ENABLED</p>
        </div>
        <div class="aureon-system-item system-live">
          <div class="aureon-system-top"><strong>Blockers</strong><span>${blockers.length}</span></div>
          <p>${escapeHtml(blockers.join(", ") || "none visible")}</p>
        </div>
      </div>
    `);
  }

  async function loadClassroomState() {
    try {
      const [classroom, meta] = await Promise.all([
        fetchJson("/api/classroom/state"),
        fetchJson("/api/metacognition"),
      ]);
      renderObservers(classroom);
      renderMetacognition(meta.monitor || {});
    } catch {
      renderObservers(null);
    }
  }

  function renderObservers(classroom) {
    const observerRows = asList(classroom?.observers).length ? asList(classroom.observers) : state.observers;
    setHtml("observerCards", observerRows.map((observer) => `
      <div class="aureon-system-item system-live">
        <div class="aureon-system-top"><strong>${escapeHtml(observer.label || observer.id)}</strong><span>${escapeHtml(observer.status || "idle")}</span></div>
        <p>${escapeHtml(observer.notes || observer.lastRunAt || "ready")}</p>
      </div>
    `).join(""));
    setText("classroomState", `${observerRows.length} observer lane(s) visible`);
    setHtml("contextStream", state.messages.slice(-6).map((message) => `
      <div class="aureon-system-item">
        <div class="aureon-system-top"><strong>${escapeHtml(message.role)}</strong><span>${escapeHtml(message.createdAt.slice(11, 19))}</span></div>
        <p>${escapeHtml(message.text.slice(0, 180))}</p>
      </div>
    `).join("") || `<div class="empty-panel">No context events yet.</div>`);
    setHtml("memoryViz", `
      <div class="aureon-systems-summary">
        <strong>${state.messages.length} turns</strong>
        <span>${$("classroomMode")?.checked ? "observing" : "standby"}</span>
      </div>
    `);
  }

  function renderMetacognition(monitor) {
    setHtml("metacognitionCard", `
      <div class="aureon-systems-summary">
        <strong>${escapeHtml(monitor.stabilityIndex ?? "held")}% stability</strong>
        <span>${escapeHtml(monitor.dominantProvider || "none")}</span>
      </div>
      <div class="aureon-systems-list">
        ${(asList(monitor.guidance).slice(0, 3).map((item) => `
          <div class="aureon-system-item system-live"><p>${escapeHtml(item)}</p></div>
        `).join("")) || `<div class="empty-panel">Waiting for conversation evidence.</div>`}
      </div>
    `);
  }

  async function runTerminalCommand() {
    const command = $("terminalCommand")?.value.trim() || "";
    if (!command) return;
    setText("terminalState", "running");
    try {
      const result = await postJson("/api/terminal/run", {
        command,
        approved: Boolean($("terminalApproval")?.checked),
      });
      setText("terminalState", result.blocked ? "blocked" : result.ok ? "ok" : "error");
      setText("terminalOutput", [
        `> ${command}`,
        result.safety?.reason ? `guard: ${result.safety.reason}` : "",
        result.stdout || "",
        result.stderr || "",
      ].filter(Boolean).join("\n"));
    } catch (error) {
      setText("terminalState", "blocked");
      setText("terminalOutput", error.message);
    }
  }

  async function checkTerminalAndSandbox() {
    try {
      const terminal = await fetchJson("/api/terminal/status");
      setText("terminalState", terminal.enabled ? "ready" : "guarded off");
      setText("terminalCwd", terminal.cwd || "local terminal");
      setText("hostTerminalStatus", terminal.enabled ? "Host terminal API enabled" : "Host terminal guarded off");
      setText("hostTerminalState", terminal.enabled ? "ready" : "guarded");
    } catch (error) {
      setText("terminalState", "unavailable");
      setText("hostTerminalStatus", error.message);
    }
    try {
      const sandbox = await fetchJson("/api/sandbox/status");
      setText("sandboxState", sandbox.enabled ? "ready" : "guarded off");
      setText("sandboxStatus", sandbox.enabled ? `Docker ${sandbox.dockerAvailable ? "available" : "checking"}` : "Sandbox guarded off");
    } catch (error) {
      setText("sandboxState", "unavailable");
      setText("sandboxStatus", error.message);
    }
  }

  async function flameballPlan() {
    const task = $("flameballTask")?.value.trim() || "";
    if (!task) return;
    setText("flameballState", "planning");
    setText("flameballOutput", "Asking local Aureon planner...");
    try {
      const response = await postJson("/api/assistant/cli", {
        task,
        mode: "plan",
        model: selectedValue("model", "aureon-architect"),
        responseStyle: selectedValue("aureonResponseStyle", "safe"),
        swarmRoute: selectedValue("swarmRoute", "direct"),
      });
      state.flameballPlan = response;
      setText("flameballState", "planned");
      setHtml("flameballQueue", `
        <div class="flameball-plan-text">${escapeHtml(response.reply || "No plan returned.")}</div>
      `);
      setText("flameballOutput", response.stderr || "Plan loaded. Review before running any guarded command.");
    } catch (error) {
      setText("flameballState", "blocked");
      setHtml("flameballQueue", `<div class="empty-panel">${escapeHtml(error.message)}</div>`);
      setText("flameballOutput", error.message);
    }
  }

  async function loadResearchFeed() {
    const query = $("researchQuery")?.value.trim() || "Aureon local runtime organism integration";
    setHtml("researchFeedCard", `<div class="empty-panel">Loading research feed...</div>`);
    try {
      const response = await fetchJson(`/api/research/feed?q=${encodeURIComponent(query)}&limit=3`);
      const items = asList(response.feed?.items || response.feed?.results);
      setHtml("researchFeedCard", items.map((item) => `
        <div class="aureon-system-item system-live">
          <div class="aureon-system-top"><strong>${escapeHtml(item.title || item.label || "research item")}</strong><span>${escapeHtml(item.source || "source")}</span></div>
          <p>${escapeHtml(item.summary || item.url || JSON.stringify(item).slice(0, 180))}</p>
        </div>
      `).join("") || `<div class="empty-panel">No feed rows returned.</div>`);
    } catch (error) {
      setHtml("researchFeedCard", `<div class="empty-panel">Research feed blocked: ${escapeHtml(error.message)}</div>`);
    }
  }

  function bindEvents() {
    $("provider")?.addEventListener("change", updateModels);
    $("model")?.addEventListener("change", updateActiveLabels);
    $("assistantEngine")?.addEventListener("change", updateActiveLabels);
    $("temperature")?.addEventListener("input", () => setText("tempValue", selectedValue("temperature", "0.7")));
    $("sendBtn")?.addEventListener("click", sendChat);
    $("userInput")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendChat();
      }
    });
    $("clearHistory")?.addEventListener("click", () => {
      state.messages = [];
      setHtml("chatMessages", "");
      renderObservers(null);
    });
    $("exportBtn")?.addEventListener("click", async () => {
      const text = JSON.stringify({ exportedAt: new Date().toISOString(), messages: state.messages }, null, 2);
      await navigator.clipboard?.writeText(text).catch(() => {});
      setStatus("Conversation export copied to clipboard.", "ok");
    });
    $("desktopRefreshBtn")?.addEventListener("click", refreshAureon);
    $("desktopRestartWebBtn")?.addEventListener("click", () => setStatus("Restart is handled by the PowerShell launcher, not the browser UI.", "warn"));
    $("desktopRestartRuntimeBtn")?.addEventListener("click", () => setStatus("Runtime restart stays in the reviewed local launcher.", "warn"));
    $("desktopRestartAureonBtn")?.addEventListener("click", () => setStatus("Aureon core remains owned by AUREON_PRODUCTION_LIVE.cmd.", "warn"));
    $("desktopOpenLogsBtn")?.addEventListener("click", () => setStatus("Logs are in integrations/aureon_murge/logs/activation.", "info"));
    $("terminalRunBtn")?.addEventListener("click", runTerminalCommand);
    $("terminalCopyBtn")?.addEventListener("click", async () => {
      await navigator.clipboard?.writeText($("terminalCommand")?.value || "").catch(() => {});
      setStatus("Terminal command copied.", "ok");
    });
    document.querySelectorAll("#terminalSuggestions button").forEach((button) => {
      button.addEventListener("click", () => {
        const command = button.getAttribute("data-command") || "";
        if ($("terminalCommand")) $("terminalCommand").value = command;
      });
    });
    $("sandboxStatusBtn")?.addEventListener("click", checkTerminalAndSandbox);
    $("sandboxConnectBtn")?.addEventListener("click", () => setText("sandboxStatus", "PTY connect remains guarded by sandbox activation."));
    $("sandboxNewSessionBtn")?.addEventListener("click", () => setText("sandboxSessionLabel", `sandbox-${Date.now().toString().slice(-6)}`));
    $("hostTerminalConnectBtn")?.addEventListener("click", () => setText("hostTerminalStatus", "Host PTY connect remains guarded by host terminal activation."));
    $("hostTerminalNewSessionBtn")?.addEventListener("click", () => setText("hostSessionLabel", `host-${Date.now().toString().slice(-6)}`));
    $("flameballPlanBtn")?.addEventListener("click", flameballPlan);
    $("flameballRunBtn")?.addEventListener("click", () => setText("flameballOutput", "Safe execution is routed through the local CLI/terminal guards. Generate a plan first, then use reviewed terminal commands."));
    $("flameballCopyBtn")?.addEventListener("click", async () => {
      await navigator.clipboard?.writeText(state.flameballPlan?.reply || $("flameballOutput")?.textContent || "").catch(() => {});
      setStatus("flAmeBall output copied.", "ok");
    });
    $("flameballClearBtn")?.addEventListener("click", () => {
      state.flameballPlan = null;
      setHtml("flameballQueue", `<div class="empty-panel">No execution plan loaded.</div>`);
      setText("flameballOutput", "Aureon Executor ready. Host runtime: http://127.0.0.1:7331");
    });
    $("researchSearchBtn")?.addEventListener("click", loadResearchFeed);
    $("addGemmaObserverBtn")?.addEventListener("click", () => addObserver("gemma", "Gemma Context Observer"));
    $("addObserverBtn")?.addEventListener("click", () => addObserver(selectedValue("observerPreset", "logic"), $("observerPreset")?.selectedOptions?.[0]?.textContent || "Observer"));
    $("classroomMode")?.addEventListener("change", () => renderObservers(null));
    $("langEn")?.addEventListener("click", () => setLanguage("en"));
    $("langPl")?.addEventListener("click", () => setLanguage("pl"));
  }

  function addObserver(id, label) {
    if (!state.observers.some((observer) => observer.id === id)) {
      state.observers.push({ id, label, status: "idle", notes: "Added locally" });
    }
    renderObservers(null);
  }

  function setLanguage(language) {
    state.language = language;
    $("langEn")?.classList.toggle("active", language === "en");
    $("langPl")?.classList.toggle("active", language === "pl");
  }

  async function init() {
    updateModels();
    updateActiveLabels();
    setLanguage("en");
    appendMessage("assistant", "Flameborn UI is online. Aureon supervisor, Phi bridge, capability inventory, terminal guards, and classroom observers are loading.");
    bindEvents();
    await Promise.allSettled([refreshAureon(), checkTerminalAndSandbox(), loadClassroomState()]);
    setInterval(refreshAureon, 15000);
    setInterval(checkTerminalAndSandbox, 30000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
