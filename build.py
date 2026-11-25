"""Rebuild index.html with fresh data from the research project.

Run this after you've run AI models in llm-rca-bench, so the website shows
your real results:

    python build.py --rca ../llm-rca-bench

It embeds a sample of incidents (one per fault, a control and a two-fault case,
each in all 4 evidence conditions), every method's answer for those incidents,
and the accuracy summary over the full dataset.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_LOG_LINES = 80


def build_rca_data(rca_root: Path) -> dict:
    sys.path.insert(0, str(rca_root))
    from rcabench import evaluate, simulate
    from rcabench.faults import FAULTS, LABELS, NO_INCIDENT

    dataset = simulate.load_dataset(rca_root / "data" / "dataset.jsonl")
    predictions = evaluate.load_predictions(rca_root / "results" / "predictions.jsonl")
    summary = evaluate.summarize(dataset, predictions)

    # pick sample trials: first trial of each fault, one control, one two-fault trial
    trials, seen = [], set()
    for b in dataset:
        labels = b["truth"]["labels"]
        key = "multi" if b["truth"]["multi_fault"] else labels[0]
        if key not in seen:
            seen.add(key)
            trials.append(b["trial_id"])
    random.Random(3).shuffle(trials)  # so the truth can't be guessed from the order

    latest = {(p["bundle_id"], p["method"]): p["prediction"] for p in predictions}
    methods = sorted(summary["methods"])
    incidents = []
    for n, trial in enumerate(trials, 1):
        bundles = {b["condition"]: b for b in dataset if b["trial_id"] == trial}
        conditions, answers = {}, {}
        for cond, b in bundles.items():
            m = b["metrics"]
            conditions[cond] = {
                "alert": b["alert"],
                "endpoints": {p: {"b": e["baseline"], "i": e["incident"]} for p, e in m["endpoints"].items()},
                "overall": {"b": m["overall"]["baseline"], "i": m["overall"]["incident"]},
                "status": {"b": m["status_codes"]["baseline"], "i": m["status_codes"]["incident"]},
                "cpu": {"b": m["cpu_utilization"]["baseline"], "i": m["cpu_utilization"]["incident"]},
                "version": {"b": m["service_version"]["baseline"], "i": m["service_version"]["incident"]},
                "changes": b["recent_changes"],
                "logs": b["logs"][-MAX_LOG_LINES:],
                "log_total": len(b["logs"]),
            }
            answers[cond] = {
                meth: {
                    "answer": latest[(b["id"], meth)]["root_cause"],
                    "confidence": latest[(b["id"], meth)].get("confidence", 0),
                    "explanation": latest[(b["id"], meth)].get("explanation", "")[:300],
                }
                for meth in methods if (b["id"], meth) in latest
            }
        any_b = next(iter(bundles.values()))
        incidents.append({"n": n, "truth": any_b["truth"]["labels"], "conditions": conditions, "answers": answers})

    return {
        "generated": date.today().isoformat(),
        "labels": LABELS,
        "descriptions": {**{k: v.description for k, v in FAULTS.items()},
                         NO_INCIDENT: "Nothing is broken; a harmless traffic spike tripped the alert."},
        "methods": methods,
        "summary": {
            meth: {
                "by_condition": {c: {"acc": r["by_condition"][c]["acc"], "n": r["by_condition"][c]["n"],
                                     "ci": r["by_condition"][c]["ci"]} for c in simulate.CONDITIONS},
                "overall": r["overall"]["acc"],
            }
            for meth, r in summary["methods"].items()
        },
        "dataset_size": len(dataset),
        "incidents": incidents,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rca", type=Path, default=HERE.parent / "llm-rca-bench")
    args = ap.parse_args()
    data = build_rca_data(args.rca.resolve())
    html = (HERE / "template.html").read_text(encoding="utf-8")
    html = html.replace("__RCA_JSON__", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html built: {len(data['incidents'])} incidents, methods: {', '.join(data['methods'])}")


if __name__ == "__main__":
    main()
