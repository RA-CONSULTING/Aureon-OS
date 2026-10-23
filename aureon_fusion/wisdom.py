"""🕯 WISDOM — the deep-knowledge layer of the fused organism.

One resident module, zero network, stdlib + upstream read-only imports:

  wisdom banks   — the 13 upstream civilization banks
                   (aureon-os-upstream/wisdom_data/*.json: celtic, norse,
                   chinese, egyptian, aztec, mayan, hindu, pythagorean,
                   warfare, plantagenet, ghost_dance, mogollon + friends),
                   read lazily, never written.
  book recall    — 'The Bhoys Eyes — Part 1' (Belfast 1982, Falls Road),
                   extracted from the upstream .docx into
                   aureon_fusion/knowledge/bhoys_eyes_part_1.md and served
                   through a small dedicated ResearchCorpusIndex rooted at
                   aureon_fusion/knowledge/ (cache in fusion state).
  decoders       — read-only summaries of the upstream decode corpora:
                   emerald_spec (_VERSE_CATALOG / _EARTH_ASPECT_TABLE /
                   _IONO_LAYER_TABLE), celtic_ogham (_FEDA, 25 feda),
                   iching_decoder (_HEXAGRAM_CATALOG, 64 hexagrams),
                   maeshowe_seer_decode (_RUNE_TABLE, 24 runes).
  bhoys quotes   — aureon.wisdom.bhoys_wisdom (victory / patience /
                   resilience / strategy / unity / legacy), imported lazily
                   behind the suppression env with a source-parse fallback.
  seed           — one-way fold of the banks + decoder tables into the live
                   KnowledgeDataset (aureon_fusion/state/queen_mind/
                   knowledge_dataset.json) as tagged fragments. Dedups on
                   text; re-runs add nothing.

CLI:
    python -m aureon_fusion.wisdom banks
    python -m aureon_fusion.wisdom recall <domain> [query] [--limit N]
    python -m aureon_fusion.wisdom quote [category]
    python -m aureon_fusion.wisdom decoders [emerald|ogham|iching|maeshowe]
    python -m aureon_fusion.wisdom book <query>
    python -m aureon_fusion.wisdom seed [--yes]

Import-safe: no upstream import at module import time (all lazy), no
network, no threads. Upstream repo is READ-ONLY from here.
"""
from __future__ import annotations

import ast
import json
import os
import random
import re
import sys
import time
import types
from pathlib import Path

# Script-or-module bootstrap: the registrar may launch this file directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aureon_fusion.paths import AUREON_UPSTREAM, AUREON_PKG, FUSION_STATE, WORKSPACE

# ── SUPPRESSION ENV — every upstream import through this module sees a
# suppressed, audited environment (mirrors aureon_fusion.queen_mind).
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

ORGAN_NAME = "wisdom"
MIND_DIR = FUSION_STATE / "queen_mind"
KNOWLEDGE_DIR = WORKSPACE / "aureon_fusion" / "knowledge"
BOOK_MD = KNOWLEDGE_DIR / "bhoys_eyes_part_1.md"
BOOK_INDEX_CACHE = MIND_DIR / "knowledge_corpus_index.json"
KNOWLEDGE_DATASET_PATH = MIND_DIR / "knowledge_dataset.json"
WISDOM_BANK_DIR = AUREON_UPSTREAM / "wisdom_data"
BHOYS_WISDOM_PY = AUREON_PKG / "wisdom" / "bhoys_wisdom.py"

# Per-persona recall domains, consumed by queen_mind's cycle. sero gets the
# felt-sense banks, the seer gets the decode corpora, lyra gets the Belfast
# book + pythagorean harmony, the queen gets the widest sweep.
PERSONA_DOMAINS = {
    "queen": ["celtic", "chinese", "egyptian", "norse"],
    "sero":  ["celtic", "warfare"],
    "seer":  ["maeshowe", "emerald", "iching"],
    "lyra":  ["pythagorean", "bhoys"],
}

# Knowledge-wave-2 domains (untapped assets): sero draws on the public
# symbolic codices + grants pipeline, the queen on the owner governance
# files (USER.md / MEMORY.md standing constraints), the seer on the
# intelligence package + whitepaper canon, lyra on substack + papers.
WAVE2_DOMAINS = {
    "queen": ["owner"],
    "sero":  ["codices", "grants"],
    "seer":  ["intelligence", "whitepapers"],
    "lyra":  ["substack", "papers"],
}

PUBLIC_DIR = AUREON_UPSTREAM / "public"
INTEL_DIR = AUREON_PKG / "intelligence"
GRANTS_PIPELINE = AUREON_UPSTREAM / "data/research/grants/pipeline.json"
SUBSTACK_DIR = WORKSPACE / "substack_output"
PAPERS_DIRS = (WORKSPACE / "research/papers", WORKSPACE / "zenodo_papers")
OWNER_FILES = (WORKSPACE / "USER.md", WORKSPACE / "MEMORY.md")
# Files under public/ that are app state, not symbolic codices.
_CODEX_SKIP = {"manifest.json", "experiment_manifest.json", "hive_state.json"}

_SEED_MARKER = "wisdom"
_BANKS: dict | None = None
_CODICES: dict | None = None
_INTEL: list | None = None
_BOOK_INDEX = None  # lazy ResearchCorpusIndex


# ─────────────────────────────── banks ─────────────────────────────────────

def _load_banks() -> dict:
    """Lazily load all wisdom banks (read-only). {bank_name: payload}."""
    global _BANKS
    if _BANKS is not None:
        return _BANKS
    banks: dict = {}
    if WISDOM_BANK_DIR.is_dir():
        for path in sorted(WISDOM_BANK_DIR.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            banks[path.stem] = payload
    _BANKS = banks
    return banks


def list_banks() -> list:
    """One row per bank: name, civilization, insights, principles, topics."""
    rows = []
    for name, payload in _load_banks().items():
        rows.append({
            "bank": name,
            "civilization": payload.get("civilization", name),
            "insights": len(payload.get("learned_insights") or []),
            "principles": len(payload.get("core_principles") or []),
            "topics": len(payload.get("topics") or []),
            "version": payload.get("version"),
        })
    return rows


def _bank_entries(bank: dict) -> list:
    """Flatten one bank into scored-able entries."""
    entries: list = []
    civ = str(bank.get("civilization") or "")
    for ins in bank.get("learned_insights") or []:
        content = str(ins.get("content") or "").strip()
        if content:
            entries.append({
                "kind": "insight",
                "civilization": civ or str(ins.get("civilization") or ""),
                "topic": str(ins.get("topic") or ""),
                "source": str(ins.get("source") or ""),
                "content": content,
            })
    for principle in bank.get("core_principles") or []:
        text = str(principle if isinstance(principle, str)
                   else principle.get("principle") or principle.get("content") or "").strip()
        if text:
            entries.append({"kind": "principle", "civilization": civ,
                            "topic": "", "source": "core_principles", "content": text})
    symbols = bank.get("symbols") or {}
    if isinstance(symbols, dict):
        for sym_name, sym_val in symbols.items():
            text = f"{sym_name}: {sym_val}".strip(": ")
            if text:
                entries.append({"kind": "symbol", "civilization": civ,
                                "topic": str(sym_name), "source": "symbols", "content": text})
    for topic in bank.get("topics") or []:
        content = str(topic.get("content") or "").strip()
        if content:
            entries.append({"kind": "topic", "civilization": civ,
                            "topic": str(topic.get("name") or ""),
                            "source": "topics", "content": content[:400]})
    return entries


def _match_bank(name: str, banks: dict) -> str | None:
    """Resolve a domain name to a bank key (fuzzy, case-insensitive)."""
    name_l = name.lower()
    aliases = {
        "greek": "pythagorean", "hellenic": "pythagorean", "harmony": "pythagorean",
        "maya": "mayan", "vikings": "norse", "norse": "norse",
        "celt": "celtic", "irish": "celtic", "gaelic": "celtic",
        "china": "chinese", "i_ching": "chinese", "iching": "chinese",
        "egypt": "egyptian", "kemet": "egyptian",
        "war": "warfare", "battle": "warfare", "siege": "warfare",
        "ancestral": "ghost_dance", "native": "ghost_dance",
        "belfast": "bhoys", "bhoy": "bhoys", "falls": "bhoys", "ira": "warfare",
    }
    name_l = aliases.get(name_l, name_l)
    for key in banks:
        if name_l == key.lower() or name_l in key.lower():
            return key
    for key, target in aliases.items():
        if name_l == key and target in banks:
            return target
    return None


def recall(domain: str, query: str | None = None, limit: int = 5) -> list:
    """Deep recall for a domain (+ optional query).

    Domains: wisdom-bank names (celtic, norse, …) plus the wave-2 domains
    codices / intelligence / substack / papers / grants / whitepapers /
    owner. Scoring: query-token overlap when a query is given; otherwise a
    stable rotation so successive cycles cite different rows.
    """
    name = re.sub(r"[^a-z]", "", domain.lower())
    if name in ("codex", "codices", "codex", "public", "symbols"):
        return _recall_codices(query, limit)
    if name in ("intelligence", "intel", "oracle", "oracles"):
        return _recall_intelligence(query, limit)
    if name in ("substack", "essays", "essay"):
        return _recall_prose(SUBSTACK_DIR.glob("*.md"), "substack", query, limit)
    if name in ("papers", "paper", "research", "zenodo"):
        files = []
        for d in PAPERS_DIRS:
            files.extend(sorted(d.glob("*.txt")))
        return _recall_prose(files, "papers", query, limit)
    if name in ("grants", "grant", "funding", "pipeline"):
        return _recall_grants(query, limit)
    if name in ("whitepapers", "whitepaper", "wp"):
        return _recall_whitepapers(query, limit)
    if name in ("owner", "user", "memory", "governance", "standing"):
        return owner_constraints(query=query, limit=limit)
    banks = _load_banks()
    key = _match_bank(domain, banks)
    if key is None:
        return []
    entries = _bank_entries(banks[key])
    if not entries:
        return []
    if query:
        tokens = set(re.findall(r"[a-z]{3,}", query.lower()))
        def score(e):
            hay = (e["content"] + " " + e["topic"]).lower()
            return sum(1 for t in tokens if t in hay)
        ranked = sorted(entries, key=score, reverse=True)
        top_score = score(ranked[0])
        if top_score <= 0:
            # Query matched nothing in this bank — rotate instead of citing
            # arbitrary top rows.
            return recall(domain, None, limit)
        picked = [e for e in ranked if score(e) == top_score]
        return picked[:limit]
    # No query: deterministic rotation so each call surfaces fresh rows.
    rng = random.Random(f"{key}:{len(entries)}")
    order = list(range(len(entries)))
    rng.shuffle(order)
    start = int(time.time() // 300) % len(order)   # re-pick every 5 minutes
    rotated = order[start:] + order[:start]
    return [entries[i] for i in rotated[:limit]]


# ─────────────────────── wave-2: codices ───────────────────────────────────

def _load_codices() -> dict:
    """Lazily load the public symbolic codices (read-only)."""
    global _CODICES
    if _CODICES is not None:
        return _CODICES
    codices: dict = {}
    for path in sorted(PUBLIC_DIR.glob("*.json")):
        if path.name in _CODEX_SKIP:
            continue
        try:
            codices[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    _CODICES = codices
    return codices


def list_codices() -> list:
    rows = []
    for name, payload in _load_codices().items():
        if isinstance(payload, dict):
            desc = str(payload.get("description") or payload.get("title") or "")
            size = len(payload)
        elif isinstance(payload, list):
            desc = ""
            size = len(payload)
        else:
            desc, size = "", 0
        rows.append({"codex": name, "entries": size, "description": desc[:120]})
    return rows


def codex(name: str) -> dict | None:
    """One codex payload by fuzzy name, or None."""
    name_l = re.sub(r"[^a-z0-9]", "", name.lower())
    codices = _load_codices()
    for key, payload in codices.items():
        if name_l == re.sub(r"[^a-z0-9]", "", key.lower()):
            return {"codex": key, "payload": payload}
    for key, payload in codices.items():
        if name_l in re.sub(r"[^a-z0-9]", "", key.lower()):
            return {"codex": key, "payload": payload}
    return None


def _recall_codices(query: str | None, limit: int) -> list:
    tokens = set(re.findall(r"[a-z]{3,}", (query or "").lower()))
    rows = []
    for key, payload in _load_codices().items():
        text = json.dumps(payload, ensure_ascii=False)
        if tokens:
            hay = text.lower()
            score = sum(1 for t in tokens if t in hay)
            if not score:
                continue
        rows.append({"domain": "codices", "kind": "codex", "codex": key,
                     "content": text[:400]})
    if not rows:
        return rows
    if tokens:
        rows.sort(key=lambda r: sum(1 for t in tokens if t in r["content"].lower()),
                  reverse=True)
    else:
        rng = random.Random("codices")
        rng.shuffle(rows)
    out = []
    for r in rows[:limit]:
        payload = _load_codices()[r["codex"]]
        out.append({"domain": "codices", "kind": "codex", "codex": r["codex"],
                    "content": _codex_excerpt(payload)})
    return out


def _codex_excerpt(payload, cap: int = 320) -> str:
    """A readable first-content excerpt from a codex payload."""
    if isinstance(payload, list) and payload:
        first = payload[0]
        return json.dumps(first, ensure_ascii=False)[:cap]
    if isinstance(payload, dict):
        for key in ("description", "title", "tokens", "base_frequencies",
                    "nodes", "cards", "runes", "feda", "symbols"):
            if key in payload and payload[key]:
                return f"{key}: " + json.dumps(payload[key], ensure_ascii=False)[:cap]
        for key, val in payload.items():
            if isinstance(val, (list, dict)) and val:
                return f"{key}: " + json.dumps(val, ensure_ascii=False)[:cap]
        return json.dumps(payload, ensure_ascii=False)[:cap]
    return str(payload)[:cap]


# ─────────────────── wave-2: intelligence (AST only) ───────────────────────

def _load_intelligence() -> list:
    """AST-parse aureon/intelligence/*.py — docstring + module constants.

    The package is NEVER imported (some modules are unprobed upstream); we
    read string/number assignments straight off the syntax tree.
    """
    global _INTEL
    if _INTEL is not None:
        return _INTEL
    rows: list = []
    if INTEL_DIR.is_dir():
        for path in sorted(INTEL_DIR.glob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8",
                                                errors="replace"))
            except (OSError, SyntaxError):
                continue
            doc = ast.get_docstring(tree) or ""
            consts: list = []
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                        and isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                    if not name.isupper():
                        continue
                    try:
                        val = ast.literal_eval(node.value)
                    except (ValueError, SyntaxError):
                        continue
                    consts.append(f"{name}={str(val)[:60]}")
                if len(consts) >= 6:
                    break
            rows.append({"module": path.stem,
                         "docstring": " ".join(doc.split())[:400],
                         "constants": consts})
    _INTEL = rows
    return rows


def _recall_intelligence(query: str | None, limit: int) -> list:
    rows = _load_intelligence()
    if not rows:
        return []
    if query:
        tokens = set(re.findall(r"[a-z]{3,}", query.lower()))
        def score(r):
            hay = (r["module"] + " " + r["docstring"]).lower()
            return sum(1 for t in tokens if t in hay)
        ranked = sorted(rows, key=score, reverse=True)
        if score(ranked[0]) > 0:
            rows = [r for r in ranked if score(r) == score(ranked[0])]
        else:
            rows = ranked
    else:
        start = int(time.time() // 300) % len(rows)
        rows = rows[start:] + rows[:start]
    return [{"domain": "intelligence", "kind": "module", "module": r["module"],
             "content": (r["docstring"] or "constants: " + ", ".join(r["constants"]))[:280]}
            for r in rows[:limit]]


# ─────────────── wave-2: prose / grants / whitepapers / owner ──────────────

def _recall_prose(files, domain: str, query: str | None, limit: int) -> list:
    files = [f for f in files if f.is_file()]
    if not files:
        return []
    tokens = set(re.findall(r"[a-z]{3,}", (query or "").lower()))
    picked: list = []
    ranked = list(files)
    if tokens:
        def fscore(f):
            return sum(1 for t in tokens if t in f.stem.lower())
        ranked = sorted(files, key=fscore, reverse=True)
        if fscore(ranked[0]) == 0:
            ranked = list(files)
    else:
        start = int(time.time() // 300) % len(ranked)
        ranked = ranked[start:] + ranked[:start]
    for f in ranked:
        if len(picked) >= limit:
            break
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 80]
        if not paras:
            continue
        if tokens:
            best = None
            for p in paras:
                if sum(1 for t in tokens if t in p.lower()):
                    best = p
                    break
            excerpt = best or paras[0]
        else:
            excerpt = paras[0]
        picked.append({"domain": domain, "kind": "prose", "source": f.name,
                       "content": " ".join(excerpt.split())[:280]})
    return picked


def _recall_grants(query: str | None, limit: int) -> list:
    """Summary-level grants pipeline rows (counts + statuses only)."""
    try:
        payload = json.loads(GRANTS_PIPELINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = []
    summary = payload.get("summary") or {}
    if isinstance(summary, dict):
        rows.append({"domain": "grants", "kind": "summary", "query_blind": True,
                     "content": f"grants pipeline tracks {len(summary)} "
                                f"tracked application entries"})
    for key in ("active_applications",):
        apps = payload.get(key) or []
        if isinstance(apps, list):
            rows.append({"domain": "grants", "kind": key, "query_blind": True,
                         "content": f"{len(apps)} active applications in "
                                    f"the pipeline"})
    for key, val in payload.items():
        if isinstance(val, dict) and key.startswith("last_"):
            when = val.get("date") or val.get("timestamp") or val.get("run_at")
            rows.append({"domain": "grants", "kind": key, "query_blind": True,
                         "content": f"{key.replace('last_', '').replace('_', ' ')}"
                                    f": {when or 'recorded'}"})
        if len(rows) >= limit + 3:
            break
    return rows[:limit] if rows else rows


def _recall_whitepapers(query: str | None, limit: int) -> list:
    """Whitepaper-canon recall over the knowledge corpus index.

    Searches a deep top_k and filters by the whitepapers root; the old
    top_k=3-then-unfiltered fallback let a 'zero point' query return
    Belfast memoir paragraphs (benchmark finding). The unfiltered path
    still exists but is honestly labelled fallback=True.
    """
    hits = recall_book(query or "HNC unified framework phi",
                       top_k=max(25, limit * 8))
    wp = [{"domain": "whitepapers", "kind": "whitepaper", "fallback": False,
           "source": h["path"] or h["title"], "content": h["paragraph"]}
          for h in hits
          if "whitepapers" in str(h.get("path") or h.get("title"))]
    if wp:
        return wp[:limit]
    return [{"domain": "whitepapers", "kind": "fallback", "fallback": True,
             "source": h["path"] or h["title"], "content": h["paragraph"]}
            for h in hits[:limit]]


def owner_constraints(query: str | None = None, limit: int = 3) -> list:
    """Standing-constraint lines from USER.md / MEMORY.md (owner-consented).

    Governance-flavoured lines only (rule/never/always/pin/constraint); the
    files are treated as untrusted data and only recalled as text.
    """
    kw = re.compile(r"(constraint|never|always|do not|don't|rule|pin|hold|"
                    r"red line|veto|forbid|must)", re.I)
    tokens = set(re.findall(r"[a-z]{3,}", (query or "").lower()))
    rows: list = []
    for f in OWNER_FILES:
        if not f.is_file():
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip().lstrip("-*#> ").strip()
            if len(line) < 12 or not kw.search(line):
                continue
            if tokens and not any(t in line.lower() for t in tokens):
                continue
            rows.append({"domain": "owner", "kind": f.name,
                         "content": line[:200]})
    if not tokens:
        start = int(time.time() // 300) % max(1, len(rows))
        rows = rows[start:] + rows[:start]
    return rows[:limit]


# ─────────────────────────────── quotes ────────────────────────────────────

def _bhoys_quotes() -> dict:
    """Import aureon.wisdom.bhoys_wisdom; fall back to source parsing."""
    if not str(AUREON_UPSTREAM) in sys.path:
        sys.path.insert(0, str(AUREON_UPSTREAM))
    try:
        import aureon._path_setup  # noqa: F401  (pins package paths)
    except Exception:
        pass
    try:
        from aureon.wisdom import bhoys_wisdom as bw
        if getattr(bw, "BHOYS_WISDOM", None):
            return {str(k): list(v) for k, v in bw.BHOYS_WISDOM.items()}
    except Exception:
        pass
    try:
        sys.path.insert(0, str(AUREON_PKG / "wisdom"))
        import bhoys_wisdom as bw_top
        if getattr(bw_top, "BHOYS_WISDOM", None):
            return {str(k): list(v) for k, v in bw_top.BHOYS_WISDOM.items()}
    except Exception:
        pass
    # Last resort: parse the dict literal out of the source (read-only).
    try:
        tree = ast.parse(BHOYS_WISDOM_PY.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    getattr(t, "id", "") == "BHOYS_WISDOM" for t in node.targets):
                raw = ast.literal_eval(node.value)
                return {str(k): [str(q) for q in v] for k, v in raw.items()}
    except Exception:
        pass
    return {}


def quote(category: str | None = None, seed: int | None = None) -> str:
    """One bhoys quote. category: victory|patience|resilience|strategy|
    unity|legacy (or None for any)."""
    quotes = _bhoys_quotes()
    if not quotes:
        return "Tiocfaidh ár lá! - Our day will come!"
    rng = random.Random(seed) if seed is not None else random
    pool: list = []
    cat_l = (category or "").lower()
    for cat, rows in quotes.items():
        cat_name = cat.split(".")[-1].split("(")[0].strip().lower() \
            if "." in cat or "(" in cat else cat.lower()
        cat_name = re.sub(r"[^a-z]", "", cat_name)
        if not cat_l or cat_l in cat_name or cat_name in cat_l:
            pool.extend(rows)
    if not pool:
        pool = [q for rows in quotes.values() for q in rows]
    return rng.choice(pool) if pool else "Our day will come."


# ─────────────────────────────── decoders ──────────────────────────────────

def _import_upstream(dotted: str):
    if str(AUREON_UPSTREAM) not in sys.path:
        sys.path.insert(0, str(AUREON_UPSTREAM))
    try:
        import aureon._path_setup  # noqa: F401
    except Exception:
        pass
    import importlib
    return importlib.import_module(dotted)


def decoder_summary(name: str) -> dict:
    """Read-only summary of one upstream decode corpus (JSON-safe dict)."""
    key = re.sub(r"[^a-z]", "", name.lower())
    if key in ("emerald", "emeraldspec", "tablet", "hermetic"):
        mod = _import_upstream("aureon.decoders.emerald_spec")
        verses = [{
            "key": v.key, "latin": v.latin_fragment, "hermetic": v.hermetic_text,
            "technical": v.technical_translation, "stage": v.pipeline_stage,
        } for v in getattr(mod, "_VERSE_CATALOG", ())]
        return {
            "name": "emerald", "verses": verses,
            "earth_aspects": [list(row) for row in getattr(mod, "_EARTH_ASPECT_TABLE", ())],
            "iono_layers": [list(row) for row in getattr(mod, "_IONO_LAYER_TABLE", ())],
        }
    if key in ("ogham", "celticogham", "feda", "celtic"):
        mod = _import_upstream("aureon.decoders.celtic_ogham")
        feda = [{
            "aicme": f.aicme, "position": f.position, "name": f.name,
            "letter": f.letter, "tree": f.tree, "hz": round(f.solfeggio_hz, 2),
            "mode": f.mode, "notes": f.notes,
        } for f in getattr(mod, "_FEDA", ())]
        return {"name": "ogham", "feda": feda, "count": len(feda)}
    if key in ("iching", "i_ching", "hexagram", "hexagrams", "chinese"):
        mod = _import_upstream("aureon.decoders.iching_decoder")
        hexes = [{
            "number": h.number, "symbol": h.symbol, "name_zh": h.name_zh,
            "name_en": h.name_en, "upper": h.upper, "lower": h.lower,
            "theme": h.theme, "judgment": str(h.judgment)[:200],
        } for h in getattr(mod, "_HEXAGRAM_CATALOG", ())]
        return {"name": "iching", "hexagrams": hexes, "count": len(hexes)}
    if key in ("maeshowe", "runes", "rune", "futhark", "seer"):
        mod = _import_upstream("aureon.wisdom.maeshowe_seer_decode")
        runes = [{
            "name": r.name, "unicode": r.unicode, "aett": r.aett, "pos": r.pos,
            "meaning": r.meaning, "domain": r.domain, "mode": r.mode,
            "hz": r.effective_hz,
        } for r in getattr(mod, "_RUNE_TABLE", ())]
        return {"name": "maeshowe", "runes": runes, "count": len(runes)}
    raise ValueError(f"unknown decoder {name!r} (emerald|ogham|iching|maeshowe)")


def decoder_names() -> list:
    return ["emerald", "ogham", "iching", "maeshowe"]


# ─────────────────────────────── book recall ───────────────────────────────

def _book_index():
    """Lazy small ResearchCorpusIndex rooted at aureon_fusion/knowledge/."""
    global _BOOK_INDEX
    if _BOOK_INDEX is not None:
        return _BOOK_INDEX
    from aureon.queen.research_corpus_index import ResearchCorpusIndex
    idx = ResearchCorpusIndex(root=str(KNOWLEDGE_DIR),
                              cache_path=str(BOOK_INDEX_CACHE),
                              ingest_exts=(".md", ".txt"))
    idx.ensure_built()
    _BOOK_INDEX = idx
    return idx


def recall_book(query: str, top_k: int = 3) -> list:
    """Recall paragraphs from the extracted Bhoys Eyes book."""
    if not BOOK_MD.exists():
        return []
    idx = _book_index()
    hits = idx.search(query, top_k=top_k) or []
    rows = []
    for h in hits:
        rows.append({
            "path": str(getattr(h, "doc_id", getattr(h, "path", ""))),
            "title": str(getattr(h, "title", "")),
            "paragraph": str(getattr(h, "text", ""))[:300],
        })
    return rows


# ─────────────────────────────── seed ──────────────────────────────────────

def _seed_entries_wave2() -> list:
    """Distilled wave-2 fragments: intelligence headers, codex excerpts,
    substack + whitepaper canon. Big prose stays corpus-index only."""
    entries: list = []
    for r in _load_intelligence():
        text = f"intelligence/{r['module']}: {r['docstring'][:280]}"
        entries.append(types.SimpleNamespace(
            value=text, tags=[_SEED_MARKER, "intelligence", "module"],
            phase_angle=0.0))
    for row in list_codices():
        c = codex(row["codex"])
        excerpt = _codex_excerpt(c["payload"], 200) if c else ""
        entries.append(types.SimpleNamespace(
            value=f"codex {row['codex']}: {excerpt}",
            tags=[_SEED_MARKER, "codices"], phase_angle=0.0))
    for f in sorted(SUBSTACK_DIR.glob("*.md"))[:12]:
        try:
            head = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        title = next((l.strip("# ").strip() for l in head if l.strip()), f.stem)
        entries.append(types.SimpleNamespace(
            value=f"substack {f.stem}: {title[:200]}",
            tags=[_SEED_MARKER, "substack"], phase_angle=0.0))
    wp_dir = KNOWLEDGE_DIR / "whitepapers"
    if wp_dir.is_dir():
        for f in sorted(wp_dir.glob("*.md")):
            entries.append(types.SimpleNamespace(
                value=f"whitepaper {f.stem}",
                tags=[_SEED_MARKER, "whitepapers"], phase_angle=0.0))
    return entries


def _seed_entries(per_bank_cap: int = 40) -> list:
    """Build the full fragment-entry list from banks + decoders + quotes."""
    entries: list = []
    banks = _load_banks()
    for bank_name, payload in banks.items():
        rows = _bank_entries(payload)
        # Deterministic thinning to the cap, preserving order diversity.
        if len(rows) > per_bank_cap:
            step = len(rows) / per_bank_cap
            rows = [rows[int(i * step)] for i in range(per_bank_cap)]
        for e in rows:
            text = e["content"][:600]
            tags = [_SEED_MARKER, bank_name, e["kind"]]
            if e["topic"]:
                tags.append(re.sub(r"\s+", "_", e["topic"].lower())[:30])
            entries.append(types.SimpleNamespace(value=text, tags=tags,
                                                 phase_angle=0.0))
    # Decoder tables: a compact presence, not the full corpus.
    for dec in ("ogham", "maeshowe"):
        try:
            summary = decoder_summary(dec)
        except Exception:
            continue
        rows = summary.get("feda") or summary.get("runes") or []
        for row in rows[:26]:
            if "tree" in row:
                text = (f"Ogham feda {row['name']} ({row['letter']}) — tree "
                        f"{row['tree']}, mode {row['mode']}, {row['hz']} Hz: "
                        f"{row['notes']}")
            else:
                text = (f"Rune {row['name']} {row['unicode']} — aett "
                        f"{row['aett']} pos {row['pos']}, {row['meaning']} "
                        f"({row['domain']}), {row['mode']} {row['hz']} Hz")
            entries.append(types.SimpleNamespace(
                value=text, tags=[_SEED_MARKER, dec, "decoder"], phase_angle=0.0))
    try:
        for verse in decoder_summary("emerald").get("verses", [])[:14]:
            text = (f"Emerald Tablet {verse['key']}: {verse['hermetic']} — "
                    f"{verse['technical']}")
            entries.append(types.SimpleNamespace(
                value=text, tags=[_SEED_MARKER, "emerald", "decoder"],
                phase_angle=0.0))
    except Exception:
        pass
    # Bhoys quotes as fragments (lyra's voice bank).
    for cat, rows in _bhoys_quotes().items():
        cat_name = cat.split(".")[-1].split("(")[0].strip().lower()
        for q in rows[:3]:
            entries.append(types.SimpleNamespace(
                value=f"Bhoys wisdom ({cat_name}): {q}",
                tags=[_SEED_MARKER, "bhoys", cat_name[:20]], phase_angle=0.0))
    return entries


def seed(max_total: int = 2000, per_bank_cap: int = 40) -> dict:
    """Fold wisdom into the live KnowledgeDataset. Idempotent on text."""
    from aureon.queen.knowledge_dataset import KnowledgeDataset
    ds = KnowledgeDataset(path=str(KNOWLEDGE_DATASET_PATH), max_fragments=max_total)
    before = (ds.get_status() or {}).get("fragments", 0)
    existing = {str(getattr(f, "text", "")).strip()
                for f in getattr(ds, "_fragments", [])}
    capacity_left = max_total - before
    all_new = [e for e in (_seed_entries(per_bank_cap=per_bank_cap)
                           + _seed_entries_wave2())
               if e.value.strip() not in existing]
    total_offered = len(_seed_entries(per_bank_cap)) + len(_seed_entries_wave2())
    entries = all_new[:max(0, capacity_left)]
    added = 0
    if entries:
        pocket = types.SimpleNamespace(goal_id="wisdom_seed", owner="wisdom",
                                       entries=entries)
        added = ds.absorb(pocket)
    after = (ds.get_status() or {}).get("fragments", before + added)
    return {"before": before, "added": added, "after": after,
            "skipped_duplicates": total_offered - len(all_new),
            "path": str(KNOWLEDGE_DATASET_PATH)}


# ─────────────────────────────── CLI ───────────────────────────────────────

def _print_json(payload) -> None:
    try:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    except UnicodeEncodeError:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    verb, rest = argv[0], argv[1:]
    limit = 5
    if "--limit" in rest:
        i = rest.index("--limit")
        try:
            limit = max(1, int(rest[i + 1]))
        except (ValueError, IndexError):
            limit = 5
        del rest[i:i + 2]

    if verb == "banks":
        _print_json(list_banks())
    elif verb == "codices":
        _print_json(list_codices())
    elif verb == "codex":
        if not rest:
            print("usage: codex <name>")
            return 2
        row = codex(rest[0])
        if row is None:
            print(f"codex {rest[0]!r} not found; see `codices`")
            return 1
        _print_json({"codex": row["codex"], "excerpt": _codex_excerpt(row["payload"], 900),
                     "keys": list(row["payload"])[:12]
                     if isinstance(row["payload"], dict) else None,
                     "entries": len(row["payload"])
                     if isinstance(row["payload"], (dict, list)) else None})
    elif verb == "recall":
        if not rest:
            print("usage: recall <domain> [query]")
            return 2
        rows = recall(rest[0], query=" ".join(rest[1:]) or None, limit=limit)
        _print_json(rows)
        return 0 if rows else 1
    elif verb == "quote":
        print(quote(rest[0] if rest else None))
    elif verb == "decoders":
        names = rest or decoder_names()
        out = {}
        for name in names:
            try:
                out[name] = decoder_summary(name)
            except Exception as exc:
                out[name] = {"error": str(exc)}
        _print_json(out)
    elif verb == "book":
        if not rest:
            print("usage: book <query>")
            return 2
        rows = recall_book(" ".join(rest), top_k=limit)
        _print_json(rows)
        return 0 if rows else 1
    elif verb == "seed":
        if "--yes" not in rest:
            print("seed writes to the live KnowledgeDataset; re-run with --yes")
            return 2
        _print_json(seed())
    else:
        print(f"unknown verb {verb!r}; see --help")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
