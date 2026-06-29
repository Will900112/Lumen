import traceback
from openai import APIError, APIConnectionError, RateLimitError
from state import AgentSharedState
from agents.agent1_profile_analyzer import run_agent1
from agents.agent2_clinical_proposer import run_agent2
from agents.agent3_rag_grounder import run_agent3
from agents.agent4_safety_report import run_agent4
from agents.agent5_chat import run_agent5


class PipelineError(Exception):
    def __init__(self, step: str, message: str):
        self.step = step
        super().__init__(f"[{step}] {message}")


async def _run_step(step_name: str, fn, *args):
    try:
        return await fn(*args)
    except RateLimitError:
        raise PipelineError(step_name, "OpenAI rate limit reached. Please try again later.")
    except APIConnectionError:
        raise PipelineError(step_name, "Cannot connect to OpenAI. Please check your network.")
    except APIError as e:
        raise PipelineError(step_name, f"OpenAI API error: {e.message}")
    except Exception as e:
        traceback.print_exc()
        raise PipelineError(step_name, str(e))


async def run(questionnaire: dict) -> AgentSharedState:
    state = AgentSharedState(raw_questionnaire=questionnaire)
    print("  [1/4] Profile analyzer...", flush=True)
    state = await _run_step("Agent1", run_agent1, state)
    print("  [2/4] Clinical proposer...", flush=True)
    state = await _run_step("Agent2", run_agent2, state)
    print("  [3/4] RAG grounder...", flush=True)
    state = await _run_step("Agent3", run_agent3, state)
    print("  [4/4] Safety report...", flush=True)
    state = await _run_step("Agent4", run_agent4, state)
    return state


async def chat(
    state: AgentSharedState,
    conversation_history: list[dict],
    user_message: str,
) -> tuple[str, list[dict]]:
    reply = await _run_step("Agent5", run_agent5, state, conversation_history, user_message)
    updated_history = conversation_history + [
        {"role": "user",      "content": user_message},
        {"role": "assistant", "content": reply},
    ]
    return reply, updated_history
