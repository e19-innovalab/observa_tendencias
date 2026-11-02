"""Fine-tunes a multilingual embedding model so Spanish job names land near their CIUO-08 group.

Training pairs, from data/labels_es.jsonl: (any name of a code) → (its CIUO title, and its ESCO
preferred names). In-batch negatives (MultipleNegativesRankingLoss): the other pairs in a batch
act as wrong answers, so each batch must not repeat a code.

Held out, never trained on:
- every test-set phrase (exact match after removing accents and case);
- all names of a random share of codes (train.holdout_share), to check generalisation.
The held-out codes are saved with the model (holdout.json).

Runs on a CUDA GPU (Alienware) or, slowly, on CPU/Apple. Usage:
  .venv/bin/python train.py            # writes models/occupation-match-es
Then copy that folder back and run evaluate.py.
"""
import json
import random
import unicodedata
from collections import defaultdict
from pathlib import Path

import torch
import yaml
from datasets import Dataset
from sentence_transformers import (SentenceTransformer, SentenceTransformerTrainer,
                                   SentenceTransformerTrainingArguments)
from sentence_transformers.losses import MultipleNegativesRankingLoss
from sentence_transformers.training_args import BatchSamplers

HERE = Path(__file__).parent
CONF = yaml.safe_load((HERE / "config.yaml").read_text())
T = CONF["train"]


def _path(key: str) -> Path:
    return (HERE / CONF["paths"][key]).resolve()


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).lower().strip()


def pairs() -> tuple[list[dict], list[str]]:
    labels = [json.loads(line) for line in _path("labels").read_text().splitlines()]
    tests = {fold(t["q"]) for t in yaml.safe_load(_path("testset").read_text())["queries"]}
    by_code: dict[str, list[dict]] = defaultdict(list)
    for r in labels:
        by_code[r["code"]].append(r)
    rng = random.Random(T["seed"])
    codes = sorted(by_code)
    holdout = sorted(rng.sample(codes, int(len(codes) * T["holdout_share"])))
    out = []
    for code in codes:
        if code in holdout:
            continue
        targets = [r["label"] for r in by_code[code] if r["kind"] in ("ciuo_title", "esco_preferred")]
        for r in by_code[code]:
            if fold(r["label"]) in tests:
                continue
            for target in targets:
                if target != r["label"]:
                    out.append({"anchor": T["query_prefix"] + r["label"],
                                "positive": T["passage_prefix"] + target, "code": code})
    rng.shuffle(out)
    return out, holdout


def main() -> None:
    data, holdout = pairs()
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"{len(data)} pares, {len(holdout)} códigos reservados · dispositivo: {device}")
    model = SentenceTransformer(T["base_model"], device=device)
    # the "code" column is only for the no-duplicates sampler; the loss uses anchor and positive
    train = Dataset.from_list([{"anchor": d["anchor"], "positive": d["positive"]} for d in data])
    out = _path("trained_model")
    args = SentenceTransformerTrainingArguments(
        output_dir=str(out / "checkpoints"),
        num_train_epochs=T["epochs"],
        per_device_train_batch_size=T["batch_size"],
        learning_rate=T["learning_rate"],
        warmup_ratio=0.1,
        fp16=device == "cuda",
        batch_sampler=BatchSamplers.NO_DUPLICATES,
        save_strategy="no",
        logging_steps=50,
        seed=T["seed"],
        report_to=[],
    )
    trainer = SentenceTransformerTrainer(model=model, args=args, train_dataset=train,
                                         loss=MultipleNegativesRankingLoss(model))
    trainer.train()
    model.save(str(out))
    (out / "holdout.json").write_text(json.dumps({"codes": holdout, "train_config": T}, indent=1))
    print(f"Modelo guardado en {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
