"""Phase 1b-final: balance the benchmark to an equal size per index.

The indexes are scored independently, so imbalance does not distort per-index
recall — but an equal split (60/60/60) is cleaner to report. Because every
surviving gold already passed generation + verification (no low scores), we
downsample RANDOMLY rather than by score: picking the highest-scored would bake
in the grader model's preference (a bias), whereas a fixed-seed random sample
preserves the true distribution.

Reads eval_set.jsonl + verify_flags.json (to carry each gold's score through),
writes the pruned, renumbered eval_set.jsonl and a fresh eval_review.md.
"""

import json
import os
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EVAL_SET_PATH = os.path.join(DATA_DIR, "eval_set.jsonl")
FLAGS_PATH = os.path.join(DATA_DIR, "verify_flags.json")
REVIEW_PATH = os.path.join(DATA_DIR, "eval_review.md")

SEED = 42
PER_INDEX = 60
INDEX_ORDER = ["lumen-gap", "lumen-clinical", "lumen-interactions"]


def main() -> None:
    rows = [json.loads(l) for l in open(EVAL_SET_PATH, encoding="utf-8")]

    scores = {}
    if os.path.exists(FLAGS_PATH):
        flags = json.load(open(FLAGS_PATH, encoding="utf-8"))
        scores = {g["qid"]: (g["score"], g.get("reason", "")) for g in flags["graded"]}

    by_index: dict[str, list[dict]] = {}
    for r in rows:
        by_index.setdefault(r["index"], []).append(r)

    rng = random.Random(SEED)
    kept: list[dict] = []
    for idx in INDEX_ORDER:
        pool = by_index.get(idx, [])
        take = min(PER_INDEX, len(pool))
        sample = rng.sample(pool, take)
        sample.sort(key=lambda r: r["qid"])  # stable, readable order
        print(f"[{idx}] {len(pool)} -> kept {take}")
        kept.extend(sample)

    # renumber qid 1..N, keep original id for traceability + attach score
    with open(EVAL_SET_PATH, "w", encoding="utf-8") as f:
        for new_qid, r in enumerate(kept, start=1):
            score, _ = scores.get(r["qid"], (None, ""))
            out = {
                "qid": new_qid,
                "orig_qid": r["qid"],
                "query": r["query"],
                "gold_id": r["gold_id"],
                "index": r["index"],
                "gold_score": score,
                "gold_text": r["gold_text"],
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Eval Set ({len(kept)} queries, {PER_INDEX}/index)\n\n")
        for new_qid, r in enumerate(kept, start=1):
            score, reason = scores.get(r["qid"], (None, ""))
            f.write(f"\n---\n\n## Q{new_qid}  ({r['index']} / {r['gold_id']} / score {score})\n\n")
            f.write(f"**Query:** {r['query']}\n\n")
            if reason:
                f.write(f"**Grader note:** {reason}\n\n")
            f.write(f"**Gold chunk (full):**\n\n> {r['gold_text']}\n")

    print(f"[done] {len(kept)} queries -> {EVAL_SET_PATH}")


if __name__ == "__main__":
    main()
