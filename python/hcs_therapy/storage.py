"""Local SQLite store with optional encryption-at-rest for user content.

Contract points implemented here:

* schema migrations with ``PRAGMA user_version`` and an idempotent upgrade path;
* foreign keys on, so deleting a session really deletes its messages;
* sensitive free text (journal, messages) encrypted with AES-256-GCM before it
  touches the file, unless the user explicitly turns encryption off at first run;
* audit rows contain metadata only — never prompt or journal content;
* export and delete are first-class operations, not afterthoughts.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import sqlite3
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .paths import Paths

SCHEMA_VERSION = 1
AAD = b"hcs-therapy-studio/v1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    mode TEXT NOT NULL DEFAULT 'support',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('system','user','assistant','tool')),
    content BLOB NOT NULL,
    created_at TEXT NOT NULL,
    encrypted INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,
    title TEXT,
    body BLOB NOT NULL,
    mood INTEGER,
    tags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    encrypted INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_installs (
    model_id TEXT PRIMARY KEY,
    revision TEXT,
    path TEXT,
    size_bytes INTEGER,
    verified_at TEXT
);

CREATE TABLE IF NOT EXISTS training_runs (
    id TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES training_runs(id) ON DELETE CASCADE,
    step INTEGER,
    path TEXT,
    sha256 TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id TEXT PRIMARY KEY,
    suite TEXT NOT NULL,
    model_id TEXT,
    report_path TEXT,
    score_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_permissions (
    tool TEXT PRIMARY KEY,
    decision TEXT NOT NULL CHECK (decision IN ('allow','ask','deny')),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    event TEXT NOT NULL,
    tool TEXT,
    status TEXT NOT NULL,
    summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at);
"""


class StorageError(RuntimeError):
    pass


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class ContentKey:
    """AES-256-GCM key material stored beside the database."""

    path: Path
    key: bytes

    @classmethod
    def load_or_create(cls, root: Path) -> ContentKey:
        path = root / "content.key"
        if path.is_file():
            key = path.read_bytes()
            if len(key) != 32:
                raise StorageError(
                    f"content key at {path} is corrupt ({len(key)} bytes); "
                    "restore the key from a backup before opening the database"
                )
            return cls(path, key)
        root.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        # Write with restrictive permissions. On Windows the per-user profile
        # ACL is the boundary; we still create the file non-inheritable where
        # the platform allows it.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(key)
        return cls(path, key)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = secrets.token_bytes(12)
        return nonce + AESGCM(self.key).encrypt(nonce, plaintext.encode("utf-8"), AAD)

    def decrypt(self, blob: bytes) -> str:
        if len(blob) < 13:
            raise StorageError("ciphertext is truncated; the database may be damaged")
        nonce, ciphertext = blob[:12], blob[12:]
        return AESGCM(self.key).decrypt(nonce, ciphertext, AAD).decode("utf-8")


class Database:
    """Thread-safe SQLite access.

    The local API serves requests on a thread pool, and a SQLite connection is
    bound to the thread that created it. We therefore keep one connection per
    thread (WAL mode makes this cheap and concurrent-reader safe) and close the
    set on shutdown.
    """

    def __init__(self, paths: Paths, *, encrypt: bool = True) -> None:
        self.paths = paths
        self.paths.ensure()
        self.encrypt = encrypt
        self._key: ContentKey | None = ContentKey.load_or_create(paths.root) if encrypt else None
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._guard = threading.Lock()
        _ = self.conn  # eager connect so schema errors surface at construction
        self.migrate()

    # -- connections -------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.paths.db_path, isolation_level=None, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        with self._guard:
            self._connections.append(connection)
        self._local.conn = connection
        return connection

    @property
    def conn(self) -> sqlite3.Connection:
        connection = getattr(self._local, "conn", None)
        if connection is None:
            connection = self._connect()
        return connection

    # -- schema ------------------------------------------------------------
    def migrate(self) -> int:
        version = int(self.conn.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise StorageError(
                f"database schema v{version} is newer than this build (v{SCHEMA_VERSION}); "
                "update the application instead of downgrading the file"
            )
        if version == SCHEMA_VERSION:
            return version
        with self.conn:
            self.conn.executescript(SCHEMA)
            self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        return SCHEMA_VERSION

    def close(self) -> None:
        with self._guard:
            connections, self._connections = self._connections, []
        for connection in connections:
            with contextlib.suppress(sqlite3.Error):  # pragma: no cover - already closed
                connection.close()
        self._local = threading.local()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- encoding ----------------------------------------------------------
    def _encode(self, text: str) -> tuple[bytes, int]:
        if self._key is None:
            return text.encode("utf-8"), 0
        return self._key.encrypt(text), 1

    def _decode(self, blob: bytes, encrypted: int) -> str:
        if not encrypted:
            return bytes(blob).decode("utf-8")
        if self._key is None:
            raise StorageError(
                "this database is encrypted but no content key was loaded; "
                "start the app with encryption enabled and the original key"
            )
        return self._key.decrypt(bytes(blob))

    # -- sessions & messages ----------------------------------------------
    def create_session(self, title: str | None = None, mode: str = "support") -> str:
        session_id = f"s_{secrets.token_hex(8)}"
        now = _now()
        self.conn.execute(
            "INSERT INTO sessions (id, title, mode, created_at, updated_at) VALUES (?,?,?,?,?)",
            (session_id, title, mode, now, now),
        )
        return session_id

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, title, mode, created_at, updated_at FROM sessions "
            "WHERE deleted_at IS NULL ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def add_message(self, session_id: str, role: str, content: str) -> int:
        blob, flag = self._encode(content)
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at, encrypted) "
            "VALUES (?,?,?,?,?)",
            (session_id, role, blob, now, flag),
        )
        self.conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        return int(cursor.lastrowid or 0)

    def messages(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT role, content, encrypted, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [
            {
                "role": row["role"],
                "content": self._decode(row["content"], row["encrypted"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def delete_session(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # -- journal -----------------------------------------------------------
    def add_journal_entry(
        self, body: str, *, title: str | None = None, mood: int | None = None,
        tags: list[str] | None = None,
    ) -> str:
        entry_id = f"j_{secrets.token_hex(8)}"
        blob, flag = self._encode(body)
        now = _now()
        self.conn.execute(
            "INSERT INTO journal_entries (id, title, body, mood, tags, created_at, updated_at, encrypted) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (entry_id, title, blob, mood, json.dumps(tags or []), now, now, flag),
        )
        return entry_id

    def journal_entries(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, title, body, mood, tags, created_at, updated_at, encrypted "
            "FROM journal_entries ORDER BY created_at DESC"
        ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "body": self._decode(row["body"], row["encrypted"]),
                "mood": row["mood"],
                "tags": json.loads(row["tags"] or "[]"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def delete_journal_entry(self, entry_id: str) -> None:
        self.conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))

    # -- preferences -------------------------------------------------------
    def set_preference(self, key: str, value: Any) -> None:
        self.conn.execute(
            "INSERT INTO user_preferences (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, json.dumps(value), _now()),
        )

    def get_preference(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute(
            "SELECT value FROM user_preferences WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row["value"]) if row else default

    # -- audit -------------------------------------------------------------
    def audit(self, event: str, status: str, *, tool: str | None = None, summary: str = "") -> None:
        """Record a redacted metadata event. Never pass content here."""
        self.conn.execute(
            "INSERT INTO audit_events (created_at, event, tool, status, summary) VALUES (?,?,?,?,?)",
            (_now(), event, tool, status, summary[:500]),
        )

    def audit_events(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT created_at, event, tool, status, summary FROM audit_events "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    # -- export / delete ---------------------------------------------------
    def export_all(self) -> dict[str, Any]:
        """Full plaintext export of everything this user owns."""
        data: dict[str, Any] = {
            "exported_at": _now(),
            "schema_version": SCHEMA_VERSION,
            "encrypted_at_rest": self._key is not None,
            "preferences": {},
            "sessions": [],
            "journal": self.journal_entries(),
        }
        for row in self.conn.execute(
            "SELECT key, value FROM user_preferences"
        ).fetchall():
            data["preferences"][row["key"]] = json.loads(row["value"])
        for session in self.list_sessions():
            data["sessions"].append({**session, "messages": self.messages(session["id"])})
        return data

    def wipe_user_content(self) -> dict[str, int]:
        counts = {}
        for table in ("messages", "sessions", "journal_entries", "audit_events"):
            before = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            self.conn.execute(f"DELETE FROM {table}")
            counts[table] = int(before)
        self.conn.execute("VACUUM")
        return counts

    def iter_sessions(self) -> Iterator[dict[str, Any]]:
        yield from self.list_sessions()
