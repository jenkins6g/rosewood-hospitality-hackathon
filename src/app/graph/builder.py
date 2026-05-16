from langgraph.graph import END, START, StateGraph

from src.app.graph.edges import after_agent, after_classify, after_enrich
from src.app.graph.nodes import GraphNodes
from src.app.state import AgentState


def build_graph(nodes: GraphNodes):
    graph = StateGraph(AgentState)

    graph.add_node("resolve", nodes.resolve)
    graph.add_node("context", nodes.build_context)
    graph.add_node("classify", nodes.classify)
    graph.add_node("extract", nodes.extract_operational_update)
    graph.add_node("guest", nodes.resolve_guest)
    graph.add_node("enrich", nodes.enrich_operational_update)
    graph.add_node("agent", nodes.agent)
    graph.add_node("tool", nodes.run_tools)
    graph.add_node("finalize", nodes.finalize)
    graph.add_node("summarize", nodes.summarize)

    graph.add_edge(START, "resolve")
    graph.add_edge("resolve", "context")
    graph.add_edge("context", "classify")
    graph.add_conditional_edges(
        "classify",
        after_classify,
        {
            "extract": "extract",
            "finalize": "finalize",
        },
    )
    graph.add_edge("extract", "guest")
    graph.add_edge("guest", "enrich")
    graph.add_conditional_edges(
        "enrich",
        after_enrich,
        {
            "agent": "agent",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "agent",
        after_agent,
        {
            "tool": "tool",
            "finalize": "finalize",
        },
    )
    graph.add_edge("tool", "agent")
    graph.add_edge("finalize", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
