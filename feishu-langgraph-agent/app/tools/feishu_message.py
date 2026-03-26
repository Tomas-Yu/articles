"""
Tool: send_feishu_message

Allows the agent to proactively send a message to a Feishu user or chat.
"""
from langchain_core.tools import tool
from app.feishu_client import feishu


@tool
def send_feishu_message(
    receive_id: str,
    text: str,
    receive_id_type: str = "open_id",
) -> str:
    """
    Send a message to a Feishu user or group chat.

    Args:
        receive_id: The target's open_id (user) or chat_id (group).
        text: The message text to send.
        receive_id_type: Either 'open_id' (default) or 'chat_id'.

    Returns:
        A confirmation string with the created message_id.
    """
    result = feishu.send_message(receive_id, text, receive_id_type)
    msg_id = result.get("data", {}).get("message_id", "unknown")
    return f"Message sent successfully. message_id={msg_id}"
