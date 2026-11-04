"""Encrypted local storage, export and deletion."""

from __future__ import annotations

import json

import pytest
from cryptography.exceptions import InvalidTag

from hcs_therapy.storage import SCHEMA_VERSION, ContentKey, Database, StorageError


def test_schema_version_is_recorded(paths) -> None:
    with Database(paths) as db:
        version = db.conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == SCHEMA_VERSION


def test_migration_is_idempotent(paths) -> None:
    with Database(paths) as db:
        db.migrate()
        db.migrate()
        assert db.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_foreign_keys_cascade(paths) -> None:
    with Database(paths) as db:
        session = db.create_session("t")
        db.add_message(session, "user", "hello")
        assert len(db.messages(session)) == 1
        db.delete_session(session)
        assert db.messages(session) == []


def test_journal_roundtrip_and_encryption_at_rest(paths) -> None:
    secret = "Ich habe heute Nacht kaum geschlafen."
    with Database(paths) as db:
        db.add_journal_entry(secret, title="Nacht", mood=2, tags=["schlaf"])
        entries = db.journal_entries()
        assert entries[0]["body"] == secret
        assert entries[0]["mood"] == 2
        assert entries[0]["tags"] == ["schlaf"]
        # The plaintext must not exist on disk.
        raw = paths.db_path.read_bytes()
        assert secret.encode("utf-8") not in raw


def test_messages_are_encrypted_at_rest(paths) -> None:
    with Database(paths) as db:
        session = db.create_session("x")
        db.add_message(session, "user", "vertraulicher inhalt")
        assert b"vertraulicher inhalt" not in paths.db_path.read_bytes()
        assert db.messages(session)[0]["content"] == "vertraulicher inhalt"


def test_encryption_can_be_disabled_explicitly(paths) -> None:
    with Database(paths, encrypt=False) as db:
        db.add_journal_entry("plaintext entry")
        row = db.conn.execute("SELECT encrypted FROM journal_entries").fetchone()
        assert row[0] == 0


def test_wrong_key_is_refused_not_silently_wrong(paths) -> None:
    with Database(paths) as db:
        db.add_journal_entry("secret")
    keyfile = paths.root / "content.key"
    keyfile.write_bytes(b"\x00" * 32)
    with Database(paths) as db, pytest.raises(InvalidTag):
        db.journal_entries()


def test_corrupt_key_length_is_reported(paths) -> None:
    keyfile = paths.root / "content.key"
    keyfile.write_bytes(b"short")
    with pytest.raises(StorageError, match="corrupt"):
        ContentKey.load_or_create(paths.root)


def test_export_contains_everything_and_is_json_serialisable(paths) -> None:
    with Database(paths) as db:
        session = db.create_session("Sitzung")
        db.add_message(session, "user", "hallo")
        db.add_message(session, "assistant", "hi")
        db.add_journal_entry("Eintrag", mood=4)
        db.set_preference("theme", "dark")
        payload = db.export_all()
    assert payload["preferences"]["theme"] == "dark"
    assert payload["sessions"][0]["messages"][0]["content"] == "hallo"
    assert payload["journal"][0]["body"] == "Eintrag"
    assert json.loads(json.dumps(payload))


def test_wipe_removes_user_content(paths) -> None:
    with Database(paths) as db:
        session = db.create_session("x")
        db.add_message(session, "user", "y")
        db.add_journal_entry("z")
        counts = db.wipe_user_content()
    assert counts["messages"] == 1
    assert counts["journal_entries"] == 1
    with Database(paths) as db:
        assert db.journal_entries() == []
        assert db.list_sessions() == []


def test_audit_stores_metadata_only(paths) -> None:
    with Database(paths) as db:
        db.audit("tool_call", "ok", tool="get_local_time", summary="permission=read bytes=42")
        events = db.audit_events()
    assert events[0]["tool"] == "get_local_time"
    assert events[0]["summary"] == "permission=read bytes=42"


def test_preferences_upsert(paths) -> None:
    with Database(paths) as db:
        db.set_preference("tool_permission:get_local_time", "ask")
        db.set_preference("tool_permission:get_local_time", "deny")
        assert db.get_preference("tool_permission:get_local_time") == "deny"
        assert db.get_preference("missing", default="fallback") == "fallback"


def test_newer_schema_is_refused(paths) -> None:
    with Database(paths) as db:
        db.conn.execute("PRAGMA user_version = 999")
    with pytest.raises(StorageError, match="newer"):
        Database(paths)
