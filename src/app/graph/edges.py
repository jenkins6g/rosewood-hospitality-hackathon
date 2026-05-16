from langchain_core.messages import AIMessage

from src.app.state import AgentState


def after_classify(state: AgentState) -> str:
    return "finalize" if state["action"] == "ignore" else "extract"


def after_enrich(state: AgentState) -> str:
    return "weather"


def after_recommend(state: AgentState) -> str:
    if state.get("final_response"):
        return "finalize"
    return "agent" if state["action"] == "reply" else "finalize"


def after_agent(state: AgentState) -> str:
    if state.get("final_response"):
        return "finalize"

    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        if state.get("tool_rounds", 0) >= state["debug"]["max_tool_rounds"]:
            return "finalize"
        return "tool"

    return "finalize"
