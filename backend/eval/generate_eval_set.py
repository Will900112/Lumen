"""Phase 1b: build a synthetic retrieval benchmark from the corpus snapshot.

Pipeline (junk chunks stay in the corpus as realistic distractors — filtering
only decides which chunks are worth generating queries FROM):

    stratified random sample (3x oversample per index)
      -> rule filter        (drop obvious non-prose: too short, low letter ratio)
      -> LLM filter + generate  (one gpt-4o-mini call judges usability AND
                                 writes a production-style retrieval query)
      -> keep first N per index

Queries mimic the style of agent3's `query_context` (short clinical phrases),
because that is the query distribution production retrieval actually serves.

Output:
    eval/data/eval_set.jsonl   canonical benchmark (one row per query)
    eval/data/eval_review.md   human-readable version for manual review
"""

import asyncio
import json
import os
import random

from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CORPUS_PATH = os.path.join(DATA_DIR, "corpus.jsonl")
EVAL_SET_PATH = os.path.join(DATA_DIR, "eval_set.jsonl")
REVIEW_PATH = os.path.join(DATA_DIR, "eval_review.md")

SEED = 42
MODEL = "gpt-5.6-terra"
CONCURRENCY = 10

# sample_size per index. gap gets a bigger multiplier because its realism
# constraint rejects more chunks. every usable query is kept so the reviewer
# can prune down to the desired final size manually.
# Each index is scored independently, so each needs enough queries to make its
# own recall comparison statistically stable (~40 after review is plenty).
# Sizes account for differing usable rates, not corpus size.
SAMPLE_SIZE = {
    "lumen-gap": 550,       # strict realism + cause/outcome rule 
    "lumen-clinical": 200,  # citation/boundary/rare-disease filters 
    "lumen-interactions": 90,  # clean corpus, high usable rate 
}

MIN_CHARS = 300
MIN_LETTER_RATIO = 0.65

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
semaphore = asyncio.Semaphore(CONCURRENCY)

# Each index is queried in production with a distinct query_context style
# (see agent1 / agent2 / agent4). The benchmark must reproduce that exact
# distribution, so we use a per-index generation prompt.

_SHARED_HEADER = """\
You are building a retrieval benchmark for a supplement-recommendation RAG \
system. Each index is queried in production with ONE specific style of phrase.

Your task: given the textbook chunk below, decide whether it can serve as the \
gold (correct) answer to a realistic retrieval query in the style described \
below, and if so, write that query.

USABILITY — set "usable": false and "query": null if ANY of these hold:
  - The chunk is structural non-content: a table of contents, chapter outline, \
reference/citation list (author names + journal + year + pages), figure or \
table caption, standalone heading, or publishing boilerplate.
  - The chunk's prose body is DOMINATED by citations, OR the query's topic \
appears only in a heading or a single passing phrase while the prose is \
actually about a DIFFERENT topic (common when a chunk straddles a section \
boundary: the body belongs to the previous section and only a trailing heading \
names the next topic).
  - The index-specific realism rule below is violated.
A chunk IS usable if it contains a substantive passage that genuinely answers \
the query, even if citations follow that passage. Do not reject a chunk merely \
for starting or ending mid-sentence — that is normal for extracted chunks.

QUERY QUALITY — when usable:
  - Write the query in the exact style described below.
  - The nutrient / supplement / condition / drug NAMES may and should appear — \
production queries contain them. Only the descriptive wording must be \
paraphrased: do NOT copy distinctive multi-word phrases verbatim from the chunk.
  - Make the query specific enough that THIS chunk is clearly its best answer \
and few other chunks in the corpus could answer it equally well.

The required query style:
"""

_SHARED_FOOTER = """
Chunk:
---
{chunk}
---

Return ONLY JSON: {{"usable": true/false, "query": "..." or null}}
"""

# gap index — agent1 style: cause + physiological mechanism + deficiency outcome
PROMPT_GAP = _SHARED_HEADER + """
Query style (nutrient-gap reasoning, 10-18 words). It must weave together:
  1. a diet/lifestyle cause (e.g. "vegan diet", "limited sun exposure")
  2. a physiological mechanism (e.g. "impaired absorption", "reduced synthesis")
  3. a deficiency outcome (e.g. "vitamin D depletion", "B12 deficiency risk")
Example: "limited sun exposure reduces cutaneous synthesis leading to vitamin D deficiency"

REALISM CONSTRAINT: the app only knows these diet/lifestyle facts about a \
user — age, gender, diet type (omnivore / pescatarian / vegetarian / vegan / \
keto), weekly fish intake, dairy intake, sun exposure, exercise frequency, \
stress level, sleep hours. The CAUSE in your query must be plausibly inferable \
from these facts. Set "usable": false if the deficiency's cause requires \
something the questionnaire never captures — fasting/refeeding, pregnancy or \
lactation, alcoholism, a medical procedure, or a malabsorption/disease state. \
A disease appearing as the OUTCOME or RISK of the deficiency (e.g. "increasing \
osteoporosis fracture risk") is fine — only the CAUSE is constrained.
""" + _SHARED_FOOTER

# clinical index — agent2 style: [supplement] [verb] [outcome] in [condition/target]
PROMPT_CLINICAL = _SHARED_HEADER + """
Query style (clinical evidence phrase, 8-16 words): "[supplement] [action verb] [specific outcome] in [condition/target]".
Example: "melatonin reduces sleep onset latency in insomnia patients"
Example: "CoQ10 improves mitochondrial energy production in chronic fatigue"

REALISM CONSTRAINT: the target condition must be reachable from a vague \
complaint an ordinary user would report (e.g. insomnia, fatigue, joint pain, \
poor digestion, low mood, skin issues, headaches) OR one of these long-term \
goals — immune_support, cognitive_enhancement, sports_performance, \
cardiovascular_protection, anti_aging, hormonal_balance. A specific diagnosis \
is acceptable only if a lay user with a common symptom could plausibly map to \
it (e.g. joint pain -> osteoarthritis). Set "usable": false if the condition \
is a rare disease, an inpatient-only syndrome, or a lab-only phenomenon no \
ordinary user would present with.
""" + _SHARED_FOOTER

# interactions index — agent4 style: keyword-style entity stack, NOT a sentence
PROMPT_INTERACTIONS = _SHARED_HEADER + """
Query style (interaction keyword stack, 6-12 words): the word "interaction" \
plus the relevant herb/supplement names, drug names or drug classes, and the \
clinical effect — as keywords, NOT a grammatical sentence.
Example: "interaction St John's wort SSRI antidepressants serotonin syndrome"
Example: "interaction ginkgo warfarin antiplatelet bleeding risk"
The chunk must describe an actual or investigated interaction (or its absence) \
between a named herb/supplement and a drug — not merely mention a herb in \
passing. Entity names are used literally here (that is the production style); \
just avoid copying a whole descriptive sentence verbatim.
""" + _SHARED_FOOTER

PROMPTS = {
    "lumen-gap": PROMPT_GAP,
    "lumen-clinical": PROMPT_CLINICAL,
    "lumen-interactions": PROMPT_INTERACTIONS,
}


def load_corpus() -> dict[str, list[dict]]:
    by_index: dict[str, list[dict]] = {}
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            by_index.setdefault(row["index"], []).append(row)
    return by_index


def passes_rule_filter(text: str) -> bool:
    if len(text) < MIN_CHARS:
        return False
    letters = sum(c.isalpha() or c.isspace() for c in text)
    return letters / len(text) >= MIN_LETTER_RATIO


async def judge_and_generate(row: dict) -> dict | None:
    prompt = PROMPTS[row["index"]].format(chunk=row["document"])
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
                await asyncio.sleep(2 ** attempt)  # 1s .. 32s backoff
        else:
            return None
    try:
        result = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return None
    if not result.get("usable") or not result.get("query"):
        return None
    return {
        "query": result["query"].strip(),
        "gold_id": row["id"],
        "index": row["index"],
        "gold_text": row["document"],
    }


async def build_for_index(index_name: str, rows: list[dict], sample_size: int) -> list[dict]:
    candidates = [r for r in rows if passes_rule_filter(r["document"])]
    rng = random.Random(SEED)
    sample = rng.sample(candidates, min(sample_size, len(candidates)))

    results = await asyncio.gather(*[judge_and_generate(r) for r in sample])
    usable = [r for r in results if r is not None]
    print(f"[{index_name}] sampled {len(sample)}, usable {len(usable)}")
    return usable


def write_outputs(items: list[dict]) -> None:
    with open(EVAL_SET_PATH, "w", encoding="utf-8") as f:
        for qid, item in enumerate(items, start=1):
            f.write(json.dumps({"qid": qid, **item}, ensure_ascii=False) + "\n")

    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write("# Eval Set Review\n\n")
        f.write("Check each query: could the gold chunk plausibly be the best "
                "evidence for it? Note the qid of any bad pair.\n")
        for qid, item in enumerate(items, start=1):
            f.write(f"\n---\n\n## Q{qid}  ({item['index']} / {item['gold_id']})\n\n")
            f.write(f"**Query:** {item['query']}\n\n")
            f.write(f"**Gold chunk (full):**\n\n> {item['gold_text']}\n")


async def main() -> None:
    by_index = load_corpus()
    items: list[dict] = []
    for index_name, sample_size in SAMPLE_SIZE.items():
        items.extend(await build_for_index(index_name, by_index[index_name], sample_size))

    write_outputs(items)
    print(f"[done] {len(items)} queries -> {EVAL_SET_PATH}")
    print(f"[done] review file -> {REVIEW_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
