# Read-only staged-candidate static QA

Status: local evidence control only  
Python receipt schema: `aureon.design-candidate-static-qa.v1`  
JavaScript receipt schema: `aureon.design-candidate-javascript-syntax.v1`  
Python implementation: `aureon/operator/design_candidate_static_qa.py`  
JavaScript adapter: `tools/aureon_candidate_javascript_syntax_v1.js`

## Purpose

The historical V28 audits are useful references, but they are not safe
candidate commands unchanged. They hard-code the canonical `website/` tree,
some write reports below `docs/audits/`, and the design audit starts package
or PowerShell checks. These successors perform candidate-scoped, deterministic
static checks without modifying the candidate, canonical site, repository or
provider.

The complete future command order is:

1. `candidate.website-operator-static.v1`
2. `candidate.javascript-syntax.v1`
3. `candidate.v28-design-system-static.v1`
4. `candidate.v28-metadata-ethos-static.v1`

The first, third and fourth IDs use the Python tool with different fixed
modes. The second uses the Node adapter. The existing
`design_candidate_visual_review` control remains responsible for browser and
human visual evidence.

`v28-composite-visual-release-gate` is deliberately deferred. No output from
these tools satisfies it, substitutes for it, or may be labelled as composite
visual acceptance.

## Exact command surfaces

The Python tool accepts exactly four arguments in this order:

```text
python -I aureon/operator/design_candidate_static_qa.py --mode <MODE> --candidate-root <ABS_STAGE_WEBSITE>
```

`MODE` is exactly one of:

- `website-operator-static`
- `v28-design-system-static`
- `v28-metadata-ethos-static`

The Node adapter accepts exactly the staged root followed by the three fixed,
ordered relative paths:

```text
node tools/aureon_candidate_javascript_syntax_v1.js <ABS_STAGE_WEBSITE> script.js funding/funding-status.js live/live.js
```

Neither command accepts a report, output, write, executable, policy,
configuration, claim-input, script, URL, shell, retry or environment
parameter. Unknown, duplicate, missing, reordered or additional arguments
fail the trust boundary.

`<ABS_STAGE_WEBSITE>` must resolve exactly to:

```text
<repo>/artifacts/website-candidates/<run-id>/website
```

The canonical `<repo>/website`, work-order area, nested candidate paths,
relative paths, traversal, UNC paths, and `file:`, HTTP or other URL inputs are
rejected. The trusted candidate-test executor remains responsible for binding
this staged tree to one passed `aureon.design-candidate.v1` receipt and for
pinning the tools and policy by hash.

## Read-only trust boundary

The Python tool resolves the repository from its trusted `__file__` location
and reads only the fixed
`aureon/operator/website_operator.defaults.json` configuration. Claim inputs
whose configured paths start with `website/` are projected in memory to the
staged candidate root. There is no caller-selected configuration or claim
input.

Both tools:

- enumerate without following symbolic links, junctions or reparse points;
- reject special files, hard-linked files and case-fold path collisions;
- prove every resolved entry stays inside the exact staged root;
- hash the complete tree before and after the audit;
- reject endpoint drift;
- emit relative paths only; and
- retain no timestamps, UUIDs, absolute paths, raw public copy, raw secrets or
  parser messages.

Endpoint comparison is not a continuous filesystem sandbox. A malicious
mutate-then-restore action between observations is a residual limitation. The
trusted candidate-test executor separately observes its wider integrity
surfaces before and after each command.

Python uses strict UTF-8 and strict JSON. UTF-8 BOMs, NUL bytes, malformed
encoding, duplicate JSON keys and non-finite JSON numbers fail closed. The
Node adapter uses a fatal UTF-8 decoder and `vm.Script` only to parse the three
fixed scripts. It does not execute them.

## Python modes

### `website-operator-static`

This mode covers the static WebsiteOperator successor:

- required critical and release files;
- in-memory staged claim-input projection and optional schema binding;
- total-site, file-count, per-file and critical-page direct-byte budgets;
- blocked public filenames and extensions, including every `.env.*` variant;
- fixed packaging allowed-filename and allowed-extension enforcement over the
  required and browser-loadable release closure, including social images,
  object/embed/iframe/media/SVG/form/refresh references, CSS `url()`,
  structural `@import` and `image-set()` strings, after comment removal and
  CSS identifier/value escape canonicalisation, and every supported
  webmanifest URL field (`start_url`, optional `scope`, icons, shortcuts,
  screenshots, share/protocol/file handlers, `note_taking.new_note_url`,
  `tab_strip.new_tab_button.url` and service-worker source); missing, remote,
  executable and non-public manifest targets fail closed;
  intentional unreferenced operator scripts and documentation remain source
  members, not release members;
- configured secret-pattern scanning over every bounded regular file,
  including unknown and non-public suffixes;
- strict text and public JSON parsing; and
- exact tree stability.

### `v28-design-system-static`

This mode covers the safe static portion of the V28 design-system audit:

- one title, canonical and H1 plus duplicate-ID detection;
- fail-closed duplicate HTML attribute detection before any semantic audit;
- local HTML and CSS references, exact path case and fragment targets,
  including every audited browser-active URL attribute; stylesheets must be
  staged local relative references, so same-host absolute and
  protocol-relative aliases are not accepted;
- rejection of `data:`, `javascript:`, `blob:`, `file:` and `vbscript:`
  active URLs, plus remote active-content, form, beacon and automatic-
  navigation targets;
- active fetch-policy checks for prefetch, preload, modulepreload, prerender,
  preconnect and DNS-prefetch links, plus refresh forms both with and without
  an explicit `url=`;
- recursive XML parsing of locally referenced SVG/XML resources, rejecting
  scripts, event handlers, XML stylesheet processing instructions, SMIL
  `set`/`animate` URL mutation, every inherited XML Base (`xml:base`)
  attribute, remote paint-server URLs, embedded active containers,
  active/remote URLs, executable dependencies, DTD/entity declarations and
  malformed XML;
- main landmarks, image alternatives, button types, iframe titles and safe
  new-tab links;
- autoplay and marquee rejection;
- rejection of inline executable scripts, event handlers, `srcdoc`, and
  executable script URLs containing any scheme or network location—even the
  public first-party host—and JavaScript outside the exact reviewed
  `script.js`, `funding/funding-status.js`, `live/live.js` allowlist;
- rejection of HTML `base` elements that could retarget an otherwise reviewed
  relative script reference;
- comment- and string-aware reduced-motion evidence requiring a non-empty
  effective CSS declaration—not a custom property or contradictory nested
  conditional branch—and a positive `matchMedia(...).matches` conditional in
  a local reviewed script that an audited HTML page actually loads. The
  JavaScript gate must be the first executable structural statement; only
  whitespace, comments, semicolons and one exact `"use strict";` or
  `'use strict';` directive may precede it. Negated gates, literal/void-only
  branches, function/IIFE/callback gates, dead control arms, call-graph
  inference, prior throw/await/infinite-loop prefixes, RegExp/string/comment
  decoys and unloaded scripts fail closed. A candidate with no structural gate
  receives `reduced-motion-javascript-gate-missing`; a structural gate that
  cannot satisfy the restricted proof receives
  `reduced-motion-javascript-proof-unavailable`. CSS conditional ranges are
  computed by one bounded structural pass;
- rejection of non-void HTML self-closing syntax that browsers parse as an
  open element;
- separation of executable/browser-active elements from rendered semantic
  evidence: `template`, `noscript`, `[inert]`, `[hidden]`, hidden inline
  styles, and external CSS concealment cannot supply visible text, IDs,
  headings, landmarks, accessibility evidence, fragments, titles or JSON-LD.
  The preliminary parse retains every ordinary rendered element, its exact
  root-to-self ancestor indices, tag and attributes for each HTML document.
  Head content, pseudo-elements, inactive templates, inert/hidden branches,
  closed dialogs and fallback/foreign non-rendered containers do not enter
  that rendered tree. Every external stylesheet, embedded `<style>` block and
  inline style is matched against the actual element tree. A concealment or
  geometry source on an ordinary wrapper is projected only to real critical
  `body`, `main` or `h1` descendants on that ancestor chain; a sibling,
  nonmatching wrapper or wrapper with no critical descendant supplies no
  semantic concealment evidence. Selector lists, attributes and substring
  operators, `:is()`, `:where()`, negative/structural pseudos, universal
  subjects, conditional and unknown grouping at-rules, and native nesting
  with `&` retain parent selector context. Child (`>`) and descendant
  combinators retain their distinct ancestry constraints; sibling
  combinators remain conservative. Pseudo-element-only rules do not hide
  their originating element. Concealment declarations include `display`,
  `visibility`, `content-visibility`, zero or dynamically computed opacity,
  `var()` indirection, filter opacity, zero scale, singular or zero-area
  matrices, clipping, and bounded off-screen positioning. Every standard
  `transform` function is parsed into a 4x4 homogeneous step:
  `matrix*`, `translate*`, `scale*`, `rotate*`, `skew*` and `perspective`.
  The steps are post-multiplied in declaration order. Constant matrix values
  retain exact arity; absolute translation units normalize to CSS pixels, and
  affine relative translations retain signed per-unit coefficients through
  numeric scale, rotation and skew steps. A scale-aware rank check rejects a
  singular composed matrix. The transformed z=0 origin and x/y basis are
  projected through homogeneous `w`; non-finite, nonpositive or near-zero
  sampled `w`, collapsed 3D area, and collapsed screen-projected area reject.
  The projected origin supplies the composed pixel displacement.
  `translate()`, `translateX()`, `translateY()`, `translateZ()` and
  `translate3d()` inspect both rendered axes, order, signs and supported CSS
  units. The individual `translate`, `rotate` and nonzero `scale` properties
  remain matrix-bearing and compose in their CSS-defined order before the
  `transform` list: `translate`, then `rotate`, then `scale`, then
  `transform`, independent of declaration order. Thus an individual
  `scale:2` amplifies a following transform translation, while a preceding
  individual translation is not incorrectly amplified. Physical, logical,
  one-to-four-value `inset`, `inset-block` and `inset-inline` declarations are
  expanded in declaration order with `!important` precedence. Each element's
  position and transform properties compose before its descendant matrix, and
  ancestor matrices compose root-to-critical as `M_parent @ M_child`.
  Supported relative translation coefficients are mapped through those
  numeric matrices, preserving scale/rotation effects and signed
  cancellation. Across rules and rendered-element ancestors, distinct
  property/source slots aggregate conservatively; competing values for the
  same property on the same source remain cascade alternatives rather than
  being falsely summed. The bounded Cartesian replay retains at most 4096
  distinct geometry states per critical target and at most 2,000,000
  selector-element match operations per document; an exceeded bound produces
  `candidate-css-complexity-limit`. Legacy `clip:rect()` evaluates its
  horizontal and vertical axes independently, normalizes absolute length
  units, applies the determinate zero semantics of `auto` top/left, and
  rejects known equal or inverted extents even if the other axis remains
  `auto`. Inline styles use the same declaration and aggregation policy.
  Malformed CSS and more than 256 nested blocks produce canonical
  `candidate-css-structure-invalid` or `candidate-css-complexity-limit`
  blockers instead of parser escape or recursion. Closed dialogs, `select`,
  `style`, `script`, head and fallback/foreign containers remain
  non-semantic;
- categorical rejection of `iframe`, `noembed`, `noframes`, `plaintext`,
  `textarea` and `xmp`, including non-void self-closing spellings, because
  Python's tokenizer cannot reproduce their browser RAWTEXT, fallback or
  plaintext state transitions;
- shared asset version presence and consistency; and
- exact tree stability.

It does not run a package builder, PowerShell, a browser, visual diffs,
performance measurements or responsive geometry checks.

The bounded off-screen decision applies to cumulative signed displacement:
at least `1000px`, after converting CSS absolute-length units, or at least
`100` for percent, font-relative, viewport, container and other supported
non-empty length units. Same-unit terms cancel exactly. Incomparable units
contribute conservatively as fractions of their respective bounds. Constant
compositions below those bounds are non-concealing controls; unitless nonzero
offsets are not accepted as CSS lengths. A dynamic
`calc()`/`clamp()`/`env()`/`min()`/`max()`/`var()` transform, translate or
resolved inset cannot prove a safe bound and therefore fails closed.

This is a bounded concealment proof, not a browser layout engine. It samples
the local z=0 origin and unit basis and does not resolve box dimensions,
`transform-origin`, containing blocks, writing modes, scrolling, or exact
cross-rule conditional/specificity outcomes. Same-property cascade
exclusivity is retained as alternatives; different properties and ancestor
layers are assumed able to coincide when exclusivity cannot be proved.
Sibling-selector application is conservatively over-approximated because the
rendered tree binds ancestry rather than a complete browser selector engine.

### `v28-metadata-ethos-static`

This mode covers the safe static portion of the V28 metadata and ethos audit:

- doctype, language, UTF-8, viewport, title, description, canonical and H1;
- fail-closed indexing-suppression rejection on every configured critical
  route, including `none`, crawler-specific meta aliases, `X-Robots-Tag`
  metadata or `.htaccess` headers; `.htaccess` `Define`, `SetEnv`,
  `SetEnvIf`, `SetEnvIfExpr` and rewrite environment substitutions are
  conservatively expanded, unresolved header substitutions fail closed, and
  `robots.txt` paths receive at most four strict UTF-8 percent transformations
  before slash and Unicode normalisation; malformed, control-bearing or
  still-escaped paths fail closed. Repeated decoding is a conservative
  anti-smuggling over-approximation, not standards-equivalent URI matching;
- Open Graph and Twitter card consistency;
- duplicate canonical and metadata-identity detection;
- first-party local social-image presence;
- structurally parsed embedded JSON-LD and route schema-family checks (HTML
  comments are not evidence);
- typed, local, exact-case webmanifest navigation, scope, asset, handler and
  service-worker fields with ordinary-file and media-type checks;
- fixed-config research, evidence, boundary and human-authority signals;
- configured prohibited-claim patterns;
- per-route evidence and authority-boundary language; and
- staged claim-input presence and schema binding.

The receipt contains finding codes and evidence hashes, never the matched
wording.

## Receipt and exits

stdout is exactly one newline-terminated canonical JSON object. Python output
has exactly:

```json
{
  "schema": "aureon.design-candidate-static-qa.v1",
  "mode": "website-operator-static",
  "source": {
    "root": "artifacts/website-candidates/example/website",
    "tree_sha256": "<SHA256>",
    "file_count": 0,
    "total_bytes": 0
  },
  "checks": [],
  "findings": [],
  "decision": {
    "status": "pass",
    "blocker_count": 0,
    "finding_set_sha256": "<SHA256>"
  },
  "limitations": [],
  "authority": {}
}
```

Each check contains only `id`, boolean `passed`, and sorted
`blocker_codes`. Each finding contains only `code`, `severity`, candidate-
relative `path`, integer `line`, and `evidence_hash`.

Node output uses the same source boundary and includes the three bound script
hashes plus sorted hash-only syntax failures. Any additional `.js` file fails
the reviewed-tree boundary before parsing, whether or not an HTML page
references it.

Exit codes are:

- `0`: the selected static scope passed;
- `2`: static findings were retained; and
- `3`: invalid CLI, root, filesystem, UTF-8, JSON, configuration or mutation
  trust boundary.

An exit `0` proves only the selected static scope for one unchanged staged
tree. It is not candidate validation, package approval, deployment approval,
human visual acceptance, owner approval or release authority.

The immutable historical V44 candidate intentionally does not satisfy the
restricted successor JavaScript grammar. Its design-mode receipt must fail
closed with exactly `reduced-motion-javascript-proof-unavailable`; V44 is not
rewritten or exempted by path, hash or legacy call-graph inference. A successor
must expose the small first-executable gate above.

## Verification

Focused checks:

```text
python -m pytest tests/test_design_candidate_static_qa.py -q
node tests/test_candidate_javascript_syntax_v1.js
python -m ruff check aureon/operator/design_candidate_static_qa.py tests/test_design_candidate_static_qa.py
python -m ruff format --check aureon/operator/design_candidate_static_qa.py tests/test_design_candidate_static_qa.py
python -m mypy --strict --follow-imports=skip aureon/operator/design_candidate_static_qa.py
python -m py_compile aureon/operator/design_candidate_static_qa.py
node --check tools/aureon_candidate_javascript_syntax_v1.js
```

The adversarial suite covers canonical-root substitution, nested layout and
path traversal, UNC and URL inputs, unknown/duplicate/write arguments,
hardlinks and reparses, invalid UTF-8, duplicate and non-finite JSON, missing
references and fragments, metadata/ethos/privacy failures, secret and budget
evidence, `.env.*` variants, packaging allowlist enforcement, endpoint
mutation, determinism, duplicate HTML attributes and metadata identities,
comment/string/custom-property/nested-media/unreachable-loop/void
reduced-motion decoys, first-executable throw/await/infinite-loop prefixes,
function/IIFE/arrow/object/class/generator/catch gates, RegExp and
division/RegExp ambiguity, negated and literal-only branches, unloaded scripts,
inert/hidden/raw-text/select/closed-dialog structure
and copy, conditional external-CSS hiding, non-void self-closing parser
differentials, crawler-meta/indirect-`.htaccess`/percent-encoded-`robots.txt`
indexing suppression, same-host absolute and protocol-relative scripts and
stylesheets, active `data:`/`javascript:`/`blob:`/`file:` surfaces, shorthand
refresh and active fetch links, recursively active SVG, XML stylesheet
instructions, SMIL mutations, remote paint URLs, remote embedded content, and
browser-loadable PowerShell payloads reached through HTML, SVG, social
metadata, escaped/comment-split CSS imports/URLs/image sets and all
webmanifest URL families. A synthetic large-CSS test binds visibility and
hundreds of reduced-motion conditionals to a five-second upper bound. The
suite also covers compound hidden-main selectors, statically false numeric
JavaScript gates, parser-differential HTML elements, inherited XML Base, and
one- through five-layer percent-smuggling plus malformed/control vectors. It
also covers additional and inline malformed JavaScript, non-execution, and
the absence of subprocess, filesystem-writer and network-client calls in the
Node adapter. The Node adapter deliberately remains syntax-only; reduced-
motion reachability is enforced by the Python design mode.

The CSS corpus additionally covers escaped property names, comma-safe
selector functions, `:root`, universal/negative/structural pseudos, exact and
substring attributes, native nested selectors and nested grouping
declarations, undefined and cross-rule custom properties, `calc()`,
`min()`/`clamp()`/`env()`, filter opacity and scale. Geometry cases include
zero and nonzero singular 2D/3D matrices, collapsed axes and planes,
off-screen matrix terms, transform-function and individual translations,
both axes and signs, pixel/absolute/relative/viewport units, whitespace and
scientific notation, physical/logical/shorthand and split-rule insets, and
equal/inverted legacy clip rectangles. The composition corpus permanently
adds all nine independently sealed cumulative/mixed-`auto` reproducers plus
ordered matrix/function multiplication, scale and rotation mapping,
same-rule and cross-rule property composition, ancestor propagation,
same-property cascade alternatives, mixed-unit conservative sums, signed
cancellation, and inline parity. Implementation-generated homogeneous tests
cover z=0 planes with zero, negative and near-zero `w`, identity, and valid
perspective; they are not attributed to the independent reproducer record.
Identity/rotation matrices, bounded cumulative translations and insets,
positive-area mixed-`auto` clips, pseudo-element non-regression, unclosed EOF
rules, and 300-level adversarial nesting remain positive or boundary controls
as appropriate.

The rendered-ancestor corpus additionally seals ordinary wrappers around the
only `main`/`h1` for display removal, full transparency, direct and cumulative
transform translation, layout-plus-transform displacement, and
individual-translate-plus-transform displacement. It covers external rules,
embedded style blocks and inline style attributes; nested wrapper matrices;
ancestor/child amplification and signed cancellation; same-source cascade
alternatives; exact child-combinator constraints; pseudo-elements;
nonmatching, sibling and noncritical wrappers; and decoy critical markup below
template, inert and foreign non-rendered branches. Individual-transform
regressions bind declaration-order independence, zero and nonzero scale,
downscale and reciprocal-scale controls, translate/rotate/scale/transform
order, and the exact `scale:2` plus `translateX(600px)` reproducer.
