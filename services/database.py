"""
数据库服务 - SQLite 实现
提供 ontology、conversation、message、run 的 CRUD 操作
"""
import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


def _get_db_path() -> Path:
    """获取数据库文件路径"""
    base_dir = Path(__file__).parent.parent
    db_dir = base_dir / "data"
    db_dir.mkdir(exist_ok=True)
    return db_dir / "nextstudio.db"


class DatabaseService:
    """
    SQLite 数据库服务
    提供 ontology、conversation、message、run 的 CRUD 操作
    """

    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def initialize(self):
        """初始化数据库连接并创建表"""
        if self._conn is not None:
            return

        db_path = _get_db_path()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        print(f"SQLite database initialized: {db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.initialize()
        return self._conn

    def _create_tables(self):
        """创建所有表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Ontologies 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ontologies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                yaml_content TEXT NOT NULL,
                version TEXT DEFAULT '1.0.0',
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)

        # Conversations 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                ontology_id TEXT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (ontology_id) REFERENCES ontologies(id)
            )
        """)

        # Messages 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # Runs 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        conn.commit()

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    # ========== Ontology CRUD ==========

    def create_ontology(self, name: str, description: str, yaml_content: str, version: str = "1.0.0") -> Optional[Dict[str, Any]]:
        """创建 ontology"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            oid = self._new_id()
            now = self._now()
            try:
                conn.execute(
                    "INSERT INTO ontologies (id, name, description, yaml_content, version, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (oid, name, description, yaml_content, version, now)
                )
                conn.commit()
                return {
                    "id": oid,
                    "name": name,
                    "description": description,
                    "yaml_content": yaml_content,
                    "version": version,
                    "created_at": now,
                }
            except Exception as e:
                print(f"Error creating ontology: {e}")
                return None

    def get_ontology(self, ontology_id: str) -> Optional[Dict[str, Any]]:
        """获取单个 ontology"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            try:
                cursor = conn.execute("SELECT * FROM ontologies WHERE id = ?", (ontology_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                print(f"Error getting ontology: {e}")
                return None

    def list_ontologies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """列出所有 ontologies"""
        if not self.is_connected:
            return []

        conn = self._get_conn()
        with self._lock:
            try:
                cursor = conn.execute(
                    "SELECT * FROM ontologies ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error listing ontologies: {e}")
                return []

    def update_ontology(self, ontology_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新 ontology"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            data["updated_at"] = self._now()
            try:
                fields = ", ".join(f"{k} = ?" for k in data.keys())
                conn.execute(
                    f"UPDATE ontologies SET {fields} WHERE id = ?",
                    (*data.values(), ontology_id)
                )
                conn.commit()
                return self.get_ontology(ontology_id)
            except Exception as e:
                print(f"Error updating ontology: {e}")
                return None

    def delete_ontology(self, ontology_id: str) -> bool:
        """删除 ontology"""
        if not self.is_connected:
            return False

        conn = self._get_conn()
        with self._lock:
            try:
                conn.execute("DELETE FROM ontologies WHERE id = ?", (ontology_id,))
                conn.commit()
                return True
            except Exception as e:
                print(f"Error deleting ontology: {e}")
                return False

    # ========== Conversation CRUD ==========

    def create_conversation(self, ontology_id: str, title: str) -> Optional[Dict[str, Any]]:
        """创建对话"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            oid = self._new_id()
            now = self._now()
            try:
                conn.execute(
                    "INSERT INTO conversations (id, ontology_id, title, created_at) VALUES (?, ?, ?, ?)",
                    (oid, ontology_id, title, now)
                )
                conn.commit()
                return {"id": oid, "ontology_id": ontology_id, "title": title, "created_at": now}
            except Exception as e:
                print(f"Error creating conversation: {e}")
                return None

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            try:
                cursor = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                print(f"Error getting conversation: {e}")
                return None

    def list_conversations(self, ontology_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """列出对话"""
        if not self.is_connected:
            return []

        conn = self._get_conn()
        with self._lock:
            try:
                if ontology_id:
                    cursor = conn.execute(
                        "SELECT * FROM conversations WHERE ontology_id = ? ORDER BY created_at DESC LIMIT ?",
                        (ontology_id, limit)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ?",
                        (limit,)
                    )
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error listing conversations: {e}")
                return []

    # ========== Message CRUD ==========

    def create_message(self, conversation_id: str, role: str, content: str, intent: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """创建消息"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            oid = self._new_id()
            now = self._now()
            try:
                conn.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, intent, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (oid, conversation_id, role, content, intent, now)
                )
                conn.commit()
                return {"id": oid, "conversation_id": conversation_id, "role": role, "content": content, "intent": intent, "created_at": now}
            except Exception as e:
                print(f"Error creating message: {e}")
                return None

    def list_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """列出对话的所有消息"""
        if not self.is_connected:
            return []

        conn = self._get_conn()
        with self._lock:
            try:
                cursor = conn.execute(
                    "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                    (conversation_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error listing messages: {e}")
                return []

    # ========== Run CRUD ==========

    def create_run(self, conversation_id: str, message: str) -> Optional[Dict[str, Any]]:
        """创建运行记录"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            oid = self._new_id()
            now = self._now()
            try:
                conn.execute(
                    "INSERT INTO runs (id, conversation_id, message, status, created_at) VALUES (?, ?, ?, ?, ?)",
                    (oid, conversation_id, message, "pending", now)
                )
                conn.commit()
                return {"id": oid, "conversation_id": conversation_id, "message": message, "status": "pending", "created_at": now}
            except Exception as e:
                print(f"Error creating run: {e}")
                return None

    def update_run_status(self, run_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """更新运行状态"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            import json
            data = {"status": status}
            if result:
                data["result"] = json.dumps(result)
            if status in ("completed", "error", "aborted"):
                data["completed_at"] = self._now()

            try:
                fields = ", ".join(f"{k} = ?" for k in data.keys())
                conn.execute(f"UPDATE runs SET {fields} WHERE id = ?", (*data.values(), run_id))
                conn.commit()
                return self.get_run(run_id)
            except Exception as e:
                print(f"Error updating run status: {e}")
                return None

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """获取运行记录"""
        if not self.is_connected:
            return None

        conn = self._get_conn()
        with self._lock:
            try:
                cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                print(f"Error getting run: {e}")
                return None

    def list_runs(self, conversation_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """列出运行记录"""
        if not self.is_connected:
            return []

        conn = self._get_conn()
        with self._lock:
            try:
                if conversation_id:
                    cursor = conn.execute(
                        "SELECT * FROM runs WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
                        (conversation_id, limit)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
                        (limit,)
                    )
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error listing runs: {e}")
                return []


# 全局实例
_database_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """获取数据库服务实例"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
        _database_service.initialize()
    return _database_service
