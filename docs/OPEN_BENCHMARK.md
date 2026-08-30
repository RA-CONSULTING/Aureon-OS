# Open benchmark — Aureon vs the published competition

Adapter resolved by the one door: `AureonLocalAdapter` — model `qwen2.5:3b-instruct`

## Aureon (measured here)

| Set | n | ok turns | score |
|---|---|---|---|
| GSM8K | 25 | 25 | 0.64 |
| HumanEval | 25 | 25 | 0.48 |

## Competition (vendor-published, cited)

| Model | Source |
|---|---|
| Kimi K2 Instruct (Moonshot AI, open weights) | https://huggingface.co/moonshotai/Kimi-K2-Instruct |
| DeepSeek-V3 (open weights) | https://huggingface.co/deepseek-ai/DeepSeek-V3 |
| Llama 3.1 405B Instruct (Meta, open weights) | https://huggingface.co/meta-llama/Llama-3.1-405B-Instruct |
| Qwen2.5-72B-Instruct (Alibaba, open weights) | https://huggingface.co/Qwen/Qwen2.5-72B-Instruct |

## Architectural contract (pinned)

| Feature | Aureon | Raw model API |
|---|---|---|
| Enforced response envelope (sources named or absence stated) | measured — b53 | not offered |
| Measured knowledge reach + reach class on every answer | measured — b57 | not offered |
| Conscience veto + hard authority boundaries (wall first) | measured — b61 | not offered |
| Field-driven coherence aperture (tighten-only, live signal) | measured — b58 | not offered |
| Film-Reel actualization ledger (realized vs parked) | measured — b54 | not offered |
| Bake-until-complete with honest incompleteness seal | measured — b56 | not offered |
| Heart charter (alive / love / power consequences stated) | measured — b59 | not offered |
| Deterministic pipeline-order pin (the flow itself tested) | measured — b61 | not offered |

> Aureon rows are measured on THIS machine's resolved adapter and scale with the provider set behind the one door; competition rows are vendor-published citations; the architecture columns cite the Tier-A benchmark that pins each feature.
