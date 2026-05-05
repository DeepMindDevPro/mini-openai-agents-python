"""SQLite session implementation."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional, Union

from microagent.memory.session import Session, SessionABC
from microagent.items import TResponseInputItem


class SQLiteSession(SessionABC):
    """SQLite-based session implementation."""

    def __init__(
        self,
        *,
        db_path: str = ":memory:",
        session_id: str | None = None,
        table_name: str = "session_items",
    ) -> None:
        """Initialize SQLite session."""
        self.db_path = db_path
        self.session_id = session_id or "default"
        self.table_name = table_name
        self._conn: sqlite3.Connection | None = None
        
        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                item_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_id (session_id)
            )
        """)
        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        """Add items to the session."""
        conn = self._get_connection()
        try:
            for item in items:
                item_json = json.dumps(item, default=str)
                conn.execute(
                    f"INSERT INTO {self.table_name} (session_id, item_data) VALUES (?, ?)",
                    (self.session_id, item_json)
                )
            conn.commit()
        finally:
            conn.close()

    async def get_items(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TResponseInputItem]:
        """Get items from the session."""
        conn = self._get_connection()
        try:
            query = f"""
                SELECT item_data FROM {self.table_name} 
                WHERE session_id = ? 
                ORDER BY created_at ASC, id ASC
            """
            params = [self.session_id]
            
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            items: list[TResponseInputItem] = []
            for row in rows:
                try:
                    item = json.loads(row[0])
                    items.append(item)
                except json.JSONDecodeError:
                    # Skip invalid JSON
                    continue
            
            return items
        finally:
            conn.close()

    async def clear_items(self) -> None:
        """Clear all items from the session."""
        conn = self._get_connection()
        try:
            conn.execute(
                f"DELETE FROM {self.table_name} WHERE session_id = ?",
                (self.session_id,)
            )
            conn.commit()
        finally:
            conn.close()

    async def get_size(self) -> int:
        """Get the number of items in the session."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE session_id = ?",
                (self.session_id,)
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    async def delete_items(self, *, limit: int | None = None) -> None:
        """Delete items from the session."""
        conn = self._get_connection()
        try:
            if limit is None:
                query = f"DELETE FROM {self.table_name} WHERE session_id = ?"
                params = [self.session_id]
            else:
                query = f"""
                    DELETE FROM {self.table_name} 
                    WHERE session_id = ? AND id IN (
                        SELECT id FROM {self.table_name} 
                        WHERE session_id = ? 
                        ORDER BY created_at ASC, id ASC 
                        LIMIT ?
                    )
                """
                params = [self.session_id, self.session_id, limit]
            
            conn.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    async def search_items(
        self,
        query: str,
        *,
        limit: int | None = None,
    ) -> list[TResponseInputItem]:
        """Search items in the session."""
        conn = self._get_connection()
        try:
            sql_query = f"""
                SELECT item_data FROM {self.table_name} 
                WHERE session_id = ? AND item_data LIKE ?
                ORDER BY created_at ASC, id ASC
            """
            params = [self.session_id, f"%{query}%"]
            
            if limit is not None:
                sql_query += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(sql_query, params)
            rows = cursor.fetchall()
            
            items: list[TResponseInputItem] = []
            for row in rows:
                try:
                    item = json.loads(row[0])
                    items.append(item)
                except json.JSONDecodeError:
                    # Skip invalid JSON
                    continue
            
            return items
        finally:
            conn.close()

    async def get_metadata(self) -> Dict[str, Any]:
        """Get session metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM {self.table_name} WHERE session_id = ?",
                (self.session_id,)
            )
            count, min_time, max_time = cursor.fetchone()
            
            return {
                "session_id": self.session_id,
                "item_count": count,
                "created_at": min_time,
                "updated_at": max_time,
            }
        finally:
            conn.close()

    async def close(self) -> None:
        """Close the session."""
        # SQLite connections are managed per-operation, so nothing to close
        pass


class SQLiteSession(Session):
    """SQLite session wrapper."""
    
    def __init__(
        self,
        *,
        db_path: str = ":memory:",
        session_id: str | None = None,
        table_name: str = "session_items",
    ) -> None:
        """Initialize SQLite session."""
        self._session = SQLiteSessionABC(
            db_path=db_path,
            session_id=session_id,
            table_name=table_name,
        )

    def __getattr__(self, name: str) -> Any:
        """Delegate to underlying session."""
        return getattr(self._session, name)


# Alias for convenience
SQLiteSessionABC = SQLiteSession