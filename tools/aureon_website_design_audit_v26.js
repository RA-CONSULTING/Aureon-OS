"use strict";

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.join(repoRoot, "website");
const auditRoot = path.join(repoRoot, "docs", "audits");
const runId = process.argv[2] || new Date().toISOString().replace(/\D/g, "").slice(0, 14);
const checks = [];

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(target) : [target];
  });
}

function check(id, passed, detail) {
  checks.push({ id, passed: Boolean(passed), detail });
}

function count(source, expression) {
  return [...source.matchAll(expression)].length;
}

const htmlFiles = walk(siteRoot).filter((file) => file.toLowerCase().endsWith(".html"));
const pages = htmlFiles.map((file) => {
  const source = fs.readFileSync(file, "utf8");
  return {
    file,
    relative: path.relative(siteRoot, file).replace(/\\/g, "/"),
    source,
    noindex: /<meta\s+name="robots"[^>]*content="[^"]*noindex/i.test(source)
  };
});
const indexable = pages.filter((page) => !page.noindex);
const styles = fs.readFileSync(path.join(siteRoot, "styles.css"), "utf8");
const tokens = fs.readFileSync(path.join(siteRoot, "tokens.css"), "utf8");
const script = fs.readFileSync(path.join(siteRoot, "script.js"), "utf8");
const htaccess = fs.readFileSync(path.join(siteRoot, ".htaccess"), "utf8");
const home = fs.readFileSync(path.join(siteRoot, "index.html"), "utf8");
const research = fs.readFileSync(path.join(repoRoot, "RESEARCH.md"), "utf8");

check("html_corpus", pages.length === 54, `${pages.length} HTML files`);
check("indexable_route_count", indexable.length === 15, `${indexable.length} indexable routes`);

const missingCoreMetadata = pages.filter((page) => {
  return !/<title>[^<]+<\/title>/i.test(page.source)
    || !/<meta name="description" content="[^"]+">/i.test(page.source)
    || !/<link rel="canonical" href="https:\/\/aureonzorzatechnologies\.pl\//i.test(page.source)
    || !/<meta property="og:title"/i.test(page.source)
    || !/<meta name="twitter:card"/i.test(page.source)
    || !/<link rel="icon"/i.test(page.source)
    || !/<link rel="apple-touch-icon"/i.test(page.source);
});
check("per_page_metadata", missingCoreMetadata.length === 0, missingCoreMetadata.map((page) => page.relative));

const duplicateCanonicalPages = pages.filter((page) => count(page.source, /<link rel="canonical"/gi) !== 1);
check("one_canonical_per_page", duplicateCanonicalPages.length === 0, duplicateCanonicalPages.map((page) => page.relative));

const tokenLoadFailures = pages.filter((page) => {
  const stylesheets = [...page.source.matchAll(/<link rel="stylesheet" href="([^"]+)">/gi)].map((match) => match[1]);
  return !stylesheets.length || !/tokens\.css\?v=evidence-os-20260726-v26$/.test(stylesheets.at(-1));
});
check("tokens_loaded_last", tokenLoadFailures.length === 0, tokenLoadFailures.map((page) => page.relative));

const imageFailures = [];
for (const page of pages) {
  for (const match of page.source.matchAll(/<img\b[^>]*>/gi)) {
    if (!/\balt="/i.test(match[0]) || !/\bwidth="/i.test(match[0]) || !/\bheight="/i.test(match[0])) {
      imageFailures.push(`${page.relative}: ${match[0]}`);
    }
  }
}
check("static_image_contract", imageFailures.length === 0, imageFailures);

const inlineStylePages = pages.filter((page) => /\sstyle="/i.test(page.source));
check("no_inline_styles", inlineStylePages.length === 0, inlineStylePages.map((page) => page.relative));

const executableInlineScripts = [];
for (const page of pages) {
  for (const match of page.source.matchAll(/<script([^>]*)>[\s\S]*?<\/script>/gi)) {
    if (!/\bsrc=/i.test(match[1]) && !/type="application\/ld\+json"/i.test(match[1])) {
      executableInlineScripts.push(page.relative);
    }
  }
}
check("no_executable_inline_script", executableInlineScripts.length === 0, executableInlineScripts);

const malformedJsonLd = [];
for (const page of pages) {
  for (const match of page.source.matchAll(/<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi)) {
    try { JSON.parse(match[1]); } catch (error) { malformedJsonLd.push(`${page.relative}: ${error.message}`); }
  }
}
check("json_ld_valid", malformedJsonLd.length === 0, malformedJsonLd);

const indexableSemanticFailures = indexable.filter((page) => {
  return count(page.source, /<h1\b/gi) !== 1
    || !/<a class="skip-link"/i.test(page.source)
    || !/<header\b/i.test(page.source)
    || !/<nav\b/i.test(page.source)
    || !/<main\b/i.test(page.source)
    || !/<footer\b/i.test(page.source);
});
check("indexable_semantics", indexableSemanticFailures.length === 0, indexableSemanticFailures.map((page) => page.relative));

const navFailures = pages.filter((page) => {
  const match = page.source.match(/<div class="links">([\s\S]*?)<\/div>/i);
  return match && count(match[1], /<a\b/gi) !== 7;
});
check("canonical_seven_link_navigation", navFailures.length === 0, navFailures.map((page) => page.relative));
check("runtime_seven_link_navigation", /function synchronizePrimaryNavigation/.test(script)
  && !/\["home",\s*"Home"/.test(script)
  && count(script.match(/function synchronizePrimaryNavigation[\s\S]*?\n  }/)[0], /\["(?:projects|diligence|research|funding|publications|about|contact)"/g) === 7,
  "Platform, Diligence, Research, Funding, Evidence, Company, Contact");
check("mobile_navigation_disclosure", /function setupMobileNavigation/.test(script)
  && /aria-controls/.test(script)
  && /aria-expanded/.test(script)
  && /event\.key !== "Escape"/.test(script),
  "button disclosure, state, and Escape handling");

check("research_strategy_first", research.startsWith("Design Aureon as a quiet, local-first evidence instrument"), "RESEARCH.md visual strategy is first");
check("research_reference_set", ["Linear", "Stripe", "Vercel", "Anthropic", "Palantir", "Datadog", "Snyk", "Vanta", "Credo AI", "Holistic AI", "IBM watsonx.governance", "Monitaur", "Fairly AI"].every((name) => research.includes(name)), "all named sector references present");

const requiredTokenNames = [
  "--navy-950", "--navy-50", "--gold-500", "--teal-500",
  "--state-source", "--state-company", "--state-provider", "--state-independent", "--state-open",
  "--space-1", "--space-24", "--radius-1", "--radius-4", "--elevation-1", "--elevation-3",
  "--step--1", "--step-5", "--motion-fast", "--motion-base", "--motion-slow"
];
check("design_tokens_complete", requiredTokenNames.every((name) => tokens.includes(name)), requiredTokenNames);
check("typography_contract", /@font-face/.test(tokens) && /max-width:\s*65ch/.test(tokens) && /tabular-nums/.test(tokens) && /letter-spacing:\s*-0\.052em/.test(tokens), "self-hosted fonts, 65ch measure, tabular figures, optical display tracking");
check("self_hosted_fonts", ["manrope-latin-variable.woff2", "ibm-plex-mono-latin-400.woff2", "ibm-plex-mono-latin-600.woff2"].every((name) => fs.statSync(path.join(siteRoot, "assets", "fonts", name)).size > 1000), "three non-empty WOFF2 subsets");
check("no_font_cdn", !/fonts\.(?:googleapis|gstatic)\.com/i.test(pages.map((page) => page.source).join("\n")), "no third-party font requests");

const motionDurations = [...tokens.matchAll(/--motion-[^:]+:\s*(\d+)ms/g)].map((match) => Number(match[1]));
check("motion_cap", motionDurations.length === 3 && Math.max(...motionDurations) <= 400, motionDurations);
check("compositor_only_motion", /transition-property:\s*transform,\s*opacity\s*!important/.test(tokens) && /animation:\s*none\s*!important/.test(tokens), "transform and opacity only; ambient animation disabled");
check("reduced_motion", /@media\s*\(prefers-reduced-motion:\s*reduce\)/.test(tokens), "reduced-motion override present");
check("no_parallax", !/background-attachment:\s*fixed/i.test(styles + tokens) && !/addEventListener\("scroll"/.test(script), "no fixed backgrounds or JS scroll animation");

check("no_js_evidence_path", !/data-control-panel="(?:source|claim|gate|decision)"[^>]*\shidden/i.test(home)
  && /\.home-control-band:not\(\.is-enhanced\)/.test(tokens),
  "all five stages remain readable without JavaScript");
check("keyboard_evidence_path", /ArrowRight/.test(script) && /ArrowLeft/.test(script) && /event\.key === "Home"/.test(script) && /event\.key === "End"/.test(script), "Arrow, Home, and End keys");

check("responsive_picture_assets", count(home, /<picture\b/gi) >= 2
  && /aureon-evidence-observatory-960\.webp/.test(home)
  && /aureon-evidence-observatory-1600\.webp/.test(home)
  && /aureon-zorza-logo-240\.webp/.test(home)
  && /aureon-zorza-logo-480\.webp/.test(home),
  "responsive WebP hero and logo sources");
check("hero_asset_reduction", fs.statSync(path.join(siteRoot, "assets", "images", "brand", "aureon-evidence-observatory-1600.webp")).size
  < fs.statSync(path.join(siteRoot, "assets", "images", "brand", "aureon-evidence-observatory-20260720.png")).size / 4,
  "1600px WebP is less than one quarter of PNG bytes");

check("styleguide_and_404", fs.existsSync(path.join(siteRoot, "styleguide.html")) && fs.existsSync(path.join(siteRoot, "404.html")), "both required pages exist");
check("guarded_htaccess", ["<IfModule mod_rewrite.c>", "<IfModule mod_deflate.c>", "<IfModule mod_expires.c>", "<IfModule mod_headers.c>"].every((token) => htaccess.includes(token)), "optional Apache modules guarded");
check("canonical_https", /https:\/\/aureonzorzatechnologies\.pl%\{REQUEST_URI\}/.test(htaccess), "TLS and canonical hostname rewrite");
check("security_headers", ["Content-Security-Policy", "Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy"].every((name) => htaccess.includes(name)), "defensive headers present");
check("strict_csp", /script-src 'self'/.test(htaccess) && /style-src 'self'/.test(htaccess) && !/unsafe-inline|unsafe-eval/.test(htaccess), "no unsafe script or style allowances");
check("cache_contract", /no-cache, no-store, must-revalidate/.test(htaccess) && /max-age=31536000, immutable/.test(htaccess), "HTML revalidation and immutable static assets");
check("branded_404", /ErrorDocument 404 \/404\.html/.test(htaccess), "server-bound branded 404");

const failures = checks.filter((entry) => !entry.passed);
const result = {
  run_id: runId,
  generated_at: new Date().toISOString(),
  site_root: siteRoot,
  status: failures.length ? "FAIL" : "PASS",
  totals: { checks: checks.length, passed: checks.length - failures.length, failed: failures.length },
  checks
};

fs.mkdirSync(auditRoot, { recursive: true });
const baseName = `AUREON_WEBSITE_DESIGN_AUDIT_${runId}_V26`;
const jsonPath = path.join(auditRoot, `${baseName}.json`);
const markdownPath = path.join(auditRoot, `${baseName}.md`);
fs.writeFileSync(jsonPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
fs.writeFileSync(markdownPath, [
  `# Aureon website design audit — ${runId}`,
  "",
  `**Status:** ${result.status}  `,
  `**Checks:** ${result.totals.passed}/${result.totals.checks} passed`,
  "",
  "| Check | Result | Detail |",
  "|---|---:|---|",
  ...checks.map((entry) => `| ${entry.id} | ${entry.passed ? "PASS" : "FAIL"} | ${String(Array.isArray(entry.detail) ? entry.detail.join(", ") : entry.detail).replace(/\|/g, "\\|")} |`),
  ""
].join("\n"), "utf8");

console.log(JSON.stringify({ status: result.status, checks: result.totals, jsonPath, markdownPath, failures }, null, 2));
process.exitCode = failures.length ? 1 : 0;
