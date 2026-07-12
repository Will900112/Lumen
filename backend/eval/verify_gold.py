"""Phase 1b-verify: independent check that each gold chunk answers its query.

Generation and verification are deliberately separate steps. The generator was
biased toward its own query (it wrote it), so a fresh call re-reads the FULL
chunk and judges — without seeing the generator's reasoning — whether the chunk
actually contains a passage that answers the query.

Each gold is scored 1-5 on how well the chunk's prose answers its query
(leading/trailing citations from an adjacent section do not lower the score).
A score is continuous quality, so the reviewer picks the cutoff (e.g. keep >=3
or >=4) rather than the grader deciding pass/fail.

Output: eval/data/verify_flags.json — every qid with its score and reason.
Does not modify eval_set.jsonl; pruning is a separate step.
"""

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EVAL_SET_PATH = os.path.join(DATA_DIR, "eval_set.jsonl")
FLAGS_PATH = os.path.join(DATA_DIR, "verify_flags.json")

MODEL = "gpt-5.6-terra"
CONCURRENCY = 10

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
semaphore = asyncio.Semaphore(CONCURRENCY)

PROMPT = """\
You are grading one entry in a retrieval benchmark. Below is a search QUERY and \
a textbook CHUNK claimed to be the correct answer (the "gold") for that query.

Rate, 1-5, how well the chunk's actual prose answers this specific query. \
Leading or trailing citations, or content from an adjacent section, do NOT \
lower the score as long as the answering passage is present.

  5 = the chunk directly and substantively answers the query (a passage clearly
      supports the query's specific claim).
  4 = the chunk answers the query, but the supporting passage is brief or partial.
  3 = on the right topic and relevant, but does not clearly support the query's
      specific claim.
  2 = only loosely related; the query's subject appears mostly in a heading or a
      passing mention, with little supporting prose.
  1 = does not answer the query at all — e.g. the chunk is essentially a
      reference/citation list, or its prose is about a different topic.

QUERY: {query}

CHUNK:
---
{chunk}
---

Return ONLY JSON: {{"score": 1-5, "reason": "<one short sentence>"}}
"""


async def verify(row: dict) -> dict:
    prompt = PROMPT.format(query=row["query"], chunk=row["gold_text"])
    async with semaphore:
        for attempt in range(6):
            try:
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                break
            except RateLimitError:
                await asyncio.sleep(2 ** attempt)
        else:
            return {"qid": row["qid"], "error": "rate_limited"}
    try:
        result = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"qid": row["qid"], "error": "bad_json"}
    try:
        score = int(result.get("score"))
    except (TypeError, ValueError):
        return {"qid": row["qid"], "error": "bad_score"}
    return {
        "qid": row["qid"],
        "index": row["index"],
        "query": row["query"],
        "score": score,
        "reason": result.get("reason", ""),
    }


async def main() -> None:
    rows = [json.loads(l) for l in open(EVAL_SET_PATH, encoding="utf-8")]
    results = await asyncio.gather(*[verify(r) for r in rows])

    scored = [r for r in results if "error" in r or "score" in r]
    graded = [r for r in scored if "score" in r]
    errors = [r for r in scored if "error" in r]
    graded.sort(key=lambda r: (r["score"], r["qid"]))

    with open(FLAGS_PATH, "w", encoding="utf-8") as f:
        json.dump({"graded": graded, "errors": errors}, f, ensure_ascii=False, indent=2)

    from collections import Counter
    dist = Counter(r["score"] for r in graded)
    print(f"graded {len(graded)}, errors {len(errors)}")
    print("score distribution (all):")
    for s in (5, 4, 3, 2, 1):
        print(f"  {s}: {dist.get(s, 0)}")
    print("low scores (<=2) by index:")
    low_by_index = Counter(r["index"] for r in graded if r["score"] <= 2)
    for idx in ["lumen-gap", "lumen-clinical", "lumen-interactions"]:
        print(f"  {idx}: {low_by_index.get(idx, 0)}")
    print(f"[done] full scores -> {FLAGS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
