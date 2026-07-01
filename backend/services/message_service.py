"""
AI Personal Cloud Drive - Message Service

Cross-device text messaging between PC and phone.
All operations use the shared messages table.
"""
from models.database import get_db


def send_message(content: str, sender: str) -> dict:
    """Insert a message and return it with id + timestamp."""
    if sender not in ("PC", "手机"):
        raise ValueError("sender must be 'PC' or '手机'")
    if not content or not content.strip():
        raise ValueError("content cannot be empty")

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (content, sender) VALUES (?, ?)",
            (content.strip(), sender),
        )
        conn.commit()
        msg_id = cursor.lastrowid

        cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
        row = cursor.fetchone()
        return dict(row)
    finally:
        conn.close()


def get_messages(limit: int = 50) -> list[dict]:
    """Return recent messages in chronological order."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM messages ORDER BY created_at ASC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_message(msg_id: int) -> bool:
    """Delete a single message by id. Returns True if deleted."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def clear_messages() -> int:
    """Delete all messages. Returns count of deleted rows."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
