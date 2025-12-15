# umb.py (Universal Memory Bus)
import sqlite3
import threading
import json
import uuid
from datetime import datetime

class UniversalMemoryBus:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path="genesis_memory.db"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UniversalMemoryBus, cls).__new__(cls)
                cls._instance.db_path = db_path
                cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            # Core memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS short_term_memory (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def log_interaction(self, session_id, role, content):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            entry_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO short_term_memory (id, session_id, role, content) VALUES (?, ?, ?, ?)",
                (entry_id, session_id, role, str(content))
            )
            conn.commit()

    def get_recent_context(self, session_id, limit=5):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM short_term_memory WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

# Singleton Accessor
def get_memory_bus():
    return UniversalMemoryBus()