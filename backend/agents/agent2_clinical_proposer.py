from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import json
from state import AgentSharedState, SupplementCandidate
from config import LLM_MODEL

load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def run_agent2(state: AgentSharedState) -> AgentSharedState:

    # Collect existing gap-layer names so Layer 2/3 don't repeat them
    existing_names = [c.name.lower() for c in state.gap_candidates]

    prompt = f"""
You are a clinical nutritionist. Based on the symptoms and health goal below, 
propose supplements with clinical evidence.

Symptom tags: {state.symptom_tags}
Long-term health goal: {state.health_goal}
Already recommended (do NOT repeat these): {existing_names}

Return ONLY this JSON:
{{
  "symptom_candidates": [
    {{"name": "Melatonin", "query_context": "melatonin reduces sleep onset latency in insomnia patients"}},
    {{"name": "Magnesium Glycinate", "query_context": "magnesium glycinate improves sleep quality and reduces nighttime awakening"}}
  ],
  "goal_candidates": [
    {{"name": "Lion's Mane", "query_context": "lion's mane improves memory consolidation and cognitive function"}}
  ]
}}

Rules:
- symptom_candidates: 5-7 supplements, each with strong clinical evidence for the symptoms
- goal_candidates: 3-5 supplements for long-term goal optimization
- query_context format: "[supplement] [action verb] [specific outcome] in [condition/target]"
  Good: "ashwagandha reduces cortisol and improves stress resilience"
  Good: "CoQ10 improves mitochondrial energy production in fatigue patients"
  Bad:  "ashwagandha stress clinical trial evidence"
- Do NOT include any supplement already in the "already recommended" list
"""

    response = await openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    state.symptom_candidates = [
        SupplementCandidate(
            name=item["name"],
            layer="symptom",
            query_context=item["query_context"]
        )
        for item in result.get("symptom_candidates", [])
    ]
    state.goal_candidates = [
        SupplementCandidate(
            name=item["name"],
            layer="goal",
            query_context=item["query_context"]
        )
        for item in result.get("goal_candidates", [])
    ]

    return state