from pydantic import BaseModel
from typing import List

class SupplementCandidate(BaseModel):
    name: str
    layer: str          # "gap" / "symptom" / "goal"
    query_context: str  # Precise phrase used by Agent 3 for RAG retrieval
    evidence_score: float = 0.0
    evidence_snippet: str = ""
    passed: bool = False

class SupplementRecommendation(BaseModel):
    name: str
    reason: str
    tip: str = ""
    evidence_snippet: str
    affiliate_url: str = ""

class AgentSharedState(BaseModel):
    # Raw input
    raw_questionnaire: dict = {}

    # Agent 1 output
    gap_candidates: List[SupplementCandidate] = []  # Layer 1: derived from diet/lifestyle
    symptom_tags: List[str] = []
    health_goal: str = ""
    safety_profile: dict = {}

    # Agent 2 output
    symptom_candidates: List[SupplementCandidate] = []  # Layer 2
    goal_candidates: List[SupplementCandidate] = []     # Layer 3

    # Agent 4 output
    safety_warnings: List[str] = []
    gap_pack: List[SupplementRecommendation] = []
    symptom_pack: List[SupplementRecommendation] = []
    goal_pack: List[SupplementRecommendation] = []
    narrative_report: str = ""