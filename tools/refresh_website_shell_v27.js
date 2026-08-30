"use strict";

const fs = require("fs");
const path = require("path");

const websiteRoot = path.resolve(__dirname, "..", "website");
const releaseKey = "evidence-os-20260726-v27";

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(target) : [target];
  });
}

function attributeValue(source, expression) {
  const match = source.match(expression);
  return match ? match[1] : "";
}

function canonicalNavigation(rootHref, activePage) {
  const links = [
    ["projects", "Platform", "projects/"],
    ["research", "Research", "research/"],
    ["publications", "Evidence", "publications/"],
    ["diligence", "Diligence", "diligence/"],
    ["about", "Company", "about/"],
    ["diligence-cta", "Open diligence", "diligence/", "nav-cta"]
  ];
  const markup = links.map(([id, label, route, className]) => {
    const current = id === activePage ? ' active" aria-current="page' : "";
    const classes = className || current ? ` class="${className || ""}${current}"` : "";
    return `<a${classes} data-nav="${id}" href="${rootHref}${route}">${label}</a>`;
  }).join("");
  return `<div class="links">${markup}</div>`;
}

function institutionalBrand(rootHref) {
  return `<a class="brand brand-lockup" href="${rootHref}" aria-label="Aureon Zorza Technologies home"><span class="brand-symbol" aria-hidden="true">A</span><span><strong>Aureon Zorza</strong><small>Research &amp; evidence systems</small></span></a>`;
}

function institutionalFooter(rootHref) {
  return `<footer class="footer brand-footer institutional-footer">
    <div class="wrap institutional-footer-grid">
      <div class="footer-identity">
        <a class="brand brand-lockup" href="${rootHref}" aria-label="Aureon Zorza Technologies home"><span class="brand-symbol" aria-hidden="true">A</span><span><strong>Aureon Zorza</strong><small>Research &amp; evidence systems</small></span></a>
        <p>Technology and R&amp;D programme of R&amp;A Consulting and Brokerage Services Ltd.</p>
      </div>
      <nav aria-label="Platform links"><strong>Review</strong><a href="${rootHref}projects/">Platform</a><a href="${rootHref}research/">Research</a><a href="${rootHref}publications/">Evidence</a><a href="${rootHref}diligence/">Diligence</a></nav>
      <nav aria-label="Public record links"><strong>Public records</strong><a href="https://orcid.org/0009-0004-2792-4649" target="_blank" rel="noopener noreferrer">ORCID</a><a href="https://zenodo.org/search?q=metadata.creators.person_or_org.name%3A%22Leckey%2C%20Gary%22" target="_blank" rel="noopener noreferrer">Zenodo</a><a href="https://github.com/RA-CONSULTING/Aureon-OS" target="_blank" rel="noopener noreferrer">GitHub</a><a href="https://find-and-update.company-information.service.gov.uk/company/NI696693" target="_blank" rel="noopener noreferrer">Companies House</a></nav>
      <nav aria-label="Company links"><strong>Company</strong><a href="${rootHref}about/">About</a><a href="${rootHref}contact/">Contact</a><a href="${rootHref}privacy.html">Privacy</a><a href="${rootHref}accessibility.html">Accessibility</a></nav>
    </div>
    <div class="wrap institutional-footer-legal">
      <p>&copy; 2026 R&amp;A Consulting and Brokerage Services Ltd · NI696693 · Northern Ireland, United Kingdom.</p>
      <p>Public records establish source and attribution only; they do not establish independent validation, commercial performance, customer adoption, funding or endorsement.</p>
    </div>
  </footer>`;
}

let changedFiles = 0;
const htmlFiles = walk(websiteRoot).filter((file) => file.toLowerCase().endsWith(".html"));

for (const file of htmlFiles) {
  const original = fs.readFileSync(file, "utf8");
  let source = original.replaceAll("evidence-os-20260726-v26", releaseKey);
  const relativeDirectory = path.relative(websiteRoot, path.dirname(file));
  const depth = relativeDirectory ? relativeDirectory.split(path.sep).length : 0;
  const isErrorPage = path.basename(file).toLowerCase() === "404.html";
  const rootHref = isErrorPage ? "/" : (depth ? "../".repeat(depth) : "./");
  const activePage = attributeValue(source, /<body[^>]*\bdata-page="([^"]+)"/i);

  source = source.replace(
    /(<link rel="stylesheet" href="(?:\.\/|\.\.\/)*styles\.css)(?:\?[^"]*)?(">)/gi,
    `$1?v=${releaseKey}$2`
  );
  source = source.replace(
    /(<link rel="stylesheet" href="(?:\.\/|\.\.\/)*assets\/css\/aureon-zorza-backgrounds\.css)(?:\?[^"]*)?(">)/gi,
    "$1?v=ra-owner-20260726-v27$2"
  );
  source = source.replace(/^[ \t]*<link rel="stylesheet" href="(?:\.\/|\.\.\/)*tokens\.css(?:\?[^"]*)?">\r?\n?/gim, "");
  source = source.replace(/<\/head>/i, `  <link rel="stylesheet" href="${rootHref === "./" ? "" : rootHref}tokens.css?v=${releaseKey}">\n</head>`);
  source = source.replace(
    /(<script src="(?:\.\/|\.\.\/)*script\.js)(?:\?[^"]*)?("><\/script>)/gi,
    `$1?v=${releaseKey}$2`
  );
  if (/<div class="links">/i.test(source) && !/<script src="(?:\.\/|\.\.\/)*script\.js/i.test(source)) {
    source = source.replace(/<\/body>/i, `  <script src="${rootHref === "./" ? "" : rootHref}script.js?v=${releaseKey}"></script>\n</body>`);
  }

  if (!/<a class="skip-link"/i.test(source)) {
    source = source.replace(/(<body[^>]*>\r?\n?)/i, `$1  <a class="skip-link" href="#main-content">Skip to content</a>\n`);
  }
  source = source.replace(/<main(?![^>]*\bid=)([^>]*)>/i, '<main id="main-content"$1>');

  if (/<div class="links">/i.test(source)) {
    source = source.replace(/<div class="links">[\s\S]*?<\/div>/i, canonicalNavigation(rootHref, activePage));
    source = source.replace(
      /(<nav class="nav"[^>]*>\s*)<a class="[^"]*\bbrand\b[^"]*"[\s\S]*?<\/a>/i,
      `$1${institutionalBrand(rootHref)}`
    );
  }
  source = source.replace(
    /(<a class="[^"]*\bbrand\b[^"]*"[\s\S]*?<small>)[\s\S]*?(<\/small>)/i,
    "$1Research &amp; evidence systems$2"
  );
  if (/<footer\b/i.test(source)) {
    source = source.replace(/<footer\b[\s\S]*?<\/footer>/i, institutionalFooter(rootHref));
  }

  source = source
    .replace(/\bV26\b/g, "V27")
    .replace(/aureon-evidence-os-social-v4-20260721\.png/g, "aureon-research-instrument-v27-social.jpg")
    .replace(/(<meta property="og:image" content="[^"]*\/)aureon-zorza-logo\.jpg(">)/g, "$1aureon-research-instrument-v27-social.jpg$2")
    .replace(/(<meta name="twitter:image" content="[^"]*\/)aureon-zorza-logo\.jpg(">)/g, "$1aureon-research-instrument-v27-social.jpg$2")
    .replace(/(<meta property="og:image:width" content=")\d+(">)/g, "$11600$2")
    .replace(/(<meta property="og:image:height" content=")\d+(">)/g, "$1900$2");

  if (/<meta property="og:image"/i.test(source) && !/<meta property="og:image:alt"/i.test(source)) {
    source = source.replace(
      /(<meta property="og:image" content="[^"]+">\r?\n?)/i,
      '$1  <meta property="og:image:alt" content="Aureon Zorza Technologies research and evidence systems">\n'
    );
  }
  if (/<meta name="twitter:image"/i.test(source) && !/<meta name="twitter:image:alt"/i.test(source)) {
    source = source.replace(
      /(<meta name="twitter:image" content="[^"]+">\r?\n?)/i,
      '$1  <meta name="twitter:image:alt" content="Aureon Zorza Technologies research and evidence systems">\n'
    );
  }
  if (isErrorPage) {
    source = source.replace(
      /\b(href|src)="(?!https?:|mailto:|tel:|#|\/)(?:\.\/)?/gi,
      '$1="/'
    );
  }

  if (source !== original) {
    fs.writeFileSync(file, source, "utf8");
    changedFiles += 1;
  }
}

console.log(JSON.stringify({ websiteRoot, htmlFiles: htmlFiles.length, changedFiles, releaseKey }, null, 2));
