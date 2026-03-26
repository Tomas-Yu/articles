"""
Feishu API client.

Handles:
- tenant_access_token acquisition and auto-refresh
- Generic authenticated HTTP requests
- Convenience methods: send_message, get_doc, update_doc, create_doc
"""
import time
import logging
import httpx
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """Thin wrapper around Feishu REST API with automatic token refresh."""

    def __init__(self):
        self._token: str = ""
        self._token_expires_at: float = 0.0
        self._http = httpx.Client(timeout=30)

    # ------------------------------------------------------------------ #
    #  Auth                                                                #
    # ------------------------------------------------------------------ #

    def _refresh_token(self) -> None:
        resp = self._http.post(
            f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            json={
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu auth failed: {data}")
        self._token = data["tenant_access_token"]
        # expire slightly early to avoid edge cases
        self._token_expires_at = time.time() + data["expire"] - 60
        logger.info("Feishu token refreshed, expires in %s s", data["expire"])

    @property
    def token(self) -> str:
        if time.time() >= self._token_expires_at:
            self._refresh_token()
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    #  Generic request                                                     #
    # ------------------------------------------------------------------ #

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
    ) -> dict:
        url = f"{FEISHU_BASE}{path}"
        resp = self._http.request(
            method, url, headers=self._headers(), params=params, json=json
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"Feishu API error: {data}")
        return data

    # ------------------------------------------------------------------ #
    #  Messaging                                                           #
    # ------------------------------------------------------------------ #

    def send_message(
        self,
        receive_id: str,
        text: str,
        receive_id_type: str = "open_id",
    ) -> dict:
        """Send a plain-text message to a user or chat."""
        import json as _json

        return self.request(
            "POST",
            "/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            json={
                "receive_id": receive_id,
                "msg_type": "text",
                "content": _json.dumps({"text": text}),
            },
        )

    def reply_message(self, message_id: str, text: str) -> dict:
        """Reply to a specific message."""
        import json as _json

        return self.request(
            "POST",
            f"/im/v1/messages/{message_id}/reply",
            json={
                "msg_type": "text",
                "content": _json.dumps({"text": text}),
            },
        )

    # ------------------------------------------------------------------ #
    #  Documents                                                           #
    # ------------------------------------------------------------------ #

    def get_doc_content(self, doc_token: str) -> str:
        """
        Return the plain-text content of a Feishu document.
        Walks all top-level blocks and extracts text runs.
        """
        data = self.request("GET", f"/docx/v1/documents/{doc_token}/blocks")
        blocks = data.get("data", {}).get("items", [])
        lines: list[str] = []
        for block in blocks:
            for key in ("heading1", "heading2", "heading3", "text", "bullet", "todo"):
                if key in block:
                    elements = block[key].get("elements", [])
                    text = "".join(
                        e.get("text_run", {}).get("content", "") for e in elements
                    )
                    if text.strip():
                        lines.append(text)
        return "\n".join(lines)

    def append_to_doc(self, doc_token: str, text: str) -> dict:
        """Append a plain-text paragraph to the end of a document."""
        # First, get the document's page block_id (same as doc_token for root)
        return self.request(
            "POST",
            f"/docx/v1/documents/{doc_token}/blocks/{doc_token}/children",
            json={
                "children": [
                    {
                        "block_type": 2,  # text block
                        "text": {
                            "elements": [
                                {"text_run": {"content": text}}
                            ],
                            "style": {},
                        },
                    }
                ],
                "index": -1,
            },
        )

    def create_doc(self, title: str, folder_token: str = "") -> dict:
        """Create a new Feishu document. Returns the full API response."""
        payload: dict = {"title": title}
        if folder_token:
            payload["folder_token"] = folder_token
        return self.request("POST", "/docx/v1/documents", json=payload)


# Singleton instance used across the app
feishu = FeishuClient()
