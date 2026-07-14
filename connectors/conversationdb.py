"""
AI Assistant conversation persistence — SQLite-backed store for chat threads
so a conversation survives a page reload and can be resumed later, browsed
in a history list, or started fresh.

Schema
------
conversations
  id           INTEGER PK
  title        TEXT    (auto-derived from the first user message, or renamed)
  created_at   TEXT    ISO-8601
  updated_at   TEXT    ISO-8601 (bumped on every new message — used for sort order)

conversation_messages
  id               INTEGER PK
  conversation_id  INTEGER FK -> conversations.id
  role             TEXT    ("user" or "assistant")
  content          TEXT
  tool_log         TEXT    JSON blob (assistant messages only; null for user turns)
  created_at       TEXT    ISO-8601
"""

import json
import sqlite3
import time
from pathlib import Path
from connectors import paths

DATA_DIR = paths.DATA_DIR
DB_PATH = DATA_DIR / "conversations.db"


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL DEFAULT 'New conversation',
                created_at   TEXT    NOT NULL,
                updated_at   TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at DESC);

            CREATE TABLE IF NOT EXISTS conversation_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT    NOT NULL,
                content         TEXT    NOT NULL,
                tool_log        TEXT,
                created_at      TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conv_msg ON conversation_messages(conversation_id, created_at);
        """)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _default_title(first_message: str) -> str:
    text = (first_message or "").strip().replace("\n", " ")
    if not text:
        return "New conversation"
    return text[:60] + ("…" if len(text) > 60 else "")


def create_conversation(title: str = None, first_message: str = "") -> int:
    """Create a new conversation, auto-titling from the first message if no title given."""
    now = _now_iso()
    final_title = (title or "").strip() or _default_title(first_message)
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO conversations (title, created_at, updated_at) VALUES (?,?,?)",
            (final_title, now, now),
        )
        return cur.lastrowid


def add_message(conversation_id: int, role: str, content: str, tool_log: list = None) -> int:
    """Append a message to a conversation and bump its updated_at."""
    now = _now_iso()
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO conversation_messages (conversation_id, role, content, tool_log, created_at)
               VALUES (?,?,?,?,?)""",
            (conversation_id, role, content, json.dumps(tool_log) if tool_log else None, now),
        )
        con.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
        return cur.lastrowid


def list_conversations(limit: int = 100) -> list:
    """Return conversation summaries, most recently updated first."""
    with _conn() as con:
        rows = con.execute("""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT COUNT(*) FROM conversation_messages m WHERE m.conversation_id = c.id) AS message_count
              FROM conversations c
             ORDER BY c.updated_at DESC
             LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: int) -> dict | None:
    """Return a conversation with all its messages, chronologically ordered."""
    with _conn() as con:
        conv = con.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if not conv:
            return None
        rows = con.execute(
            "SELECT * FROM conversation_messages WHERE conversation_id=? ORDER BY created_at, id",
            (conversation_id,),
        ).fetchall()
    messages = []
    for row in rows:
        d = dict(row)
        if d.get("tool_log"):
            try:
                d["tool_log"] = json.loads(d["tool_log"])
            except Exception:
                d["tool_log"] = None
        messages.append(d)
    result = dict(conv)
    result["messages"] = messages
    return result


def rename_conversation(conversation_id: int, title: str) -> bool:
    title = (title or "").strip()
    if not title:
        return False
    with _conn() as con:
        cur = con.execute("UPDATE conversations SET title=? WHERE id=?", (title, conversation_id))
    return cur.rowcount > 0


def delete_conversation(conversation_id: int) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
    return cur.rowcount > 0


init_db()
