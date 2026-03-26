"""
Tools: Feishu document operations

- feishu_read_doc   — read the text content of a document
- feishu_append_doc — append text to an existing document
- feishu_create_doc — create a new blank document
"""
from langchain_core.tools import tool
from app.feishu_client import feishu


@tool
def feishu_read_doc(doc_token: str) -> str:
    """
    Read the text content of a Feishu document.

    Args:
        doc_token: The document token (extracted from the document URL:
                   https://xxx.feishu.cn/docx/<doc_token>).

    Returns:
        The plain-text content of the document, or an error message.
    """
    try:
        content = feishu.get_doc_content(doc_token)
        if not content.strip():
            return "(Document is empty)"
        return content
    except Exception as e:
        return f"Error reading document: {e}"


@tool
def feishu_append_doc(doc_token: str, text: str) -> str:
    """
    Append text content to the end of a Feishu document.

    Args:
        doc_token: The document token.
        text: The text paragraph to append.

    Returns:
        A confirmation string, or an error message.
    """
    try:
        feishu.append_to_doc(doc_token, text)
        return f"Successfully appended text to document {doc_token}."
    except Exception as e:
        return f"Error appending to document: {e}"


@tool
def feishu_create_doc(title: str, folder_token: str = "") -> str:
    """
    Create a new Feishu document with the given title.

    Args:
        title: The title for the new document.
        folder_token: Optional folder token to place the document in.

    Returns:
        The new document's token and URL.
    """
    try:
        result = feishu.create_doc(title, folder_token)
        doc_data = result.get("data", {}).get("document", {})
        doc_token = doc_data.get("document_id", "unknown")
        url = f"https://feishu.cn/docx/{doc_token}"
        return f"Document created. token={doc_token}, url={url}"
    except Exception as e:
        return f"Error creating document: {e}"
