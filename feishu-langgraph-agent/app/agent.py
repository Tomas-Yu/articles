"""
LangGraph ReAct agent.

State:
    messages — full conversation history (HumanMessage / AIMessage / ToolMessage)

Nodes:
    llm_node  — call the LLM, may emit tool calls
    tool_node — execute requested tools, emit ToolMessages

Edges:
    llm_node  → END           (if no tool calls)
    llm_node  → tool_node     (if tool calls present)
    tool_node → llm_node      (always, to process tool results)
"""
from __future__ import annotations

import logging
from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.config import settings
from app.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  State definition                                                    #
# ------------------------------------------------------------------ #

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ------------------------------------------------------------------ #
#  LLM                                                                 #
# ------------------------------------------------------------------ #

def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
        streaming=False,
    ).bind_tools(ALL_TOOLS)


_llm = _build_llm()
_tool_node = ToolNode(ALL_TOOLS)


# ------------------------------------------------------------------ #
#  Nodes                                                               #
# ------------------------------------------------------------------ #

def llm_node(state: AgentState) -> AgentState:
    """Prepend system prompt and call the LLM."""
    system = SystemMessage(content=settings.system_prompt)
    messages = [system] + state["messages"]
    response = _llm.invoke(messages)
    logger.debug("LLM response: %s", response)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """Route: if the last message has tool_calls → tools; else → END."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


# ------------------------------------------------------------------ #
#  Graph                                                               #
# ------------------------------------------------------------------ #

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("llm", llm_node)
    graph.add_node("tools", _tool_node)

    graph.set_entry_point("llm")

    graph.add_conditional_edges(
        "llm",
        should_continue,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "llm")

    return graph.compile()


# Compiled graph — reused across requests
agent_graph = build_graph()


# ------------------------------------------------------------------ #
#  Public API                                                          #
# ------------------------------------------------------------------ #

# In-memory session store: session_key → list[BaseMessage]
# Replace with Redis or a DB for production use.
_sessions: dict[str, list[BaseMessage]] = {}


def run_agent(session_key: str, user_message: str) -> str:
    """
    Run the agent for a given session and user message.

    Args:
        session_key: Unique identifier for the conversation (e.g. chat_id or open_id).
        user_message: The incoming message text from the user.

    Returns:
        The agent's final text reply.
    """
    from langchain_core.messages import HumanMessage

    history = _sessions.get(session_key, [])
    history.append(HumanMessage(content=user_message))

    result = agent_graph.invoke({"messages": history})

    # Persist updated history
    _sessions[session_key] = result["messages"]

    # Return the last AI message's text content
    last = result["messages"][-1]
    if hasattr(last, "content"):
        if isinstance(last.content, str):
            return last.content
        # content may be a list of dicts (multi-modal)
        texts = [
            c["text"] for c in last.content if isinstance(c, dict) and "text" in c
        ]
        return " ".join(texts)
    return "(no response)"


def clear_session(session_key: str) -> None:
    """Clear conversation history for a session."""
    _sessions.pop(session_key, None)
