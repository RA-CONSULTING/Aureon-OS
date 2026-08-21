(function () {
  "use strict";

  const scriptElement = document.currentScript;
  const siteRoot = new URL(".", scriptElement.src);
  const dataReleaseKey = new URL(scriptElement.src).searchParams.get("v") || "evidence-os-live";
  const projectMapLabels = {
    runtime: ["Task input", "Policy gate", "Human approval", "Bounded action"],
    research: ["Research question", "Evidence trail", "Reproduction audit", "Review boundary"],
    provenance: ["Source lineage", "Model output", "Agreement risk", "Validation gate"],
    operator: ["Input queue", "Evidence review", "Human gate", "Draft action"],
    feed: ["Source stream", "Freshness check", "Data boundary", "Review view"],
    market: ["Simulation input", "Integrity check", "Evidence ledger", "Review gate"],
    environment: ["Public source", "Baseline window", "Anomaly signal", "Validation"],
    shield: ["Assumption layer", "Boundary model", "Engineering review", "Claim gate"],
    governance: ["Invariant draft", "Test case", "Review gate", "Revision"],
    memory: ["Source node", "Tagged trace", "Retention rule", "Audit path"],
    energy: ["Hardware baseline", "Workload", "Measurement", "Reproduction"],
    archive: ["Record", "Context", "Preservation", "Reference"]
  };
  function siteUrl(path) {
    return new URL(String(path || "").replace(/^\/+/, ""), siteRoot).href;
  }

  async function loadJson(path) {
    const dataUrl = new URL(siteUrl(path));
    dataUrl.searchParams.set("v", dataReleaseKey);
    const response = await fetch(dataUrl.href, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("DATA_UNAVAILABLE");
    }
    return response.json();
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#039;"
    })[character]);
  }

  function statusClass(value) {
    const normalized = String(value || "").toLowerCase();
    if (normalized.includes("verified") || normalized.includes("public link") || normalized.includes("implementation") || normalized.includes("completed") || normalized.includes("deployed")) return "ok";
    if (normalized.includes("archive")) return "archive";
    if (normalized.includes("verify") || normalized.includes("draft") || normalized.includes("private")) return "warn";
    return "info";
  }

  function badge(value) {
    return `<span class="badge ${statusClass(value)}">${escapeHtml(value)}</span>`;
  }

  function projectName(project) {
    return project.public_name || project.name || "Aureon platform";
  }

  function projectDescriptor(project) {
    return project.category || project.type || project.source_status || "Public platform";
  }

  function updateSourceBadge(update) {
    return `<span class="update-evidence source">${escapeHtml(update.source_name || "Public source")}</span>`;
  }

  function updateSourceLink(update) {
    if (!update.source_url) return "";
    const isExternal = /^https?:\/\//i.test(update.source_url);
    const href = isExternal ? update.source_url : siteUrl(update.source_url);
    const attributes = isExternal ? ' target="_blank" rel="noopener noreferrer"' : "";
    return `<a class="progress-source" href="${escapeHtml(href)}"${attributes}>${escapeHtml(update.source_label || "Open the source")}<span aria-hidden="true"> ↗</span></a>`;
  }

  function formatUpdateDate(value, compact = false) {
    const parsed = new Date(`${value}T00:00:00Z`);
    if (Number.isNaN(parsed.getTime())) return String(value || "");
    return new Intl.DateTimeFormat("en-GB", compact
      ? { day: "numeric", month: "short", timeZone: "UTC" }
      : { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(parsed);
  }

  function externalLink(url, label, className = "btn compact") {
    if (!url) return "";
    return `<a class="${className}" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
  }

  function localLink(path, label, className = "btn compact") {
    return `<a class="${className}" href="${escapeHtml(siteUrl(path))}">${escapeHtml(label)}</a>`;
  }

  function sourceGroup(project) {
    const value = `${project.source_status} ${project.verification_status}`.toLowerCase();
    if (value.includes("verified") || value.includes("public code") || value.includes("public research")) return "verified";
    if (value.includes("archive")) return "archive";
    if (value.includes("draft") || value.includes("private")) return "draft";
    return "to-verify";
  }

  function projectRow(project) {
    const sources = [
      externalLink(project.github_url, "GitHub"),
      externalLink(project.zenodo_url, "Zenodo")
    ].filter(Boolean).join("");

    return `
      <tr>
        <td class="project-cell">
          <div class="project-cell-layout">
            <img class="project-thumb" src="${escapeHtml(siteUrl(project.thumbnail_asset))}" alt="" width="72" height="48" loading="lazy" decoding="async">
            <div>
              <span class="registry-id">${escapeHtml(project.source_status || project.type || "Public source")}</span>
              <strong>${escapeHtml(projectName(project))}</strong>
              <span class="mini">${escapeHtml(project.type)}</span>
            </div>
          </div>
        </td>
        <td>${escapeHtml(project.category)}</td>
        <td>${badge(project.status)}</td>
        <td class="source-cell">${badge(project.source_status)}<div class="mini">${escapeHtml(project.verification_status)}</div></td>
        <td class="project-summary">${escapeHtml(project.summary)}</td>
        <td>${escapeHtml(project.next_step || "Next validation defined")}</td>
        <td><div class="row-actions">${localLink(project.page_url, "Open project", "btn compact primary")}${sources || '<span class="source-empty">No public source</span>'}</div></td>
      </tr>`;
  }

  function populateSelect(select, values, allLabel) {
    if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="all">${escapeHtml(allLabel)}</option>` + values
      .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
      .join("");
    if (["all", ...values].includes(current)) select.value = current;
  }

  function setupProjectTable(projects, tableBody) {
    const scope = tableBody.closest("[data-registry]") || document;
    const searchInput = scope.querySelector("[data-search]");
    const categoryFilter = scope.querySelector("[data-category-filter]");
    const statusFilter = scope.querySelector("[data-status-filter]");
    const sourceFilter = scope.querySelector("[data-source-filter]");
    const sortSelect = scope.querySelector("[data-sort-select]");
    const clearButton = scope.querySelector("[data-clear-filters]");
    const resultCount = scope.querySelector("[data-result-count]");
    const limit = Number(tableBody.dataset.limit || 0);
    const state = { key: "name", direction: "asc" };

    populateSelect(categoryFilter, [...new Set(projects.map((project) => project.category))].sort(), "All categories");
    populateSelect(statusFilter, [...new Set(projects.map((project) => project.status))].sort(), "All statuses");

    function updateSortIndicators() {
      scope.querySelectorAll("th[data-sort]").forEach((header) => {
        const active = header.dataset.sort === state.key;
        header.setAttribute("aria-sort", active ? (state.direction === "asc" ? "ascending" : "descending") : "none");
      });
      if (sortSelect) sortSelect.value = `${state.key}:${state.direction}`;
    }

    function render() {
      const query = String(searchInput?.value || "").trim().toLowerCase();
      const category = categoryFilter?.value || "all";
      const status = statusFilter?.value || "all";
      const source = sourceFilter?.value || "all";
      const filtered = projects.filter((project) => {
        const haystack = [
          project.name,
          project.type,
          project.category,
          project.status,
          project.source_status,
          project.summary,
          project.technical_summary,
          project.caution,
          project.next_step
        ].join(" ").toLowerCase();
        return (!query || haystack.includes(query))
          && (category === "all" || project.category === category)
          && (status === "all" || project.status === status)
          && (source === "all" || sourceGroup(project) === source);
      }).sort((left, right) => {
        const result = String(left[state.key] || "").localeCompare(String(right[state.key] || ""), "en", { sensitivity: "base" });
        return state.direction === "asc" ? result : -result;
      });

      const visible = limit ? filtered.slice(0, limit) : filtered;
      tableBody.innerHTML = visible.length
        ? visible.map(projectRow).join("")
        : `<tr><td class="empty-row" colspan="7">No projects match the selected filters.</td></tr>`;
      if (resultCount) {
        resultCount.textContent = `${filtered.length} of ${projects.length} projects`;
      }
      updateSortIndicators();
    }

    [searchInput, categoryFilter, statusFilter, sourceFilter].forEach((control) => {
      if (control) control.addEventListener(control.tagName === "INPUT" ? "input" : "change", render);
    });

    scope.querySelectorAll("th[data-sort] button").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.closest("th").dataset.sort;
        if (state.key === key) {
          state.direction = state.direction === "asc" ? "desc" : "asc";
        } else {
          state.key = key;
          state.direction = "asc";
        }
        render();
      });
    });

    if (sortSelect) {
      sortSelect.addEventListener("change", () => {
        [state.key, state.direction] = sortSelect.value.split(":");
        render();
      });
    }

    if (clearButton) {
      clearButton.addEventListener("click", () => {
        if (searchInput) searchInput.value = "";
        [categoryFilter, statusFilter, sourceFilter].forEach((control) => {
          if (control) control.value = "all";
        });
        state.key = "name";
        state.direction = "asc";
        render();
      });
    }

    render();
  }

  function renderStats(projects) {
    document.querySelectorAll("[data-project-stats]").forEach((container) => {
      const verified = projects.filter((project) => sourceGroup(project) === "verified").length;
      const review = projects.filter((project) => ["to-verify", "draft"].includes(sourceGroup(project))).length;
      const categories = new Set(projects.map((project) => project.category)).size;
      const stats = [
        [projects.length, "Portfolio entries"],
        [verified, "Verified public-source entries"],
        [review, "Review-bound entries"],
        [categories, "Portfolio categories"]
      ];
      container.innerHTML = stats.map(([value, label]) => `<div class="stat"><strong>${value}</strong><span>${escapeHtml(label)}</span></div>`).join("");
    });
  }

  async function renderEcosystem(projects) {
    const container = document.querySelector("[data-project-graph]");
    if (!container) return;
    try {
      const graph = await loadJson("data/project-graph.json");
      const bySlug = new Map(projects.map((project) => [project.slug, project]));
      const groups = new Map();
      graph.nodes.forEach((node) => {
        if (!groups.has(node.group)) groups.set(node.group, []);
        const project = bySlug.get(node.slug);
        if (project) groups.get(node.group).push(projectName(project));
      });
      const nodes = [...groups.entries()].map(([group, names]) => `
        <div class="ecosystem-node"><strong>${escapeHtml(group)}</strong><span>${escapeHtml(names.join(" / "))}</span></div>`).join("");
      const relations = graph.edges.filter((edge) => bySlug.has(edge.from) && bySlug.has(edge.to)).map((edge) => {
        const from = bySlug.get(edge.from) ? projectName(bySlug.get(edge.from)) : edge.from;
        const to = bySlug.get(edge.to) ? projectName(bySlug.get(edge.to)) : edge.to;
        return `<span>${escapeHtml(from)} -> ${escapeHtml(to)}: ${escapeHtml(edge.label)}</span>`;
      }).join("");
      container.innerHTML = `<div class="ecosystem-map">${nodes}</div><div class="relationship-ledger" aria-label="Project relationships">${relations}</div>`;
    } catch (_error) {
      showInlineError(container, "The project relationship map is temporarily unavailable.");
    }
  }

  function evidenceStateClass(value) {
    const normalized = String(value || "To verify").toLowerCase();
    if (normalized.includes("independent")) return "independent";
    if (normalized.includes("provider")) return "provider";
    if (normalized.includes("company")) return "company";
    if (normalized.includes("source")) return "source";
    return "verify";
  }

  function publicationActions(record) {
    return [
      externalLink(record.source_url, `Open ${record.channel || "source"}`, "evidence-record-link"),
      externalLink(record.doi_url, "Open DOI", "evidence-record-link secondary"),
      record.internal_url ? localLink(record.internal_url, "Read company context", "evidence-record-link secondary") : ""
    ].filter(Boolean).join("");
  }

  function renderPublications(data) {
    const records = Array.isArray(data) ? data : (data.records || []);

    document.querySelectorAll("[data-publications]").forEach((tableBody) => {
      tableBody.innerHTML = records.map((record) => `
        <tr>
          <td><strong>${escapeHtml(record.record_group || record.project)}</strong></td>
          <td>${escapeHtml(record.title || record.artifact)}</td>
          <td>${escapeHtml(record.record_type || record.type)}</td>
          <td>${escapeHtml(record.channel || "Not listed")}</td>
          <td>${badge(record.evidence_state || record.status)}</td>
          <td>${escapeHtml(record.boundary || record.notes)}</td>
          <td><div class="actions">${publicationActions(record)}</div></td>
        </tr>`).join("");
    });

    document.querySelectorAll("[data-publications-preview]").forEach((container) => {
      const limit = Number(container.dataset.limit || 3);
      const previewRecords = [...records].sort((a, b) => Number(Boolean(b.featured)) - Number(Boolean(a.featured))).slice(0, limit);
      container.innerHTML = previewRecords.map((record) => `
        <article class="record-item">
          <div>${badge(record.evidence_state || record.status)}</div>
          <div><h3>${escapeHtml(record.title || record.project)}</h3><p>${escapeHtml(record.record_type || record.artifact)}. ${escapeHtml(record.boundary || record.notes)}</p></div>
          <div class="actions">${publicationActions(record)}</div>
        </article>`).join("");
    });

    document.querySelectorAll("[data-evidence-library]").forEach((library) => {
      const search = library.querySelector("[data-evidence-search]");
      const group = library.querySelector("[data-evidence-group]");
      const channel = library.querySelector("[data-evidence-channel]");
      const clear = library.querySelector("[data-evidence-clear]");
      const resultCount = library.querySelector("[data-evidence-result-count]");
      const container = library.querySelector("[data-evidence-records]");
      if (!search || !group || !channel || !clear || !resultCount || !container) return;

      const addOptions = (select, values) => {
        values.forEach((value) => {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = value;
          select.appendChild(option);
        });
      };
      addOptions(group, [...new Set(records.map((record) => record.record_group).filter(Boolean))].sort());
      addOptions(channel, [...new Set(records.map((record) => record.channel).filter(Boolean))].sort());

      const renderFilteredRecords = () => {
        const query = search.value.trim().toLowerCase();
        const groupValue = group.value;
        const channelValue = channel.value;
        const filtered = records.filter((record) => {
          const searchable = [record.title, record.record_type, record.author, record.channel, record.record_group, record.boundary].join(" ").toLowerCase();
          return (!query || searchable.includes(query)) && (!groupValue || record.record_group === groupValue) && (!channelValue || record.channel === channelValue);
        });

        resultCount.textContent = filtered.length === records.length ? "All public records shown" : "Filtered public records shown";
        if (!records.length) {
          container.innerHTML = '<div class="evidence-empty"><strong>No evidence records are available in this public view.</strong><span>Use the public research index or contact the company for a scoped evidence request.</span></div>';
          return;
        }
        if (!filtered.length) {
          container.innerHTML = '<div class="evidence-empty"><strong>No records match these filters.</strong><span>Clear the search or change the record group and channel.</span></div>';
          return;
        }
        container.innerHTML = filtered.map((record) => `
          <article class="evidence-record-card${record.featured ? " featured" : ""}">
            <div class="evidence-record-top">
              <span class="evidence-record-group">${escapeHtml(record.record_group)}</span>
              <span class="evidence-state ${evidenceStateClass(record.evidence_state)}">${escapeHtml(record.evidence_state)}</span>
            </div>
            <h3>${escapeHtml(record.title)}</h3>
            <dl class="evidence-record-meta">
              <div><dt>Type</dt><dd>${escapeHtml(record.record_type)}</dd></div>
              <div><dt>Channel</dt><dd>${escapeHtml(record.channel)}</dd></div>
              <div><dt>Author</dt><dd>${escapeHtml(record.author)}</dd></div>
            </dl>
            <p class="evidence-record-boundary"><strong>Boundary</strong>${escapeHtml(record.boundary)}</p>
            <div class="evidence-record-actions">${publicationActions(record)}</div>
          </article>`).join("");
      };

      search.addEventListener("input", renderFilteredRecords);
      group.addEventListener("change", renderFilteredRecords);
      channel.addEventListener("change", renderFilteredRecords);
      clear.addEventListener("click", () => {
        search.value = "";
        group.value = "";
        channel.value = "";
        search.focus();
        renderFilteredRecords();
      });
      renderFilteredRecords();
    });
  }

  function renderResearch(data) {
    const profiles = data.profiles || [];
    const papers = data.papers || [];
    const uniquePapers = papers.filter((paper, index, list) => list.findIndex((candidate) => candidate.url === paper.url) === index);
    const nameById = {};
    profiles.forEach((profile) => { nameById[profile.id] = profile.name; });

    document.querySelectorAll("[data-research-profiles]").forEach((container) => {
      container.innerHTML = profiles.map((profile) => `
        <article class="card">
          <div class="card-accent"></div>
          <div class="eyebrow">${escapeHtml(profile.public_role || profile.role)}</div>
          <h3>${escapeHtml(profile.name)}</h3>
          <p>${escapeHtml(profile.summary)}</p>
          <div class="github-channel-actions">${(profile.links || []).map((link) => externalLink(link.url, link.label)).join("")}</div>
          ${(profile.collections || []).map((collection) => `<p class="mini">${externalLink(collection.url, collection.label)} &mdash; ${escapeHtml(collection.note)}</p>`).join("")}
        </article>`).join("");
    });

    document.querySelectorAll("[data-research-notes]").forEach((container) => {
      container.innerHTML = (data.featured_notes || []).map((note) => `
        <article class="source-card research-note-card">
          <span class="source-type">${escapeHtml(note.record_type)}</span>
          <h3>${escapeHtml(note.title)}</h3>
          <p class="research-note-channel">Published through <em>${escapeHtml(note.channel)}</em></p>
          <p class="research-note-boundary">${escapeHtml(note.verification_status)}</p>
          <span class="research-note-checked">Author-published public source</span>
          ${externalLink(note.url, "Read the public note", "research-note-link")}
        </article>`).join("");
    });

    document.querySelectorAll("[data-research]").forEach((tableBody) => {
      tableBody.innerHTML = uniquePapers.map((paper) => `
          <tr>
            <td><strong>${escapeHtml(nameById[paper.author] || paper.author)}</strong></td>
            <td>${escapeHtml(paper.title)}</td>
            <td>${escapeHtml(paper.type)}</td>
            <td>${escapeHtml(paper.platform)}</td>
            <td>${badge(paper.verification_status || "Public source listed; independent review remains separate.")}</td>
            <td>${externalLink(paper.url, "View")}${externalLink(paper.doi, "DOI")}${(!paper.url && !paper.doi) ? '<span class="source-empty">Not listed</span>' : ""}</td>
          </tr>`).join("");
    });
  }

  function renderResearchCatalogue(data) {
    const orcid = data.orcid || {};
    const zenodo = data.zenodo || {};
    const breadth = data.research_breadth || {};
    const researchOrientation = {
      "[data-research-catalogue-orcid-role]": orcid.role || "Persistent researcher identity and public work index",
      "[data-research-catalogue-zenodo-role]": zenodo.role || "Formal public repository and DOI source",
      "[data-research-catalogue-review-posture]": breadth.review_posture || "Independent challenge and domain-qualified review remain the relevant proof gates.",
      "[data-research-catalogue-translation-gate]": breadth.translation_gate || "Translation requires an explicit use case, authority boundary, test method and evidence standard."
    };
    Object.entries(researchOrientation).forEach(([selector, value]) => {
      document.querySelectorAll(selector).forEach((element) => { element.textContent = String(value); });
    });
    document.querySelectorAll("[data-research-catalogue-boundary]").forEach((element) => {
      element.textContent = data.evidence_boundary || "";
    });

    document.querySelectorAll("[data-research-catalogue-recent]").forEach((container) => {
      container.innerHTML = (data.recent_records || []).map((record) => `
        <article class="research-catalogue-record">
          <div class="research-catalogue-record-meta">
            <span>${escapeHtml(record.record_type || "Public record")}</span>
            <time datetime="${escapeHtml(record.publication_date)}">${escapeHtml(record.publication_date)}</time>
          </div>
          <h3>${escapeHtml(record.title)}</h3>
          <p>${escapeHtml(record.doi)}</p>
          <div class="research-catalogue-record-actions">
            ${externalLink(record.url, "Open Zenodo record")}
            ${externalLink(record.doi_url, "Open DOI")}
          </div>
        </article>`).join("");
    });
  }

  function renderPublicFootprint(data) {
    const signals = Array.isArray(data.signals) ? data.signals : [];
    const byMetric = Object.fromEntries(signals.map((signal) => [signal.metric, signal]));
    const github = byMetric.main_branch_commits || {};
    const githubSecondary = github.secondary_metrics || {};
    const values = {
      public_work_groups: byMetric.public_work_groups?.value,
      main_branch_commits: github.value,
      research_reads: byMetric.research_reads?.value,
      github_stars: githubSecondary.stars,
      github_forks: githubSecondary.forks
    };
    const formatNumber = (value) => new Intl.NumberFormat("en-GB").format(Number(value));

    document.querySelectorAll("[data-footprint-value]").forEach((element) => {
      const value = values[element.dataset.footprintValue];
      if (Number.isFinite(Number(value))) element.textContent = formatNumber(value);
    });

    const textValues = {
      github_summary: `${formatNumber(values.main_branch_commits)} commits · ${formatNumber(values.github_stars)} stars · ${formatNumber(values.github_forks)} forks`,
      github_secondary: `${formatNumber(values.github_stars)} stars · ${formatNumber(values.github_forks)} forks · 21 Aug 2026`
    };
    document.querySelectorAll("[data-footprint-text]").forEach((element) => {
      const value = textValues[element.dataset.footprintText];
      if (value) element.textContent = value;
    });
  }

  function renderSubstackCatalogue(data) {
    const entries = [...(data.entries || [])].sort((left, right) => String(right.published_utc || "").localeCompare(String(left.published_utc || "")));
    const themes = [...(data.themes || [])];
    const themeById = new Map(themes.map((theme) => [theme.id, theme]));
    const formatDate = (value, options = { day: "numeric", month: "short", year: "numeric" }) => {
      if (!value) return "Date not listed";
      const date = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
      if (Number.isNaN(date.getTime())) return value;
      return new Intl.DateTimeFormat("en-GB", { ...options, timeZone: "UTC" }).format(date);
    };

    document.querySelectorAll("[data-substack-guides]").forEach((container) => {
      const guides = entries.filter((entry) => Number(entry.guide_rank) > 0).sort((left, right) => Number(left.guide_rank) - Number(right.guide_rank));
      container.innerHTML = guides.map((entry) => `
        <article class="journal-guide-card">
          <span>0${escapeHtml(entry.guide_rank)} / ${escapeHtml(entry.guide_label || "Orientation")}</span>
          <h3>${escapeHtml(entry.title)}</h3>
          <p>${escapeHtml(themeById.get(entry.topic)?.description || "Open the author-published orientation note.")}</p>
          ${externalLink(entry.url, "Open orientation note", "journal-guide-link")}
        </article>`).join("");
    });

    document.querySelectorAll("[data-substack-catalogue]").forEach((container) => {
      const section = container.closest("section") || document;
      const filterRoot = section.querySelector("[data-substack-filter]");
      const searchInput = section.querySelector("[data-substack-search]");
      const resultCount = section.querySelector("[data-substack-result-count]");
      let activeTheme = "all";

      if (filterRoot) {
        const filterItems = [{ id: "all", label: "All notes" }, ...themes];
        filterRoot.innerHTML = filterItems.map((theme, index) => `<button type="button" class="${index === 0 ? "is-active" : ""}" data-substack-filter-value="${escapeHtml(theme.id)}" aria-pressed="${index === 0 ? "true" : "false"}">${escapeHtml(theme.label)}</button>`).join("");
      }

      const render = () => {
        const query = String(searchInput?.value || "").trim().toLowerCase();
        const visibleEntries = entries.filter((entry) => {
          const theme = themeById.get(entry.topic);
          const matchesTheme = activeTheme === "all" || entry.topic === activeTheme;
          const haystack = [entry.title, theme?.label, theme?.description].join(" ").toLowerCase();
          return matchesTheme && (!query || haystack.includes(query));
        });

        if (resultCount) {
          resultCount.textContent = visibleEntries.length === entries.length ? "All public notes shown" : "Filtered public notes shown";
        }

        container.innerHTML = visibleEntries.length ? visibleEntries.map((entry) => {
          const theme = themeById.get(entry.topic) || { label: "Unclassified", prompt: "Open the source and assess its evidence boundary." };
          const archiveLabel = entry.archive_visible === false ? "Direct public note" : "Archive listed";
          const archiveClass = entry.archive_visible === false ? "direct" : "archive";
          const artwork = entry.artwork ? `
              <a class="journal-note-art" href="${escapeHtml(entry.url)}" target="_blank" rel="noopener noreferrer" aria-label="Open ${escapeHtml(entry.title)} on Substack">
                <picture>
                  ${entry.artwork_small ? `<source media="(max-width: 700px)" srcset="${escapeHtml(siteUrl(entry.artwork_small))}" type="image/webp">` : ""}
                  <img src="${escapeHtml(siteUrl(entry.artwork))}" alt="${escapeHtml(entry.artwork_alt || "")}" width="1200" height="675" loading="lazy" decoding="async">
                </picture>
                <span>${escapeHtml(entry.artwork_caption || "Editorial illustration · author-published note")}</span>
              </a>` : "";
          return `
            <article class="journal-note-card${entry.artwork ? " has-artwork" : ""}" data-journal-topic="${escapeHtml(entry.topic)}">
              ${artwork}
              <div class="journal-note-meta"><span class="journal-topic">${escapeHtml(theme.label)}</span><span class="journal-listing-state ${archiveClass}">${archiveLabel}</span></div>
              <h3>${escapeHtml(entry.title)}</h3>
              ${entry.subtitle ? `<p class="journal-note-summary">${escapeHtml(entry.subtitle)}</p>` : ""}
              <p class="journal-reading-prompt"><span>Reading prompt</span>${escapeHtml(theme.prompt)}</p>
              <div class="journal-note-footer"><time datetime="${escapeHtml(entry.published_utc)}">${escapeHtml(formatDate(entry.published_utc))}</time>${externalLink(entry.url, "Open public note", "journal-note-link")}</div>
            </article>`;
        }).join("") : '<div class="journal-empty-state"><strong>No notes match this view.</strong><p>Clear the search or choose another reading theme. The provider archive remains available above.</p></div>';
      };

      filterRoot?.querySelectorAll("[data-substack-filter-value]").forEach((button) => {
        button.addEventListener("click", () => {
          activeTheme = button.dataset.substackFilterValue || "all";
          filterRoot.querySelectorAll("[data-substack-filter-value]").forEach((item) => {
            const active = item === button;
            item.classList.toggle("is-active", active);
            item.setAttribute("aria-pressed", String(active));
          });
          render();
        });
      });
      searchInput?.addEventListener("input", render);
      render();
    });

    document.querySelectorAll("[data-substack-boundary]").forEach((container) => {
      container.textContent = data.verification_status || "";
    });

    document.querySelectorAll("[data-substack-scope]").forEach((container) => {
      container.textContent = data.catalogue_scope || "";
    });

    document.querySelectorAll("[data-substack-archive]").forEach((container) => {
      container.innerHTML = externalLink(data.archive_url, "Open the complete public archive", "btn primary")
        + externalLink(data.profile_url, "Open the publication home", "btn");
    });
  }

  function renderUpdates(data) {
    const updates = Array.isArray(data) ? data : (data.records || []);
    const controls = document.querySelector("[data-update-controls]");
    const searchInput = controls?.querySelector("[data-update-search]");
    const clearButton = controls?.querySelector("[data-update-clear]");
    const filterBar = document.querySelector("[data-update-filter]");
    let activeCategory = "all";

    const filteredUpdates = () => {
      const query = String(searchInput?.value || "").trim().toLowerCase();
      return updates.filter((update) => {
        const haystack = [update.title, update.summary, update.category, update.investor_relevance, update.source_name, update.source_label, update.next_validation].join(" ").toLowerCase();
        return (activeCategory === "all" || update.category === activeCategory)
          && (!query || haystack.includes(query));
      });
    };

    const render = () => {
      const filtered = filteredUpdates();
      document.querySelectorAll("[data-update-result-count]").forEach((node) => {
        node.textContent = filtered.length === updates.length ? "All milestone themes shown" : "Filtered milestone view";
      });

      document.querySelectorAll("[data-updates]").forEach((container) => {
        const limit = Number(container.dataset.limit || filtered.length);
        const visibleUpdates = filtered.slice(0, limit);
        container.innerHTML = visibleUpdates.length ? visibleUpdates.map((update) => `
          <article class="progress-entry" data-update-id="${escapeHtml(update.id)}" data-update-category="${escapeHtml(update.category)}">
            <div class="progress-date"><span>${escapeHtml(formatUpdateDate(update.date, true))}</span><time datetime="${escapeHtml(update.date)}">${escapeHtml(formatUpdateDate(update.date))}</time><i class="progress-marker" aria-hidden="true"></i></div>
            <div class="progress-card">
              <div class="progress-meta"><span class="progress-category">${escapeHtml(update.category)}</span>${updateSourceBadge(update)}</div>
              <h3>${escapeHtml(update.title)}</h3>
              <p>${escapeHtml(update.summary)}</p>
              <div class="progress-decision-grid">
                <div class="progress-boundary"><strong>Why it matters</strong><span>${escapeHtml(update.investor_relevance)}</span></div>
                <div class="progress-gate"><strong>Next validation</strong><span>${escapeHtml(update.next_validation)}</span></div>
              </div>
              <div class="progress-card-footer"><div><span class="progress-reading-label">Public source</span><p>${escapeHtml(update.source_name)}</p></div><div class="progress-record-actions">${updateSourceLink(update)}</div></div>
            </div>
          </article>`).join("") : '<div class="update-empty-state"><strong>No milestones match this view.</strong><p>Clear the search or choose another investor signal.</p></div>';
      });
    };

    filterBar?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-update-filter-value]");
      if (!button) return;
      activeCategory = button.dataset.updateFilterValue || "all";
      filterBar.querySelectorAll("[data-update-filter-value]").forEach((candidate) => {
        const active = candidate === button;
        candidate.classList.toggle("is-active", active);
        candidate.setAttribute("aria-pressed", String(active));
      });
      render();
    });
    searchInput?.addEventListener("input", render);
    clearButton?.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      activeCategory = "all";
      filterBar?.querySelectorAll("[data-update-filter-value]").forEach((button) => {
        const active = button.dataset.updateFilterValue === "all";
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      searchInput?.focus();
      render();
    });
    render();
  }

  function listItems(items) {
    return (items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  }

  function sourceButtons(project) {
    return [
      externalLink(project.github_url, "GitHub", "btn"),
      externalLink(project.zenodo_url, "Zenodo", "btn"),
      externalLink(project.secondary_zenodo_url, "Zenodo record 2", "btn"),
      externalLink(project.doi_url, "DOI", "btn")
    ].filter(Boolean).join("") || '<span class="source-empty">No verified public source link is listed.</span>';
  }

  function relatedCards(project, projects) {
    const bySlug = new Map(projects.map((item) => [item.slug, item]));
    const relatedProjects = (project.related_projects || []).map((slug) => bySlug.get(slug)).filter((related) => related?.active_company_project === true);
    if (!relatedProjects.length) return '<p class="notice">No additional current company platform records are linked here.</p>';
    return relatedProjects.map((related) => `
      <article class="related-card">
        <img class="related-card-visual" src="${escapeHtml(siteUrl(related.thumbnail_asset))}" alt="" width="480" height="270" loading="lazy" decoding="async">
        <div><span class="registry-id">${escapeHtml(projectDescriptor(related))}</span><h3>${escapeHtml(projectName(related))}</h3><p>${escapeHtml(related.summary)}</p></div>
        ${localLink(related.page_url, "Open project", "btn compact")}
      </article>`).join("");
  }

  function supportingVisuals(project) {
    return (project.supporting_visuals || []).map((visual) => `
      <figure class="project-visual">
        <img src="${escapeHtml(siteUrl(visual.src))}" alt="${escapeHtml(visual.alt)}" width="1280" height="720" loading="lazy" decoding="async">
      </figure>`).join("");
  }

  function renderProjectDetail(project, projects) {
    const container = document.querySelector("[data-project-detail]");
    if (!container) return;
    if (project.active_company_project !== true) {
      renderRetiredProjectRoute(container);
      return;
    }
    const labels = projectMapLabels[project.visual_mode] || projectMapLabels.runtime;
    const publicBoundary = project.public_safe
      ? "Public profile with the stated evidence and claim boundaries."
      : "Partner or draft concept. Public claims remain restricted pending review.";

    document.title = `${projectName(project)} | R&A Consulting`;
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = project.summary;

    container.innerHTML = `
      <section class="project-detail-hero">
        <img class="project-detail-hero-media" src="${escapeHtml(siteUrl(project.visual_asset))}" alt="" width="1536" height="864" fetchpriority="high" decoding="async">
        <div class="wrap">
          <a class="breadcrumbs" href="${escapeHtml(siteUrl("projects/"))}">Back to Projects</a>
          <div class="eyebrow">${escapeHtml(projectDescriptor(project))}</div>
          <h1>${escapeHtml(projectName(project))}</h1>
          <div class="badges">${badge(project.status)}${badge(project.source_status)}</div>
          <p class="lead">${escapeHtml(project.summary)}</p>
          <div class="actions">${sourceButtons(project)}</div>
        </div>
      </section>
      <section class="project-meta-strip" aria-label="Project metadata">
        <div class="project-meta"><span>Project type</span><strong>${escapeHtml(project.type)}</strong></div>
        <div class="project-meta"><span>Status</span><strong>${escapeHtml(project.status)}</strong></div>
        <div class="project-meta"><span>Source status</span><strong>${escapeHtml(project.source_status)}</strong></div>
        <div class="project-meta"><span>Next validation</span><strong>${escapeHtml(project.next_step || "Scoped validation plan")}</strong></div>
      </section>
      <section class="band alt">
        <div class="wrap">
          <div class="project-story">
            <div><div class="eyebrow">Project profile</div><h2>${escapeHtml(project.visual_label)}</h2><p>${escapeHtml(project.technical_summary)}</p><p><strong>Verification status:</strong> ${escapeHtml(project.verification_status)}</p></div>
            <div class="project-system-map" aria-label="Conceptual project map">
              ${labels.map((label) => `<div class="map-node">${escapeHtml(label)}</div>`).join("")}
              <p class="map-caption">Concept map, not operational proof.</p>
            </div>
          </div>
          <div class="project-media-rail" aria-label="Supporting project visuals">${supportingVisuals(project)}</div>
        </div>
      </section>
      <section class="band">
        <div class="wrap evidence-columns">
          <article class="evidence-panel exists"><div class="eyebrow">Current state</div><h2>What exists now</h2><ul>${listItems(project.exists_now)}</ul></article>
          <article class="evidence-panel verify"><div class="eyebrow">Evidence boundary</div><h2>What is TO VERIFY</h2><ul>${listItems(project.to_verify)}</ul></article>
        </div>
      </section>
      <section class="band boundary-band">
        <div class="wrap grid cols-2">
          <div><div class="eyebrow">Public claim boundary</div><h2>${escapeHtml(publicBoundary)}</h2></div>
          <div class="panel"><h3>Required caution</h3><p>${escapeHtml(project.caution)}</p></div>
        </div>
      </section>
      <section class="band alt"><div class="wrap next-step"><strong>Next step</strong><p>${escapeHtml(project.next_step)}</p></div></section>
      <section class="band"><div class="wrap"><div class="section-head"><div><div class="eyebrow">Portfolio links</div><h2>Related projects</h2></div><p>Relationships indicate shared questions or workflow context, not validation transfer between projects.</p></div><div class="related-grid">${relatedCards(project, projects)}</div></div></section>
      <section class="band warm"><div class="wrap"><div class="eyebrow">Sources</div><h2>Open project links</h2><p class="lead">Public links are listed only where the registry provides them. Missing links remain visibly unverified.</p><div class="actions">${sourceButtons(project)}${localLink("publications/", "Public records", "btn")}</div></div></section>`;

  }

  function renderRetiredProjectRoute(container) {
    if (!container) return;
    document.title = "Archived reference | Aureon Zorza Technologies";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "Historical route retained for link continuity; it is not a current R&A Consulting product or company research record.";
    let robots = document.querySelector('meta[name="robots"]');
    if (!robots) {
      robots = document.createElement("meta");
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    robots.content = "noindex,follow";
    container.innerHTML = `
      <section class="page-hero"><div class="wrap"><div class="eyebrow">Archived route</div><h1>Not part of the current company platform registry.</h1><p class="lead">This URL remains available only so older links resolve safely. It is not presented as an R&amp;A Consulting product, company research project, evidence of capability, or current investment material.</p><div class="actions">${localLink("projects/", "Open current platform record", "btn primary")}${localLink("research/", "Open verified research index", "btn")}</div></div></section>`;
  }

  function showInlineError(container, message) {
    if (!container) return;
    if (container.tagName === "TBODY") {
      container.innerHTML = `<tr><td class="empty-row" colspan="7" role="status">${escapeHtml(message)}</td></tr>`;
      return;
    }
    container.innerHTML = `<p class="notice error" role="status">${escapeHtml(message)}</p>`;
  }

  function setActiveNavigation() {
    const page = document.body.dataset.page;
    const selectedNavigation = page === "projects" && window.location.hash === "#blades"
      ? "applications"
      : page;
    document.querySelectorAll("[data-nav]").forEach((link) => {
      link.classList.remove("active");
      link.removeAttribute("aria-current");
      if (link.dataset.nav === selectedNavigation) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
    });
    if (page === "projects" && !window.__aureonProjectNavHashBound) {
      window.__aureonProjectNavHashBound = true;
      window.addEventListener("hashchange", setActiveNavigation);
    }
  }

  function setupHomeControlPath() {
    document.querySelectorAll("[data-home-control-map]").forEach((root) => {
      const shell = root.querySelector(".home-control-shell");
      const tabs = Array.from(root.querySelectorAll("[data-control-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-control-panel]"));
      const nodes = Array.from(root.querySelectorAll("[data-control-node]"));
      if (!shell || !tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (stage, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.controlTab === stage) || tabs[0];
        const activeStage = nextTab.dataset.controlTab;
        const activeIndex = tabs.indexOf(nextTab);
        shell.dataset.activeControl = activeStage;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel.dataset.controlPanel === activeStage;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        nodes.forEach((node) => {
          const nodeIndex = tabs.findIndex((tab) => tab.dataset.controlTab === node.dataset.controlNode);
          node.classList.toggle("is-active", node.dataset.controlNode === activeStage);
          node.classList.toggle("is-past", nodeIndex >= 0 && nodeIndex < activeIndex);
        });
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.controlTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.controlTab, true);
        });
      });

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      activate(initial.dataset.controlTab);
    });
  }

  function setupPlatformArchitecture() {
    document.querySelectorAll("[data-platform-architecture]").forEach((root) => {
      const shell = root.querySelector(".platform-architecture-shell");
      const tabs = Array.from(root.querySelectorAll("[data-platform-layer-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-platform-layer-panel]"));
      const nodes = Array.from(root.querySelectorAll("[data-platform-layer-node]"));
      if (!shell || !tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (layer, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.platformLayerTab === layer) || tabs[0];
        const activeLayer = nextTab.dataset.platformLayerTab;
        const activeIndex = tabs.indexOf(nextTab);
        shell.dataset.activePlatformLayer = activeLayer;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel.dataset.platformLayerPanel === activeLayer;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        nodes.forEach((node) => {
          const nodeIndex = tabs.findIndex((tab) => tab.dataset.platformLayerTab === node.dataset.platformLayerNode);
          node.classList.toggle("is-active", node.dataset.platformLayerNode === activeLayer);
          node.classList.toggle("is-past", nodeIndex >= 0 && nodeIndex < activeIndex);
        });
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.platformLayerTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.platformLayerTab, true);
        });
      });

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      activate(initial.dataset.platformLayerTab);
    });
  }

  function setupPublicPacketInspector() {
    document.querySelectorAll("[data-packet-inspector]").forEach((root) => {
      const shell = root.querySelector(".packet-inspector-shell");
      const tabs = Array.from(root.querySelectorAll("[data-packet-layer-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-packet-layer-panel]"));
      const nodes = Array.from(root.querySelectorAll("[data-packet-layer-node]"));
      const readout = root.querySelector("[data-packet-readout]");
      if (!shell || !tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (layer, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.packetLayerTab === layer) || tabs[0];
        const activeLayer = nextTab.dataset.packetLayerTab;
        const activeIndex = tabs.indexOf(nextTab);
        const activePanel = panels.find((panel) => panel.dataset.packetLayerPanel === activeLayer) || panels[0];
        shell.dataset.activePacketLayer = activeLayer;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel === activePanel;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        nodes.forEach((node) => {
          const nodeIndex = tabs.findIndex((tab) => tab.dataset.packetLayerTab === node.dataset.packetLayerNode);
          node.classList.toggle("is-active", node.dataset.packetLayerNode === activeLayer);
          node.classList.toggle("is-past", nodeIndex >= 0 && nodeIndex < activeIndex);
        });
        if (readout) readout.textContent = activePanel.dataset.packetReadoutLabel || nextTab.textContent.trim();
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.packetLayerTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.packetLayerTab, true);
        });
      });

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      activate(initial.dataset.packetLayerTab);
    });
  }

  function setupLiveFreshnessConsole() {
    document.querySelectorAll("[data-live-freshness-console]").forEach((root) => {
      const shell = root.querySelector(".freshness-console-shell");
      const tabs = Array.from(root.querySelectorAll("[data-freshness-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-freshness-panel]"));
      const nodes = Array.from(root.querySelectorAll("[data-freshness-node]"));
      const readout = root.querySelector("[data-freshness-readout]");
      if (!shell || !tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (state, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.freshnessTab === state) || tabs[0];
        const activeState = nextTab.dataset.freshnessTab;
        const activeIndex = tabs.indexOf(nextTab);
        const activePanel = panels.find((panel) => panel.dataset.freshnessPanel === activeState) || panels[0];
        shell.dataset.activeFreshness = activeState;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel === activePanel;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        nodes.forEach((node) => {
          const nodeIndex = tabs.findIndex((tab) => tab.dataset.freshnessTab === node.dataset.freshnessNode);
          node.classList.toggle("is-active", node.dataset.freshnessNode === activeState);
          node.classList.toggle("is-past", nodeIndex >= 0 && nodeIndex < activeIndex);
        });
        if (readout) readout.textContent = activePanel.dataset.freshnessReadoutLabel || nextTab.textContent.trim();
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.freshnessTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.freshnessTab, true);
        });
      });

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      activate(initial.dataset.freshnessTab);
    });
  }

  function setupEngagementRouter() {
    document.querySelectorAll("[data-engagement-router]").forEach((root) => {
      const shell = root.querySelector(".engagement-router-shell");
      const tabs = Array.from(root.querySelectorAll("[data-engagement-route-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-engagement-route-panel]"));
      const readout = root.querySelector("[data-engagement-router-readout]");
      if (!shell || !tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (route, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.engagementRouteTab === route) || tabs[0];
        const activeRoute = nextTab.dataset.engagementRouteTab;
        const activePanel = panels.find((panel) => panel.dataset.engagementRoutePanel === activeRoute) || panels[0];
        shell.dataset.activeEngagementRoute = activeRoute;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel === activePanel;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        if (readout) readout.textContent = activePanel.dataset.engagementRouteLabel || nextTab.textContent.trim();
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.engagementRouteTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.engagementRouteTab, true);
        });
      });

      const routeAliases = {
        commercial: "pilot",
        evaluation: "pilot",
        grant: "partner",
        sector: "partner",
        "technical-review": "research",
        company: "investor",
        "investor-partner": "investor"
      };
      const requestedRoute = new URLSearchParams(window.location.search).get("route");
      const initialRoute = routeAliases[requestedRoute] || requestedRoute;
      const initial = tabs.find((tab) => tab.dataset.engagementRouteTab === initialRoute)
        || tabs.find((tab) => tab.getAttribute("aria-selected") === "true")
        || tabs[0];
      activate(initial.dataset.engagementRouteTab);
    });
  }

  function setupResearchEvidencePath() {
    document.querySelectorAll("[data-research-evidence-path]").forEach((root) => {
      const shell = root.querySelector(".research-proof-shell");
      const tabs = Array.from(root.querySelectorAll("[data-research-stage-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-research-stage-panel]"));
      const nodes = Array.from(root.querySelectorAll("[data-research-stage-node]"));
      if (!shell || !tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (stage, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.researchStageTab === stage) || tabs[0];
        const activeStage = nextTab.dataset.researchStageTab;
        const activeIndex = tabs.indexOf(nextTab);
        shell.dataset.activeResearchStage = activeStage;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel.dataset.researchStagePanel === activeStage;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        nodes.forEach((node) => {
          const nodeIndex = tabs.findIndex((tab) => tab.dataset.researchStageTab === node.dataset.researchStageNode);
          node.classList.toggle("is-active", node.dataset.researchStageNode === activeStage);
          node.classList.toggle("is-past", nodeIndex >= 0 && nodeIndex < activeIndex);
        });
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.researchStageTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.researchStageTab, true);
        });
      });

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      activate(initial.dataset.researchStageTab);
    });
  }

  function setupInvestorReviewLens() {
    document.querySelectorAll("[data-review-lens]").forEach((root) => {
      const tabs = Array.from(root.querySelectorAll("[data-review-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-review-panel]"));
      if (!tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (lens, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.reviewTab === lens) || tabs[0];
        const activeLens = nextTab.dataset.reviewTab;
        root.dataset.activeLens = activeLens;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel.dataset.reviewPanel === activeLens;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.reviewTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.reviewTab, true);
        });
      });

      const initial = tabs.find((tab) => tab.classList.contains("is-active")) || tabs[0];
      activate(initial.dataset.reviewTab);
    });
  }

  function setupDiligenceReviewQueue() {
    document.querySelectorAll("[data-diligence-queue]").forEach((root) => {
      const shell = root.querySelector(".diligence-queue-shell");
      const tabs = Array.from(root.querySelectorAll("[data-diligence-gate-tab]"));
      const panels = Array.from(root.querySelectorAll("[data-diligence-gate-panel]"));
      const nodes = Array.from(root.querySelectorAll("[data-diligence-gate-node]"));
      if (!shell || !tabs.length || !panels.length) return;

      root.classList.add("is-enhanced");
      const activate = (gate, moveFocus = false) => {
        const nextTab = tabs.find((tab) => tab.dataset.diligenceGateTab === gate) || tabs[0];
        const activeGate = nextTab.dataset.diligenceGateTab;
        const activeIndex = tabs.indexOf(nextTab);
        shell.dataset.activeGate = activeGate;

        tabs.forEach((tab) => {
          const active = tab === nextTab;
          tab.classList.toggle("is-active", active);
          tab.setAttribute("aria-selected", String(active));
          tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          const active = panel.dataset.diligenceGatePanel === activeGate;
          panel.classList.toggle("is-active", active);
          panel.hidden = !active;
        });
        nodes.forEach((node) => {
          const nodeIndex = tabs.findIndex((tab) => tab.dataset.diligenceGateTab === node.dataset.diligenceGateNode);
          node.classList.toggle("is-active", node.dataset.diligenceGateNode === activeGate);
          node.classList.toggle("is-past", nodeIndex >= 0 && nodeIndex < activeIndex);
        });
        if (moveFocus) nextTab.focus();
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab.dataset.diligenceGateTab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex = null;
          if (event.key === "ArrowRight" || event.key === "ArrowDown") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === null) return;
          event.preventDefault();
          activate(tabs[targetIndex].dataset.diligenceGateTab, true);
        });
      });

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      activate(initial.dataset.diligenceGateTab);
    });
  }

  function synchronizePrimaryNavigation() {
    const tabs = [
      ["projects", "Core", "projects/#core"],
      ["applications", "Applications", "projects/#blades"],
      ["research", "Research", "research/"],
      ["publications", "Evidence", "publications/"],
      ["about", "Company", "about/"],
      ["investor", "Investor brief", "funding/investor-deck/", "nav-cta"]
    ];
    document.querySelectorAll(".links").forEach((links) => {
      links.innerHTML = tabs.map(([id, label, path, className]) => `<a${className ? ` class="${className}"` : ""} data-nav="${id}" href="${escapeHtml(siteUrl(path))}">${escapeHtml(label)}</a>`).join("");
    });
    document.querySelectorAll(".brand small").forEach((subtitle) => {
      subtitle.textContent = "Evidence systems & deep-tech";
    });
  }

  function setupMobileNavigation() {
    const mobile = window.matchMedia("(max-width: 900px)");
    document.querySelectorAll(".nav").forEach((nav, index) => {
      const links = nav.querySelector(".links");
      if (!links || nav.querySelector(".nav-toggle")) return;

      links.id = links.id || `primary-navigation-${index + 1}`;
      const button = document.createElement("button");
      button.className = "nav-toggle";
      button.type = "button";
      button.setAttribute("aria-controls", links.id);
      button.innerHTML = '<span class="nav-toggle-label">Menu</span><span class="nav-toggle-lines" aria-hidden="true"></span>';
      nav.insertBefore(button, links);
      nav.classList.add("nav-enhanced");

      const setExpanded = (requested, returnFocus = false) => {
        const expanded = mobile.matches ? requested : true;
        links.hidden = mobile.matches && !expanded;
        button.setAttribute("aria-expanded", String(expanded));
        button.setAttribute("aria-label", expanded ? "Close navigation" : "Open navigation");
        if (returnFocus) button.focus();
      };

      button.addEventListener("click", () => {
        setExpanded(button.getAttribute("aria-expanded") !== "true");
      });
      links.addEventListener("click", (event) => {
        if (mobile.matches && event.target.closest("a")) setExpanded(false);
      });
      nav.addEventListener("keydown", (event) => {
        if (event.key !== "Escape" || !mobile.matches || button.getAttribute("aria-expanded") !== "true") return;
        event.preventDefault();
        setExpanded(false, true);
      });

      const synchroniseMode = () => setExpanded(false);
      if (typeof mobile.addEventListener === "function") mobile.addEventListener("change", synchroniseMode);
      else mobile.addListener(synchroniseMode);
      synchroniseMode();
    });
  }

  function setupProgressiveReveal() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const main = document.querySelector("main");
    if (main) {
      Array.from(main.children).forEach((item) => {
        const isRevealSection = item.tagName === "SECTION"
          || item.classList.contains("hero")
          || item.classList.contains("band")
          || item.classList.contains("public-review-path");
        if (isRevealSection && !item.hasAttribute("data-reveal")) {
          item.setAttribute("data-reveal", "");
        }
      });
    }
    const items = Array.from(document.querySelectorAll("[data-reveal]"));
    if (!items.length) return;
    document.documentElement.classList.add("reveal-enabled");
    if (!("IntersectionObserver" in window)) {
      items.forEach((item) => item.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        if (typeof entry.target.animate === "function") {
          entry.target.animate([
            { opacity: 0.72, transform: "translateY(12px)" },
            { opacity: 1, transform: "translateY(0)" }
          ], {
            duration: 520,
            easing: "cubic-bezier(0.2, 0.75, 0.2, 1)"
          });
        }
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8%", threshold: 0.08 });
    items.forEach((item) => observer.observe(item));

    const revealHashTarget = () => {
      const id = decodeURIComponent(window.location.hash.replace(/^#/, ""));
      if (!id) return;
      const target = document.getElementById(id);
      const revealTarget = target && (target.matches("[data-reveal]") ? target : target.closest("[data-reveal]"));
      if (!revealTarget) return;
      revealTarget.classList.add("is-visible");
      observer.unobserve(revealTarget);
    };
    window.addEventListener("hashchange", revealHashTarget);
    window.requestAnimationFrame(revealHashTarget);
  }

  function renderPublicReviewPath() {
    const main = document.querySelector("main");
    if (!main || main.querySelector("[data-public-review-path]")) return;

    const page = document.body.dataset.page || "home";
    if (!["home", "projects", "diligence"].includes(page)) return;
    const stages = [
      {
        id: "core",
        label: "Shared core",
        path: "projects/#core",
        detail: "Source, claim state, human authority and receipt"
      },
      {
        id: "application",
        label: "Application blade",
        path: "projects/#blades",
        detail: "Buyer, mission use case and inherited controls"
      },
      {
        id: "evidence",
        label: "Evidence state",
        path: "diligence/",
        detail: "What exists, what remains open and what is not implied"
      },
      {
        id: "engage",
        label: "Appropriate route",
        path: "contact/",
        detail: "Pilot, sector, research or investor conversation"
      }
    ];
    const stageByPage = {
      about: "core",
      projects: "application",
      research: "evidence",
      publications: "evidence",
      live: "evidence",
      diligence: "evidence",
      community: "evidence",
      updates: "evidence",
      vision: "evidence",
      funding: "engage",
      contact: "engage"
    };
    const currentId = stageByPage[page] || "";
    const currentIndex = stages.findIndex((stage) => stage.id === currentId);
    let nextStage = currentIndex >= 0 && currentIndex < stages.length - 1
      ? stages[currentIndex + 1]
      : stages[0];
    let nextLabel = `Continue to ${nextStage.label}`;
    if (page === "funding") {
        nextStage = { label: "founder conversation", path: "contact/" };
        nextLabel = "Start a conversation";
    } else if (page === "contact") {
      nextLabel = "Restart with the company record";
    }

    const stageMarkup = stages.map((stage, index) => {
      const isCurrent = stage.id === currentId;
      return `
        <li class="public-review-step${isCurrent ? " current" : ""}">
          <a href="${escapeHtml(siteUrl(stage.path))}"${isCurrent ? ' aria-current="step"' : ""}>
            <span class="public-review-number">0${index + 1}</span>
            <strong>${escapeHtml(stage.label)}</strong>
            <span>${escapeHtml(stage.detail)}</span>
          </a>
        </li>`;
    }).join("");

    main.insertAdjacentHTML("beforeend", `
      <section class="public-review-path" aria-labelledby="public-review-path-title" data-public-review-path data-reveal>
        <div class="wrap public-review-path-head">
          <div><div class="eyebrow eyebrow-gold">Public review path</div><h2 id="public-review-path-title">Move from the shared core to a blade, its evidence state and the right route.</h2></div>
          <p><span>One sequence makes breadth legible without turning a submission, discussion or research record into a stronger claim.</span><a class="public-review-key" href="${escapeHtml(siteUrl("diligence/#evidence-language"))}">Read the five claim states <span aria-hidden="true">&rarr;</span></a></p>
        </div>
        <div class="wrap">
          <ol class="public-review-rail">${stageMarkup}</ol>
          <a class="public-review-next" href="${escapeHtml(siteUrl(nextStage.path))}">${escapeHtml(nextLabel)} <span aria-hidden="true">&rarr;</span></a>
        </div>
      </section>`);
  }

  function addCompanySourceLink() {
    const card = Array.from(document.querySelectorAll("#company .card")).find((item) => /Companies House\s+NI696693/i.test(item.textContent || ""));
    if (!card || card.querySelector("[data-company-register-source]")) return;
    card.insertAdjacentHTML("beforeend", '<p><a data-company-register-source href="https://find-and-update.company-information.service.gov.uk/company/NI696693" target="_blank" rel="noopener noreferrer">Open the current Companies House record</a></p>');
  }

  function ensureFundingNavigation() {
    document.querySelectorAll(".links").forEach((links) => {
      if (links.querySelector('[data-nav="funding"]')) return;
      const fundingLink = document.createElement("a");
      fundingLink.href = siteUrl("funding/");
      fundingLink.dataset.nav = "funding";
      fundingLink.textContent = "Funding & partners";
      const contactLink = links.querySelector('[data-nav="contact"]');
      if (contactLink) links.insertBefore(fundingLink, contactLink);
      else links.appendChild(fundingLink);
    });

    document.querySelectorAll(".footer-links").forEach((links) => {
      if (links.querySelector('[data-nav="funding-footer"], [href*="funding/"]')) return;
      const fundingLink = document.createElement("a");
      fundingLink.href = siteUrl("funding/");
      fundingLink.dataset.nav = "funding-footer";
      fundingLink.textContent = "Funding & partners";
      const contactLink = Array.from(links.querySelectorAll("a")).find((link) => /contact/i.test(link.textContent || ""));
      if (contactLink) links.insertBefore(fundingLink, contactLink);
      else links.appendChild(fundingLink);
    });
  }

  function ensureDiligenceNavigation() {
    document.querySelectorAll(".links").forEach((links) => {
      if (links.querySelector('[data-nav="diligence"]')) return;
      const diligenceLink = document.createElement("a");
      diligenceLink.href = siteUrl("diligence/");
      diligenceLink.dataset.nav = "diligence";
      diligenceLink.textContent = "Diligence hub";
      const companyLink = links.querySelector('[data-nav="about"]');
      if (companyLink) links.insertBefore(diligenceLink, companyLink);
      else links.appendChild(diligenceLink);
    });

    document.querySelectorAll(".footer-links").forEach((links) => {
      if (links.querySelector('[data-nav="diligence-footer"], [data-nav="diligence"], [href*="diligence/"]')) return;
      const diligenceLink = document.createElement("a");
      diligenceLink.href = siteUrl("diligence/");
      diligenceLink.dataset.nav = "diligence-footer";
      diligenceLink.textContent = "Diligence hub";
      const contactLink = Array.from(links.querySelectorAll("a")).find((link) => /contact/i.test(link.textContent || ""));
      if (contactLink) links.insertBefore(diligenceLink, contactLink);
      else links.appendChild(diligenceLink);
    });
  }

  function ensureCommunityNavigation() {
    document.querySelectorAll(".footer-links").forEach((links) => {
      if (links.querySelector('[data-nav="community-footer"], [href*="community/"]')) return;
      const communityLink = document.createElement("a");
      communityLink.href = siteUrl("community/");
      communityLink.dataset.nav = "community-footer";
      communityLink.textContent = "Community";
      const contactLink = Array.from(links.querySelectorAll("a")).find((link) => /contact/i.test(link.textContent || ""));
      if (contactLink) links.insertBefore(communityLink, contactLink);
      else links.appendChild(communityLink);
    });
  }

  function ensurePublicEvidenceNavigation() {
    document.querySelectorAll(".footer-links").forEach((links) => {
      if (links.querySelector('[data-nav="live-footer"], [href*="live/"]')) return;
      const liveLink = document.createElement("a");
      liveLink.href = siteUrl("live/");
      liveLink.dataset.nav = "live-footer";
      liveLink.textContent = "Public proof";
      const contactLink = Array.from(links.querySelectorAll("a")).find((link) => /contact/i.test(link.textContent || ""));
      if (contactLink) links.insertBefore(liveLink, contactLink);
      else links.appendChild(liveLink);
    });
  }

  async function initialize() {
    synchronizePrimaryNavigation();
    setupMobileNavigation();
    setActiveNavigation();
    setupHomeControlPath();
    setupPlatformArchitecture();
    setupPublicPacketInspector();
    setupLiveFreshnessConsole();
    setupEngagementRouter();
    setupResearchEvidencePath();
    setupInvestorReviewLens();
    setupDiligenceReviewQueue();
    renderPublicReviewPath();
    setupProgressiveReveal();
    ensurePublicEvidenceNavigation();
    addCompanySourceLink();
    const projectDataNeeded = Boolean(
      document.querySelector("[data-project-table], [data-project-stats], [data-project-graph], [data-project-detail]")
      || document.body.dataset.projectActive === "true"
    );
    if (projectDataNeeded) {
      let projects;
      try {
        projects = await loadJson("data/company-platform.json");
        const currentCompanyProjects = projects.filter((project) => project.active_company_project === true);
        document.querySelectorAll("[data-project-table]").forEach((tableBody) => setupProjectTable(currentCompanyProjects, tableBody));
        renderStats(currentCompanyProjects);
        await renderEcosystem(currentCompanyProjects);
        const slug = document.body.dataset.projectSlug;
        const activeProjectRoute = document.body.dataset.projectActive === "true";
        if (slug && activeProjectRoute) {
          const project = projects.find((item) => item.slug === slug);
          if (project && project.active_company_project === true) renderProjectDetail(project, projects);
          else renderRetiredProjectRoute(document.querySelector("[data-project-detail]"));
        }
      } catch (_error) {
        document.querySelectorAll("[data-project-table], [data-project-stats], [data-project-graph]").forEach((container) => {
          showInlineError(container, "The public platform record is temporarily unavailable. Use the public repository or contact route for source access.");
        });
        if (document.body.dataset.projectActive === "true") {
          showInlineError(document.querySelector("[data-project-detail]"), "The public platform record is temporarily unavailable. Use the public repository or contact route for source access.");
        }
      }
    }

    if (document.querySelector("[data-publications], [data-publications-preview], [data-evidence-library]")) {
      try {
        renderPublications(await loadJson("data/publications.json"));
      } catch (_error) {
        document.querySelectorAll("[data-publications], [data-publications-preview], [data-evidence-records]").forEach((container) => showInlineError(container, "Public records are temporarily unavailable. Do not infer a hidden register; please retry or use the Research and Contact routes."));
      }
    }

    if (document.querySelector("[data-research], [data-research-profiles], [data-research-notes]")) {
      try {
        renderResearch(await loadJson("data/research.json"));
      } catch (_error) {
        document.querySelectorAll("[data-research], [data-research-profiles], [data-research-notes]").forEach((container) => showInlineError(container, "The research index is temporarily unavailable."));
      }
    }

    if (document.querySelector("[data-research-catalogue-recent], [data-research-catalogue-total], [data-research-catalogue-orcid], [data-research-catalogue-zenodo]")) {
      try {
        renderResearchCatalogue(await loadJson("data/research-catalogue.json"));
      } catch (_error) {
        document.querySelectorAll("[data-research-catalogue-recent]").forEach((container) => showInlineError(container, "The ORCID and Zenodo orientation records are temporarily unavailable. Use the direct profile links to inspect the source records."));
      }
    }

    if (document.querySelector("[data-footprint-value], [data-footprint-text]")) {
      try {
        renderPublicFootprint(await loadJson("data/public-attention-snapshot.json"));
      } catch (_error) {
        // The dated, source-labelled HTML values remain visible as a fail-open fallback.
      }
    }

    if (document.querySelector("[data-substack-catalogue]")) {
      try {
        renderSubstackCatalogue(await loadJson("data/substack-research-index.json"));
      } catch (_error) {
        document.querySelectorAll("[data-substack-catalogue]").forEach((container) => showInlineError(container, "The public research-note catalogue is temporarily unavailable."));
      }
    }

    if (document.querySelector("[data-updates]")) {
      try {
        renderUpdates(await loadJson("data/updates.json"));
      } catch (_error) {
        document.querySelectorAll("[data-updates]").forEach((container) => showInlineError(container, "Investor milestones are temporarily unavailable."));
      }
    }
  }

  initialize();
})();
