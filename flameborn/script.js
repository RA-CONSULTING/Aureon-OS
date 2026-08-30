(() => {
  "use strict";

  const WORKER_ACCESS_TOKEN_SESSION_KEY = "aureon.workerAccessToken";

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

  function workerAccessToken() {
    try {
      return String(window.sessionStorage.getItem(WORKER_ACCESS_TOKEN_SESSION_KEY) || "").trim();
    } catch {
      return "";
    }
  }

  function saveWorkerAccessTokenForSession() {
    const input = $("workerAccessToken");
    const token = String(input?.value || "").trim();
    try {
      if (token) {
        window.sessionStorage.setItem(WORKER_ACCESS_TOKEN_SESSION_KEY, token);
      } else {
        window.sessionStorage.removeItem(WORKER_ACCESS_TOKEN_SESSION_KEY);
      }
    } catch {
      setStatus("Session storage is unavailable; the access token was not retained.", "warn");
      return;
    } finally {
      if (input) input.value = "";
    }
    setStatus(token ? "Worker access token is active for this tab." : "Worker access token cleared.", token ? "ok" : "info");
  }

  async function fetchJson(url, options = {}) {
    const target = new URL(url, window.location.href);
    const requestOptions = { ...options };
    if (target.origin === window.location.origin && (target.pathname === "/api" || target.pathname.startsWith("/api/"))) {
      const token = workerAccessToken();
      if (!token) throw new Error("Worker access token is required for API routes.");
      const headers = new Headers(options.headers || {});
      headers.set("Authorization", `Bearer ${token}`);
      requestOptions.headers = headers;
    }
    const response = await fetch(url, requestOptions);
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
      // Route through Conversation Engine if toggle is on
      if ($("conversationModeToggle")?.checked && provider === "aureon") {
        const response = await postJson("/api/conversation", { action: "respond", message, voice: "queen" });
        removeNode(loading);
        const reply = response.result?.text || JSON.stringify(response.result, null, 2);
        appendMessage("assistant", reply);
        setStatus("Queen responded via Conversation Engine", "ok");
        if ($("classroomMode")?.checked) {
          mirrorConversation(message, reply);
        }
        return;
      }
      const endpoint = provider === "aureon" ? "/api/message" : "/api/chat";
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

  async function refreshCapabilities() {
    try {
      setText("capabilitiesStatus", "Scanning...");
      const data = await fetchJson("/api/aureon/capabilities");
      renderCapabilities(data);
      setText("capabilitiesStatus", `${data.import_ok}/${data.total_modules} modules OK`);
    } catch (error) {
      setHtml("capabilitiesCard", `<div class="empty-panel">Capability scan failed: ${escapeHtml(error.message)}</div>`);
      setText("capabilitiesStatus", "Scan failed");
    }
  }

  function renderCapabilities(data) {
    const categories = data.categories || {};
    const catOrder = ["coding", "llm", "integrations", "queen", "vault", "autonomous"];
    const html = catOrder.map((cat) => {
      const info = categories[cat];
      if (!info) return "";
      const ok = info.import_ok || 0;
      const total = info.total || 0;
      const statusClass = ok === total ? "system-live" : ok > 0 ? "system-live" : "system-missing";
      const items = (info.modules || []).slice(0, 6).map((m) => {
        const cls = m.import_ok ? "system-live" : "system-missing";
        return `<div class="aureon-system-item ${cls}"><div class="aureon-system-top"><strong>${escapeHtml(m.module_path.split(".").pop())}</strong><span>${m.import_ok ? "OK" : "FAIL"}</span></div></div>`;
      }).join("");
      return `
        <div class="capability-category">
          <div class="aureon-systems-summary">
            <strong>${escapeHtml(cat.toUpperCase())}</strong>
            <span>${ok}/${total}</span>
          </div>
          <div class="aureon-systems-list">${items}</div>
        </div>
      `;
    }).join("");
    setHtml("capabilitiesCard", html || `<div class="empty-panel">No capability data.</div>`);
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
    $("saveWorkerAccessToken")?.addEventListener("click", saveWorkerAccessTokenForSession);
    $("workerAccessToken")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveWorkerAccessTokenForSession();
      }
    });
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
    $("vaultToggleBtn")?.addEventListener("click", openVaultIframe);
    $("vaultCloseBtn")?.addEventListener("click", closeVaultIframe);
    $("loopStartBtn")?.addEventListener("click", () => aureonPost("/api/aureon/vault/api/loop/start", {}, "Loop started"));
    $("loopStopBtn")?.addEventListener("click", () => aureonPost("/api/aureon/vault/api/loop/stop", {}, "Loop stopped"));
    $("loopTickBtn")?.addEventListener("click", () => aureonPost("/api/aureon/vault/api/tick", {}, "Tick triggered"));
    $("queenConverseBtn")?.addEventListener("click", () => aureonPost("/api/aureon/vault/api/converse", {}, "Queen conversing"));
    $("queenMemoryBtn")?.addEventListener("click", () => aureonGet("/api/aureon/vault/api/queen/memory", "Queen memory"));
    $("queenSpeakBtn")?.addEventListener("click", () => {
      const voice = selectedValue("aureonVoiceSelect", "queen");
      aureonPost("/api/aureon/vault/api/speak", { voice }, `${voice} speaking`);
    });
    $("capabilitiesRefreshBtn")?.addEventListener("click", refreshCapabilities);
    $("coderSkillsBtn")?.addEventListener("click", () => aureonGet("/api/coder/skills", "Coder skills"));
    $("llmModelsBtn")?.addEventListener("click", () => aureonGet("/api/llm/models", "LLM models"));
    $("integrationsBtn")?.addEventListener("click", () => aureonGet("/api/integrations/status", "Integrations"));
    $("runnerExecuteBtn")?.addEventListener("click", executeRunner);
    $("tradingRefreshBtn")?.addEventListener("click", refreshTrading);
    $("worldDataIngestBtn")?.addEventListener("click", ingestWorldData);
    $("selfEnhanceBtn")?.addEventListener("click", triggerSelfEnhance);
    $("auditRefreshBtn")?.addEventListener("click", refreshAudit);
    $("orchestratorRefreshBtn")?.addEventListener("click", refreshOrchestrator);
    $("orchestratorSpinBtn")?.addEventListener("click", spinOrchestrator);
    $("orchestratorStartBtn")?.addEventListener("click", () => commandOrchestrator("start"));
    $("orchestratorStopBtn")?.addEventListener("click", () => commandOrchestrator("stop"));
    $("neuralMapRefreshBtn")?.addEventListener("click", refreshNeuralMap);
    $("executionPaperBtn")?.addEventListener("click", executePaperTrade);
    $("stressTestRunBtn")?.addEventListener("click", runStressTest);
    $("validatorRefreshBtn")?.addEventListener("click", runValidatorAll);
    $("deepScanBtn")?.addEventListener("click", runDeepScan);
    $("codeAgentRunBtn")?.addEventListener("click", runCodeAgent);
    $("conversationRunBtn")?.addEventListener("click", runConversation);
    $("agentTeamRefreshBtn")?.addEventListener("click", refreshAgentTeam);
    $("agentTeamCreateBtn")?.addEventListener("click", createAgentTeam);
    $("agentTeamRunBtn")?.addEventListener("click", runAgentTeam);
    $("agentTeamRunAgentBtn")?.addEventListener("click", runSingleAgent);
    $("fileEditorListBtn")?.addEventListener("click", listFileEditor);
    $("fileEditorReadBtn")?.addEventListener("click", readFileEditor);
    $("fileEditorSaveBtn")?.addEventListener("click", saveFileEditor);
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

  function openVaultIframe() {
    const iframe = $("vaultIframe");
    const dock = $("vaultIframeDock");
    const chat = $("mainChatPanel");
    if (!iframe || !dock || !chat) return;
    iframe.src = "http://127.0.0.1:5566";
    dock.style.display = "flex";
    chat.style.display = "none";
  }

  function closeVaultIframe() {
    const iframe = $("vaultIframe");
    const dock = $("vaultIframeDock");
    const chat = $("mainChatPanel");
    if (!iframe || !dock || !chat) return;
    iframe.src = "about:blank";
    dock.style.display = "none";
    chat.style.display = "flex";
  }

  async function aureonPost(endpoint, body, okMessage) {
    try {
      await postJson(endpoint, body);
      setStatus(okMessage, "ok");
    } catch (error) {
      setStatus(`Aureon action failed: ${error.message}`, "warn");
    }
  }

  async function aureonGet(endpoint, label) {
    try {
      const data = await fetchJson(endpoint);
      setStatus(`${label}: ${JSON.stringify(data).slice(0, 120)}`, "ok");
    } catch (error) {
      setStatus(`${label} failed: ${error.message}`, "warn");
    }
  }

  async function executeRunner() {
    const script = $("runnerScript")?.value.trim() || "";
    const args = ($("runnerArgs")?.value.trim() || "").split(/\s+/).filter(Boolean);
    if (!script) {
      setText("runnerOutput", "Error: script path is required.");
      return;
    }
    setText("runnerOutput", "Executing...");
    try {
      const result = await postJson("/api/aureon/run", { script, args, timeout: 30_000 });
      const out = [
        `Exit code: ${result.exitCode}`,
        result.stdout ? `--- stdout ---\n${result.stdout}` : "",
        result.stderr ? `--- stderr ---\n${result.stderr}` : "",
      ].filter(Boolean).join("\n");
      setText("runnerOutput", out.slice(0, 3000));
      setStatus("Runner completed", result.ok ? "ok" : "warn");
    } catch (error) {
      setText("runnerOutput", `Execution failed: ${error.message}`);
      setStatus("Runner failed", "warn");
    }
  }

  function connectSseBridge() {
    try {
      const source = new EventSource("/api/aureon/sse");
      source.addEventListener("message", (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "aureon-status") {
            const lambda = payload.data?.lambda_state?.lambda?.toFixed(2) ?? "—";
            const level = payload.data?.lambda_state?.level ?? "—";
            setText("vaultStatusLabel", `Vault: ${level} | Λ=${lambda}`);
          }
        } catch {
          // ignore malformed SSE
        }
      });
      source.addEventListener("error", () => {
        // reconnect handled automatically by EventSource
      });
    } catch {
      // SSE not supported
    }
  }

  async function refreshTrading() {
    try {
      const data = await fetchJson("/api/trading/status");
      const exchanges = (data.exchanges || []).map((ex) => `
        <div class="aureon-system-item ${ex.enabled ? "system-live" : "system-missing"}">
          <div class="aureon-system-top"><strong>${escapeHtml(ex.label)}</strong><span>${ex.enabled ? (ex.hasKeys ? "keys set" : "no keys") : "missing"}</span></div>
        </div>
      `).join("");
      const bots = (data.bots || []).map((b) => `
        <div class="aureon-system-item ${b.enabled ? "system-live" : "system-missing"}">
          <div class="aureon-system-top"><strong>${escapeHtml(b.label)}</strong><span>${b.enabled ? "available" : "missing"}</span></div>
        </div>
      `).join("");
      setHtml("tradingCard", `<div class="aureon-systems-list">${exchanges}${bots}</div>`);
      setText("tradingStatusLabel", `Mode: ${escapeHtml(data.mode || "unknown")}`);
    } catch (error) {
      setHtml("tradingCard", `<div class="empty-panel">Trading status unavailable: ${escapeHtml(error.message)}</div>`);
    }
  }

  async function ingestWorldData() {
    const query = $("worldDataQuery")?.value.trim() || "bitcoin market news";
    setText("worldDataOutput", "Ingesting...");
    try {
      const result = await postJson("/api/world-data/ingest", { query });
      const items = (result.items || []).map((i) => `[${escapeHtml(i.source)}] ${escapeHtml(i.title || i.topic)}`).join("\n");
      setText("worldDataOutput", `Query: ${escapeHtml(result.query)}\nCount: ${result.count || 0}\n\n${items}`.slice(0, 2000));
      setStatus("World data ingested", "ok");
    } catch (error) {
      setText("worldDataOutput", `Ingest failed: ${error.message}`);
      setStatus("World data ingest failed", "warn");
    }
  }

  async function triggerSelfEnhance() {
    setText("enhanceOutput", "Triggering self-enhancement cycle...");
    try {
      const result = await postJson("/api/self-enhance/trigger", {});
      setText("enhanceOutput", `Status: ${escapeHtml(result.status || "unknown")}\n${JSON.stringify(result, null, 2)}`.slice(0, 2000));
      setStatus("Self-enhancement triggered", "ok");
    } catch (error) {
      setText("enhanceOutput", `Trigger failed: ${error.message}`);
      setStatus("Self-enhancement failed", "warn");
    }
  }

  async function refreshAudit() {
    try {
      const data = await fetchJson("/api/audit/trail");
      const entries = (data.entries || []).slice(-10).map((e) => `
        <div class="aureon-system-item system-live">
          <div class="aureon-system-top"><strong>${escapeHtml(e.event || e.type || "event")}</strong><span>${escapeHtml(e.timestamp || "")}</span></div>
          <p>${escapeHtml(JSON.stringify(e).slice(0, 120))}</p>
        </div>
      `).join("");
      setHtml("auditCard", entries || `<div class="empty-panel">No audit entries found.</div>`);
    } catch (error) {
      setHtml("auditCard", `<div class="empty-panel">Audit unavailable: ${escapeHtml(error.message)}</div>`);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ORCHESTRATOR CONTROL PANEL
  // ═══════════════════════════════════════════════════════════════════════════

  async function refreshOrchestrator() {
    try {
      const data = await fetchJson("/api/orchestrator/status");
      const items = (data.orchestrators || []).map((o) => `
        <div class="aureon-system-item ${o.import_ok ? "system-live" : "system-missing"}">
          <div class="aureon-system-top"><strong>${escapeHtml(o.class)}</strong><span>${o.import_ok ? "ready" : "blocked"}</span></div>
          <p>${escapeHtml(o.module)} · ${o.methods.length} methods</p>
        </div>
      `).join("");
      setHtml("orchestratorCard", `<div class="aureon-systems-list">${items}</div>`);
      setText("orchestratorStatusLabel", `${data.orchestrators?.length || 0} orchestrators scanned`);
    } catch (error) {
      setHtml("orchestratorCard", `<div class="empty-panel">Orchestrator status unavailable: ${escapeHtml(error.message)}</div>`);
    }
  }

  async function spinOrchestrator() {
    const symbol = $("orchestratorSymbol")?.value.trim() || "BTCUSD";
    setText("orchestratorStatusLabel", `Spinning ${symbol}...`);
    try {
      const result = await postJson("/api/orchestrator/spin", { symbol });
      setText("orchestratorStatusLabel", `Spin complete: ${escapeHtml(result.signal?.direction || "?")} (${(result.signal?.confidence || 0).toFixed(2)})`);
      setStatus(`Orchestrator spin: ${result.signal?.direction || "unknown"}`, "ok");
    } catch (error) {
      setText("orchestratorStatusLabel", `Spin failed: ${error.message}`);
      setStatus("Orchestrator spin failed", "warn");
    }
  }

  async function commandOrchestrator(action) {
    const target = "global";
    setText("orchestratorStatusLabel", `${action} ${target}...`);
    try {
      const result = await postJson("/api/orchestrator/command", { action, target });
      setText("orchestratorStatusLabel", `${action}: ${escapeHtml(result.status || result.started || result.stopped || "ok")}`);
      setStatus(`Orchestrator ${action}: OK`, "ok");
    } catch (error) {
      setText("orchestratorStatusLabel", `${action} failed: ${error.message}`);
      setStatus(`Orchestrator ${action} failed`, "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // NEURAL PATHWAY MAPPER
  // ═══════════════════════════════════════════════════════════════════════════

  async function refreshNeuralMap() {
    setHtml("neuralMapCard", `<div class="empty-panel">Building neural map...</div>`);
    try {
      const data = await fetchJson("/api/neural-map");
      const categories = {};
      for (const node of data.nodes || []) {
        const cat = node.category || "unknown";
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push(node);
      }
      const catHtml = Object.entries(categories).map(([cat, nodes]) => `
        <div class="neural-category">
          <strong>${escapeHtml(cat)}</strong> <span>${nodes.length} nodes</span>
          <div class="neural-nodes">
            ${nodes.slice(0, 8).map((n) => `<span class="neural-node ${n.type}">${escapeHtml(n.label)}</span>`).join("")}
            ${nodes.length > 8 ? `<span class="neural-node">+${nodes.length - 8} more</span>` : ""}
          </div>
        </div>
      `).join("");
      const edgeSummary = `<div class="neural-edges"><strong>${data.edgeCount}</strong> import edges across <strong>${data.nodeCount}</strong> modules</div>`;
      setHtml("neuralMapCard", `${edgeSummary}${catHtml}`);
    } catch (error) {
      setHtml("neuralMapCard", `<div class="empty-panel">Neural map unavailable: ${escapeHtml(error.message)}</div>`);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // LIVE TRADING EXECUTION
  // ═══════════════════════════════════════════════════════════════════════════

  async function executePaperTrade() {
    const symbol = $("executionSymbol")?.value.trim() || "BTCUSD";
    const exchange = $("executionExchange")?.value || "kraken";
    setText("executionOutput", `Executing paper trade for ${symbol} on ${exchange}...`);
    try {
      const result = await postJson("/api/trading/execute", { symbol, exchange, mode: "paper" });
      const trade = result.trade || {};
      setText("executionOutput", [
        `Symbol: ${trade.symbol}`,
        `Exchange: ${trade.exchange}`,
        `Direction: ${trade.direction}`,
        `Confidence: ${trade.confidence}`,
        `Entry: ${trade.entry_price}`,
        `Status: ${trade.status}`,
        `Time: ${trade.timestamp}`,
      ].join("\n"));
      setStatus(`Paper trade executed: ${trade.direction}`, "ok");
    } catch (error) {
      setText("executionOutput", `Execution failed: ${error.message}`);
      setStatus("Paper trade failed", "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // STRESS TEST SUITE
  // ═══════════════════════════════════════════════════════════════════════════

  async function runStressTest() {
    const type = $("stressTestType")?.value || "smoke";
    setText("stressTestOutput", `Running ${type} test... this may take a while.`);
    try {
      const result = await postJson("/api/stress-test/run", { type });
      const reports = result.reports || [];
      const summary = reports.map((r) => {
        const status = r.slo_passed ? "✅" : "❌";
        return `${status} ${r.test_type}: ${r.total_requests} req, ${r.rps} rps, ${(r.availability * 100).toFixed(1)}% avail`;
      }).join("\n");
      setText("stressTestOutput", summary || JSON.stringify(result, null, 2).slice(0, 2000));
      setStatus(`Stress test complete: ${result.all_passed ? "ALL PASSED" : "FAILURES"}`, result.all_passed ? "ok" : "warn");
    } catch (error) {
      setText("stressTestOutput", `Stress test failed: ${error.message}`);
      setStatus("Stress test failed", "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ORGANISM VALIDATOR — executes each capability and reports results
  // ═══════════════════════════════════════════════════════════════════════════

  async function loadCapabilityList() {
    try {
      const data = await fetchJson("/api/capability/list");
      const caps = data.capabilities || [];
      const byCat = {};
      for (const c of caps) {
        if (!byCat[c.category]) byCat[c.category] = [];
        byCat[c.category].push(c);
      }
      let html = "";
      for (const [cat, items] of Object.entries(byCat)) {
        html += `<div class="validator-category"><strong>${escapeHtml(cat.toUpperCase())}</strong>`;
        for (const item of items) {
          html += `<button type="button" class="validator-btn" data-capability="${escapeHtml(item.key)}">${escapeHtml(item.label)}</button>`;
        }
        html += `</div>`;
      }
      setHtml("validatorCard", html);
      document.querySelectorAll(".validator-btn").forEach((btn) => {
        btn.addEventListener("click", () => runSingleCapability(btn.getAttribute("data-capability")));
      });
      setText("validatorStatusLabel", `${caps.length} capabilities ready`);
    } catch (error) {
      setHtml("validatorCard", `<div class="empty-panel">Validator unavailable: ${escapeHtml(error.message)}</div>`);
    }
  }

  async function runSingleCapability(key) {
    const btn = document.querySelector(`.validator-btn[data-capability="${key}"]`);
    if (btn) btn.textContent = "Running...";
    try {
      const result = await postJson("/api/capability/execute", { capability: key });
      const status = result.result ? "✅" : "⚠️";
      if (btn) btn.textContent = `${status} ${result.label}`;
      setStatus(`Capability ${result.label}: OK`, "ok");
    } catch (error) {
      if (btn) btn.textContent = `❌ ${key}`;
      setStatus(`Capability ${key} failed: ${error.message}`, "warn");
    }
  }

  async function runValidatorAll() {
    setText("validatorStatusLabel", "Running all capabilities...");
    try {
      const data = await fetchJson("/api/capability/list");
      const caps = data.capabilities || [];
      let pass = 0;
      let fail = 0;
      for (const cap of caps) {
        try {
          await postJson("/api/capability/execute", { capability: cap.key });
          pass++;
        } catch {
          fail++;
        }
      }
      setText("validatorStatusLabel", `${pass}/${caps.length} passed, ${fail} failed`);
      setStatus(`Organism validation complete: ${pass}/${caps.length}`, fail === 0 ? "ok" : "warn");
    } catch (error) {
      setText("validatorStatusLabel", `Validator failed: ${error.message}`);
    }
  }

  async function runDeepScan() {
    const out = $("deepScanOutput");
    if (out) out.textContent = "Deep scanning all 794 modules... this may take 60-120s.";
    try {
      const result = await fetchJson("/api/validator/deep-scan");
      const data = result.result || {};
      const summary = `[Deep Scan Result] Total: ${data.total} | Passed: ${data.passed} | Failed: ${data.failed} | Rate: ${(data.pass_rate * 100).toFixed(1)}%`;
      if (out) out.textContent = summary + "\n\nFirst 20 failures:\n" + (data.results || []).filter(r => !r.ok).slice(0, 20).map(r => `  ${r.module}: ${r.error}`).join("\n");
      setStatus(`Deep scan: ${data.passed}/${data.total} passed`, "ok");
    } catch (error) {
      if (out) out.textContent = "Deep scan failed: " + error.message;
      setStatus("Deep scan failed", "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // CODE AGENT ENGINE
  // ═══════════════════════════════════════════════════════════════════════════

  async function runCodeAgent() {
    const action = $("codeAgentAction")?.value || "capabilities";
    const input = $("codeAgentInput")?.value.trim() || "";
    setText("codeAgentOutput", `Running ${action}...`);
    try {
      if (action === "execute-plan") {
        const result = await postJson("/api/code-agent/execute-plan", { goal: input || "Analyze the codebase" });
        const out = JSON.stringify(result.result || result.raw, null, 2).slice(0, 3000);
        setText("codeAgentOutput", out);
        setStatus(`Goal plan executed`, "ok");
        return;
      }
      const body = { action };
      if (input) {
        if (action === "explore") body.pattern = input;
        else if (action === "plan") body.goal = input;
        else if (action === "execute-python") body.code = input;
        else if (action === "execute-shell") body.command = input;
        else if (action === "read-file") body.path = input;
        else if (action === "web-search") body.query = input;
        else if (action === "propose-code") { body.description = input; body.path = "test.py"; }
      }
      const result = await postJson("/api/code-agent", body);
      const out = JSON.stringify(result.result || result.raw, null, 2).slice(0, 2000);
      setText("codeAgentOutput", out);
      setStatus(`Code agent ${action}: OK`, "ok");
    } catch (error) {
      setText("codeAgentOutput", `Error: ${error.message}`);
      setStatus(`Code agent ${action} failed`, "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // AGENT TEAM VISUALIZER
  // ═══════════════════════════════════════════════════════════════════════════

  async function refreshAgentTeam() {
    setText("agentTeamStatusLabel", "Loading...");
    try {
      const result = await postJson("/api/agent-team", { action: "status" });
      const data = result.result || {};
      const agents = (data.agents || []).map((a) => `<span class="team-agent">${escapeHtml(a)}</span>`).join("");
      const teams = (data.teams || []).map((t) => `<span class="team-name">${escapeHtml(t)}</span>`).join("");
      setHtml("agentTeamCard", `
        <div class="team-section"><strong>Agents</strong><div class="team-tags">${agents || "<span class=\"empty\">No agents</span>"}</div></div>
        <div class="team-section"><strong>Teams</strong><div class="team-tags">${teams || "<span class=\"empty\">No teams</span>"}</div></div>
      `);
      setText("agentTeamStatusLabel", `${data.agents?.length || 0} agents, ${data.teams?.length || 0} teams`);
    } catch (error) {
      setHtml("agentTeamCard", `<div class="empty-panel">Team status unavailable: ${escapeHtml(error.message)}</div>`);
    }
  }

  async function createAgentTeam() {
    const name = $("agentTeamName")?.value.trim() || "default";
    const agents = $("agentTeamAgents")?.value.split(",").map((s) => s.trim()).filter(Boolean) || ["analyzer"];
    setText("agentTeamOutput", `Creating team ${name}...`);
    try {
      const result = await postJson("/api/agent-team", { action: "create-team", name, agents });
      setText("agentTeamOutput", JSON.stringify(result.result, null, 2).slice(0, 2000));
      setStatus(`Team ${name} created`, "ok");
      await refreshAgentTeam();
    } catch (error) {
      setText("agentTeamOutput", `Error: ${error.message}`);
      setStatus("Team creation failed", "warn");
    }
  }

  async function runAgentTeam() {
    const name = $("agentTeamName")?.value.trim() || "default";
    const task = $("agentTeamTask")?.value.trim() || "Analyze the codebase";
    setText("agentTeamOutput", `Running team ${name}...`);
    try {
      const result = await postJson("/api/agent-team", { action: "run-team", name, task });
      setText("agentTeamOutput", JSON.stringify(result.result, null, 2).slice(0, 2000));
      setStatus(`Team ${name} executed`, "ok");
    } catch (error) {
      setText("agentTeamOutput", `Error: ${error.message}`);
      setStatus("Team run failed", "warn");
    }
  }

  async function runSingleAgent() {
    const name = $("agentTeamName")?.value.trim() || "analyzer";
    const task = $("agentTeamTask")?.value.trim() || "Analyze the codebase";
    setText("agentTeamOutput", `Running agent ${name}...`);
    try {
      const result = await postJson("/api/agent-team", { action: "run-agent", name, task });
      setText("agentTeamOutput", JSON.stringify(result.result, null, 2).slice(0, 2000));
      setStatus(`Agent ${name} executed`, "ok");
    } catch (error) {
      setText("agentTeamOutput", `Error: ${error.message}`);
      setStatus("Agent run failed", "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // FILE EDITOR
  // ═══════════════════════════════════════════════════════════════════════════

  async function listFileEditor() {
    const dir = $("fileEditorDir")?.value.trim() || ".";
    setText("fileEditorStatusLabel", `Listing ${dir}...`);
    try {
      const result = await postJson("/api/file-editor", { action: "list", directory: dir });
      const items = (result.result?.items || []).map((item) => {
        const isDir = item.is_dir || false;
        return `<div class="file-item ${isDir ? "dir" : "file"}" data-path="${escapeHtml(item.path || item.name || "")}">${escapeHtml(item.name || item.path || "unknown")}</div>`;
      }).join("");
      setHtml("fileEditorBrowser", items || `<div class="empty-panel">No items in ${escapeHtml(dir)}</div>`);
      document.querySelectorAll(".file-item").forEach((el) => {
        el.addEventListener("click", () => {
          const path = el.getAttribute("data-path");
          if (path && $("fileEditorPath")) $("fileEditorPath").value = path;
        });
      });
      setText("fileEditorStatusLabel", `${result.result?.items?.length || 0} items in ${dir}`);
    } catch (error) {
      setHtml("fileEditorBrowser", `<div class="empty-panel">List failed: ${escapeHtml(error.message)}</div>`);
    }
  }

  async function readFileEditor() {
    const path = $("fileEditorPath")?.value.trim() || "README.md";
    setText("fileEditorStatusLabel", `Reading ${path}...`);
    try {
      const result = await postJson("/api/file-editor", { action: "read", path });
      const content = result.result?.content || "";
      $("fileEditorContent").value = content;
      setText("fileEditorStatusLabel", `Read ${path} (${content.length} chars)`);
      setStatus(`File read: ${path}`, "ok");
    } catch (error) {
      setText("fileEditorStatusLabel", `Read failed: ${error.message}`);
      setStatus(`File read failed`, "warn");
    }
  }

  async function saveFileEditor() {
    const path = $("fileEditorPath")?.value.trim() || "test.txt";
    const content = $("fileEditorContent")?.value || "";
    setText("fileEditorStatusLabel", `Saving ${path}...`);
    try {
      const result = await postJson("/api/file-editor", { action: "write", path, content });
      setText("fileEditorStatusLabel", `Saved ${path}`);
      setStatus(`File saved: ${path}`, "ok");
    } catch (error) {
      setText("fileEditorStatusLabel", `Save failed: ${error.message}`);
      setStatus(`File save failed`, "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // CONVERSATION ENGINE
  // ═══════════════════════════════════════════════════════════════════════════

  async function runConversation() {
    const action = $("conversationAction")?.value || "respond";
    const input = $("conversationInput")?.value.trim() || "";
    setText("conversationOutput", `Running ${action}...`);
    try {
      const body = { action };
      if (input) {
        if (action === "respond") body.message = input;
        else if (action === "memory-remember") body.text = input;
        else if (action === "agent-run" || action === "team-run") body.task = input;
      }
      const result = await postJson("/api/conversation", body);
      const out = JSON.stringify(result.result || result.raw, null, 2).slice(0, 2000);
      setText("conversationOutput", out);
      setStatus(`Conversation ${action}: OK`, "ok");
    } catch (error) {
      setText("conversationOutput", `Error: ${error.message}`);
      setStatus(`Conversation ${action} failed`, "warn");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // REAL-TIME WEBSOCKET BRIDGE
  // ═══════════════════════════════════════════════════════════════════════════

  function connectRealtimeBridge() {
    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/realtime`);
      ws.addEventListener("open", () => {
        setText("realtimeStatusLabel", "WebSocket connected");
        ws.send(JSON.stringify({ type: "subscribe", channel: "all" }));
      });
      ws.addEventListener("message", (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "trading-tick") {
            const d = payload.data || {};
            setHtml("realtimeTickCard", `
              <div class="realtime-tick">
                <strong>${escapeHtml(d.symbol)}</strong>
                <span class="tick-price">$${d.price}</span>
                <span class="tick-dir ${d.direction?.toLowerCase()}">${d.direction}</span>
                <span class="tick-conf">${d.confidence}</span>
                <span class="tick-time">${new Date(d.timestamp).toLocaleTimeString()}</span>
              </div>
            `);
          }
          if (payload.type === "aureon-status") {
            const lambda = payload.data?.lambda_state?.lambda?.toFixed(2) ?? "—";
            const level = payload.data?.lambda_state?.level ?? "—";
            setText("vaultStatusLabel", `Vault: ${level} | Λ=${lambda}`);
          }
        } catch {
          // ignore malformed messages
        }
      });
      ws.addEventListener("close", () => {
        setText("realtimeStatusLabel", "WebSocket disconnected — reconnecting...");
        setTimeout(connectRealtimeBridge, 5000);
      });
      ws.addEventListener("error", () => {
        setText("realtimeStatusLabel", "WebSocket error");
      });
    } catch {
      setText("realtimeStatusLabel", "WebSocket not supported");
    }
  }

  async function init() {
    updateModels();
    updateActiveLabels();
    setLanguage("en");
    appendMessage("assistant", "Flameborn UI is online. Aureon supervisor, Phi bridge, capability inventory, terminal guards, orchestrators, neural map, and classroom observers are loading.");
    bindEvents();
    await Promise.allSettled([
      refreshAureon(),
      refreshCapabilities(),
      checkTerminalAndSandbox(),
      loadClassroomState(),
      refreshOrchestrator(),
      refreshTrading(),
      loadCapabilityList(),
      refreshAgentTeam(),
    ]);
    setInterval(refreshAureon, 15000);
    connectSseBridge();
    connectRealtimeBridge();
    setInterval(checkTerminalAndSandbox, 30000);
    setInterval(refreshOrchestrator, 60000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
