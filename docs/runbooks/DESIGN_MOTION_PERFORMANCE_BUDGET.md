# Design motion and performance budget

## Purpose

`aureon.operator.design_motion_performance_budget` is a deterministic,
local-only static gate for one exact Aureon website tree. It measures motion
declarations and resource weight, applies the motion doctrine, records
privacy-minimised findings, and binds the result to the exact source, budget,
doctrine, configuration, implementation and immutable-writer bytes.

The control accepts only:

- canonical source at `website`; or
- staged source at
  `artifacts/website-candidates/<run-id>/website`.

It never opens the network, executes HTML, CSS or JavaScript, reads
credentials, mutates either source tree, creates or promotes a candidate,
packages a release, grants approval or deploys. A passing result is local
audit evidence only. Browser performance, pointer and keyboard parity,
responsive behaviour, human visual acceptance, package dependency closure,
verified backup, exact-package owner approval, deployment and live HTTPS
read-back remain separate gates.

This generic audit interface is not the staged-candidate policy authority.
Candidate orchestration must first use
`design_candidate_motion_policy_compiler.py` and replay its exact
content-addressed configuration. A worker-selected generic config, even when
stricter or accompanied by its own hash, cannot satisfy the candidate gate.

## Doctrine enforced

The pinned doctrine is
`skills/aureon-harmonic-design-suite/references/design-doctrine.md`.
Configuration cannot raise animation duration above 800 ms, raise transition
duration above 500 ms, lower the normal transition minimum below 80 ms, or
allow a reduced-motion disabling duration above 10 ms.

The static audit blocks:

- autoplay `video` or `audio`, animated GIF/APNG assets, and scripted `.play()`;
- infinite CSS, markup or SVG animation;
- an animation over the pinned maximum;
- a non-zero transition outside the pinned duration range;
- animation, transition, transform or smooth scrolling without a matching
  `prefers-reduced-motion: reduce` override;
- runtime or template-driven motion that cannot be proved statically,
  including CSS `var()`, `calc()`, `env()` or `attr()` motion values and known
  JavaScript motion APIs;
- inline event handlers, computed or direct media `play` capability, and
  scripted autoplay-property or autoplay-attribute assignment;
- statically declared JavaScript fetch/import/worker/socket/media URLs,
  `src`/`href`/`poster` assignments and resource attributes when their origin
  is undeclared; a recognisable dynamic resource assignment is an
  uninspectable-resource blocker;
- malformed or uninspectable HTML, CSS and SVG motion surfaces;
- tree, category, single-asset, declaration, remote-reference or embedded-data
  budget overruns;
- unresolved or escaping local resource paths;
- protocol-relative, malformed, unsupported or undeclared remote origins.

Recognisable dynamic or uninspectable runtime constructs block this gate. The
operator does not estimate them, run them, or retry for a favourable result.
Unrecognised program behaviour is outside this static proof and remains an
explicit browser/package-review limitation.

## Pin an exact configuration

First obtain the source binding:

```powershell
python -m aureon.operator.design_motion_performance_budget snapshot `
  --repo-root . `
  --source-root website
```

For a staged candidate, replace `website` with its exact
`artifacts/website-candidates/<run-id>/website` path. Copy the reported
upper-case `tree_sha256` into a separately reviewed configuration outside the
public source tree. Obtain the doctrine hash without editing the doctrine:

```powershell
(Get-FileHash `
  skills/aureon-harmonic-design-suite/references/design-doctrine.md `
  -Algorithm SHA256).Hash
```

The configuration is strict JSON: duplicate keys, extra keys, a BOM,
non-finite values and weakened policy values are rejected. A representative
canonical configuration is:

```json
{
  "doctrine": {
    "path": "skills/aureon-harmonic-design-suite/references/design-doctrine.md",
    "sha256": "<UPPER-CASE-DOCTRINE-SHA256>"
  },
  "policy": {
    "autoplay_media": "forbid",
    "dynamic_motion": "forbid",
    "infinite_animation": "forbid",
    "reduced_motion_override": "required",
    "undeclared_remote_origins": "forbid"
  },
  "remote_origins": {
    "allow_data_urls": false,
    "allowed": []
  },
  "schema": "aureon.design-motion-performance-budget-config.v1",
  "source": {
    "kind": "canonical-static-tree",
    "root": "website",
    "tree_sha256": "<UPPER-CASE-SOURCE-TREE-SHA256>"
  },
  "thresholds": {
    "max_animation_declarations": 24,
    "max_animation_duration_ms": 800,
    "max_css_bytes": 350000,
    "max_embedded_data_bytes": 0,
    "max_font_bytes": 750000,
    "max_html_bytes": 750000,
    "max_image_bytes": 2200000,
    "max_javascript_bytes": 300000,
    "max_media_bytes": 0,
    "max_other_bytes": 250000,
    "max_reduced_motion_duration_ms": 1,
    "max_remote_resource_references": 0,
    "max_single_asset_bytes": 500000,
    "max_total_bytes": 4500000,
    "max_transition_declarations": 80,
    "max_transition_duration_ms": 500,
    "min_transition_duration_ms": 80
  }
}
```

Thresholds are an owner-reviewed, source-bound test policy. Select them before
the improvement run and do not relax or replace them to turn a failure into a
pass. Stricter values are permitted. For staged source set
`kind` to `staged-static-tree` and use the exact staged path.

`remote_origins.allowed` contains unique, sorted, canonical HTTPS origins such
as `https://cdn.example`. An allowed origin is counted but never contacted.
Allow-listing does not prove its bytes, availability, privacy properties or
release-package closure. Prefer self-hosted, hash-bound dependencies.

## Run the audit

```powershell
python -m aureon.operator.design_motion_performance_budget audit `
  --repo-root . `
  --config data/website_operator/motion-budget.v1.json `
  --output artifacts/website-operator/motion-performance-budget/<run-id>.json
```

The optional output must be a new `.json` path below
`artifacts/website-operator/motion-performance-budget/`. Existing evidence is
never overwritten. The source, configuration and doctrine must be ordinary,
single-link, reparse-free files or directories. A source tree containing a
symbolic link, junction/reparse point, hard-linked file, non-regular entry,
portable case collision or changing byte is rejected before a receipt is
issued.

The executing module must be the repository file at
`aureon/operator/design_motion_performance_budget.py`. Its bytes must equal
the source bytes loaded by the current Python process before the audit and at
receipt finalisation. A same-path file replacement, a modified repository
copy, or a different module origin is rejected rather than described as the
implementation that ran.

Receipt creation is delegated to the hash-bound repository module at
`aureon/operator/secure_immutable_artifact.py`. That writer uses exclusive,
handle-bound creation and same-handle read-back. On Windows it denies sharing,
checks the kernel-resolved final path, file identity, link count and bytes
before and after close. NTFS alternate streams are rejected. Replay failure
never deletes the lexical path. These checks detect observed substitution and
hard-link races but are not a continuous malicious same-user isolation
boundary; use OS principal/ACL isolation when that threat is in scope.

Exit status:

- `0`: the deterministic local budget passed;
- `1`: the audit completed and emitted one or more blockers;
- `2`: an input, path, hash, syntax, receipt or filesystem invariant was
  malformed, stale or unsafe, so no valid audit decision was issued.

## Receipt semantics

The receipt schema is
`aureon.design-motion-performance-budget.v1`. It records:

- the exact repository-relative source kind and path;
- expected and observed source-tree SHA-256, file count and byte count;
- exact configuration, doctrine, implementation and immutable-writer hashes;
- a hash of the complete pinned threshold object;
- byte totals and file counts by HTML, CSS, JavaScript, image, font, media and
  other categories;
- animation and transition declaration counts and duration ranges;
- transform, smooth-scroll and reduced-override counts;
- local, remote and embedded resource counts and bytes;
- sorted blocker findings, fixed checks and a self-hash;
- an explicit authority envelope with no candidate, canonical, package,
  release, credential, network or deployment authority;
- the fixed static-analysis limitation codes that prevent the receipt being
  represented as browser, runtime, interaction or visual proof.

Findings contain public-tree paths, controlled codes, numeric measurements and
hashes. Raw selectors, CSS/HTML/JavaScript snippets, data URLs, local absolute
paths and remote origins are not copied into the receipt. There is no clock
field, so unchanged source, configuration, doctrine, implementation and
immutable-writer bytes produce the same receipt.

`pass` means only that this exact static tree met this exact static policy.
`blocked` is evidence for the next bounded repair. Neither state is candidate
acceptance, browser proof, package readiness or release approval.

## Replay a receipt

```powershell
python -m aureon.operator.design_motion_performance_budget validate `
  --repo-root . `
  --receipt artifacts/website-operator/motion-performance-budget/<run-id>.json
```

Validation rejects duplicate JSON keys, non-canonical encoding, an altered
self-hash, authority expansion, malformed findings, source/config/doctrine
drift, implementation drift, immutable-writer drift and any mismatch with a
complete current replay.
Do not manually refresh a stale tree hash. Re-run `snapshot`, review the new
tree and thresholds, create a new immutable configuration decision, and issue
new evidence.

## Static-versus-browser boundary

This control can prove only statically visible declarations and resource
references. It cannot prove:

- computed style, cascade outcome or visual quality;
- frame rate, layout shift, paint time, interaction latency or long tasks;
- pointer, keyboard, focus, history, resize or viewport parity;
- actual browser caching, compression, decoding or remote response bytes;
- JavaScript behaviour not recognisable as a bounded static construct;
- whether motion communicates the intended hierarchy or state.

JavaScript analysis is deliberately conservative pattern analysis, not a
general proof of program behaviour. It covers direct and computed media-play
capability, common motion APIs, inline event handlers, common fetch/import/
worker/socket/media constructors, static or recognisably dynamic
`src`/`href`/`poster` assignments, resource `setAttribute`, and request
`.open()` forms. Obfuscated code or behaviour assembled through other
indirection remains a browser/package-review concern; passing this static gate
must never be used to claim that arbitrary JavaScript has been proved safe.
Remote response bytes and runtime effects are never fetched. GIF and APNG
autoplay classification is intentionally extension-conservative, and SVG
finding lines are file-level. These residual limitations are repeated as
fixed codes in every receipt so they cannot be omitted during replay.

After a passing static receipt, run the source-bound candidate initial gate and
the required sequential browser matrix. Preserve a rejected first result.
Material visual changes still require named human pixel review and separate
visual acceptance. Release work still follows WebsiteOperator: reproducible
package, offline extraction test, fresh verified Home.pl backup, short-lived
exact-package owner approval, explicit upload and complete live read-back.
