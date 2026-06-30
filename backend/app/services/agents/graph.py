from langgraph.graph import StateGraph, END
from app.services.agents.state import RagenticState
from app.services.agents.nodes.classifier import classifier_node
from app.services.agents.nodes.retriever import retriever_node
from app.services.agents.nodes.critic import critic_node
from app.services.agents.nodes.rewriter import rewriter_node
from app.services.agents.nodes.responder import responder_node
from app.services.agents.edges import should_retry_edge


def build_graph():
    """
    Builds and compiles the RAGENTIC LangGraph agent graph.

    Flow:
    classifier → retriever → critic → [rewriter → retriever → critic] → responder → END

    Conditional edge after critic:
    - faithfulness < 0.7 and retry_count < 2 → rewriter
    - otherwise → responder
    """
    graph = StateGraph(RagenticState)

    # Add nodes
    graph.add_node("classifier", classifier_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("critic", critic_node)
    graph.add_node("rewriter", rewriter_node)
    graph.add_node("responder", responder_node)

    # Set entry point
    graph.set_entry_point("classifier")

    # Add edges
    graph.add_edge("classifier", "retriever")
    graph.add_edge("retriever", "critic")

    # Conditional edge after critic
    graph.add_conditional_edges(
        "critic",
        should_retry_edge,
        {
            "rewrite": "rewriter",
            "respond": "responder",
        },
    )

    # After rewriter — go back to retriever
    graph.add_edge("rewriter", "retriever")

    # After responder — end
    graph.add_edge("responder", END)

    # Compile
    compiled = graph.compile()
    print("[graph] RAGENTIC agent graph compiled successfully")
    return compiled


# Singleton graph instance
ragentic_graph = build_graph()
