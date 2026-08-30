# Aureon live visual and message audit — 30 July 2026

## Scope and authority

Read-only browser review of:

- `https://aureonzorzatechnologies.pl/`
- `https://aureonzorzatechnologies.pl/funding/investor-deck/`

The review covered the rendered desktop and mobile surfaces, visual hierarchy,
responsive behaviour, image loading, navigation, reduced-motion rules, console
errors and investor-message flow. It did not alter Home.pl, the public site or
the canonical local `website/` tree.

## Executive assessment

The live site is already a serious institutional research-and-evidence
website. It is materially stronger than a generic AI startup page:

- the category statement is immediate and memorable;
- the serif/sans editorial system, off-white and midnight palette, thin rules
  and generous spacing create authority;
- the commercial wedge, shared core, application routes and proof boundaries
  are visible on the first page;
- the research artwork is used as editorial illustration and captioned as
  non-experimental evidence; and
- the investor route feels like a controlled reading room rather than a
  public financing pitch.

The next improvement should be editorial precision and source reconciliation,
not a wholesale visual replacement.

## Verified rendered behaviour

### Desktop homepage

- Viewport reviewed: 1,665 × 825 CSS pixels.
- The hero uses a 82.32 px `Source Serif 4` headline against an off-white
  background and a structured investment-thesis panel.
- The page contains 11 main sections, 68 links and one navigation button.
- Six image elements have descriptive alternative text; none was missing an
  `alt` value.
- The five research illustrations loaded successfully when their section
  entered the viewport. The leading source asset rendered at 1,200 × 675
  pixels.
- No browser console error or warning was recorded during the review.

### Mobile homepage

- Viewport reviewed: 390 × 844 device target, 375 CSS-pixel content width.
- No horizontal overflow was present.
- The hero headline reduced to 43.2 px with a readable 40.608 px line height.
- The navigation control exposes `aria-expanded` and `aria-controls`, opened
  and closed correctly, and measured 93 × 45 pixels.
- Primary action targets measured 48 pixels high.

### Motion and accessibility

- The inspected surface uses short 0.18-second transitions rather than
  continuous decorative animation.
- Twenty-six loaded stylesheet blocks target
  `prefers-reduced-motion: reduce`.
- The global reduced-motion rule collapses transition and animation durations;
  route-specific rules also stop live indicators, orbital rings and hover
  transforms.
- Core content is present in the static DOM and does not depend on animation.

### Investor reading room

- The desktop hero has a high-spec midnight visual treatment with a controlled
  diligence panel and clear primary actions.
- The mobile route had no horizontal overflow and retained a readable 46.8 px
  headline.
- The reading sequence covers market problem, inspectable product, proof
  state, maturity, public sources and contact.

## Material gaps

### 1. Remove the public "Swiss Army" label

The homepage currently labels the capability section `Swiss Army
architecture`. The structure successfully communicates breadth, but the phrase
reduces the institutional tone.

Recommended replacement:

> Shared-core architecture

The heading can continue to show the intended quality:

> The core stays constant. The mission evidence changes.

### 2. Remove internal-looking figures from the public investor route

The investor page currently includes public-route and implementation counts,
including selected route totals, zero-state application assertions, selected
record totals, module estimates and offline test counts. Some are attached to
checks dated 22 or 25 July 2026.

Those figures conflict with the explicit no-internal-figures public direction,
age quickly and invite diligence on counting methods before the reader has
understood the product.

Replace them with:

- a direct public source link;
- a precise state label such as `Company-built`, `Source-linked` or
  `Independent review open`;
- the mechanism a reviewer can inspect; and
- the next proof gate.

Retain figures in controlled investor correspondence or the private data room
when they answer a specific diligence question.

### 3. Replace dated "current" badges with a governed freshness state

The investor hero says the public brief and source routes were checked on
25 July 2026, while the engineering section references a 22 July commit
snapshot. A static "current" badge becomes stale even when the underlying
page remains valid.

Either:

1. generate the displayed date only from a passing source-refresh receipt; or
2. remove the badge and provide a direct source route plus a clearly dated
   evidence record.

### 4. Reconcile live artwork with the canonical source policy

The live homepage currently serves and successfully renders five
Substack-related editorial illustrations with careful captions. The canonical
local research-refresh declaration still blocks external editorial artwork as
`not-cleared`, and the local `website/` source does not match the live surface
across most reviewed routes.

No redeployment should proceed until:

- the owner selects the live site or the local tree as the canonical baseline;
- a verified Home.pl backup exists;
- every retained editorial asset has a local provenance, hash, MIME,
  dimensions, source-article link, route scope and explicit human rights/use
  decision; and
- the chosen candidate passes the existing visual, accessibility,
  performance, claim and owner gates.

### 5. Add only one explanatory motion system

The live site's restraint is an advantage. The highest-value future animation
is one original HNC evidence graph:

> research record → source and claim state → Aureon OS control → human gate →
> bounded application and retained decision

It should resolve into a complete static diagram immediately, never delay the
hero, respect reduced motion and make the system easier to understand. More
ambient effects would reduce seriousness.

## V30 candidate recommendation

Preserve the current live visual system and prepare a bounded candidate that:

1. changes `Swiss Army architecture` to `Shared-core architecture`;
2. removes public internal-looking counts from the investor route;
3. makes the first-buyer and evidence-operations wedge slightly more explicit;
4. replaces stale date badges with governed source freshness;
5. retains the research imagery only through a formal asset-provenance gate;
   and
6. adds one restrained HNC evidence-graph transition with a complete static
   and reduced-motion equivalent.

This audit is design evidence only. It grants no package, deployment,
credential or production-mutation authority.
