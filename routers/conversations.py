"""
AI Assistant conversation threads API — list, create, resume, rename, delete.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from connectors import conversationdb

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationRename(BaseModel):
    title: str


@router.get("")
def list_conversations(limit: int = Query(100)):
    """List conversation threads, most recently active first."""
    return {"conversations": conversationdb.list_conversations(limit=limit)}


@router.post("")
def create_conversation(body: ConversationCreate = None):
    """Create a new, empty conversation thread."""
    title = body.title if body else None
    conv_id = conversationdb.create_conversation(title=title)
    return conversationdb.get_conversation(conv_id)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int):
    """Get a conversation with its full message history."""
    conv = conversationdb.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/{conversation_id}")
def rename_conversation(conversation_id: int, body: ConversationRename):
    if not conversationdb.rename_conversation(conversation_id, body.title):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"renamed": True}


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: int):
    if not conversationdb.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": conversation_id}
