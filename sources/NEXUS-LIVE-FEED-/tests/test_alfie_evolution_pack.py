from pathlib import Path

from planning import EvolutionPack, load_evolution_pack


def load_pack() -> EvolutionPack:
    repo_root = Path(__file__).resolve().parents[1]
    return load_evolution_pack(repo_root / "planning" / "alfie_evolution_pack.json")


def test_metadata_and_sequence():
    pack = load_pack()
    assert pack.name == "ALFIE Evolution Pack"
    assert pack.version == "1.0.0"
    assert pack.entry == "alfie_init_sequence"
    assert pack.generated.tzinfo is not None

    sequence_ids = [layer.id for layer in pack.iter_sequence_layers()]
    assert sequence_ids[0] == "identity"
    assert sequence_ids[-1] == "scenarios"

    assert pack.validate() == []


def test_phase_grouping_and_required_optional_layers():
    pack = load_pack()
    phases = pack.layers_by_phase()

    assert [layer.id for layer in phases[0]] == [
        "identity",
        "hnt_foundation",
        "tensor_spec",
    ]
    assert {layer.id for layer in phases[2]} == {
        "field_interface",
        "auris_codex",
        "prime_anchor",
    }

    required_ids = [layer.id for layer in pack.required_layers()]
    assert required_ids == [
        "identity",
        "hnt_foundation",
        "tensor_spec",
        "symbolic_compiler",
        "sandbox_flow",
        "ethics_sigma",
    ]

    optional_ids = [layer.id for layer in pack.optional_layers()]
    assert optional_ids == [
        "field_interface",
        "auris_codex",
        "prime_anchor",
        "scenarios",
    ]


def test_missing_files_detection(tmp_path):
    pack = load_pack()
    base = tmp_path

    # Create only the required layer files
    for layer in pack.required_layers():
        resolved = layer.resolved_path(base)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(layer.id)

    missing_ids = [layer.id for layer in pack.missing_files(base)]
    assert missing_ids == [
        "field_interface",
        "auris_codex",
        "prime_anchor",
        "scenarios",
    ]

