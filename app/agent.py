from typing import Optional
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langsmith import traceable

from app.config import get_settings

from app.monitoring import get_logger
logger = get_logger()

class AgentState(TypedDict):
    """
    State for the production agent.
    Uses Annotated with add_messages reducer for message accumulation.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    error: Optional[str]
    retry_count: int
    model_used: str


class ProductionAgent:
    """
    Production langgraph agent with:
    - retry on failure (model fallback)
    - graceful error handling
    - langsmith tracing
    """

    def __init__(self):
        settings = get_settings()

        self.primary_llm = ChatOpenAI(
            model = settings.primary_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0,
            timeout=30,
            max_retries=0,
        )
        self.fallback_llm = ChatOpenAI(
            model = settings.fallback_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0,
            timeout=30,
            max_retries=0,
        )
        self.max_retries = settings.max_retries
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the langgraph state machine."""

        def process_message(state: AgentState) -> dict:
            """Try to process the message with the primary model."""
            try: 
                response = self.primary_llm.invoke(state["messages"])
                return {
                    "messages": [response],
                    "error": None,
                    "model_used": "primary",
                }
            except Exception as e:

                # just for debug
                # logger.error(f"Primary LLM failed: {e!r}")   # "Fallback LLM failed" in try_fallback

                return {
                    "error": str(e),
                    "retry_count": state["retry_count"] + 1,
                    "model_used": "",
                }

        def try_fallback(state: AgentState) -> dict:
            """Fallback to secondary model."""

            try:
                response = self.fallback_llm.invoke(state["messages"])
                return {
                    "messages": [response],
                    "error": None,
                    "model_used": "fallback"
                }
            except Exception as e:

                # just for debug
                # logger.error(f"Primary LLM failed: {e!r}")   # "Fallback LLM failed" in try_fallback

                return {
                    "error": str(e),
                    "model_used": "",
                }

        def handle_error(state: AgentState) -> dict:
            """Return a graceful error message."""
            return {
                "messages": [
                    AIMessage(content=(
                        "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment."
                    ))
                ],
                "model_used": "error_handler",
            }

        def route_after_process(state: AgentState) -> str:
            """Decide what to do after primary model attempt."""
            if state.get("error") is None:
                return "done"
            elif state["retry_count"] < self.max_retries:
                return "fallback"
            else:
                return "error"

        def route_after_fallback(state: AgentState) -> str:
            """Decide what to do after fallback attempt"""
            if state.get("error") is None:
                return "done"
            else:
                return "error"

        
        # build the graph
        graph = StateGraph(AgentState)

        graph.add_node("process", process_message)
        graph.add_node("fallback", try_fallback)
        graph.add_node("error", handle_error)

        graph.add_edge(START, "process")
        graph.add_conditional_edges(
            "process",
            route_after_process,
            {"done": END, "fallback": "fallback", "error": "error"},
        )
        graph.add_conditional_edges(
            "fallback",
            route_after_fallback,
            {"done": END, "error": "error"}
        )
        graph.add_edge("error", END)

        return graph.compile()

    @traceable(name="production_agent_invoke")
    def invoke(self, message: str) -> dict:
        """
        Invoke the agent with a user message.
        Returns: {"response": str, "model_used": str, "error": str | None}
        """

        result = self.graph.invoke({
            "messages": [HumanMessage(content=message)],
            "error": None,
            "retry_count": 0,
            "model_used": "",
        })

        return {
            "response": result["messages"][-1].content,
            "model_used": result.get("model_used", "unknown"),
            "error": result.get("error"),
        }






# # test script

# uv run python -c "
# from app.agent import ProductionAgent
 
# agent = ProductionAgent()
 
# print('=== PRODUCTION AGENT - STANDALONE TEST ===')
# print()
 
# queries = [
#     'What is LangGraph in one sentence?',
#     'What is 2 + 2?',
#     'Explain the difference between RAG and fine-tuning in 2 sentences.',
# ]
 
# for query in queries:
#     print(f'--- Query: {query} ---')
#     result = agent.invoke(query)
#     print(f'Response: {result["response"]}')
#     print(f'Model used: {result["model_used"]}')
#     print(f'Error: {result["error"]}')
#     print()
 
# print('=== DONE ===')
#  "