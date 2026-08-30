"""The self-knowledge organ: grounded, sourced, and silent where it does not know.

Every test builds its own fake repository in ``tmp_path``. The company in these
fixtures does not exist — that is the point. If the reader ever returned the
real company's details from a tmp_path repo, or invented a plausible answer for
a document that is not there, these tests fail.

Nothing here touches the network, the live repository, or the environment.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from aureon.identity import Identity, SelfKnowledge, SourcedFact, read_identity
from aureon.identity import reader as reader_module
from aureon.identity import schemas as schemas_module
from aureon.identity.reader import (
    AGENT_GUIDE_DOC,
    APPLICANT_JSON,
    CHARTER_DOC,
    COMPANY_DOC,
    CONFIDENCE_PROSE,
    CONFIDENCE_STRUCTURED,
    CONFIDENCE_TABLE,
    README_DOC,
    SYNTHESIS_DOC,
)

# A company that does not exist, so a passing test cannot be a memorised answer.
ENTITY = "Bramblewick Instruments Ltd"
NUMBER = "ZZ123456"
OFFICE = "9 Kestrel Row, Fakeborough, FK1 9ZZ"
CONTACT = "Marisol Quaye"

COMPANY_MD = f"""# {ENTITY}

## Company

| | |
|---|---|
| **Registered name** | {ENTITY} |
| **Company number** | {NUMBER} (Fake Register, Nowhere) |
| **Registered office** | 9 Kestrel Row, Fakeborough |
| **Director** | {CONTACT} |
| **Website** | [example.invalid](https://example.invalid) |

## What the company builds

Bench instruments.
"""

CHARTER_MD = """# WORKSHOP CHARTER

## 1. MISSION

I keep the workshop's records honest and its instruments
calibrated. My standing mission, in order:

1. Calibrate the long-baseline interferometer before each run.
2. Publish every measurement with its uncertainty
   attached, never rounded away.
3. Refuse to state a result the data does not carry.

## 2. SOMETHING ELSE

4. This numbered item is not a mission goal.
"""

README_MD = """# Bramblewick OS

## What Bramblewick OS is

Bramblewick OS is a **bench control layer** for a small optics workshop.
It logs every calibration so a reviewer can see what was measured.

## Something else

Not the purpose.
"""

SYNTHESIS_MD = """# The Synthesis

## What This Repository Is

<!-- editorial -->
This repository is the synthesis account of the bench control layer.
<!-- /editorial -->
"""

AGENT_GUIDE_MD = """# Guide

## What this repository is (30 seconds)

A guide-level account of the bench control layer, written for assistants.
"""


def _applicant(**overrides: str) -> dict:
    block = {
        "legal_entity": ENTITY,
        "company_number": NUMBER,
        "registered_office": OFFICE,
        "lead_contact": CONTACT,
        "email": "ops@example.invalid",
    }
    block.update(overrides)
    return {"schema_version": "fake-v1", "operator": "test", "applicant": block}


def build_repo(root: Path, **docs: str | None) -> Path:
    """Write a fake repository. Pass ``doc=None`` to leave that file out."""
    content: dict[str, str | None] = {
        COMPANY_DOC: COMPANY_MD,
        CHARTER_DOC: CHARTER_MD,
        README_DOC: README_MD,
        SYNTHESIS_DOC: SYNTHESIS_MD,
        AGENT_GUIDE_DOC: AGENT_GUIDE_MD,
        APPLICANT_JSON: json.dumps(_applicant()),
    }
    content.update(docs)
    for relative, text in content.items():
        if text is None:
            continue
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return build_repo(tmp_path / "repo")


# ── she answers from the documents, not from memory ──────────────────────────


def test_reads_the_company_from_the_applicant_record(repo: Path):
    knowledge = read_identity(repo)
    assert knowledge.available is True
    assert knowledge.identity.legal_entity.value == ENTITY
    assert knowledge.identity.company_number.value == NUMBER
    assert knowledge.identity.registered_office.value == OFFICE
    assert knowledge.identity.lead_contact.value == CONTACT


def test_mission_and_goals_come_from_the_charter(repo: Path):
    knowledge = read_identity(repo)
    assert "keep the workshop's records honest" in knowledge.identity.mission.value
    # The wrapped second line is rejoined, and the list stops at the next section.
    assert [g.value for g in knowledge.goals] == [
        "Calibrate the long-baseline interferometer before each run.",
        "Publish every measurement with its uncertainty attached, never rounded away.",
        "Refuse to state a result the data does not carry.",
    ]


def test_purpose_is_read_from_the_readme(repo: Path):
    purpose = read_identity(repo).identity.purpose
    assert purpose.source_file == README_DOC
    assert "bench control layer" in purpose.value


# ── provenance is attached to every fact ─────────────────────────────────────


def test_every_fact_carries_a_source_file_that_exists(repo: Path):
    knowledge = read_identity(repo)
    assert knowledge.facts, "expected the fake repo to yield facts"
    for fact in knowledge.facts:
        assert isinstance(fact, SourcedFact)
        assert fact.source_file, f"{fact.value!r} has no provenance"
        assert (repo / fact.source_file).is_file()


def test_every_goal_carries_its_source(repo: Path):
    for goal in read_identity(repo).goals:
        assert goal.source_file == CHARTER_DOC
        assert 0.0 < goal.confidence <= schemas_module.MAX_CONFIDENCE


def test_no_fact_claims_certainty(repo: Path):
    # Nothing here is verified against an external register, so nothing is 1.0.
    for fact in read_identity(repo).facts:
        assert 0.0 < fact.confidence <= schemas_module.MAX_CONFIDENCE < 1.0


def test_a_sourced_fact_cannot_exist_without_a_source():
    with pytest.raises(TypeError):
        SourcedFact(value="something true")  # type: ignore[call-arg]


# ── absence yields blockers, never a guess ───────────────────────────────────


def test_an_empty_root_invents_nothing(tmp_path: Path):
    knowledge = read_identity(tmp_path)
    assert knowledge.available is False
    assert knowledge.identity.known == {}
    assert knowledge.goals == ()
    assert set(knowledge.identity.missing) == set(Identity.FIELDS)
    assert knowledge.blocker


def test_a_nonexistent_root_does_not_raise(tmp_path: Path):
    knowledge = read_identity(tmp_path / "no" / "such" / "place")
    assert knowledge.available is False
    assert knowledge.identity.legal_entity is None


def test_the_reader_never_reaches_outside_the_given_root(tmp_path: Path):
    """The lesson from grants_dir: a caller who names a root gets that root.

    A fallback to the real repository would make an empty fixture answer with
    live company data — the exact action-at-a-distance that hides faults.
    """
    knowledge = read_identity(tmp_path)
    assert knowledge.root == str(tmp_path)
    assert knowledge.sources_read == ()
    assert knowledge.identity.grounded is False


def test_missing_documents_are_named_in_the_blocker(tmp_path: Path):
    repo = build_repo(tmp_path / "repo", **{COMPANY_DOC: None, APPLICANT_JSON: None})
    knowledge = read_identity(repo)
    assert knowledge.identity.legal_entity is None
    assert COMPANY_DOC in knowledge.blocker
    assert APPLICANT_JSON in knowledge.blocker
    # The blocker says which field is unanswerable and where it was looked for.
    assert any(b.startswith("legal_entity: no source found") for b in knowledge.blockers)
    # ... while the fields that *were* sourced are still answered.
    assert knowledge.identity.mission is not None
    assert knowledge.available is True


def test_a_charter_without_a_mission_section_yields_no_invented_goals(tmp_path: Path):
    repo = build_repo(tmp_path / "repo", **{CHARTER_DOC: "# Charter\n\n## Notes\n\nNothing.\n"})
    knowledge = read_identity(repo)
    assert knowledge.goals == ()
    assert knowledge.identity.mission is None
    assert any("goals: no source found" in b for b in knowledge.blockers)


def test_malformed_json_is_reported_not_raised(tmp_path: Path):
    repo = build_repo(tmp_path / "repo", **{APPLICANT_JSON: "{not json at all"})
    knowledge = read_identity(repo)
    assert any("not valid JSON" in b for b in knowledge.blockers)
    assert APPLICANT_JSON not in knowledge.sources_read
    # The markdown record still answers, at the lower table confidence.
    assert knowledge.identity.legal_entity.source_file == COMPANY_DOC


def test_an_applicant_block_of_the_wrong_shape_is_tolerated(tmp_path: Path):
    repo = build_repo(
        tmp_path / "repo",
        **{APPLICANT_JSON: json.dumps({"applicant": ["not", "a", "record"]})},
    )
    knowledge = read_identity(repo)
    assert any("no applicant record" in b for b in knowledge.blockers)
    assert knowledge.identity.legal_entity.source_file == COMPANY_DOC


def test_an_empty_document_is_a_blocker_not_a_silent_pass(tmp_path: Path):
    repo = build_repo(tmp_path / "repo", **{README_DOC: "   \n\n"})
    knowledge = read_identity(repo)
    assert any(b.startswith(f"{README_DOC}: empty") for b in knowledge.blockers)
    assert README_DOC not in knowledge.sources_read


# ── two documents, one truth ─────────────────────────────────────────────────


def test_the_structured_record_outranks_the_markdown_table(repo: Path):
    entity = read_identity(repo).identity.legal_entity
    assert entity.source_file == APPLICANT_JSON
    assert entity.confidence > CONFIDENCE_TABLE


def test_the_markdown_table_answers_alone_when_the_record_is_absent(tmp_path: Path):
    repo = build_repo(tmp_path / "repo", **{APPLICANT_JSON: None})
    identity = read_identity(repo).identity
    assert identity.legal_entity.source_file == COMPANY_DOC
    assert identity.legal_entity.confidence == pytest.approx(CONFIDENCE_TABLE)
    assert identity.lead_contact.value == CONTACT


def test_agreeing_documents_corroborate_and_raise_confidence(repo: Path):
    entity = read_identity(repo).identity.legal_entity
    assert entity.corroborated_by == (COMPANY_DOC,)
    assert entity.conflicts == ()
    assert entity.confidence > CONFIDENCE_STRUCTURED


def test_a_less_specific_restatement_counts_as_agreement(repo: Path):
    # JSON says "ZZ123456"; the table says "ZZ123456 (Fake Register, Nowhere)".
    number = read_identity(repo).identity.company_number
    assert number.value == NUMBER
    assert number.corroborated_by == (COMPANY_DOC,)


def test_disagreeing_documents_are_surfaced_not_silently_resolved(tmp_path: Path):
    clashing = COMPANY_MD.replace(
        "| **Registered office** | 9 Kestrel Row, Fakeborough |",
        "| **Registered office** | 400 Elsewhere Street, Othertown |",
    )
    repo = build_repo(tmp_path / "repo", **{COMPANY_DOC: clashing})
    office = read_identity(repo).identity.registered_office
    assert office.value == OFFICE  # the higher-priority record wins the field
    assert office.conflicts == ((COMPANY_DOC, "400 Elsewhere Street, Othertown"),)
    assert office.confidence < CONFIDENCE_STRUCTURED  # and she is less sure of it
    assert "disputed by" in office.cite()


def test_prose_sources_are_not_compared_as_if_they_were_facts(repo: Path):
    """Three documents describe the purpose in three ways; that is not a conflict."""
    purpose = read_identity(repo).identity.purpose
    assert purpose.conflicts == ()
    assert purpose.corroborated_by == ()
    assert purpose.confidence == pytest.approx(CONFIDENCE_PROSE)


def test_purpose_falls_back_through_the_document_chain(tmp_path: Path):
    without_readme = build_repo(tmp_path / "a", **{README_DOC: None})
    assert read_identity(without_readme).identity.purpose.source_file == SYNTHESIS_DOC

    only_guide = build_repo(tmp_path / "b", **{README_DOC: None, SYNTHESIS_DOC: None})
    assert read_identity(only_guide).identity.purpose.source_file == AGENT_GUIDE_DOC

    none_at_all = build_repo(
        tmp_path / "c", **{README_DOC: None, SYNTHESIS_DOC: None, AGENT_GUIDE_DOC: None}
    )
    knowledge = read_identity(none_at_all)
    assert knowledge.identity.purpose is None
    assert any(b.startswith("purpose: no source found") for b in knowledge.blockers)


# ── she can say it out loud, and say what she cannot ─────────────────────────


def test_narration_cites_every_fact_it_states(repo: Path):
    spoken = read_identity(repo).narrate()
    assert ENTITY in spoken and NUMBER in spoken and CONTACT in spoken
    assert APPLICANT_JSON in spoken and CHARTER_DOC in spoken
    for goal in read_identity(repo).goals:
        assert goal.value in spoken


def test_narration_states_unknowns_as_unknown(tmp_path: Path):
    spoken = read_identity(tmp_path).narrate()
    assert spoken.count("unknown") >= 4
    assert "WHAT I CANNOT ANSWER, AND WHY" in spoken
    # Nothing was found, so nothing may be asserted.
    assert ENTITY not in spoken and NUMBER not in spoken


def test_to_dict_is_json_serialisable_and_keeps_provenance(repo: Path):
    payload = read_identity(repo).to_dict()
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped["identity"]["legal_entity"]["source_file"] == APPLICANT_JSON
    assert round_tripped["identity"]["legal_entity"]["value"] == ENTITY
    assert all(g["source_file"] == CHARTER_DOC for g in round_tripped["goals"])


def test_sources_read_lists_only_documents_that_were_actually_read(tmp_path: Path):
    repo = build_repo(tmp_path / "repo", **{SYNTHESIS_DOC: None})
    knowledge = read_identity(repo)
    assert SYNTHESIS_DOC not in knowledge.sources_read
    for relative in knowledge.sources_read:
        assert (repo / relative).is_file()


def test_self_knowledge_is_immutable(repo: Path):
    knowledge = read_identity(repo)
    with pytest.raises(dataclasses.FrozenInstanceError):
        knowledge.identity.legal_entity = None  # type: ignore[misc]


def test_an_unavailable_read_still_returns_a_readable_identity(tmp_path: Path):
    knowledge = read_identity(tmp_path)
    assert isinstance(knowledge, SelfKnowledge)
    assert isinstance(knowledge.identity, Identity)
    # A caller reading a field gets an honest absence, not an AttributeError.
    assert knowledge.identity.purpose is None


# ── the organ holds no answers of its own ────────────────────────────────────


@pytest.mark.parametrize(
    "token",
    ["NI696693", "R&A Consulting", "Gary", "Quadrant", "Zorza", "Belfast", "Leckey"],
)
def test_no_real_identity_is_written_into_the_source(token: str):
    """The answers must live in the documents, never in this package.

    If a detail is pasted into the code, the organ stops reading and starts
    reciting — and it would keep reciting after the underlying record changed.
    Every module in the package is scanned, so a future addition is covered too.
    """
    package = Path(reader_module.__file__).parent
    modules = sorted(package.glob("*.py"))
    assert len(modules) >= 3, "expected __init__, reader and schemas to be scanned"
    for path in modules:
        assert token not in path.read_text(encoding="utf-8"), f"{path.name} hardcodes {token!r}"
