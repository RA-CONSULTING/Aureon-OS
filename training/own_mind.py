"""One closed cycle of Aureon's own mind.

No Ollama, no hosted API, no borrowed weights. The cycle is:

1. The Aureon checkpoint scores its own prompt. Entropy and top-1 probability
   are measurements of this model, not of an outside system.
2. Those measurements fill the vault fields the nine Auris nodes actually read.
   Fields this cycle did not measure stay unset, and the receipt says so.
3. AurisMetacognition votes. The consensus sets how the same checkpoint is
   allowed to continue: a stabilising vote decodes greedy and short, a rally
   vote samples hotter and longer.
4. The continuation is this model's tokens. The receipt stores the vote, the
   measurements, and the text together.

    python own_mind.py --self-test
    python own_mind.py --model runs/aureon-7b-v65k/hf
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path


AURIS_CANDIDATES = (
    Path("/projects/u6vs/hnc-organism/aureon/vault/auris_metacognition.py"),
    Path(__file__).resolve().parents[1] / "aureon" / "vault" / "auris_metacognition.py",
)

UNMEASURED = ("last_casimir_force", "dominant_frequency_hz")


def load_auris():
    for path in AURIS_CANDIDATES:
        if path.is_file():
            spec = importlib.util.spec_from_file_location("auris_metacognition", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module, str(path)
    raise FileNotFoundError("auris_metacognition.py not found in " + ", ".join(map(str, AURIS_CANDIDATES)))


class MindVault:
    """The slices Auris nodes read. Only measured fields are set."""

    def __init__(self, cortex_snapshot, **fields):
        self.cortex_snapshot = dict(cortex_snapshot)
        self.__dict__.update(fields)

    def __len__(self):
        return len(self.cortex_snapshot)


def summarise(entropies, top1, vocab_size):
    if not entropies or len(entropies) != len(top1):
        raise ValueError("entropies and top1 must be the same non-empty length")
    n = len(entropies)
    mid = max(n // 2, 1)
    second = max(n - mid, 1)
    uniform = math.log(vocab_size)
    bands = {"delta": 0, "alpha": 0, "gamma": 0}
    for entropy in entropies:
        ratio = entropy / uniform
        if ratio > 0.8:
            bands["delta"] += 1
        elif ratio < 0.3:
            bands["gamma"] += 1
        else:
            bands["alpha"] += 1
    cortex = {name: count / n for name, count in bands.items()}
    dominant = max(cortex, key=cortex.get)
    chakra = {"delta": "foundation", "alpha": "connection", "gamma": "love"}[dominant]
    return {
        "positions": n,
        "vocab_size": vocab_size,
        "uniform_entropy_nats": uniform,
        "mean_entropy_nats": sum(entropies) / n,
        "mean_top1": sum(top1) / n,
        "top1_slope": (sum(top1[mid:]) / second) - (sum(top1[:mid]) / mid),
        "share_top1_above_0.05": sum(1 for p in top1 if p > 0.05) / n,
        "cortex_snapshot": cortex,
        "dominant_band": dominant,
        "dominant_chakra": chakra,
    }


def vault_from_summary(summary):
    """Map model measurements onto the vault fields the nodes inspect.

    last_lambda_t is the change in the model's own top-1 probability from the
    first half of the prompt to the second. love_amplitude is mean top-1
    probability. gratitude_score is the share of positions where the model
    assigns more than 0.05 to its favourite token. The cortex bands are the
    share of positions whose entropy is flat (delta), middling (alpha), or
    peaked (gamma) relative to a uniform distribution over the vocab.
    """
    return MindVault(
        cortex_snapshot=summary["cortex_snapshot"],
        last_lambda_t=summary["top1_slope"],
        love_amplitude=summary["mean_top1"],
        gratitude_score=summary["share_top1_above_0.05"],
        dominant_chakra=summary["dominant_chakra"],
        max_size=10000,
    )


def decode_policy(consensus):
    """The vote controls this model's decoder. It does not call another model."""
    if consensus in ("STABILISE", "SELL"):
        return {"do_sample": False, "temperature": 0.0, "max_new_tokens": 24}
    if consensus == "RALLY":
        return {"do_sample": True, "temperature": 1.0, "max_new_tokens": 64}
    if consensus == "BUY":
        return {"do_sample": True, "temperature": 0.8, "max_new_tokens": 64}
    return {"do_sample": True, "temperature": 0.7, "max_new_tokens": 48}


def self_test():
    module, path = load_auris()
    vocab = 65536
    uniform = math.log(vocab)
    flat = summarise([uniform] * 8, [1.0 / vocab] * 8, vocab)
    flat_vote = module.AurisMetacognition().vote(vault_from_summary(flat))
    peaked = summarise([0.1] * 8, [0.9] * 8, vocab)
    peaked_vote = module.AurisMetacognition().vote(vault_from_summary(peaked))
    if flat_vote.total != 9 or peaked_vote.total != 9:
        raise SystemExit("Auris did not return nine votes")
    if flat["dominant_band"] != "delta" or peaked["dominant_band"] != "gamma":
        raise SystemExit("entropy bands did not separate flat from peaked")
    flat_nodes = {v.node: v.verdict for v in flat_vote.per_node_votes}
    peaked_nodes = {v.node: v.verdict for v in peaked_vote.per_node_votes}
    moved = [name for name in flat_nodes if flat_nodes[name] != peaked_nodes[name]]
    if not moved:
        raise SystemExit("no Auris node changed its vote between flat and peaked")
    if decode_policy("STABILISE") == decode_policy("BUY"):
        raise SystemExit("decode policy ignores the vote")
    print(json.dumps({
        "auris": path,
        "flat_consensus": flat_vote.consensus,
        "flat_agreeing": flat_vote.agreeing,
        "peaked_consensus": peaked_vote.consensus,
        "peaked_agreeing": peaked_vote.agreeing,
        "nodes_that_moved": moved,
        "policy_stabilise": decode_policy("STABILISE"),
        "policy_buy": decode_policy("BUY"),
        "unmeasured": list(UNMEASURED),
    }, indent=2))
    return 0


def measure_prompt(model, ids):
    import torch
    with torch.no_grad():
        logits = model(input_ids=ids).logits[0, :-1]
        probs = torch.softmax(logits.float(), dim=-1)
        entropy = -(probs * probs.clamp_min(1e-12).log()).sum(dim=-1)
        top1 = probs.max(dim=-1).values
    return summarise(entropy.tolist(), top1.tolist(), int(probs.shape[-1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--prompt", default="Question: What should Aureon do next, and why?\nThink:\n")
    ap.add_argument("--out", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.model:
        ap.error("--model is required unless --self-test")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    module, auris_path = load_auris()
    model_dir = Path(args.model)
    export_meta = {}
    export_path = model_dir / "aureon_export.json"
    if export_path.is_file():
        export_meta = json.loads(export_path.read_text(encoding="utf-8"))

    tok = AutoTokenizer.from_pretrained(model_dir)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        model_dir, dtype=torch.bfloat16, attn_implementation="sdpa"
    ).to(device).eval()
    ids = tok(args.prompt, return_tensors="pt").input_ids.to(device)
    summary = measure_prompt(model, ids)
    vote = module.AurisMetacognition().vote(vault_from_summary(summary))
    policy = decode_policy(vote.consensus)

    gen_kwargs = {
        "max_new_tokens": policy["max_new_tokens"],
        "do_sample": policy["do_sample"],
        "pad_token_id": tok.eos_token_id,
    }
    if policy["do_sample"]:
        gen_kwargs["temperature"] = policy["temperature"]
        gen_kwargs["top_p"] = 0.95
    with torch.no_grad():
        generated = model.generate(ids, **gen_kwargs)
    text = tok.decode(generated[0][ids.shape[1]:], skip_special_tokens=True)

    receipt = {
        "model": str(model_dir),
        "export": export_meta,
        "params": sum(p.numel() for p in model.parameters()),
        "vocab_size": int(model.config.vocab_size),
        "device": device,
        "prompt": args.prompt,
        "measurements": summary,
        "unmeasured_vault_fields": list(UNMEASURED),
        "auris_source": auris_path,
        "consensus": vote.consensus,
        "confidence": vote.confidence,
        "agreeing": vote.agreeing,
        "total": vote.total,
        "lighthouse_cleared": vote.lighthouse_cleared,
        "votes": [
            {"node": v.node, "verdict": v.verdict, "confidence": v.confidence, "reasoning": v.reasoning}
            for v in vote.per_node_votes
        ],
        "decode_policy": policy,
        "continuation": text,
        "outside_model": None,
    }
    rendered = json.dumps(receipt, indent=2)
    print(rendered, flush=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
