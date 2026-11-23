import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

TRAINING = Path(__file__).resolve().parents[1] / "training"
if str(TRAINING) not in sys.path:
    sys.path.insert(0, str(TRAINING))

from pretrain import TokenStream  # noqa: E402
from train_sft import make_batches  # noqa: E402


def hf_shift(labels):
    return torch.nn.functional.pad(labels, (0, 1), value=-100)[..., 1:]


def test_pretrain_labels_share_input_timeline():
    stream = TokenStream.__new__(TokenStream)
    stream.batch_size = 1
    stream._gen = iter([np.array([10, 11, 12, 13, 14, 15], dtype=np.uint16)])

    inputs, labels = stream.batch()

    assert inputs.tolist() == [[10, 11, 12, 13, 14]]
    assert labels.tolist() == inputs.tolist()
    assert hf_shift(labels).tolist() == [[11, 12, 13, 14, -100]]


def test_sft_labels_align_first_response_and_eos():
    rows = [{"prompt": [10, 11, 12], "target": [20, 21, 1]}]

    batches, _, _ = make_batches(
        rows, batch_size=1, rank=0, world=1, seed=1337, seq_len=32
    )
    batch = batches[0]

    assert batch["input_ids"].tolist() == [[10, 11, 12, 20, 21, 1]]
    assert batch["labels"].tolist() == [[-100, -100, -100, 20, 21, 1]]
    assert batch["attention_mask"].tolist() == [[1, 1, 1, 1, 1, 1]]
    assert hf_shift(batch["labels"]).tolist() == [[-100, -100, 20, 21, 1, -100]]
