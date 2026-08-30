(() => {
  "use strict";

  const register = document.querySelector("[data-funding-register]");
  const summary = document.querySelector("[data-funding-summary]");
  const policy = document.querySelector("[data-funding-policy]");
  const diligence = document.querySelector("[data-funding-diligence]");
  const filterRoot = document.querySelector("[data-funding-filter]");
  const searchInput = document.querySelector("[data-funding-search]");
  const resultCount = document.querySelector("[data-funding-result-count]");
  const source = "../data/funding-status.json?v=aureon-v45-20260820";
  const state = { routeType: "all", query: "", records: [], routeTypes: [] };

  function make(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = text;
    return element;
  }

  function appendDetail(parent, label, value) {
    const item = make("div", "capital-route-detail");
    item.append(make("span", "", label), make("p", "", value || "Not supplied"));
    parent.append(item);
  }

  function stateLabel(value) {
    const labels = {
      "strategic-theme": "Strategic theme"
    };
    return labels[value] || "Strategic theme";
  }

  function createCard(record) {
    const card = make("article", "capital-route-card");
    card.dataset.stateGroup = record.state_group || "strategic-theme";
    card.dataset.routeType = record.route_type || "Other";

    const header = make("div", "capital-route-card-head");
    const route = make("span", "capital-route-type", record.route_type || "Other route");
    const evidenceState = make("span", "capital-route-state", stateLabel(record.state_group));
    header.append(route, evidenceState);

    const title = make("h3", "", record.title || "Strategic theme");
    const programme = make("p", "capital-route-programme", record.programme || "Programme not supplied");
    const status = make("div", "capital-route-status");
    status.append(make("span", "", "Strategic relevance"), make("strong", "", record.status_label || "Strategic theme"), make("p", "", record.status_detail || "Strategic relevance is being defined."));

    const quick = make("div", "capital-route-quick");
    const signal = make("div");
    signal.append(make("span", "", "Public evidence"), make("strong", "", record.public_signal || "Public evidence basis available"));
    const gate = make("div");
    gate.append(make("span", "", "Next validation"), make("strong", "", record.next_gate || "Scoped validation milestone"));
    quick.append(signal, gate);

    const abstract = make("p", "capital-route-abstract", record.summary || "No public summary supplied.");
    const details = make("details", "capital-route-disclosure");
    const detailsSummary = make("summary", "", "Inspect strategic relevance and boundary");
    const detailGrid = make("div", "capital-route-details");
    appendDetail(detailGrid, "Innovation focus", record.innovation_type);
    appendDetail(detailGrid, "Diligence access", "Supporting diligence is shared only in a qualified, scoped review.");
    const boundary = make("p", "capital-route-boundary", record.public_boundary || "Strategic relevance does not establish a completed outcome.");
    details.append(detailsSummary, detailGrid, boundary);

    card.append(header, programme, title, status, quick, abstract, details);
    return card;
  }

  function updateFilterButtons() {
    filterRoot?.querySelectorAll("button[data-funding-filter-value]").forEach((button) => {
      const active = button.dataset.fundingFilterValue === state.routeType;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function render() {
    if (!register) return;
    const query = state.query.trim().toLowerCase();
    const visible = state.records.filter((record) => {
      const routeMatch = state.routeType === "all" || record.route_type === state.routeType;
      const haystack = [record.route_type, record.programme, record.title, record.status_label, record.innovation_type, record.summary, record.next_gate].join(" ").toLowerCase();
      return routeMatch && (!query || haystack.includes(query));
    });

    register.replaceChildren();
    if (visible.length) {
      register.append(...visible.map(createCard));
    } else {
      const empty = make("div", "capital-route-empty");
      empty.append(make("strong", "", "No routes match this view."), make("p", "", "Clear the search or choose another route type."));
      register.append(empty);
    }
    if (resultCount) resultCount.textContent = visible.length === state.records.length ? "All strategic themes shown" : "Filtered strategic themes shown";
    updateFilterButtons();
  }

  function selectRouteType(value, scroll = false) {
    const exists = value === "all" || state.routeTypes.some((item) => item.label === value);
    state.routeType = exists ? value : "all";
    render();
    if (scroll) document.querySelector("#route-register")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function buildFilters() {
    if (!filterRoot) return;
    filterRoot.replaceChildren();
    const items = [{ label: "all", display: "All routes" }, ...state.routeTypes.map((item) => ({ label: item.label, display: item.label }))];
    items.forEach((item, index) => {
      const button = make("button", index === 0 ? "is-active" : "", item.display);
      button.type = "button";
      button.dataset.fundingFilterValue = item.label;
      button.setAttribute("aria-pressed", String(index === 0));
      button.addEventListener("click", () => selectRouteType(item.label));
      filterRoot.append(button);
    });
  }

  function setStat(selector, value) {
    const target = document.querySelector(selector);
    if (target) target.textContent = String(value ?? "Not public");
  }

  function initialiseLenses() {
    const tabs = [...document.querySelectorAll("[data-funding-lens-value]")];
    const panels = [...document.querySelectorAll("[data-funding-lens-panel]")];
    if (!tabs.length || !panels.length) return;

    const activate = (target, focus = false) => {
      tabs.forEach((tab) => {
        const active = tab === target;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
        tab.classList.toggle("is-active", active);
      });
      panels.forEach((panel) => { panel.hidden = panel.dataset.fundingLensPanel !== target.dataset.fundingLensValue; });
      if (focus) target.focus();
    };

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activate(tab));
      tab.addEventListener("keydown", (event) => {
        let next = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") next = tabs[(index + 1) % tabs.length];
        if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = tabs[(index - 1 + tabs.length) % tabs.length];
        if (event.key === "Home") next = tabs[0];
        if (event.key === "End") next = tabs[tabs.length - 1];
        if (next) { event.preventDefault(); activate(next, true); }
      });
    });
    activate(tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0]);
  }

  async function loadRegister() {
    initialiseLenses();
    document.querySelectorAll("[data-funding-route-shortcut]").forEach((control) => {
      control.addEventListener("click", () => selectRouteType(control.dataset.fundingRouteShortcut, true));
    });
    searchInput?.addEventListener("input", () => { state.query = searchInput.value; render(); });

    if (!register) return;
    try {
      const response = await fetch(source, { cache: "no-store" });
      if (!response.ok) throw new Error("FUNDING_STATUS_UNAVAILABLE");
      const data = await response.json();
      if (!data || !Array.isArray(data.routes) || !Array.isArray(data.route_types)) throw new Error("FUNDING_STATUS_INVALID");

      state.records = data.routes;
      state.routeTypes = data.route_types;
      buildFilters();
      render();

      const signals = data.public_signals || {};
      setStat("[data-funding-total]", signals.route_areas || "Cross-sector");
      setStat("[data-funding-provider]", signals.external_routes || "Strategic");
      setStat("[data-funding-company]", signals.diligence_detail || "Qualified access");
      setStat("[data-funding-gated]", signals.disclosure_boundary || "Public scope");
      if (summary) summary.textContent = data.coverage?.scope || "Strategic capital and partnership themes for the shared evidence core.";
      if (policy) policy.textContent = data.coverage?.status_policy || "The map presents strategic relevance, public evidence and the next validation.";
      if (diligence) diligence.textContent = "Supporting diligence is shared only in a qualified, scoped review.";
      document.body.dataset.fundingRegisterState = "ready";
    } catch (_error) {
      register.replaceChildren();
      const fallback = make("div", "capital-route-empty");
      fallback.append(make("strong", "", "The public route map is temporarily unavailable."), make("p", "", "Use the company contact route to request an evidence-scoped conversation."));
      register.append(fallback);
      if (summary) summary.textContent = "Public route map unavailable.";
      if (policy) policy.textContent = "The strategic orientation could not be loaded.";
      if (diligence) diligence.textContent = "Supporting diligence is shared only in a qualified, scoped review.";
      document.body.dataset.fundingRegisterState = "unavailable";
    }
  }

  loadRegister();
})();
