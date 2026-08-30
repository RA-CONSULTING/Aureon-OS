"use strict";

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.join(repoRoot, "website");
const auditRoot = path.join(repoRoot, "docs", "audits");
const releaseKey = "evidence-os-20260726-v27";
const runId = process.argv[2] || new Date().toISOString().replace(/\D/g, "").slice(0, 14);
const checks = [];

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(target) : [target];
  });
}

function count(source, expression) {
  return [...source.matchAll(expression)].length;
}

function check(id, passed, detail) {
  checks.push({ id, passed: Boolean(passed), detail });
}

function relative(file) {
  return path.relative(siteRoot, file).replace(/\\/g, "/");
}

function parseJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}

function localTarget(page, value) {
  const decoded = value.replace(/&amp;/g, "&");
  const [withoutHash] = decoded.split("#");
  const clean = withoutHash.split("?")[0];
  if (!clean) return page.file;
  const candidate = clean.startsWith("/")
    ? path.join(siteRoot, clean.replace(/^\/+/, ""))
    : path.resolve(path.dirname(page.file), clean);
  if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
    return path.join(candidate, "index.html");
  }
  if (/[\\/]$/.test(clean)) return path.join(candidate, "index.html");
  return candidate;
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const htmlFiles = walk(siteRoot).filter((file) => file.toLowerCase().endsWith(".html"));
const pages = htmlFiles.map((file) => {
  const source = fs.readFileSync(file, "utf8");
  return {
    file,
    relative: relative(file),
    source,
    noindex: /<meta\s+name="robots"[^>]*content="[^"]*noindex/i.test(source)
  };
});
const indexable = pages.filter((page) => !page.noindex);
const tokens = fs.readFileSync(path.join(siteRoot, "tokens.css"), "utf8");
const styles = fs.readFileSync(path.join(siteRoot, "styles.css"), "utf8");
const script = fs.readFileSync(path.join(siteRoot, "script.js"), "utf8");
const home = fs.readFileSync(path.join(siteRoot, "index.html"), "utf8");
const researchPage = fs.readFileSync(path.join(siteRoot, "research", "index.html"), "utf8");
const journalPage = fs.readFileSync(path.join(siteRoot, "research", "journal", "index.html"), "utf8");
const styleguide = fs.readFileSync(path.join(siteRoot, "styleguide.html"), "utf8");
const htaccess = fs.readFileSync(path.join(siteRoot, ".htaccess"), "utf8");
const sitemap = fs.readFileSync(path.join(siteRoot, "sitemap.xml"), "utf8");
const researchStrategy = fs.readFileSync(path.join(repoRoot, "RESEARCH.md"), "utf8");

check("html_corpus", pages.length === 56, `${pages.length} HTML files`);
check("indexable_route_count", indexable.length === 17, `${indexable.length} indexable routes`);

const metadataFailures = pages.filter((page) => {
  return count(page.source, /<title>[^<]+<\/title>/gi) !== 1
    || count(page.source, /<link rel="canonical" href="https:\/\/aureonzorzatechnologies\.pl\//gi) !== 1
    || !/<meta name="description" content="[^"]+">/i.test(page.source)
    || !/<meta property="og:title"/i.test(page.source)
    || !/<meta property="og:image:alt"/i.test(page.source)
    || !/<meta name="twitter:card"/i.test(page.source)
    || !/<meta name="twitter:image:alt"/i.test(page.source);
});
check("per_page_metadata", metadataFailures.length === 0, metadataFailures.map((page) => page.relative));

const semanticFailures = pages.filter((page) => {
  return count(page.source, /<h1\b/gi) !== 1
    || !/<a class="skip-link" href="#main-content">/i.test(page.source)
    || !/<main id="main-content"/i.test(page.source);
});
check("page_semantics", semanticFailures.length === 0, semanticFailures.map((page) => page.relative));

const indexableLandmarkFailures = indexable.filter((page) => {
  return !/<header\b/i.test(page.source)
    || !/<nav\b/i.test(page.source)
    || !/<footer\b/i.test(page.source);
});
check("indexable_landmarks", indexableLandmarkFailures.length === 0, indexableLandmarkFailures.map((page) => page.relative));

const cacheFailures = pages.filter((page) => {
  return !new RegExp(`tokens\\.css\\?v=${releaseKey}`).test(page.source)
    || /evidence-os-20260726-v26|ra-owner-20260719-2/.test(page.source);
});
check("release_cache_contract", cacheFailures.length === 0, cacheFailures.map((page) => page.relative));

const expectedNav = ["Platform", "Research", "Evidence", "Diligence", "Company", "Open diligence"];
const navFailures = [];
const brandFailures = [];
for (const page of pages.filter((entry) => /<header\b/i.test(entry.source))) {
  const match = page.source.match(/<div class="links">([\s\S]*?)<\/div>/i);
  const labels = match
    ? [...match[1].matchAll(/<a\b[^>]*>([^<]+)<\/a>/gi)].map((entry) => entry[1].trim())
    : [];
  if (JSON.stringify(labels) !== JSON.stringify(expectedNav)) navFailures.push({ page: page.relative, labels });
  const header = page.source.match(/<header\b[\s\S]*?<\/header>/i)?.[0] || "";
  if (!/class="brand brand-lockup"/.test(header)
    || !/class="brand-symbol"[^>]*>A<\/span>/.test(header)
    || !/<small>Research &amp; evidence systems<\/small>/.test(header)) {
    brandFailures.push(page.relative);
  }
}
check("canonical_six_link_navigation", navFailures.length === 0, navFailures);
check("canonical_header_brand", brandFailures.length === 0, brandFailures);
check("runtime_navigation", /const tabs = \[[\s\S]*?\["diligence-cta", "Open diligence"/.test(script)
  && count(script.match(/function synchronizePrimaryNavigation[\s\S]*?\n  }/)[0], /\["(?:projects|research|publications|diligence|about|diligence-cta)"/g) === 6,
  "six decision-oriented links");
check("legacy_runtime_injections_disabled", !/\n\s*renderPublicReviewPath\(\);/.test(script)
  && !/\n\s*renderSharedGithubFooter\(\);/.test(script),
  "legacy review rail and decorative GitHub footer are not invoked");

const staticImageFailures = [];
for (const page of pages) {
  for (const match of page.source.matchAll(/<img\b[^>]*>/gi)) {
    if (!/\balt="/i.test(match[0]) || !/\bwidth="/i.test(match[0]) || !/\bheight="/i.test(match[0])) {
      staticImageFailures.push(`${page.relative}: ${match[0]}`);
    }
  }
}
check("static_image_contract", staticImageFailures.length === 0, staticImageFailures);

const inlineStylePages = pages.filter((page) => /\sstyle="/i.test(page.source));
check("no_inline_styles", inlineStylePages.length === 0, inlineStylePages.map((page) => page.relative));
const inlineScriptFailures = [];
for (const page of pages) {
  for (const match of page.source.matchAll(/<script([^>]*)>[\s\S]*?<\/script>/gi)) {
    if (!/\bsrc=/i.test(match[1]) && !/type="application\/ld\+json"/i.test(match[1])) {
      inlineScriptFailures.push(page.relative);
    }
  }
}
check("no_executable_inline_scripts", inlineScriptFailures.length === 0, inlineScriptFailures);

const referenceFailures = [];
const fragmentFailures = [];
for (const page of pages) {
  for (const match of page.source.matchAll(/\b(?:href|src)="([^"]+)"/gi)) {
    const value = match[1].trim();
    if (!value || /^(?:https?:|mailto:|tel:|data:|javascript:)/i.test(value)) continue;
    const target = localTarget(page, value);
    if (!fs.existsSync(target)) {
      referenceFailures.push({ page: page.relative, reference: value, target: relative(target) });
      continue;
    }
    const hash = value.includes("#") ? value.split("#").slice(1).join("#") : "";
    if (hash && target.toLowerCase().endsWith(".html")) {
      const targetSource = fs.readFileSync(target, "utf8");
      const decodedHash = decodeURIComponent(hash);
      if (!new RegExp(`\\b(?:id|name)="${escapeRegex(decodedHash)}"`, "i").test(targetSource)) {
        fragmentFailures.push({ page: page.relative, reference: value, target: relative(target) });
      }
    }
  }
  for (const match of page.source.matchAll(/\bsrcset="([^"]+)"/gi)) {
    for (const item of match[1].split(",")) {
      const value = item.trim().split(/\s+/)[0];
      if (!value || /^(?:https?:|data:)/i.test(value)) continue;
      const target = localTarget(page, value);
      if (!fs.existsSync(target)) referenceFailures.push({ page: page.relative, reference: value, target: relative(target) });
    }
  }
}
check("local_references", referenceFailures.length === 0, referenceFailures);
check("local_fragments", fragmentFailures.length === 0, fragmentFailures);

const jsonFiles = walk(path.join(siteRoot, "data")).filter((file) => file.toLowerCase().endsWith(".json"));
const jsonFailures = [];
for (const file of jsonFiles) {
  try { parseJson(file); } catch (error) { jsonFailures.push(`${relative(file)}: ${error.message}`); }
}
check("json_validity", jsonFailures.length === 0, `${jsonFiles.length} JSON files; ${jsonFailures.join(", ")}`);

const researchCatalogue = parseJson(path.join(siteRoot, "data", "research-catalogue.json"));
check("orcid_zenodo_snapshot", researchCatalogue.checked_at.startsWith("2026-07-26")
  && researchCatalogue.orcid.public_work_groups === 74
  && researchCatalogue.zenodo.current_records === 73
  && researchCatalogue.zenodo.unique_dois === 73
  && researchCatalogue.site_view.selected_register_records === 13
  && researchCatalogue.site_view.independently_validated_records === 0,
  researchCatalogue.site_view);

const journal = parseJson(path.join(siteRoot, "data", "substack-research-index.json"));
const artworkEntries = journal.entries.filter((entry) => entry.artwork);
const artworkFailures = artworkEntries.filter((entry) => {
  const large = path.join(siteRoot, entry.artwork.replace(/\//g, path.sep));
  const small = path.join(siteRoot, String(entry.artwork_small || "").replace(/\//g, path.sep));
  return !entry.url || !entry.artwork_alt || !fs.existsSync(large) || !fs.existsSync(small);
});
check("substack_catalogue", journal.checked_on === "2026-07-26"
  && journal.entries.length === 34
  && journal.archive_entry_count === 34
  && journal.direct_entry_count === 0,
  { entries: journal.entries.length, archive: journal.archive_entry_count, direct: journal.direct_entry_count });
check("article_artwork_mapping", artworkEntries.length === 6 && artworkFailures.length === 0,
  { mapped: artworkEntries.length, failures: artworkFailures.map((entry) => entry.title) });
check("article_artwork_source_register", fs.existsSync(path.join(repoRoot, "docs", "design-assets", "substack-public-art", "SOURCE-REGISTER.md")),
  "source register present");

check("research_led_homepage", /The question creates interest\. The test earns attention\./.test(home)
  && /10\.5281\/zenodo\.21540072/.test(home)
  && /not company facilities/i.test(home)
  && /does not establish a result, facility, prototype or independent validation/i.test(home),
  "question, null protocol, source and artwork boundary are visible");
check("six_theme_research_programme", count(researchPage.match(/<div class="research-theme-grid">([\s\S]*?)<\/div>\s*<p class="research-programme-boundary"/)?.[1] || "", /<article>/g) === 6
  && ["Evidence engineering", "Complex signals", "Inspectable AI", "Physical systems", "Long-horizon sensing", "Biological coherence"].every((term) => researchPage.includes(term)),
  "six question-led themes");
check("research_journal_contract", /Questions first\. Sources visible\. Claims bounded\./.test(journalPage)
  && /Editorial illustration/.test(journalPage)
  && /formal research or independent validation/i.test(journalPage),
  "editorial notebook and evidence boundary");
check("research_strategy", /^Design Aureon as an institutional research publisher/.test(researchStrategy)
  && /Research publishing and artwork/.test(researchStrategy),
  "repository strategy begins with the institutional research model");

check("design_system", ["--ivory-100", "--paper", "--ink-950", "--orientation-gold", "--verification-teal",
  "--state-source", "--state-company", "--state-provider", "--state-independent", "--state-open",
  "--space-1", "--space-24", "--radius-1", "--radius-4", "--elevation-1", "--elevation-3",
  "--step--1", "--step-5", "--motion-fast", "--motion-base", "--motion-slow"].every((token) => tokens.includes(token)),
  "warm institutional tokens and five evidence states");
check("self_hosted_typography", ["source-serif-4-latin-variable.woff2", "manrope-latin-variable.woff2",
  "ibm-plex-mono-latin-400.woff2", "ibm-plex-mono-latin-600.woff2"].every((font) => {
  const file = path.join(siteRoot, "assets", "fonts", font);
  return fs.existsSync(file) && fs.statSync(file).size > 1000;
}) && !/fonts\.(?:googleapis|gstatic)\.com/i.test(pages.map((page) => page.source).join("\n")),
"four self-hosted font files; no font CDN");
check("restrained_motion", !/background-attachment:\s*fixed/i.test(styles + tokens)
  && /@media\s*\(prefers-reduced-motion:\s*reduce\)/.test(tokens)
  && !/setupProgressiveReveal\(\)[\s\S]*querySelectorAll\([^)]*section/i.test(script),
  "no parallax, reduced-motion mode, no automatic reveal assignment");
check("styleguide_v27", /Institutional design contract/.test(styleguide)
  && /Artwork can frame a question\. It cannot upgrade the evidence\./.test(styleguide)
  && /Source Serif for authority/.test(styleguide),
  "current institutional design contract");

const canonicalUrls = indexable.map((page) => page.source.match(/<link rel="canonical" href="([^"]+)"/i)?.[1]).filter(Boolean).sort();
const sitemapUrls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((entry) => entry[1]).sort();
check("sitemap_coverage", JSON.stringify(canonicalUrls) === JSON.stringify(sitemapUrls),
  { indexable: canonicalUrls.length, sitemap: sitemapUrls.length });
check("public_policies", indexable.some((page) => page.relative === "privacy.html")
  && indexable.some((page) => page.relative === "accessibility.html"),
  "privacy and accessibility are indexable");

check("apache_guards", ["<IfModule mod_rewrite.c>", "<IfModule mod_deflate.c>", "<IfModule mod_expires.c>", "<IfModule mod_headers.c>"].every((token) => htaccess.includes(token))
  && /ErrorDocument 404 \/404\.html/.test(htaccess)
  && /RewriteRule \\\.\(\?:zip\|bak\|log\|sql\|env\|ini\|md\|ps1\|sh\)\$/.test(htaccess),
  "optional modules guarded, branded 404 and archive patterns blocked");
check("security_headers", ["Content-Security-Policy", "Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy"].every((header) => htaccess.includes(header))
  && /script-src 'self'/.test(htaccess)
  && /style-src 'self'/.test(htaccess)
  && !/unsafe-inline|unsafe-eval/.test(htaccess),
  "strict self-hosted script/style policy");

const failures = checks.filter((entry) => !entry.passed);
const result = {
  run_id: runId,
  generated_at: new Date().toISOString(),
  site_root: siteRoot,
  release_key: releaseKey,
  status: failures.length ? "FAIL" : "PASS",
  totals: { checks: checks.length, passed: checks.length - failures.length, failed: failures.length },
  checks
};

fs.mkdirSync(auditRoot, { recursive: true });
const baseName = `AUREON_WEBSITE_DESIGN_AUDIT_${runId}_V27`;
const jsonPath = path.join(auditRoot, `${baseName}.json`);
const markdownPath = path.join(auditRoot, `${baseName}.md`);
fs.writeFileSync(jsonPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
fs.writeFileSync(markdownPath, [
  `# Aureon website institutional design audit - ${runId}`,
  "",
  `**Status:** ${result.status}  `,
  `**Checks:** ${result.totals.passed}/${result.totals.checks} passed  `,
  `**Release:** \`${releaseKey}\``,
  "",
  "| Check | Result | Detail |",
  "|---|---:|---|",
  ...checks.map((entry) => `| ${entry.id} | ${entry.passed ? "PASS" : "FAIL"} | ${String(typeof entry.detail === "string" ? entry.detail : JSON.stringify(entry.detail)).replace(/\|/g, "\\|")} |`),
  ""
].join("\n"), "utf8");

console.log(JSON.stringify({ status: result.status, checks: result.totals, jsonPath, markdownPath, failures }, null, 2));
process.exitCode = failures.length ? 1 : 0;
