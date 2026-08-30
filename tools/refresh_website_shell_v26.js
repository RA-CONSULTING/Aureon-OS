"use strict";

const fs = require("fs");
const path = require("path");

const websiteRoot = path.resolve(__dirname, "..", "website");
const releaseKey = "evidence-os-20260726-v26";
const socialImage = "https://aureonzorzatechnologies.pl/assets/images/brand/aureon-evidence-os-social-v4-20260721.png";
const socialAlt = "Aureon OS evidence workflow: Gather, Classify, Review, Export";

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

function addImageDimensions(source, imageName, width, height) {
  const escaped = imageName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const expression = new RegExp(`<img\\b([^>]*\\bsrc="[^"]*${escaped}"[^>]*)>`, "gi");
  return source.replace(expression, (tag, attributes) => {
    if (/\bwidth="/i.test(attributes) && /\bheight="/i.test(attributes)) return tag;
    return `<img${attributes} width="${width}" height="${height}">`;
  });
}

function canonicalNavigation(homeHref, activePage) {
  const links = [
    ["projects", "Platform", "projects/"],
    ["diligence", "Diligence", "diligence/"],
    ["research", "Research", "research/"],
    ["funding", "Funding", "funding/"],
    ["publications", "Evidence", "publications/"],
    ["about", "Company", "about/"],
    ["contact", "Contact", "contact/"]
  ];
  const markup = links.map(([id, label, route]) => {
    const active = id === activePage ? ' class="active" aria-current="page"' : "";
    return `<a${active} data-nav="${id}" href="${homeHref}${route}">${label}</a>`;
  }).join("");
  return `<div class="links">${markup}</div>`;
}

function socialMetadata(title, description, canonical) {
  return [
    '  <meta property="og:type" content="website">',
    '  <meta property="og:site_name" content="Aureon Zorza Technologies">',
    '  <meta property="og:locale" content="en_GB">',
    `  <meta property="og:title" content="${title}">`,
    `  <meta property="og:description" content="${description}">`,
    `  <meta property="og:url" content="${canonical}">`,
    `  <meta property="og:image" content="${socialImage}">`,
    '  <meta property="og:image:width" content="1731">',
    '  <meta property="og:image:height" content="909">',
    `  <meta property="og:image:alt" content="${socialAlt}">`,
    '  <meta name="twitter:card" content="summary_large_image">',
    `  <meta name="twitter:title" content="${title}">`,
    `  <meta name="twitter:description" content="${description}">`,
    `  <meta name="twitter:image" content="${socialImage}">`,
    `  <meta name="twitter:image:alt" content="${socialAlt}">`
  ].join("\n");
}

let changedFiles = 0;
const htmlFiles = walk(websiteRoot).filter((file) => file.toLowerCase().endsWith(".html"));

for (const file of htmlFiles) {
  const original = fs.readFileSync(file, "utf8");
  let source = original;
  const relativeDirectory = path.relative(websiteRoot, path.dirname(file));
  const depth = relativeDirectory ? relativeDirectory.split(path.sep).length : 0;
  const rootHref = depth ? "../".repeat(depth) : "./";

  // Meta refresh remains as the CSP-safe compatibility fallback.
  source = source.replace(/\s*<script>\s*window\.location\.replace\([^)]*\);\s*<\/script>\s*/gi, "\n");

  // Retain one canonical only.
  let canonicalSeen = false;
  source = source.replace(/^[ \t]*<link rel="canonical" href="[^"]+">\r?\n?/gim, (tag) => {
    if (canonicalSeen) return "";
    canonicalSeen = true;
    return tag;
  });

  if (!/<link rel="icon"/i.test(source)) {
    source = source.replace(
      /(<meta name="viewport"[^>]*>\r?\n)/i,
      `$1  <link rel="icon" href="${rootHref}assets/favicon.svg" type="image/svg+xml">\n`
    );
  }

  if (!/<link rel="apple-touch-icon"/i.test(source)) {
    source = source.replace(
      /(<link rel="icon"[^>]*>\r?\n)/i,
      `$1  <link rel="apple-touch-icon" href="${rootHref}apple-touch-icon.png">\n`
    );
  }

  source = source.replace(
    /<link rel="stylesheet" href="((?:\.\.\/)*)styles\.css(?:\?[^"]*)?">(?:\r?\n[ \t]*<link rel="stylesheet" href="(?:\.\.\/)*tokens\.css(?:\?[^"]*)?">)?/gi,
    (_tag, prefix) => `<link rel="stylesheet" href="${prefix}styles.css?v=${releaseKey}">`
  );
  source = source.replace(/^[ \t]*<link rel="stylesheet" href="(?:\.\/|\.\.\/)*tokens\.css(?:\?[^"]*)?">\r?\n?/gim, "");
  const assetPrefix = rootHref === "./" ? "" : rootHref;
  source = source.replace(
    /<\/head>/i,
    `  <link rel="stylesheet" href="${assetPrefix}tokens.css?v=${releaseKey}">\n</head>`
  );

  source = source.replace(
    /(<script src="(?:\.\.\/)*script\.js)(?:\?[^"]*)?("><\/script>)/gi,
    `$1?v=${releaseKey}$2`
  );

  const homeHref = attributeValue(source, /<a\s+class="[^"]*\bbrand\b[^"]*"\s+href="([^"]+)"/i);
  const activePage = attributeValue(source, /<body[^>]*\bdata-page="([^"]+)"/i);
  if (homeHref && /<div class="links">/i.test(source)) {
    source = source.replace(/<div class="links">[\s\S]*?<\/div>/i, canonicalNavigation(homeHref, activePage));
  }

  if (!/<meta property="og:title"/i.test(source)) {
    const title = attributeValue(source, /<title>([^<]+)<\/title>/i);
    const description = attributeValue(source, /<meta name="description" content="([^"]*)">/i);
    const canonical = attributeValue(source, /<link rel="canonical" href="([^"]+)">/i);
    if (title && description && canonical) {
      source = source.replace(/(\s*<\/head>)/i, `\n${socialMetadata(title, description, canonical)}$1`);
    }
  }

  if (/aureon-(?:investor-evidence-platform|evidence-observatory)-[^"]+\.(?:png|webp)/i.test(source)) {
    source = source
      .replace(/(<meta property="og:image:width" content=")1248(">)/i, "$11672$2")
      .replace(/(<meta property="og:image:height" content=")832(">)/i, "$1941$2");
  }

  source = addImageDimensions(source, "aureon-zorza-logo.jpg", 480, 320);
  source = addImageDimensions(source, "aureon-evidence-os-social-v4-20260721.png", 1731, 909);
  source = addImageDimensions(source, "innovate-ni-silver-2025.png", 1080, 733);
  source = addImageDimensions(source, "ra-consulting-logo.jpg", 2048, 1535);
  source = addImageDimensions(source, "street-soccer-ni-homeless-world-cup-2025.jpg", 947, 1337);

  if (source !== original) {
    fs.writeFileSync(file, source, "utf8");
    changedFiles += 1;
  }
}

console.log(JSON.stringify({ websiteRoot, htmlFiles: htmlFiles.length, changedFiles, releaseKey }, null, 2));
