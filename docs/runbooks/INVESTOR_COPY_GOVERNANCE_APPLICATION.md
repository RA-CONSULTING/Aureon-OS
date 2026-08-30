# Investor-copy governance application

This control applies one exact governance-only correction for
`DESIGN-COPY-001`. It never edits `website/` or the investor-copy policy and
grants no candidate, package, release, credential, network, or deployment
authority.

## Accepted immutable V5 pair

Only this final pair is accepted:

- Proposal:
  `artifacts/website-operator/20260730T094627Z-investor-copy-governance-application-proposal-v5.json`
  - `CDCC9AB0C38338EB57EDF416ECF9CE52ED3B448C32259EF7190AE0CEAF796897`
- Validation:
  `artifacts/website-operator/20260730T094627Z-investor-copy-governance-application-proposal-validation-v5.json`
  - `A8BB51803E8A4F476A0C35C09C427D5AC6D0C7C42E147730213F6E9D4343340A`

All four earlier pairs remain immutable evidence but are rejected and not
applicable:

| Generation | Proposal / validation | Reason for rejection |
| --- | --- | --- |
| V1 | `F9061D2C2E21C4BF201D2108B931346D19945D2658C78C65ACDE5DB16B3CE072` / `D1FF5A70C0DBC8D59939705539C10395155D12F6AA310D94BCA334886326B6E7` | `incomplete-source-and-feedback-bindings` |
| V2 | `5111F351D1EAEEAD2E57E4DA372300F5614674920AACD406EE2CA27873A70DCF` / `BDFC1687BB2729ADD52FE9FA52B5531A0197B08A8D04A575EE654D7984EB6D79` | `incomplete-three-file-authority-and-supersession-language` |
| V3 | `73C53FD9E0087BA371876FFDAB02CF47E980A9472A6F4D656B4761C5E7F317BD` / `538CD6ED13688039C69DDF2A675165E99268B258A86F6029DB48482A7B1E7613` | `ambiguous-claim-route-scope` |
| V4 | `EB1F8FDAEB6CF5F314502FAAC2ECC46A5AB7D21BE5CB21D1E111FB9873E81448` / `D3F2E10DAC7D2E7182DD2D362B2035A6A4FF7E120194978BC4A64D866438FE5F` | `multi-sentence-permitted-wording-not-renderable-as-one-hash-bound-surface` |

The module rereads all eight earlier artifact hashes and requires these exact
supersession reasons. A decision bound to V1, V2, V3, or V4 is rejected.

## Exact three-file delta

| Path | Before SHA-256 | Proposed SHA-256 |
| --- | --- | --- |
| `data/website_operator/public_claim_evidence_register.v1.json` | `78032392BD3ECED2C5C9B294415AD6D2C6380FF903F7E43844C191AFD99C99A7` | `3D24208BB40CCFFC42B9EC70FA46C9226B8FD1B8363A767FC6D5E757C78959BF` |
| `data/website_operator/design_stakeholder_feedback.v1.json` | `A9DC7F847B926FF7E762A0F01EC58357D084624F05D5529E4A9596A96EF5C4DE` | `28D4F56F87A3133C2A2871303B00BFD0B5A0FAF8CBD71CC6C19034C2E4AAD2E9` |
| `data/website_operator/investor_site_design_brief.v1.json` | `6BCD1A422A5697CDA7FD94DC1AA8CA428050ABF2F21203460A11D3BD3D794046` | `FDEB5C0070FDFDE4FDC0832852E278D81E63F11C700843878709E6B2565D953C` |

The V5 correction preserves the exact V1 base delta and the source, route,
stakeholder, and design-brief bindings proven by V4. It then adds the one
source-backed sentence `One evidence OS.` to both `permitted_wording` and
`source.evidence_texts` of claim `aureon-evidence-os-positioning`. The source is
`website/projects/index.html`, SHA-256
`5D75CF500C4259CC9DCF504A98456034CE03C22080FD4EDB7F4A6C356D7CD893`,
at `meta[property="og:title"] and meta[name="twitter:title"]`, with exactly two
anchor occurrences. The claim-record SHA-256 changes exactly from
`E275C0C5751ED290A04EECF6DE5AD5B83F306C030FAD169026400CFC8C1AE5BE`
to
`B8CD9260CA76F0649FA5AB0B94E7D3E3EC674C28804C8FD51178437D5DD673B3`.

The stakeholder file changes only its claim-register SHA-256; its seven
controlled signals, evidence snapshot, and authority remain unchanged. The
brief adds the exact `projects-positioning` public source input and binds the
proposed claim-register and stakeholder-feedback hashes.

The full shadow replay must report:

- public claims: 16/16 pass and zero errors;
- stakeholder feedback: 6/6 checks and seven signal capsules;
- design brief: 17/17 checks, nine source inputs, and 18 claim capsules;
- investor-copy quality: zero findings, blockers, and warnings;
- public claim surface: 6/6 checks and zero invalid or unsafe non-claim
  surfaces;
- investor route capsule:
  `608B4AA3CF3B3A6909FD24DA370BF0C76346E81A41C55BE41531B62EEA56EEDA`;
- satisfied concepts: `commercial-wedge`, `company-category`, `human-control`.

## Separate owner decision

The tool never creates or edits an owner decision. Gary Leckey must supply one
immutable, single-link JSON file directly under
`artifacts/website-operator/owner-decisions/`. It must use schema
`aureon.investor-copy-governance-owner-decision.v1`, be no more than 24 hours
old, not be materially future-dated, and bind the exact V5 paths and hashes.
Its `decided_at` timestamp must be at or after the V5 validation timestamp,
`2026-07-30T09:47:30Z`.
The strict ASCII filename must be exactly `<decision_id>.json`; alternate data
streams, reserved names, links, and reparse points are rejected. The bytes must
be canonical UTF-8, LF-only, two-space-indented JSON with one final newline.
A UTF-8 BOM, a filename that does not match the decision id, duplicate keys,
`NaN`, and `Infinity` are rejected at every nesting level.

The only approving state is `approve-exact-governance-delta`. A valid `reject`
or `request-revision` decision causes no canonical change. General system
access, chat approval, or a decision that predates validation is not approval
under this contract; it is not an approval.

The acknowledgement object must be exactly:

```json
{
  "governance_files": [
    "data/website_operator/public_claim_evidence_register.v1.json",
    "data/website_operator/design_stakeholder_feedback.v1.json",
    "data/website_operator/investor_site_design_brief.v1.json"
  ],
  "no_policy_change": true,
  "no_website_change": true,
  "no_candidate_or_package_authority": true,
  "no_release_or_deployment_authority": true,
  "v1_through_v4_superseded_and_rejected": true,
  "sentence_level_evidence_os_wording": "One evidence OS."
}
```

The exact owner-decision wording template is below. This is deliberately a
template, not a decision: the owner must choose the decision state and create
the immutable file. Replace both angle-bracket placeholders; do not save them
literally. For approval, the `decision` value must remain exactly
`approve-exact-governance-delta`.

```json
{
  "schema": "aureon.investor-copy-governance-owner-decision.v1",
  "decision_id": "<decision_id>",
  "decided_at": "<owner-issued UTC timestamp at or after 2026-07-30T09:47:30Z>",
  "owner": "Gary Leckey",
  "decision": "approve-exact-governance-delta",
  "proposal": {
    "path": "artifacts/website-operator/20260730T094627Z-investor-copy-governance-application-proposal-v5.json",
    "sha256": "CDCC9AB0C38338EB57EDF416ECF9CE52ED3B448C32259EF7190AE0CEAF796897"
  },
  "validation": {
    "path": "artifacts/website-operator/20260730T094627Z-investor-copy-governance-application-proposal-validation-v5.json",
    "sha256": "A8BB51803E8A4F476A0C35C09C427D5AC6D0C7C42E147730213F6E9D4343340A"
  },
  "acknowledgements": {
    "governance_files": [
      "data/website_operator/public_claim_evidence_register.v1.json",
      "data/website_operator/design_stakeholder_feedback.v1.json",
      "data/website_operator/investor_site_design_brief.v1.json"
    ],
    "no_policy_change": true,
    "no_website_change": true,
    "no_candidate_or_package_authority": true,
    "no_release_or_deployment_authority": true,
    "v1_through_v4_superseded_and_rejected": true,
    "sentence_level_evidence_os_wording": "One evidence OS."
  }
}
```

## Read-only planning

Planning rehashes the decision, the V5 pair, all superseded artifacts, canonical
inputs, policy, target HTML, design-cycle receipt, and public source inputs. It
reconstructs all three exact byte streams and runs full audits in a temporary
shadow repository:

```powershell
python -m aureon.operator.design_investor_copy_governance `
  --decision artifacts/website-operator/owner-decisions/<decision_id>.json
```

`--as-of` is available only for deterministic read-only verification. A
passing plan remains non-authoritative and changes nothing.
It does not apply anything.

## Explicit application and recovery

Application requires `--apply`; mutating use of `--as-of` is rejected so an
old decision cannot be replayed against a historical clock:

```powershell
python -m aureon.operator.design_investor_copy_governance `
  --decision artifacts/website-operator/owner-decisions/<decision_id>.json `
  --apply
```

Before the first canonical replacement, the module creates a cooperative lock
and a same-volume durable journal under `data/website_operator/`. The journal
contains exact before and after images, their hashes, approval bindings, and
the expected immutable application-receipt hash. Progress moves through:

`PREPARING -> PREPARED -> COMMITTING -> VALIDATING -> VALIDATED -> receipt -> COMMITTED`

The application receipt is the commit marker:

- without the exact receipt, recovery restores every transaction-owned after
  image from the exact before backups;
- with all three exact after images and the exact receipt, recovery completes
  the committed transaction;
- an unexpected hash is preserved, blocks further work, and is never
  overwritten by recovery.

Readers refuse a pending journal. A dead writer is recovered on the next
explicit application or by
`recover_incomplete_investor_copy_governance_transaction`. Recovery is
idempotent and writes a privacy-safe immutable recovery receipt under
`artifacts/website-operator/copy-governance-recoveries/`.

This is recoverable cooperative transaction handling, not filesystem-level
multi-file atomicity against non-cooperating writers or sudden storage failure.
The per-file replacements are atomic on the same volume, while the journal and
read-back checks make interrupted multi-file progress repairable. If the exact
lock or journal cannot be cleaned, the result is
`applied-governance-maintenance-required`; the command does not report a plain
successful exit.

PID reuse can conservatively leave a dead writer reported as active if the
operating system has already assigned that PID to a different process. This is
a fail-closed availability limitation: the transaction remains intact for
manual recovery after process identity is confirmed, rather than being deleted
on age alone.

The application and recovery receipts remain governance-only. Website
candidate creation, review, packaging, owner release approval, backup,
deployment, and live read-back are separate WebsiteOperator gates.
