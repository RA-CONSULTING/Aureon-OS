(() => {
  "use strict";

  const TOKEN_KEY = "aureon.cloudflareWorkerAccessToken";
  const ALLOWED_API_ROUTES = new Set(["/api/chat", "/api/aureon/status"]);
  const byId = (id) => document.getElementById(id);

  function readToken() {
    try {
      return String(window.sessionStorage.getItem(TOKEN_KEY) || "");
    } catch {
      return "";
    }
  }

  function setMessage(text, state = "neutral") {
    const node = byId("accessMessage");
    node.textContent = text;
    node.dataset.state = state;
  }

  function updateConnectionState() {
    const active = Boolean(readToken());
    const node = byId("connectionState");
    node.textContent = active ? "Token active" : "Token required";
    node.dataset.state = active ? "active" : "blocked";
  }

  function storeToken() {
    const input = byId("workerAccessToken");
    const token = String(input.value || "").trim();
    try {
      if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
      else window.sessionStorage.removeItem(TOKEN_KEY);
      setMessage(token ? "Access token stored for this tab." : "Access token cleared.", token ? "ok" : "neutral");
    } catch {
      setMessage("Session storage is unavailable; the token was not retained.", "error");
    } finally {
      input.value = "";
      updateConnectionState();
    }
  }

  function clearToken() {
    try {
      window.sessionStorage.removeItem(TOKEN_KEY);
      setMessage("Access token cleared.", "neutral");
    } catch {
      setMessage("Session storage is unavailable.", "error");
    }
    byId("workerAccessToken").value = "";
    updateConnectionState();
  }

  async function apiRequest(path, options = {}) {
    if (!ALLOWED_API_ROUTES.has(path)) throw new Error("This route is not available in the Cloudflare console.");
    const token = readToken();
    if (!token) throw new Error("Enter the Worker access token first.");

    const target = new URL(path, window.location.href);
    if (target.origin !== window.location.origin) throw new Error("Cross-origin API requests are blocked.");
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(target.href, { ...options, headers });
    const raw = await response.text();
    let payload = {};
    try {
      payload = raw ? JSON.parse(raw) : {};
    } catch {
      throw new Error("The Worker returned an invalid JSON response.");
    }
    if (!response.ok) {
      throw new Error(payload?.error?.message || `Request failed with HTTP ${response.status}.`);
    }
    return payload;
  }

  async function refreshStatus() {
    const output = byId("statusOutput");
    output.textContent = "Loading status...";
    try {
      const payload = await apiRequest("/api/aureon/status");
      output.textContent = JSON.stringify(payload, null, 2);
    } catch (error) {
      output.textContent = `Status unavailable: ${error.message}`;
    }
  }

  async function submitChat(event) {
    event.preventDefault();
    const output = byId("chatOutput");
    const button = byId("sendMessage");
    button.disabled = true;
    output.textContent = "Waiting for the provider...";
    try {
      const body = {
        provider: byId("provider").value,
        accessMode: "free",
        rolePrompt: byId("rolePrompt").value,
        message: byId("message").value,
        temperature: 0.7,
        max_tokens: 1200,
      };
      const payload = await apiRequest("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      output.textContent = payload.reply || JSON.stringify(payload, null, 2);
    } catch (error) {
      output.textContent = `Chat failed: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  }

  byId("saveToken").addEventListener("click", storeToken);
  byId("clearToken").addEventListener("click", clearToken);
  byId("refreshStatus").addEventListener("click", refreshStatus);
  byId("chatForm").addEventListener("submit", submitChat);
  byId("workerAccessToken").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      storeToken();
    }
  });
  updateConnectionState();
})();
