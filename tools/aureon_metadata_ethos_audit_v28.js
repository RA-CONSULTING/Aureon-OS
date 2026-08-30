#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const REPO_ROOT = path.resolve(__dirname, "..");
const SITE_ROOT = path.join(REPO_ROOT, "website");
const REPORT_ROOT = path.join(REPO_ROOT, "docs", "audits");
const SITE_ORIGIN = "https://aureonzorzatechnologies.pl";
const REPORT_JSON = path.join(REPORT_ROOT, "AUREON_METADATA_ETHOS_AUDIT_V28.json");
const REPORT_MD = path.join(REPORT_ROOT, "AUREON_METADATA_ETHOS_AUDIT_V28.md");

function walkHtml(directory) {
  const output = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) output.push(...walkHtml(absolute));
    if (entry.isFile() && entry.name.toLowerCase().endsWith(".html")) output.push(absolute);
  }
  return output;
}

function decodeHtml(value) {
  return String(value || "")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, "\"")
    .replace(/&apos;|&#39;|&#x27;/gi, "'")
    .replace(/&nbsp;/gi, " ")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">");
}

function parseAttributes(tag) {
  const attributes = {};
  const pattern = /([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g;
  let match;
  while ((match = pattern.exec(tag))) {
    attributes[match[1].toLowerCase()] = decodeHtml(match[2] ?? match[3] ?? match[4] ?? "");
  }
  return attributes;
}

function tags(raw, tagName) {
  const pattern = new RegExp(`<${tagName}\\b[^>]*>`, "gi");
  return [...raw.matchAll(pattern)].map((match) => ({
    raw: match[0],
    attributes: parseAttributes(match[0]),
  }));
}

function metas(raw) {
  return tags(raw, "meta");
}

function links(raw) {
  return tags(raw, "link");
}

function scripts(raw) {
  const pattern = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  return [...raw.matchAll(pattern)].map((match) => ({
    attributes: parseAttributes(`<script ${match[1]}>`),
    body: match[2].trim(),
  }));
}

function metaValue(metaTags, key, value) {
  const lowerValue = value.toLowerCase();
  return metaTags.find((tag) => (tag.attributes[key] || "").toLowerCase() === lowerValue)?.attributes.content || "";
}

function linkValues(linkTags, relation) {
  const lowerRelation = relation.toLowerCase();
  return linkTags
    .filter((tag) => (tag.attributes.rel || "").toLowerCase().split(/\s+/).includes(lowerRelation))
    .map((tag) => tag.attributes.href || "");
}

function jsonLd(raw) {
  const blocks = [];
  for (const script of scripts(raw).filter((item) => (item.attributes.type || "").toLowerCase() === "application/ld+json")) {
    try {
      blocks.push({ valid: true, value: JSON.parse(script.body), error: null });
    } catch (error) {
      blocks.push({ valid: false, value: null, error: error.message });
    }
  }
  return blocks;
}

function collectSchemaTypes(value, output = new Set()) {
  if (Array.isArray(value)) {
    for (const item of value) collectSchemaTypes(item, output);
    return output;
  }
  if (!value || typeof value !== "object") return output;
  const current = value["@type"];
  if (Array.isArray(current)) current.forEach((item) => output.add(String(item)));
  else if (current) output.add(String(current));
  for (const child of Object.values(value)) collectSchemaTypes(child, output);
  return output;
}

function stripMarkup(raw) {
  return decodeHtml(
    raw
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ")
  ).replace(/\s+/g, " ").trim();
}

function localPathFromSiteUrl(url) {
  try {
    const parsed = new URL(url);
    if (parsed.origin !== SITE_ORIGIN) return null;
    const relative = decodeURIComponent(parsed.pathname).replace(/^\/+/, "");
    return path.join(SITE_ROOT, ...relative.split("/"));
  } catch {
    return null;
  }
}

function imageDimensions(filePath) {
  const buffer = fs.readFileSync(filePath);
  const extension = path.extname(filePath).toLowerCase();

  if (extension === ".png" && buffer.length >= 24 && buffer.toString("ascii", 1, 4) === "PNG") {
    return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
  }

  if (extension === ".jpg" || extension === ".jpeg") {
    let offset = 2;
    while (offset + 9 < buffer.length) {
      if (buffer[offset] !== 0xff) {
        offset += 1;
        continue;
      }
      const marker = buffer[offset + 1];
      const length = buffer.readUInt16BE(offset + 2);
      if ([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].includes(marker)) {
        return { width: buffer.readUInt16BE(offset + 7), height: buffer.readUInt16BE(offset + 5) };
      }
      if (!length || length < 2) break;
      offset += 2 + length;
    }
  }

  if (extension === ".webp" && buffer.length >= 30 && buffer.toString("ascii", 0, 4) === "RIFF") {
    const tag = buffer.toString("ascii", 12, 16);
    if (tag === "VP8X") {
      return { width: 1 + buffer.readUIntLE(24, 3), height: 1 + buffer.readUIntLE(27, 3) };
    }
    if (tag === "VP8 ") {
      for (let offset = 20; offset < buffer.length - 10; offset += 1) {
        if (buffer[offset] === 0x9d && buffer[offset + 1] === 0x01 && buffer[offset + 2] === 0x2a) {
          return {
            width: buffer.readUInt16LE(offset + 3) & 0x3fff,
            height: buffer.readUInt16LE(offset + 5) & 0x3fff,
          };
        }
      }
    }
    if (tag === "VP8L") {
      const bits = buffer.readUInt32LE(21);
      return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
    }
  }

  if (extension === ".svg") {
    const text = buffer.toString("utf8");
    const width = Number(text.match(/\bwidth=["'](\d+(?:\.\d+)?)/i)?.[1] || 0);
    const height = Number(text.match(/\bheight=["'](\d+(?:\.\d+)?)/i)?.[1] || 0);
    if (width && height) return { width, height };
  }

  return null;
}

function issue(list, severity, code, message) {
  list.push({ severity, code, message });
}

function releaseKeys(raw) {
  const assets = [];
  for (const link of links(raw)) {
    const href = link.attributes.href || "";
    if (/(?:styles|tokens)\.css(?:\?|$)|aureon-zorza-backgrounds\.css(?:\?|$)/i.test(href)) assets.push(href);
  }
  for (const script of scripts(raw)) {
    const src = script.attributes.src || "";
    if (/script\.js(?:\?|$)/i.test(src)) assets.push(src);
  }
  return assets.map((asset) => {
    const query = asset.includes("?") ? asset.slice(asset.indexOf("?") + 1) : "";
    const params = new URLSearchParams(query);
    return { asset, key: params.get("v") || "" };
  });
}

function auditPage(filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  const relative = path.relative(SITE_ROOT, filePath).replaceAll("\\", "/");
  const metaTags = metas(raw);
  const linkTags = links(raw);
  const titleMatches = [...raw.matchAll(/<title\b[^>]*>([\s\S]*?)<\/title>/gi)];
  const title = decodeHtml(titleMatches[0]?.[1]?.trim() || "");
  const description = metaValue(metaTags, "name", "description");
  const robots = metaValue(metaTags, "name", "robots");
  const indexable = !/\bnoindex\b/i.test(robots);
  const canonicalValues = linkValues(linkTags, "canonical");
  const canonical = canonicalValues[0] || "";
  const manifestValues = linkValues(linkTags, "manifest");
  const iconValues = linkValues(linkTags, "icon");
  const appleValues = linkValues(linkTags, "apple-touch-icon");
  const og = {
    type: metaValue(metaTags, "property", "og:type"),
    siteName: metaValue(metaTags, "property", "og:site_name"),
    locale: metaValue(metaTags, "property", "og:locale"),
    title: metaValue(metaTags, "property", "og:title"),
    description: metaValue(metaTags, "property", "og:description"),
    url: metaValue(metaTags, "property", "og:url"),
    image: metaValue(metaTags, "property", "og:image"),
    imageWidth: Number(metaValue(metaTags, "property", "og:image:width") || 0),
    imageHeight: Number(metaValue(metaTags, "property", "og:image:height") || 0),
    imageAlt: metaValue(metaTags, "property", "og:image:alt"),
  };
  const twitter = {
    card: metaValue(metaTags, "name", "twitter:card"),
    title: metaValue(metaTags, "name", "twitter:title"),
    description: metaValue(metaTags, "name", "twitter:description"),
    image: metaValue(metaTags, "name", "twitter:image"),
    imageAlt: metaValue(metaTags, "name", "twitter:image:alt"),
  };
  const htmlTag = tags(raw, "html")[0];
  const h1Count = [...raw.matchAll(/<h1\b/gi)].length;
  const ld = jsonLd(raw);
  const schemaTypes = [...ld.filter((block) => block.valid).reduce((set, block) => collectSchemaTypes(block.value, set), new Set())].sort();
  const bodyText = stripMarkup(raw);
  const issues = [];

  if (!indexable) {
    return {
      route: relative,
      indexable,
      title,
      description,
      canonical,
      robots,
      h1Count,
      schemaTypes,
      releaseKeys: releaseKeys(raw),
      issues,
    };
  }

  if (!/^<!doctype html>/i.test(raw.trimStart())) issue(issues, "error", "doctype", "Missing HTML5 doctype.");
  if (!/^en(?:-|$)/i.test(htmlTag?.attributes.lang || "")) issue(issues, "error", "language", "The html element must declare an English language.");
  if (titleMatches.length !== 1) issue(issues, "error", "title-count", `Expected one title; found ${titleMatches.length}.`);
  if (title.length < 30 || title.length > 70) issue(issues, "error", "title-length", `Title length is ${title.length}; target 30-70 characters.`);
  else if (title.length > 60) issue(issues, "warning", "title-concise", `Title length is ${title.length}; 60 or fewer is preferable.`);
  if (description.length < 90 || description.length > 170) issue(issues, "error", "description-length", `Meta description length is ${description.length}; target 90-170 characters.`);
  if (canonicalValues.length !== 1) issue(issues, "error", "canonical-count", `Expected one canonical link; found ${canonicalValues.length}.`);
  if (!canonical.startsWith(`${SITE_ORIGIN}/`) && canonical !== `${SITE_ORIGIN}/`) issue(issues, "error", "canonical-origin", `Canonical must use ${SITE_ORIGIN}.`);
  if (!robots) {
    issue(issues, "error", "robots-missing", "Indexable page needs an explicit robots directive.");
  } else {
    for (const directive of ["index", "follow", "max-image-preview:large"]) {
      if (!robots.toLowerCase().split(/\s*,\s*/).includes(directive)) issue(issues, "error", "robots-directive", `Robots directive is missing ${directive}.`);
    }
  }
  if (h1Count !== 1) issue(issues, "error", "h1-count", `Expected one h1; found ${h1Count}.`);
  if (!metaValue(metaTags, "name", "theme-color")) issue(issues, "error", "theme-color", "Missing theme-color metadata.");
  if (!iconValues.length || !appleValues.length) issue(issues, "error", "icons", "Both favicon and apple-touch-icon links are required.");
  if (manifestValues.length !== 1) issue(issues, "error", "manifest", `Expected one manifest link; found ${manifestValues.length}.`);

  const requiredOg = ["type", "siteName", "locale", "title", "description", "url", "image", "imageAlt"];
  for (const key of requiredOg) if (!og[key]) issue(issues, "error", `og-${key}`, `Missing Open Graph ${key}.`);
  if (og.title && (og.title.length < 20 || og.title.length > 80)) issue(issues, "error", "og-title-length", `Open Graph title length is ${og.title.length}; target 20-80 characters.`);
  if (og.description && (og.description.length < 50 || og.description.length > 200)) issue(issues, "error", "og-description-length", `Open Graph description length is ${og.description.length}; target 50-200 characters.`);
  if (og.url && canonical && og.url !== canonical) issue(issues, "error", "og-url-match", "Open Graph URL must match the canonical URL.");
  if (og.siteName && og.siteName !== "Aureon Zorza Technologies") issue(issues, "error", "og-site-name", "Open Graph site name is inconsistent.");
  if (og.locale && og.locale !== "en_GB") issue(issues, "error", "og-locale", "Open Graph locale must be en_GB.");

  const requiredTwitter = ["card", "title", "description", "image", "imageAlt"];
  for (const key of requiredTwitter) if (!twitter[key]) issue(issues, "error", `twitter-${key}`, `Missing Twitter ${key}.`);
  if (twitter.title && (twitter.title.length < 20 || twitter.title.length > 80)) issue(issues, "error", "twitter-title-length", `Twitter title length is ${twitter.title.length}; target 20-80 characters.`);
  if (twitter.description && (twitter.description.length < 50 || twitter.description.length > 200)) issue(issues, "error", "twitter-description-length", `Twitter description length is ${twitter.description.length}; target 50-200 characters.`);
  if (twitter.card && twitter.card !== "summary_large_image") issue(issues, "error", "twitter-card", "Twitter card must be summary_large_image.");
  if (twitter.image && og.image && twitter.image !== og.image) issue(issues, "error", "social-image-match", "Open Graph and Twitter image URLs must match.");

  if (og.image) {
    const localImage = localPathFromSiteUrl(og.image);
    if (!localImage) {
      issue(issues, "error", "social-image-origin", "Social image must use the canonical site origin.");
    } else if (!fs.existsSync(localImage)) {
      issue(issues, "error", "social-image-file", `Social image does not exist locally: ${path.relative(SITE_ROOT, localImage)}.`);
    } else {
      const dimensions = imageDimensions(localImage);
      if (!dimensions) {
        issue(issues, "warning", "social-image-dimensions", "Could not read social image dimensions.");
      } else if (og.imageWidth !== dimensions.width || og.imageHeight !== dimensions.height) {
        issue(
          issues,
          "error",
          "social-image-dimensions",
          `Declared ${og.imageWidth}x${og.imageHeight}; actual image is ${dimensions.width}x${dimensions.height}.`
        );
      }
      if (dimensions && dimensions.width / dimensions.height < 1.4) {
        issue(issues, "warning", "social-image-aspect", `Social image is ${dimensions.width}x${dimensions.height}; a wider share image will crop more predictably.`);
      }
    }
  }

  if (!ld.length) issue(issues, "error", "jsonld-missing", "Missing schema.org JSON-LD.");
  for (const block of ld.filter((item) => !item.valid)) issue(issues, "error", "jsonld-invalid", block.error);
  const pageTypes = new Set(["WebPage", "AboutPage", "ContactPage", "CollectionPage", "ProfilePage"]);
  const hasPageType = schemaTypes.some((type) => pageTypes.has(type));
  if (relative !== "index.html" && !hasPageType) issue(issues, "error", "jsonld-page-type", "Indexable route needs a WebPage-family schema type.");
  if (relative === "index.html" && !schemaTypes.includes("Organization")) issue(issues, "error", "jsonld-organization", "Homepage needs Organization schema.");

  const keys = releaseKeys(raw);
  for (const item of keys) if (!item.key) issue(issues, "error", "release-key-missing", `Version query is missing for ${item.asset}.`);
  const primaryKeys = [...new Set(keys.filter((item) => /(?:styles|tokens)\.css|script\.js/i.test(item.asset)).map((item) => item.key).filter(Boolean))];
  if (primaryKeys.length > 1) issue(issues, "error", "release-key-page-mismatch", `Primary asset release keys differ: ${primaryKeys.join(", ")}.`);

  const utilityPage = relative === "privacy.html" || relative === "accessibility.html";
  if (!utilityPage && !/\b(evidence|source|research)\b/i.test(bodyText)) {
    issue(issues, "error", "ethos-evidence", "Public route does not visibly express the research/evidence-led ethos.");
  }
  if (!utilityPage && !/\b(boundary|claim|proof|review|human|not)\b/i.test(bodyText)) {
    issue(issues, "error", "ethos-boundary", "Public route lacks visible claim, review, proof or human-authority boundary language.");
  }
  const riskyMetadata = `${title} ${description} ${og.title} ${og.description} ${twitter.title} ${twitter.description}`;
  const riskyTerms = riskyMetadata.match(/\b(world[- ]leading|industry[- ]leading|guaranteed|revolutionary|best[- ]in[- ]class|fully autonomous|production[- ]ready)\b/gi) || [];
  if (riskyTerms.length) issue(issues, "warning", "ethos-risk-term", `Review potentially promotional metadata wording: ${[...new Set(riskyTerms)].join(", ")}.`);

  return {
    route: relative,
    indexable,
    title,
    description,
    canonical,
    robots,
    h1Count,
    schemaTypes,
    socialImage: {
      url: og.image,
      declaredWidth: og.imageWidth,
      declaredHeight: og.imageHeight,
    },
    releaseKeys: keys,
    issues,
  };
}

function validateManifest() {
  const issues = [];
  const manifestPath = path.join(SITE_ROOT, "site.webmanifest");
  if (!fs.existsSync(manifestPath)) {
    issue(issues, "error", "manifest-file", "website/site.webmanifest is missing.");
    return { path: "site.webmanifest", valid: false, issues };
  }
  try {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    for (const key of ["name", "short_name", "description", "lang", "start_url", "scope", "theme_color", "icons"]) {
      if (!manifest[key] || (Array.isArray(manifest[key]) && !manifest[key].length)) issue(issues, "error", "manifest-field", `Manifest field ${key} is missing.`);
    }
    for (const icon of manifest.icons || []) {
      const local = path.join(SITE_ROOT, String(icon.src || "").replace(/^\/+/, ""));
      if (!icon.src || !fs.existsSync(local)) issue(issues, "error", "manifest-icon", `Manifest icon is missing: ${icon.src || "(empty)"}.`);
    }
  } catch (error) {
    issue(issues, "error", "manifest-json", error.message);
  }
  return { path: "site.webmanifest", valid: !issues.some((item) => item.severity === "error"), issues };
}

function audit() {
  const pages = walkHtml(SITE_ROOT).sort().map(auditPage);
  const indexablePages = pages.filter((page) => page.indexable);
  const globalIssues = [];

  for (const field of ["title", "description", "canonical"]) {
    const groups = new Map();
    for (const page of indexablePages) {
      const value = page[field];
      if (!value) continue;
      if (!groups.has(value)) groups.set(value, []);
      groups.get(value).push(page.route);
    }
    for (const [value, routes] of groups) {
      if (routes.length > 1) issue(globalIssues, "error", `duplicate-${field}`, `${field} is duplicated across ${routes.join(", ")}: ${value}`);
    }
  }

  const globalPrimaryKeys = new Map();
  for (const page of indexablePages) {
    for (const item of page.releaseKeys || []) {
      if (!/(?:styles|tokens)\.css|script\.js/i.test(item.asset) || !item.key) continue;
      if (!globalPrimaryKeys.has(item.key)) globalPrimaryKeys.set(item.key, new Set());
      globalPrimaryKeys.get(item.key).add(page.route);
    }
  }
  if (globalPrimaryKeys.size > 1) {
    issue(
      globalIssues,
      "error",
      "release-key-global-mismatch",
      `Indexable routes use multiple primary release keys: ${[...globalPrimaryKeys.keys()].join(", ")}.`
    );
  }

  const manifest = validateManifest();
  const allIssues = [
    ...globalIssues,
    ...manifest.issues,
    ...pages.flatMap((page) => page.issues.map((item) => ({ ...item, route: page.route }))),
  ];
  const errors = allIssues.filter((item) => item.severity === "error");
  const warnings = allIssues.filter((item) => item.severity === "warning");

  return {
    audit: "Aureon metadata and company-ethos audit V28",
    generatedAt: new Date().toISOString(),
    siteOrigin: SITE_ORIGIN,
    scope: {
      htmlFiles: pages.length,
      indexableRoutes: indexablePages.length,
      noindexRoutes: pages.length - indexablePages.length,
    },
    status: errors.length ? "fail" : "pass",
    totals: { errors: errors.length, warnings: warnings.length },
    manifest,
    globalIssues,
    pages,
  };
}

function markdown(report) {
  const lines = [
    "# Aureon Metadata and Company-Ethos Audit V28",
    "",
    `Generated: ${report.generatedAt}`,
    "",
    `Status: **${report.status.toUpperCase()}**`,
    "",
    `Scope: ${report.scope.htmlFiles} HTML files; ${report.scope.indexableRoutes} indexable routes; ${report.scope.noindexRoutes} noindex routes.`,
    "",
    `Findings: ${report.totals.errors} errors; ${report.totals.warnings} warnings.`,
    "",
    "## Indexable route summary",
    "",
    "| Route | Title | H1 | Schema | Errors | Warnings |",
    "| --- | --- | ---: | --- | ---: | ---: |",
  ];

  for (const page of report.pages.filter((item) => item.indexable)) {
    const errors = page.issues.filter((item) => item.severity === "error").length;
    const warnings = page.issues.filter((item) => item.severity === "warning").length;
    lines.push(`| \`${page.route}\` | ${page.title.replace(/\|/g, "\\|")} | ${page.h1Count} | ${page.schemaTypes.join(", ") || "none"} | ${errors} | ${warnings} |`);
  }

  const findings = [
    ...report.globalIssues.map((item) => ({ ...item, route: "GLOBAL" })),
    ...report.manifest.issues.map((item) => ({ ...item, route: "MANIFEST" })),
    ...report.pages.flatMap((page) => page.issues.map((item) => ({ ...item, route: page.route }))),
  ];
  lines.push("", "## Findings", "");
  if (!findings.length) {
    lines.push("No metadata, schema, release-key, social-image or automated ethos findings.");
  } else {
    for (const finding of findings) {
      lines.push(`- **${finding.severity.toUpperCase()} · ${finding.route} · ${finding.code}:** ${finding.message}`);
    }
  }

  lines.push(
    "",
    "## Interpretation boundary",
    "",
    "This audit verifies document metadata, local social-image files, structured-data syntax, explicit indexing controls, asset release keys and basic evidence-language markers. It does not prove search-engine indexing, social-platform cache refresh, scientific validation, commercial traction or production capability."
  );
  return `${lines.join("\n")}\n`;
}

const report = audit();
if (process.argv.includes("--write")) {
  fs.mkdirSync(REPORT_ROOT, { recursive: true });
  fs.writeFileSync(REPORT_JSON, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  fs.writeFileSync(REPORT_MD, markdown(report), "utf8");
}

console.log(JSON.stringify({
  status: report.status,
  scope: report.scope,
  totals: report.totals,
  reportJson: path.relative(REPO_ROOT, REPORT_JSON).replaceAll("\\", "/"),
  reportMarkdown: path.relative(REPO_ROOT, REPORT_MD).replaceAll("\\", "/"),
}, null, 2));

process.exitCode = report.status === "pass" ? 0 : 1;
