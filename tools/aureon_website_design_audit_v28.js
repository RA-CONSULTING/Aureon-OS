"use strict";

const crypto = require("crypto");
const childProcess = require("child_process");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const websiteRoot = path.join(repoRoot, "website");
const auditRoot = path.join(repoRoot, "docs", "audits");
const builderPath = path.join(repoRoot, "tools", "build-homepl-v28-narrow-release.ps1");
const baseUrl = "https://aureonzorzatechnologies.pl";
const release = "V29";
const now = new Date();
const stamp = now.toISOString().replace(/[-:]/g, "").replace(/\..+$/, "");
const jsonPath = path.join(auditRoot, `AUREON_WEBSITE_DESIGN_AUDIT_${stamp}_${release}.json`);
const markdownPath = path.join(auditRoot, `AUREON_WEBSITE_DESIGN_AUDIT_${stamp}_${release}.md`);

const primaryRoutes = [
  "index.html",
  "about/index.html",
  "community/index.html",
  "contact/index.html",
  "diligence/index.html",
  "funding/index.html",
  "funding/investor-deck/index.html",
  "live/index.html",
  "projects/index.html",
  "publications/index.html",
  "research/index.html",
  "research/journal/index.html",
  "updates/index.html",
  "vision/index.html"
];

const legacyRedirectRoutes = [
  "downloads/index.html",
  "downloads/validation-metrics-ledger/index.html"
];

const releaseHtmlRoutes = [...primaryRoutes, ...legacyRedirectRoutes];
const expectedReleaseFiles = [
  "index.html",
  "about/index.html",
  "community/index.html",
  "contact/index.html",
  "diligence/index.html",
  "downloads/index.html",
  "downloads/validation-metrics-ledger/index.html",
  "funding/index.html",
  "funding/funding-status.js",
  "funding/investor-deck/index.html",
  "live/index.html",
  "live/live.js",
  "projects/index.html",
  "publications/index.html",
  "research/index.html",
  "research/journal/index.html",
  "updates/index.html",
  "vision/index.html",
  "robots.txt",
  "sitemap.xml",
  "script.js",
  "styles.css",
  "tokens.css",
  "assets/css/aureon-zorza-backgrounds.css",
  "data/blades.json",
  "data/funding-status.json"
].sort();

const requiredClosureFiles = [
  ...expectedReleaseFiles,
  ".htaccess",
  "404.html",
  "accessibility.html",
  "privacy.html",
  "site.webmanifest",
  "data/company-platform.json",
  "data/innovation-map.json",
  "data/operator-evidence.json",
  "data/project-graph.json",
  "data/publications.json",
  "data/research.json",
  "data/research-catalogue.json",
  "data/substack-research-index.json",
  "data/updates.json"
].sort();

function readWebsite(relativePath) {
  return fs.readFileSync(path.join(websiteRoot, relativePath), "utf8");
}

function listFiles(directory = websiteRoot) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(directory, entry.name);
    return entry.isDirectory() ? listFiles(absolute) : (entry.isFile() ? [absolute] : []);
  });
}

function relative(absolutePath) {
  return path.relative(websiteRoot, absolutePath).replace(/\\/g, "/");
}

function stripTags(value) {
  return String(value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function sha256File(absolutePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(absolutePath)).digest("hex").toUpperCase();
}

function parseAttributes(tag) {
  const attributes = {};
  const body = tag.replace(/^<[^\s>]+/, "").replace(/\/?>$/, "");
  for (const match of body.matchAll(/([:\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g)) {
    attributes[match[1].toLowerCase()] = match[2] ?? match[3] ?? match[4] ?? "";
  }
  return attributes;
}

function extractMeta(html, key) {
  const lowerKey = key.toLowerCase();
  for (const match of html.matchAll(/<meta\b[^>]*>/gi)) {
    const attributes = parseAttributes(match[0]);
    if ((attributes.name || attributes.property || "").toLowerCase() === lowerKey) {
      return attributes.content || "";
    }
  }
  return "";
}

function extractLink(html, rel) {
  const lowerRel = rel.toLowerCase();
  for (const match of html.matchAll(/<link\b[^>]*>/gi)) {
    const attributes = parseAttributes(match[0]);
    if ((attributes.rel || "").toLowerCase().split(/\s+/).includes(lowerRel)) return attributes.href || "";
  }
  return "";
}

function extractIds(html) {
  return [...html.matchAll(/\bid=(?:"([^"]+)"|'([^']+)')/gi)].map((match) => match[1] || match[2]);
}

function extractHrefs(html) {
  return [...html.matchAll(/<a\b[^>]*\bhref=(?:"([^"]+)"|'([^']+)')/gi)].map((match) => match[1] || match[2]);
}

function canonicalForRoute(route) {
  if (route === "index.html") return `${baseUrl}/`;
  return `${baseUrl}/${path.posix.dirname(route)}/`;
}

function sameDomainPath(urlValue) {
  try {
    const parsed = new URL(urlValue);
    if (parsed.origin !== baseUrl) return null;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch (_error) {
    return null;
  }
}

function exactCaseExists(absolutePath) {
  if (!fs.existsSync(absolutePath)) return false;
  const relativePath = path.relative(websiteRoot, absolutePath);
  if (!relativePath || relativePath.startsWith("..") || path.isAbsolute(relativePath)) return true;
  let current = websiteRoot;
  for (const segment of relativePath.split(path.sep)) {
    const names = fs.readdirSync(current);
    if (!names.includes(segment)) return false;
    current = path.join(current, segment);
  }
  return true;
}

function resolveLocalTarget(pagePath, reference) {
  if (!reference || /^(?:mailto:|tel:|javascript:|data:|blob:)/i.test(reference)) return null;
  let value = reference;
  if (/^https?:/i.test(value)) {
    value = sameDomainPath(value);
    if (value === null) return null;
  }

  const hashIndex = value.indexOf("#");
  const fragment = hashIndex >= 0 ? value.slice(hashIndex + 1) : "";
  const beforeHash = hashIndex >= 0 ? value.slice(0, hashIndex) : value;
  const pathname = beforeHash.split("?", 1)[0];
  let decodedPathname;
  try {
    decodedPathname = decodeURIComponent(pathname);
  } catch (_error) {
    return { issue: "invalid URL encoding", fragment };
  }

  const pageDirectory = path.dirname(pagePath);
  let target = decodedPathname.startsWith("/")
    ? path.resolve(websiteRoot, decodedPathname.replace(/^\/+/, ""))
    : (decodedPathname ? path.resolve(pageDirectory, decodedPathname) : pagePath);
  if (decodedPathname.endsWith("/") || (fs.existsSync(target) && fs.statSync(target).isDirectory())) {
    target = path.join(target, "index.html");
  }
  return { target, fragment };
}

function extractLocalAssetReferences(html) {
  const references = [];
  for (const match of html.matchAll(/<(?:img|script|source|video|audio|link)\b[^>]*>/gi)) {
    const attributes = parseAttributes(match[0]);
    const tagName = /^<([^\s>]+)/.exec(match[0])?.[1].toLowerCase();
    if (attributes.src) references.push(attributes.src);
    if (attributes.poster) references.push(attributes.poster);
    if (attributes.srcset) {
      for (const candidate of attributes.srcset.split(",")) {
        const candidateUrl = candidate.trim().split(/\s+/, 1)[0];
        if (candidateUrl) references.push(candidateUrl);
      }
    }
    if (
      tagName === "link"
      && attributes.href
      && /\b(?:stylesheet|icon|preload|modulepreload|manifest)\b/i.test(attributes.rel || "")
    ) {
      references.push(attributes.href);
    }
  }
  return references;
}

function sharedAssetUrls(html) {
  return extractLocalAssetReferences(html).filter((value) => /(?:^|\/)(?:styles|tokens|script)\.(?:css|js)(?:[?#]|$)/i.test(value));
}

function versionValue(reference) {
  try {
    return new URL(reference, `${baseUrl}/`).searchParams.get("v") || "";
  } catch (_error) {
    return "";
  }
}

function bytesLabel(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
}

const checks = [];
function check(category, id, passed, detail) {
  checks.push({ category, id, passed: Boolean(passed), detail });
}

const allFiles = listFiles();
const htmlFiles = allFiles.filter((file) => path.extname(file).toLowerCase() === ".html");
const primaryText = Object.fromEntries(primaryRoutes.map((route) => [route, readWebsite(route)]));
const releaseHtmlText = Object.fromEntries(releaseHtmlRoutes.map((route) => [route, readWebsite(route)]));
const homepage = primaryText["index.html"];
const projects = primaryText["projects/index.html"];
const contact = primaryText["contact/index.html"];
const fundingPage = primaryText["funding/index.html"];
const investor = primaryText["funding/investor-deck/index.html"];
const diligence = primaryText["diligence/index.html"];
const liveHtml = primaryText["live/index.html"];
const liveScript = readWebsite("live/live.js");
const script = readWebsite("script.js");
const fundingScript = readWebsite("funding/funding-status.js");
const stylesText = readWebsite("styles.css");
const tokensText = readWebsite("tokens.css");
const styles = `${stylesText}\n${tokensText}`;

const metadataFailures = [];
const metadataRows = [];
const titles = new Map();
for (const route of primaryRoutes) {
  const html = primaryText[route];
  const title = stripTags(html.match(/<title>([\s\S]*?)<\/title>/i)?.[1] || "");
  const description = extractMeta(html, "description");
  const canonical = extractLink(html, "canonical");
  const ogTitle = extractMeta(html, "og:title");
  const ogDescription = extractMeta(html, "og:description");
  const ogUrl = extractMeta(html, "og:url");
  const ogType = extractMeta(html, "og:type");
  const ogImage = extractMeta(html, "og:image");
  const twitterCard = extractMeta(html, "twitter:card");
  const twitterTitle = extractMeta(html, "twitter:title");
  const twitterDescription = extractMeta(html, "twitter:description");
  const twitterImage = extractMeta(html, "twitter:image");
  const expectedCanonical = canonicalForRoute(route);
  const errors = [];

  if (!/<html\b[^>]*\blang="en"/i.test(html)) errors.push("missing html lang=en");
  if (!/<meta\b[^>]*\bcharset="utf-8"/i.test(html)) errors.push("missing UTF-8 charset");
  if (!/name="viewport"[^>]*content="[^"]*width=device-width[^"]*initial-scale=1/i.test(html)) {
    errors.push("missing responsive viewport");
  }
  if (title.length < 20 || title.length > 70) errors.push(`title length ${title.length}`);
  if (description.length < 70 || description.length > 180) errors.push(`description length ${description.length}`);
  if (canonical !== expectedCanonical) errors.push(`canonical ${canonical || "missing"}`);
  if (!ogTitle || !ogDescription || ogType !== "website" || ogUrl !== canonical) errors.push("incomplete or inconsistent Open Graph core");
  if (!/^https:\/\/aureonzorzatechnologies\.pl\//.test(ogImage)) errors.push("Open Graph image is not an absolute first-party HTTPS URL");
  if (twitterCard !== "summary_large_image" || !twitterTitle || !twitterDescription || twitterImage !== ogImage) {
    errors.push("incomplete or inconsistent X/Twitter card");
  }
  const socialPath = sameDomainPath(ogImage);
  if (socialPath) {
    const socialTarget = resolveLocalTarget(path.join(websiteRoot, route), socialPath)?.target;
    if (!socialTarget || !fs.existsSync(socialTarget)) errors.push("social image missing locally");
  }

  const jsonLdBlocks = [...html.matchAll(/<script\b[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi)];
  for (const block of jsonLdBlocks) {
    try {
      JSON.parse(block[1]);
    } catch (error) {
      errors.push(`invalid JSON-LD: ${error.message}`);
    }
  }

  if (titles.has(title)) errors.push(`duplicate title with ${titles.get(title)}`);
  else titles.set(title, route);
  metadataRows.push({ route, title, title_chars: title.length, description_chars: description.length, canonical, og_image: ogImage });
  if (errors.length) metadataFailures.push({ route, errors });
}
check("metadata", "primary_route_metadata", metadataFailures.length === 0, metadataFailures.length ? metadataFailures : metadataRows);

const releaseKeyRows = [];
const releaseKeyFailures = [];
const sharedReleaseKeys = new Set();
for (const route of releaseHtmlRoutes) {
  const html = releaseHtmlText[route];
  const assets = sharedAssetUrls(html);
  const expectedSharedAssets = route.includes("downloads/")
    ? ["styles.css", "tokens.css"]
    : ["styles.css", "tokens.css", "script.js"];
  const byBasename = Object.fromEntries(assets.map((asset) => [asset.split(/[?#]/, 1)[0].split("/").pop(), asset]));
  const routeKeys = [];
  for (const expectedAsset of expectedSharedAssets) {
    const reference = byBasename[expectedAsset];
    if (!reference) {
      releaseKeyFailures.push({ route, issue: `missing ${expectedAsset}` });
      continue;
    }
    const key = versionValue(reference);
    routeKeys.push(key);
    if (!/^evidence-os-20260726-v29-\d+$/.test(key)) {
      releaseKeyFailures.push({ route, asset: reference, issue: `not a final V29 release key: ${key || "missing"}` });
    }
    if (key) sharedReleaseKeys.add(key);
  }
  if (new Set(routeKeys).size > 1) releaseKeyFailures.push({ route, issue: "shared assets use different release keys", routeKeys });

  for (const match of html.matchAll(/<link\b[^>]*href="([^"]*aureon-zorza-backgrounds\.css[^"]*)"/gi)) {
    const backgroundKey = versionValue(match[1]);
    if (!/^ra-owner-20260726-v29-\d+$/.test(backgroundKey)) {
      releaseKeyFailures.push({ route, asset: match[1], issue: "background CSS does not use a final V29 key" });
    }
  }
  releaseKeyRows.push({ route, shared_assets: expectedSharedAssets, keys: [...new Set(routeKeys)] });
}
if (sharedReleaseKeys.size !== 1) {
  releaseKeyFailures.push({ issue: "more than one shared release key is in use", keys: [...sharedReleaseKeys] });
}
check("release", "release_key_consistency", releaseKeyFailures.length === 0, releaseKeyFailures.length ? releaseKeyFailures : releaseKeyRows);

const routeScriptFailures = [];
const finalSharedKey = sharedReleaseKeys.size === 1 ? [...sharedReleaseKeys][0] : "";
for (const route of primaryRoutes) {
  const html = primaryText[route];
  for (const match of html.matchAll(/<script\b[^>]*src="([^"]+)"[^>]*>/gi)) {
    const src = match[1];
    if (/^https?:/i.test(src)) continue;
    const basename = src.split(/[?#]/, 1)[0].split("/").pop();
    if (basename === "script.js") continue;
    const key = versionValue(src);
    if (["funding-status.js", "live.js"].includes(basename) && key !== finalSharedKey) {
      routeScriptFailures.push({ route, src, issue: `route script key differs from shared key ${finalSharedKey || "(mixed)"}` });
    }
  }
}
const fundingDataKey = /data\/funding-status\.json\?v=([^"']+)/.exec(fundingScript)?.[1] || "";
if (fundingDataKey !== finalSharedKey) {
  routeScriptFailures.push({
    file: "funding/funding-status.js",
    issue: `funding data key ${fundingDataKey || "missing"} differs from shared key ${finalSharedKey || "(mixed)"}`
  });
}
check("release", "route_script_cache_keys", routeScriptFailures.length === 0, routeScriptFailures.length ? routeScriptFailures : "Route scripts and funding data use the shared release key.");

const structuralFailures = [];
for (const file of htmlFiles) {
  const html = fs.readFileSync(file, "utf8");
  const ids = extractIds(html);
  const duplicateIds = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
  const h1Count = (html.match(/<h1\b/gi) || []).length;
  const titleCount = (html.match(/<title>[\s\S]*?<\/title>/gi) || []).length;
  const canonicalCount = (html.match(/<link\b[^>]*rel="canonical"/gi) || []).length;
  const missingAlts = [...html.matchAll(/<img\b[^>]*>/gi)].filter((match) => !/\balt=(?:"[^"]*"|'[^']*')/i.test(match[0]));
  const missingButtonTypes = [...html.matchAll(/<button\b[^>]*>/gi)].filter((match) => !/\btype=(?:"[^"]+"|'[^']+')/i.test(match[0]));
  const unsafeBlankTargets = [...html.matchAll(/<a\b[^>]*target="_blank"[^>]*>/gi)].filter((match) => !/\brel=(?:"[^"]*\bnoopener\b[^"]*"|'[^']*\bnoopener\b[^']*')/i.test(match[0]));
  if (
    duplicateIds.length
    || h1Count !== 1
    || titleCount !== 1
    || canonicalCount !== 1
    || missingAlts.length
    || missingButtonTypes.length
    || unsafeBlankTargets.length
  ) {
    structuralFailures.push({
      page: relative(file),
      duplicateIds,
      h1Count,
      titleCount,
      canonicalCount,
      missingAltCount: missingAlts.length,
      missingButtonTypeCount: missingButtonTypes.length,
      unsafeBlankTargetCount: unsafeBlankTargets.length
    });
  }
}
check("html", "whole_site_structure", structuralFailures.length === 0, structuralFailures.length ? structuralFailures : `${htmlFiles.length} HTML files checked`);

const accessibilityFailures = [];
for (const route of primaryRoutes) {
  const html = primaryText[route];
  const ids = new Set(extractIds(html));
  const routeFailures = [];
  if (!/<a\b[^>]*class="[^"]*\bskip-link\b[^"]*"[^>]*href="#main-content"/i.test(html)) routeFailures.push("skip link missing");
  if (!/<main\b[^>]*id="main-content"/i.test(html)) routeFailures.push("main-content landmark missing");
  for (const match of html.matchAll(/\baria-controls="([^"]+)"/gi)) {
    if (!ids.has(match[1])) routeFailures.push(`aria-controls target missing: ${match[1]}`);
  }
  const tabs = (html.match(/\brole="tab"/gi) || []).length;
  const panels = (html.match(/\brole="tabpanel"/gi) || []).length;
  const tablists = (html.match(/\brole="tablist"/gi) || []).length;
  if ((tabs || panels || tablists) && (!tablists || tabs !== panels)) {
    routeFailures.push(`tab structure mismatch: ${tablists} tablist, ${tabs} tabs, ${panels} panels`);
  }
  if (routeFailures.length) accessibilityFailures.push({ route, issues: routeFailures });
}
const keyboardMarkers = [
  'event.key === "ArrowRight"',
  'event.key === "ArrowLeft"',
  'event.key === "Home"',
  'event.key === "End"',
  'event.key !== "Escape"',
  'setAttribute("aria-selected"',
  ".focus()"
];
if (!keyboardMarkers.every((marker) => script.includes(marker))) {
  accessibilityFailures.push({ file: "script.js", issue: "shared interactive modules do not expose the complete keyboard marker set" });
}
if (!/:focus-visible/.test(styles)) {
  accessibilityFailures.push({ file: "styles.css/tokens.css", issue: "focus-visible treatment missing" });
}
check("accessibility", "keyboard_and_landmark_basics", accessibilityFailures.length === 0, accessibilityFailures.length ? accessibilityFailures : `${primaryRoutes.length} routes plus shared interactions checked`);

const localReferenceFailures = [];
for (const file of htmlFiles) {
  const html = fs.readFileSync(file, "utf8");
  const references = [
    ...extractHrefs(html).map((value) => ({ kind: "link", value })),
    ...extractLocalAssetReferences(html).map((value) => ({ kind: "asset", value }))
  ];
  for (const reference of references) {
    const resolved = resolveLocalTarget(file, reference.value);
    if (!resolved) continue;
    if (resolved.issue) {
      localReferenceFailures.push({ page: relative(file), reference: reference.value, kind: reference.kind, issue: resolved.issue });
      continue;
    }
    if (!resolved.target.startsWith(websiteRoot)) {
      localReferenceFailures.push({ page: relative(file), reference: reference.value, kind: reference.kind, issue: "outside website root" });
      continue;
    }
    if (!fs.existsSync(resolved.target)) {
      localReferenceFailures.push({ page: relative(file), reference: reference.value, kind: reference.kind, issue: "target missing" });
      continue;
    }
    if (!exactCaseExists(resolved.target)) {
      localReferenceFailures.push({ page: relative(file), reference: reference.value, kind: reference.kind, issue: "path case differs from disk" });
    }
    if (reference.kind === "link" && resolved.fragment && path.extname(resolved.target).toLowerCase() === ".html") {
      const targetHtml = fs.readFileSync(resolved.target, "utf8");
      let decodedFragment = resolved.fragment;
      try {
        decodedFragment = decodeURIComponent(resolved.fragment);
      } catch (_error) {
        localReferenceFailures.push({ page: relative(file), reference: reference.value, kind: reference.kind, issue: "invalid fragment encoding" });
        continue;
      }
      if (!new Set(extractIds(targetHtml)).has(decodedFragment)) {
        localReferenceFailures.push({ page: relative(file), reference: reference.value, kind: reference.kind, issue: "fragment missing" });
      }
    }
  }
}

for (const cssFile of allFiles.filter((file) => path.extname(file).toLowerCase() === ".css")) {
  const css = fs.readFileSync(cssFile, "utf8");
  for (const match of css.matchAll(/url\((?:"([^"]+)"|'([^']+)'|([^)]+))\)/gi)) {
    const value = (match[1] || match[2] || match[3] || "").trim();
    const resolved = resolveLocalTarget(cssFile, value);
    if (!resolved || resolved.issue) continue;
    if (!fs.existsSync(resolved.target)) {
      localReferenceFailures.push({ page: relative(cssFile), reference: value, kind: "css asset", issue: "target missing" });
    } else if (!exactCaseExists(resolved.target)) {
      localReferenceFailures.push({ page: relative(cssFile), reference: value, kind: "css asset", issue: "path case differs from disk" });
    }
  }
}
check("links", "whole_site_local_references", localReferenceFailures.length === 0, localReferenceFailures.length ? localReferenceFailures : `${htmlFiles.length} HTML files and all CSS files checked`);

const jsonFiles = allFiles.filter((file) => relative(file).startsWith("data/") && path.extname(file).toLowerCase() === ".json");
const jsonFailures = [];
const parsedJson = {};
for (const file of jsonFiles) {
  try {
    parsedJson[relative(file)] = JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
  } catch (error) {
    jsonFailures.push({ file: relative(file), error: error.message });
  }
}
check("data", "public_json_validity", jsonFailures.length === 0, jsonFailures.length ? jsonFailures : `${jsonFiles.length} JSON files parsed`);

const blades = parsedJson["data/blades.json"];
const requiredBladeFields = [
  "id",
  "lane",
  "name",
  "buyer",
  "problem_or_use_case",
  "shared_core",
  "public_evidence_basis",
  "strategic_relevance",
  "next_validation",
  "public_boundary",
  "source_links"
];
const bladeContractFailures = [];
if (!blades || !Array.isArray(blades.lanes) || !Array.isArray(blades.blades)) {
  bladeContractFailures.push("lanes or blades array missing");
} else {
  if (blades.lanes.length !== 3) bladeContractFailures.push(`expected 3 lanes, found ${blades.lanes.length}`);
  if (blades.blades.length !== 11) bladeContractFailures.push(`expected 11 blades, found ${blades.blades.length}`);
  const laneIds = new Set(blades.lanes.map((lane) => lane.id));
  const bladeIds = new Set();
  for (const blade of blades.blades) {
    if (bladeIds.has(blade.id)) bladeContractFailures.push(`duplicate blade id ${blade.id}`);
    bladeIds.add(blade.id);
    if (!laneIds.has(blade.lane)) bladeContractFailures.push(`${blade.id} references unknown lane ${blade.lane}`);
    const missing = requiredBladeFields.filter((field) => {
      const value = blade[field];
      return value === undefined || value === null || value === "" || (Array.isArray(value) && value.length === 0);
    });
    if (missing.length) bladeContractFailures.push(`${blade.id} missing ${missing.join(", ")}`);
    for (const legacyField of ["decision_or_use_case", "current_evidence_state", "controlled_evidence", "grant_or_provider_evidence", "partner_evidence", "next_proof"]) {
      if (Object.hasOwn(blade, legacyField)) bladeContractFailures.push(`${blade.id} exposes legacy field ${legacyField}`);
    }
  }
}
check("data", "blade_data_contract", bladeContractFailures.length === 0, bladeContractFailures.length ? bladeContractFailures : { lane_count: blades?.lanes?.length, blade_count: blades?.blades?.length });

const innovationMap = parsedJson["data/innovation-map.json"];
const innovationMapFailures = [];
const innovationPathRequiredFields = [
  "id",
  "title",
  "research_question",
  "hnc_method",
  "formal_records",
  "public_explanations",
  "aureon_os_capability",
  "application_blades",
  "next_validation",
  "public_boundary"
];
if (!innovationMap || !innovationMap.positioning || !innovationMap.artifact_roles || !Array.isArray(innovationMap.paths)) {
  innovationMapFailures.push("positioning, artifact_roles or paths missing");
} else {
  if (innovationMap.paths.length < 3) innovationMapFailures.push(`expected at least 3 research-to-application paths, found ${innovationMap.paths.length}`);
  const knownBladeIds = new Set(Array.isArray(blades?.blades) ? blades.blades.map((blade) => blade.id) : []);
  const innovationPathIds = new Set();
  for (const pathRecord of innovationMap.paths) {
    if (innovationPathIds.has(pathRecord.id)) innovationMapFailures.push(`duplicate innovation path id ${pathRecord.id}`);
    innovationPathIds.add(pathRecord.id);
    const missing = innovationPathRequiredFields.filter((field) => {
      const value = pathRecord[field];
      return value === undefined || value === null || value === "" || (Array.isArray(value) && value.length === 0);
    });
    if (missing.length) innovationMapFailures.push(`${pathRecord.id || "unnamed path"} missing ${missing.join(", ")}`);
    for (const bladeId of Array.isArray(pathRecord.application_blades) ? pathRecord.application_blades : []) {
      if (!knownBladeIds.has(bladeId)) innovationMapFailures.push(`${pathRecord.id} references unknown blade ${bladeId}`);
    }
    for (const record of Array.isArray(pathRecord.formal_records) ? pathRecord.formal_records : []) {
      if (!record.id || !record.label || !record.url || record.artifact_role !== "formal_record" || !record.evidence_state) {
        innovationMapFailures.push(`${pathRecord.id} has an incomplete formal record`);
      }
    }
    for (const explanation of Array.isArray(pathRecord.public_explanations) ? pathRecord.public_explanations : []) {
      if (!explanation.label || !explanation.url || explanation.artifact_role !== "public_explanation" || !explanation.evidence_state) {
        innovationMapFailures.push(`${pathRecord.id} has an incomplete public explanation`);
      }
    }
  }
}
check(
  "data",
  "innovation_map_contract",
  innovationMapFailures.length === 0,
  innovationMapFailures.length ? innovationMapFailures : {
    path_count: innovationMap?.paths?.length,
    artifact_roles: Object.keys(innovationMap?.artifact_roles || {})
  }
);

const ethosFailures = [];
if (!homepage.includes("Evidence infrastructure for decisions that cannot afford ambiguity.")) ethosFailures.push("homepage thesis missing");
if (!projects.includes("One research engine. One evidence operating system. Many high-consequence applications.")) {
  ethosFailures.push("applications page does not restate the shared-core, bounded-blade portfolio thesis");
}
if (!homepage.includes("The public research makes the method inspectable; independent review remains open.")) {
  ethosFailures.push("research is not bounded as inspectable with independent review open");
}
const publicDisclosureText = [
  homepage,
  projects,
  fundingPage,
  investor,
  diligence,
  JSON.stringify(blades || {}),
  JSON.stringify(parsedJson["data/funding-status.json"] || {})
].join("\n");
for (const requiredBoundary of [
  "Supporting diligence is shared only in a qualified, scoped review.",
  "Decision-relevant supporting material remains available through qualified diligence."
]) {
  if (!publicDisclosureText.includes(requiredBoundary)) {
    ethosFailures.push(`public disclosure boundary missing: ${requiredBoundary}`);
  }
}
const forbiddenPublicDisclosurePatterns = [
  /\b0261-[0-9-]+\b/i,
  /\b1020[0-9]{4}\b/i,
  /\bACC[0-9]{6,}\b/i,
  /\bAUREON_CONTINUOUS_FUNDING_MONITOR\b/i,
  /\/public_html\b/i,
  /\b(?:Gmail|Calendly|WebFTP)\b/i,
  /\b(?:AureonLocalAdapter|qwen2\.5)\b/i,
  /\/(?:healthz|readyz)\b/i,
  /(?:£|€)\s*\d/i,
  /\b(?:five submitted applications|two route-fit discussions|direct-submit-ready|safe portal actions)\b/i,
  /\b(?:valuation|runway|fundraising target|raise target|annual recurring revenue|ARR|committed capital)\b/i,
  /\binternal (?:company |operating )?records?\b/i,
  /\bapplication values?\b/i,
  /\bgrant (?:reference|application|value)\b/i,
  /\bportal records?\b/i,
  /\bfinancing (?:requirements?|assumptions?|forecasts?)\b/i,
  /\bcurrent revenue\b/i,
  /\b(?:provider|submission) receipt\b/i,
  /\brecord path\s*\/\s*v\d+\b/i,
  /\b(?:operator|deployment|hosting|correspondence) (?:record|receipt|reference|run|log|account|quota|figure|value|status)\b/i,
  /\b(?:application|grant|provider|correspondence|operator|deployment|hosting)_(?:id|number|reference|receipt|record|run|log|account|quota)\b/i
];
for (const pattern of forbiddenPublicDisclosurePatterns) {
  const match = publicDisclosureText.match(pattern);
  if (match) ethosFailures.push({ issue: "internal company record disclosed in public route", match: match[0], pattern: String(pattern) });
}
const releaseVisibleText = releaseHtmlRoutes.map((route) => stripTags(releaseHtmlText[route])).join("\n");
const forbiddenVisibleLegacyPatterns = [
  /\bCompany-recorded\b/i,
  /\bProvider-confirmed\b/i,
  /\bprivate route records?\b/i,
  /\bFinancing requirements\b/i
];
for (const pattern of forbiddenVisibleLegacyPatterns) {
  const match = releaseVisibleText.match(pattern);
  if (match) ethosFailures.push({ issue: "legacy public-policy framing remains visible on a release page", match: match[0], pattern: String(pattern) });
}
if (!projects.includes("PULSE-CAL is the formal electro-optical materials and technology (EOMT) identity. It is not flight hardware, a mission-endorsed instrument or independently validated.")) {
  ethosFailures.push("PULSE-CAL public research boundary is missing");
}
if (!projects.includes("These are market theses, not claims of customer adoption, partnership, deployment or validated performance. Each must earn its own design partner and measured outcome.")) {
  ethosFailures.push("sector theses lack the public non-relationship boundary");
}
const requiredInvestorStrategySignals = [
  "Investment thesis",
  "These are public-attention and technical-access signals, not customers, production use, scientific validation or independent adoption.",
  "Every blade must justify its own buyer, evidence burden and commercial milestone before it earns further scale.",
  "What will Aureon prove next?",
  "This is a public architecture description. Each implementation still requires scoped validation for its intended use.",
  "Start an investor conversation"
];
const missingInvestorStrategySignals = requiredInvestorStrategySignals.filter((signal) => !investor.includes(signal));
if (missingInvestorStrategySignals.length) {
  ethosFailures.push({
    issue: "investor brief is missing current thesis or validation-boundary signals",
    missing: missingInvestorStrategySignals
  });
}
const toySignalText = `${liveHtml}\n${liveScript}\n${stylesText}`;
const toySignalHits = [...new Set(
  [...toySignalText.matchAll(/\b(?:public-pulse|open-meteo|weather|earthquake|USGS)\b/gi)].map((match) => match[0])
)];
if (toySignalHits.length) ethosFailures.push({ issue: "toy-like public pulse residue remains", hits: toySignalHits });
const primaryPublicText = primaryRoutes.map((route) => stripTags(primaryText[route])).join("\n");
const unsupportedHype = [...primaryPublicText.matchAll(/\b(?:Fortune 500|world[- ]class|market[- ]leading|industry[- ]leading|guaranteed returns|certified compliant|production-ready)\b/gi)].map((match) => match[0]);
if (unsupportedHype.length) ethosFailures.push({ issue: "unsupported promotional claim language", hits: [...new Set(unsupportedHype)] });
check("ethos", "evidence_led_company_ethos", ethosFailures.length === 0, ethosFailures.length ? ethosFailures : "Shared core, public research, sector theses and investor claims retain explicit boundaries while internal company records remain controlled.");

const expectedNav = ["Core", "Applications", "Research", "Evidence", "Company", "Investor brief"];
check(
  "information_architecture",
  "decision_oriented_navigation",
  expectedNav.every((label) => script.includes(`"${label}"`))
    && /projects\/#core/.test(script)
    && /projects\/#blades/.test(script)
    && /funding\/investor-deck\//.test(script),
  expectedNav
);

check(
  "information_architecture",
  "contact_route_architecture",
  contact.includes("Start an investor conversation")
    && contact.includes("mailto:gary@aureonzorzatechnologies.com")
    && contact.includes("Four details are enough to start well.")
    && ["Who:", "Thesis:", "Question:", "Next step:"].every((detail) => contact.includes(detail)),
  "The investor-first CTA, direct company-domain founder email and four-detail first-note structure are explicit."
);

const motionFailures = [];
if (!/@media\s*\(prefers-reduced-motion:\s*reduce\)/.test(stylesText)) motionFailures.push("styles.css reduced-motion media query missing");
if (!/@media\s*\(prefers-reduced-motion:\s*reduce\)/.test(tokensText)) motionFailures.push("tokens.css reduced-motion media query missing");
if (!/matchMedia\("\(prefers-reduced-motion: reduce\)"\)\.matches/.test(script)) motionFailures.push("progressive reveal does not short-circuit for reduced motion");
if (!/animation-duration:\s*0\.01ms\s*!important/.test(styles)) motionFailures.push("global reduced animation duration missing");
if (/<marquee\b/i.test(primaryPublicText) || /\bautoplay\b/i.test(primaryRoutes.map((route) => primaryText[route]).join("\n"))) {
  motionFailures.push("marquee or autoplay behavior found");
}
const slowTransitions = [];
for (const [file, css] of [["styles.css", stylesText], ["tokens.css", tokensText]]) {
  css.split(/\r?\n/).forEach((line, index) => {
    if (!/\btransition(?:-duration)?:/i.test(line)) return;
    for (const match of line.matchAll(/(\d+)ms/g)) {
      if (Number(match[1]) > 500) slowTransitions.push({ file, line: index + 1, duration_ms: Number(match[1]) });
    }
  });
}
if (slowTransitions.length) motionFailures.push({ issue: "transition exceeds 500ms", matches: slowTransitions });
check("motion", "purposeful_motion_and_reduced_motion", motionFailures.length === 0, motionFailures.length ? motionFailures : "Motion is bounded, keyboard-independent and reduced-motion aware.");

const responsiveFailures = [];
for (const breakpoint of ["900px", "840px", "680px"]) {
  if (!styles.includes(`max-width: ${breakpoint}`)) responsiveFailures.push(`missing ${breakpoint} responsive breakpoint`);
}
if (!/\bminmax\(0,\s*1fr\)/.test(styles)) responsiveFailures.push("defensive minmax grid sizing missing");
if (!/\boverflow-wrap:\s*(?:anywhere|break-word)/.test(styles)) responsiveFailures.push("long-token overflow protection missing");
check("responsive", "responsive_layout_contract", responsiveFailures.length === 0, responsiveFailures.length ? responsiveFailures : "Desktop, tablet, mobile and long-token containment rules found.");

const sitemap = readWebsite("sitemap.xml");
const robots = readWebsite("robots.txt");
const sitemapUrls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1]);
const expectedSitemapUrls = primaryRoutes.map(canonicalForRoute);
const sitemapFailures = expectedSitemapUrls.filter((url) => !sitemapUrls.includes(url)).map((url) => ({ missing: url }));
const duplicateSitemapUrls = [...new Set(sitemapUrls.filter((url, index) => sitemapUrls.indexOf(url) !== index))];
if (duplicateSitemapUrls.length) sitemapFailures.push({ duplicate_urls: duplicateSitemapUrls });
if (!/Sitemap:\s*https:\/\/aureonzorzatechnologies\.pl\/sitemap\.xml/i.test(robots)) sitemapFailures.push({ issue: "robots.txt sitemap declaration missing" });
check("metadata", "sitemap_and_robots", sitemapFailures.length === 0, sitemapFailures.length ? sitemapFailures : `${expectedSitemapUrls.length} primary canonical URLs found`);

const builderText = fs.readFileSync(builderPath, "utf8");
const releaseBlock = /\$releaseFiles\s*=\s*@\(([\s\S]*?)\r?\n\)/.exec(builderText)?.[1] || "";
const builderFiles = [...releaseBlock.matchAll(/'([^']+)'/g)].map((match) => match[1].replace(/\\/g, "/")).sort();
const builderMissing = expectedReleaseFiles.filter((file) => !builderFiles.includes(file));
const builderUnexpected = builderFiles.filter((file) => !expectedReleaseFiles.includes(file));
const builderDuplicates = [...new Set(builderFiles.filter((file, index) => builderFiles.indexOf(file) !== index))];
const builderFailures = [];
if (builderMissing.length) builderFailures.push({ missing: builderMissing });
if (builderUnexpected.length) builderFailures.push({ unexpected: builderUnexpected });
if (builderDuplicates.length) builderFailures.push({ duplicates: builderDuplicates });
for (const file of builderFiles) {
  if (!fs.existsSync(path.join(websiteRoot, file))) builderFailures.push({ missing_on_disk: file });
}
const requiredBuilderMarkers = [
  "[switch]$VerifyOnly",
  "release-plan-verified",
  "Refusing to overwrite existing release target",
  "Release path escapes the website root",
  "ZIP SHA-256 mismatch",
  "package_validation",
  "deployment_state = 'audited-release-prepared-not-uploaded'",
  "package_root = '/'",
  "remote_root = 'action-time-confirmation-required'"
];
const missingBuilderMarkers = requiredBuilderMarkers.filter((marker) => !builderText.includes(marker));
if (missingBuilderMarkers.length) builderFailures.push({ missing_safety_markers: missingBuilderMarkers });
check("release", "package_allowlist_and_verifier", builderFailures.length === 0, builderFailures.length ? builderFailures : { file_count: builderFiles.length, files: builderFiles });

let verifiedReleasePlan = null;
let verifiedReleasePlanError = "";
try {
  const output = childProcess.execFileSync(
    "powershell.exe",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", builderPath, "-Release", release, "-VerifyOnly"],
    { cwd: repoRoot, encoding: "utf8", windowsHide: true, maxBuffer: 32 * 1024 * 1024 }
  );
  verifiedReleasePlan = JSON.parse(output.replace(/^\uFEFF/, ""));
} catch (error) {
  verifiedReleasePlanError = String(error.stderr || error.stdout || error.message || error);
}

const verifiedFiles = Array.isArray(verifiedReleasePlan?.Files)
  ? verifiedReleasePlan.Files.map((item) => ({
      path: String(item.Path || "").replace(/\\/g, "/"),
      bytes: Number(item.Bytes || 0),
      sha256: String(item.Sha256 || "").toUpperCase()
    })).sort((left, right) => left.path.localeCompare(right.path))
  : [];
const verifiedFilePaths = new Set(verifiedFiles.map((item) => item.path));
const closure = verifiedReleasePlan?.Closure || {};
const closureFailures = [];
if (verifiedReleasePlanError) closureFailures.push({ verify_only_error: verifiedReleasePlanError });
if (verifiedReleasePlan?.State !== "release-plan-verified") closureFailures.push({ state: verifiedReleasePlan?.State || "missing" });
for (const file of requiredClosureFiles) {
  if (!verifiedFilePaths.has(file)) closureFailures.push({ required_dependency_missing: file });
}
if (Number(closure.missing_local_reference_count ?? -1) !== 0) {
  closureFailures.push({ missing_local_reference_count: closure.missing_local_reference_count ?? "missing" });
}
if (Number(closure.local_reference_count ?? -1) !== Number(closure.included_local_reference_count ?? -2)) {
  closureFailures.push({
    local_reference_count: closure.local_reference_count ?? "missing",
    included_local_reference_count: closure.included_local_reference_count ?? "missing"
  });
}
if (Number(closure.missing_fragment_reference_count ?? -1) !== 0) {
  closureFailures.push({ missing_fragment_reference_count: closure.missing_fragment_reference_count ?? "missing" });
}
if (Number(closure.fragment_reference_count ?? -1) !== Number(closure.verified_fragment_reference_count ?? -2)) {
  closureFailures.push({
    fragment_reference_count: closure.fragment_reference_count ?? "missing",
    verified_fragment_reference_count: closure.verified_fragment_reference_count ?? "missing"
  });
}
if (verifiedFiles.length !== Number(verifiedReleasePlan?.FileCount || 0)) {
  closureFailures.push({ plan_file_count: verifiedReleasePlan?.FileCount || 0, manifest_file_count: verifiedFiles.length });
}
for (const item of verifiedFiles) {
  const absolute = path.join(websiteRoot, item.path);
  if (!fs.existsSync(absolute)) {
    closureFailures.push({ missing_on_disk: item.path });
    continue;
  }
  const stat = fs.statSync(absolute);
  if (!stat.isFile() || stat.size !== item.bytes) closureFailures.push({ byte_mismatch: item.path });
  if (sha256File(absolute) !== item.sha256) closureFailures.push({ sha256_mismatch: item.path });
}
check(
  "release",
  "package_dependency_closure",
  closureFailures.length === 0,
  closureFailures.length
    ? closureFailures
    : {
        state: closure.state,
        entry_file_count: closure.entry_file_count,
        discovered_file_count: closure.discovered_file_count,
        local_reference_count: closure.local_reference_count,
        included_local_reference_count: closure.included_local_reference_count,
        missing_local_reference_count: closure.missing_local_reference_count,
        fragment_reference_count: closure.fragment_reference_count,
        verified_fragment_reference_count: closure.verified_fragment_reference_count,
        missing_fragment_reference_count: closure.missing_fragment_reference_count,
        remote_reference_count: closure.remote_reference_count,
        non_file_reference_count: closure.non_file_reference_count,
        remote_origins: closure.remote_origins,
        file_count: verifiedFiles.length
      }
);

const releaseManifest = verifiedFiles;
const releaseBytes = releaseManifest.reduce((sum, item) => sum + item.bytes, 0);
check(
  "release",
  "package_manifest_readback",
  releaseManifest.length === Number(verifiedReleasePlan?.FileCount || 0)
    && releaseManifest.length > 0
    && releaseManifest.every((item) => item.bytes > 0 && /^[A-F0-9]{64}$/.test(item.sha256)),
  { file_count: releaseManifest.length, total_bytes: releaseBytes, total_size: bytesLabel(releaseBytes), files: releaseManifest }
);

const syntaxFailures = [];
for (const file of ["script.js", "funding/funding-status.js", "live/live.js"]) {
  try {
    new Function(readWebsite(file));
  } catch (error) {
    syntaxFailures.push({ file, error: error.message });
  }
}
check("assets", "javascript_syntax", syntaxFailures.length === 0, syntaxFailures.length ? syntaxFailures : "Shared, funding and live scripts parse.");

const secretPatterns = [
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  /\bsk-[A-Za-z0-9_-]{20,}\b/,
  /\bAIza[0-9A-Za-z_-]{20,}\b/,
  /\b(?:password|passwd)\s*[:=]\s*["'][^"']{8,}["']/i
];
const secretHits = [];
for (const file of [
  ...htmlFiles,
  ...releaseManifest
    .map((item) => item.path)
    .filter((file) => /\.(?:js|json|xml|txt|webmanifest)$/i.test(file))
    .map((file) => path.join(websiteRoot, file))
]) {
  const text = fs.readFileSync(file, "utf8");
  if (secretPatterns.some((pattern) => pattern.test(text))) secretHits.push(relative(file));
}
check("security", "no_public_secret_patterns", secretHits.length === 0, [...new Set(secretHits)]);

const websiteBytes = allFiles.reduce((sum, file) => sum + fs.statSync(file).size, 0);
const byExtension = {};
for (const file of allFiles) {
  const extension = path.extname(file).toLowerCase() || "[no extension]";
  const size = fs.statSync(file).size;
  if (!byExtension[extension]) byExtension[extension] = { files: 0, bytes: 0 };
  byExtension[extension].files += 1;
  byExtension[extension].bytes += size;
}
const largestFiles = allFiles
  .map((file) => ({ path: relative(file), bytes: fs.statSync(file).size }))
  .sort((a, b) => b.bytes - a.bytes)
  .slice(0, 15)
  .map((item) => ({ ...item, size: bytesLabel(item.bytes) }));
const storageInventory = {
  scope: "local website tree only; provider quota and free space require authenticated Home.pl read-back",
  website_file_count: allFiles.length,
  website_bytes: websiteBytes,
  website_size: bytesLabel(websiteBytes),
  planned_release_file_count: releaseManifest.length,
  planned_release_bytes: releaseBytes,
  planned_release_size: bytesLabel(releaseBytes),
  by_extension: Object.fromEntries(Object.entries(byExtension).sort((a, b) => b[1].bytes - a[1].bytes)),
  largest_files: largestFiles
};
check("storage", "local_storage_inventory", true, storageInventory);

const passed = checks.filter((item) => item.passed).length;
const failed = checks.length - passed;
const report = {
  status: failed === 0 ? "PASS" : "FAIL",
  release,
  generated_at: now.toISOString(),
  website_root: websiteRoot,
  scope: {
    primary_routes: primaryRoutes,
    legacy_redirect_routes: legacyRedirectRoutes,
    all_html_files_checked: htmlFiles.length,
    all_json_files_checked: jsonFiles.length
  },
  storage: storageInventory,
  package_manifest: releaseManifest,
  checks: { total: checks.length, passed, failed },
  results: checks
};

fs.mkdirSync(auditRoot, { recursive: true });
fs.writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

const groupedChecks = [...new Set(checks.map((item) => item.category))].flatMap((category) => [
  `### ${category[0].toUpperCase()}${category.slice(1)}`,
  "",
  ...checks
    .filter((item) => item.category === category)
    .map((item) => `- ${item.passed ? "PASS" : "FAIL"} — \`${item.id}\`: ${stripTags(typeof item.detail === "string" ? item.detail : JSON.stringify(item.detail))}`),
  ""
]);
const markdown = [
  `# Aureon Website Design Audit ${release}`,
  "",
  `- Generated: ${report.generated_at}`,
  `- Status: **${report.status}**`,
  `- Checks: ${passed}/${checks.length} passed`,
  `- Primary routes: ${primaryRoutes.length}`,
  `- Whole-site HTML: ${htmlFiles.length} files`,
  `- Local website footprint: ${storageInventory.website_size} across ${storageInventory.website_file_count} files`,
  `- Planned narrow release: ${storageInventory.planned_release_size} across ${storageInventory.planned_release_file_count} files`,
  "- Hosting quota: not inferred from local files; requires authenticated Home.pl read-back",
  "",
  "## Results",
  "",
  ...groupedChecks,
  "## Release thesis",
  "",
  "One accountable evidence-and-control core is presented through three bounded portfolio lanes: scoped commercial evaluation, sector routes under review and gated deep-tech options. Each blade carries a buyer, evidence state, public boundary and next proof.",
  ""
].join("\n");
fs.writeFileSync(markdownPath, markdown, "utf8");

console.log(JSON.stringify({
  status: report.status,
  checks: report.checks,
  primaryRoutes: primaryRoutes.length,
  htmlFiles: htmlFiles.length,
  storage: storageInventory,
  jsonPath,
  markdownPath,
  failures: checks.filter((item) => !item.passed)
}, null, 2));

if (failed > 0) process.exitCode = 1;
