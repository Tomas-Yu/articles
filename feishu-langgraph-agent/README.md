# Feishu × LangGraph Agent

A production-ready template for integrating Feishu (Lark) with a LangGraph-based AI agent.

## Architecture

```
Feishu App (WebSocket)
        ↓
FastAPI + Uvicorn (HTTP server)
        ↓
LangGraph Agent (ReAct loop)
    ├── feishu_send_message     — send messages back to Feishu
    ├── feishu_read_doc         — read a Feishu document by token
    ├── feishu_write_doc        — append content to a Feishu document
    └── feishu_create_doc       — create a new Feishu document
        ↓
OpenAI-compatible API (any base_url)
```

## Features

- **Feishu WebSocket** long connection via `lark-oapi` SDK — no need for a public webhook endpoint
- **LangGraph ReAct agent** with persistent conversation memory per chat session
- **Feishu tools**: send messages, read/write/create documents
- **FastAPI** admin endpoints for health check and session management
- **Configurable** via `.env` file

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Project Structure

```
feishu-langgraph-agent/
├── app/
│   ├── main.py              # FastAPI app + Feishu WebSocket startup
│   ├── agent.py             # LangGraph agent definition
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── feishu_message.py  # Tool: send Feishu message
│   │   └── feishu_doc.py      # Tools: read/write/create Feishu docs
│   ├── feishu_client.py     # Feishu API client (auth + requests)
│   └── config.py            # Settings from .env
├── .env.example
├── requirements.txt
└── README.md
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FEISHU_APP_ID` | Feishu App ID (`cli_xxx`) |
| `FEISHU_APP_SECRET` | Feishu App Secret |
| `LLM_BASE_URL` | OpenAI-compatible API base URL (e.g. `https://api.openai.com/v1`) |
| `LLM_API_KEY` | API key for the LLM endpoint |
| `LLM_MODEL` | Model name (e.g. `gpt-4o`, `claude-3-5-sonnet`) |

## Notes

- The Feishu App must have the following permissions: `im:message`, `im:message.receive_v1`, `docx:document`, `docx:document:readonly`
- Conversation history is stored in-memory per `session_key` (chat_id). Replace with Redis/DB for production.
