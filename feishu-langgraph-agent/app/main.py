"""
FastAPI application entry point.

Responsibilities:
1. Expose HTTP endpoints (health check, session management)
2. Start Feishu WebSocket long connection on startup
3. Route incoming Feishu messages to the LangGraph agent
4. Reply to the user via Feishu API
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
)
from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import run_agent, clear_session
from app.config import settings
from app.feishu_client import feishu

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Feishu event handler                                                #
# ------------------------------------------------------------------ #

def _on_message(data: P2ImMessageReceiveV1) -> None:
    """
    Called for every im.message.receive_v1 event from Feishu.
    Runs synchronously in a background thread so it can block on LLM calls.
    """
    try:
        event = data.event
        msg = event.message

        # Only handle plain-text messages
        if msg.message_type != "text":
            logger.info("Ignoring non-text message type: %s", msg.message_type)
            return

        import json as _json

        text: str = _json.loads(msg.content).get("text", "").strip()
        if not text:
            return

        sender_id = event.sender.sender_id
        open_id = sender_id.open_id
        chat_id = msg.chat_id
        message_id = msg.message_id

        # Use chat_id as session key so group chats share history
        session_key = chat_id or open_id

        logger.info(
            "Message from %s (session=%s): %s", open_id, session_key, text[:80]
        )

        # Run agent (blocking — this runs in a thread pool)
        reply = run_agent(session_key, text)

        # Reply in the same thread
        feishu.reply_message(message_id, reply)

    except Exception:
        logger.exception("Error handling Feishu message")


# ------------------------------------------------------------------ #
#  Feishu WebSocket client                                             #
# ------------------------------------------------------------------ #

def _start_feishu_ws() -> None:
    """Start the Feishu WebSocket long-connection client in a background thread."""
    cli = (
        lark.Client.builder()
        .app_id(settings.feishu_app_id)
        .app_secret(settings.feishu_app_secret)
        .build()
    )

    ws_client = (
        lark.ws.Client.builder()
        .app_id(settings.feishu_app_id)
        .app_secret(settings.feishu_app_secret)
        .event_handler(
            lark.EventDispatcherHandler.builder(
                encrypt_key="", verification_token=""
            )
            .register(P2ImMessageReceiveV1, _on_message)
            .build()
        )
        .build()
    )

    def _run():
        logger.info("Starting Feishu WebSocket client...")
        ws_client.start()  # blocks indefinitely

    thread = threading.Thread(target=_run, daemon=True, name="feishu-ws")
    thread.start()
    logger.info("Feishu WebSocket thread started")


# ------------------------------------------------------------------ #
#  FastAPI                                                             #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    _start_feishu_ws()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Feishu × LangGraph Agent",
    description="AI agent connected to Feishu via WebSocket",
    version="1.0.0",
    lifespan=lifespan,
)


# ------------------------------------------------------------------ #
#  HTTP endpoints                                                      #
# ------------------------------------------------------------------ #

@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


class ChatRequest(BaseModel):
    session_key: str
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    (Optional) HTTP endpoint to test the agent directly without Feishu.
    Useful for development and integration testing.
    """
    reply = run_agent(req.session_key, req.message)
    return ChatResponse(reply=reply)


@app.delete("/sessions/{session_key}")
def delete_session(session_key: str) -> dict:
    """Clear the conversation history for a session."""
    clear_session(session_key)
    return {"status": "cleared", "session_key": session_key}
