"""The single LangGraph agent (Task 2).

A StateGraph with two nodes:
  - `agent`: a Claude model bound to the tools; decides what to do next.
  - `tools`: executes the requested tool calls (extraction, Sheets, WhatsApp, audio).

`tools_condition` loops back to the agent until it stops calling tools. A
checkpointer (MongoDB, falling back to in-memory) persists state per
`thread_id` (== chat session id), so conversation context — including which
contact a later voice note belongs to — survives across requests and supports
multiple concurrent chat sessions.
"""
from __future__ import annotations

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.config import get_settings
from app.services.mongo import get_mongo

logger = logging.getLogger(__name__)

_graph = None


def _build_llm() -> ChatAnthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — the agent cannot run.")
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=2048,
        timeout=60,
    )


def _agent_node_factory():
    llm_with_tools = _build_llm().bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    return agent_node


def _make_checkpointer():
    """Prefer durable MongoDB checkpoints; fall back to in-memory if the
    optional dependency is unavailable."""
    settings = get_settings()
    try:
        from langgraph.checkpoint.mongodb import MongoDBSaver

        client = get_mongo()._client  # reuse the existing connection
        saver = MongoDBSaver(client, db_name=settings.mongodb_db)
        logger.info("LangGraph checkpointer: MongoDB")
        return saver
    except Exception as exc:  # pragma: no cover - environment dependent
        from langgraph.checkpoint.memory import MemorySaver

        logger.warning(
            "Falling back to in-memory checkpointer (%s). Conversation state "
            "will not survive a restart.",
            exc,
        )
        return MemorySaver()


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("agent", _agent_node_factory())
    builder.add_node("tools", ToolNode(ALL_TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    builder.add_edge("agent", END)
    return builder.compile(checkpointer=_make_checkpointer())


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
