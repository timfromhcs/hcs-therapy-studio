# ADR-0006 — Local data encryption

- **Status:** accepted
- **Date:** 2026-11-04

## Context

The app stores journals and conversations. GDPR Article 9 treats health data as
a special category; a diary entry about mood is exactly that. SQLite on a shared
Windows profile is not automatically safe.

## Options

| Option | Verdict |
|---|---|
| SQLCipher | Strong, but adds a native dependency and a build problem on Windows |
| AES-256-GCM per field via `cryptography` | **chosen** |
| OS-level EFS / BitLocker only | not guaranteed on, and invisible to the user |
| No encryption, documented | unacceptable for a "private journal" claim |
| Encryption disabled | must be possible, but explicit and reversible |

## Decision

- Content columns (`messages.content`, `journal_entries.body`) are encrypted
  before reaching SQLite with AES-256-GCM, random 12-byte nonce per value,
  AAD bound to the schema version.
- Key: 32 random bytes in `<data dir>/content.key`, created `0o600`, never logged,
  never exported with the database.
- Metadata (timestamps, mood integer, tags, roles) stays plaintext so the app can
  list and filter without decrypting everything.
- Encryption can be turned off explicitly at first run; the column records which
  mode each row used, so a mixed database still reads correctly.
- Export produces a **decrypted** JSON the user chose to create; it is written to
  the exports folder and is their responsibility.
- Loss of the key means loss of content. This is stated in the UI and the README
  rather than hidden.

## Evidence

`tests/test_storage.py` asserts that the plaintext does not appear in the
database file, that a wrong key raises rather than returning garbage, and that a
corrupt key file is reported instead of silently re-generated.

## Consequences

- No full-text search over encrypted bodies without decrypting in memory. The
  journal list works on metadata; a search feature must decrypt.
- Multi-process access works because each thread opens its own connection and WAL
  is enabled.

## Rollback

A database can be re-written with `encrypt=False` via an explicit migration; the
per-row `encrypted` flag makes that safe.
