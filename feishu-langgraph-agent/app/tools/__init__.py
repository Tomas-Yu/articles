"""Feishu tools package."""
from app.tools.feishu_message import send_feishu_message
from app.tools.feishu_doc import (
    feishu_read_doc,
    feishu_append_doc,
    feishu_create_doc,
)

ALL_TOOLS = [
    send_feishu_message,
    feishu_read_doc,
    feishu_append_doc,
    feishu_create_doc,
]
