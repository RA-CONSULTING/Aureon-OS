const promptText = "Build a full-stack client task tracker with backend API, frontend dashboard, local data store, tests, runbook, and browser preview proof.";
const apiBase = localStorage.getItem("aureonFullStackApi") || "http://127.0.0.1:8787";
const statusEl = document.querySelector("[data-status]");
const listEl = document.querySelector("[data-items]");
const summaryEl = document.querySelector("[data-summary]");
const form = document.querySelector("form");

const fallbackItems = [
  { id: "local-001", title: "Frontend preview loaded", owner: "Frontend Engineer", status: "ready" },
  { id: "local-002", title: "Start backend/server.py for live API", owner: "API Engineer", status: "queued" },
];

function render(payload, source) {
  const items = payload.items || fallbackItems;
  const summary = payload.summary || { total: items.length, ready: 1, in_progress: 0, queued: 1 };
  statusEl.textContent = source;
  summaryEl.innerHTML = Object.entries(summary).map(([key, value]) => `<span><strong>${value}</strong>${key.replace("_", " ")}</span>`).join("");
  listEl.innerHTML = items.map((item) => `<li><span>${item.title}</span><small>${item.owner} / ${item.status}</small></li>`).join("");
}

async function loadItems() {
  try {
    const response = await fetch(`${apiBase}/api/items`);
    if (!response.ok) throw new Error(`API status ${response.status}`);
    render(await response.json(), "live backend connected");
  } catch (error) {
    render({ items: fallbackItems }, "static preview; start backend for live API");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const payload = { title: data.get("title"), owner: data.get("owner"), status: "queued" };
  try {
    const response = await fetch(`${apiBase}/api/items`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`API status ${response.status}`);
    form.reset();
    await loadItems();
  } catch (error) {
    statusEl.textContent = "backend not running; local preview remains available";
  }
});

document.querySelector("[data-prompt]").textContent = promptText;
loadItems();
