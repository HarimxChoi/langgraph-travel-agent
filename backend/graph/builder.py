"""Graph builder: wire nodes, conditional edges, checkpointer."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from ..config.settings import llm
from ..tools.flights import search_flights
from ..tools.hotels import search_and_compare_hotels
from ..tools.activities import search_activities_by_city
from ..tools.sms import send_sms_notification
from ..tools.crm import send_to_hubspot
from .nodes import call_model_node, synthesize_results_node
from .state import TravelAgentState

tools = [
    search_flights,
    search_and_compare_hotels,
    search_activities_by_city,
    send_sms_notification,
    send_to_hubspot,
]
tool_llm = llm.bind_tools(tools)


def build_enhanced_graph(checkpointer=None):
    """Build the production LangGraph workflow."""
    if checkpointer is None:
        checkpointer = InMemorySaver()

    workflow = StateGraph(TravelAgentState)

    workflow.add_node("call_model_and_tools", call_model_node)
    workflow.add_node("synthesize_results", synthesize_results_node)

    workflow.set_entry_point("call_model_and_tools")

    workflow.add_conditional_edges(
        "call_model_and_tools",
        lambda state: state["current_step"],
        {
            "collecting_info": END,
            "synthesizing": "synthesize_results",
            "complete": END,
        },
    )

    workflow.add_edge("synthesize_results", END)

    print("Graph compiled successfully")
    return workflow.compile(checkpointer=checkpointer)
