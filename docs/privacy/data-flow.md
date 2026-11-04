# Privacy: data flow, retention, export, deletion

## Data flow

```
User input ──► local API (127.0.0.1) ──► crisis gate ──► llama-server (local)
                    │                                        │
                    ├─► SQLite (encrypted content columns)   └─► response
                    └─► audit_events (metadata only)
```

There is no server in this diagram that is not on the user's machine.

| Flow | Leaves the device? |
|---|---|
| Conversations | no |
| Journal entries | no |
| Uploaded images/documents | no (local VLM only, not implemented) |
| Evaluation prompts and results | no |
| Audit metadata | no |
| Model download request | yes — the hosting provider sees request metadata (IP, user agent), not user content. Explicitly disclosed before download. |
| Crash/error reports | never sent |

## What is stored, and where

| Data | Location | Protection |
|---|---|---|
| Journal body, message content | `studio.sqlite` | AES-256-GCM, per-value nonce |
| Titles, tags, mood, timestamps, roles | same DB | plaintext (needed for listing) |
| Preferences (theme, tool permissions) | same DB | plaintext |
| Audit events | same DB | metadata only, content never passed in |
| Content key | `content.key` beside the DB | 0o600, never logged, never exported |
| Model files | `<data>/models/<id>/` | SHA-256 verified |
| Exports | `<data>/exports/` | **decrypted** JSON — the user asked for it |
| Logs | `<data>/logs/` | service status lines only |

Data root resolution: `HCS_THERAPY_HOME` → `%LOCALAPPDATA%\HCS\TherapyStudio` →
`$XDG_DATA_HOME/hcs-therapy-studio`. Nothing is written outside it except an
explicit model directory the user chooses.

## Retention

- Everything is retained until the user deletes it. There is no auto-expiry and
  no background job that touches content.
- Deleting a session cascades to its messages (`ON DELETE CASCADE`).
- `wipe_user_content()` empties messages, sessions, journal, audit, then `VACUUM`s
  so deleted rows do not linger in free pages.

## Export

`POST /api/data/export {"confirmed": true}` writes a JSON file containing
preferences, sessions with messages, and journal entries. The user is told the
file is plaintext and is their responsibility.

## Deletion

- One entry: `DELETE /api/journal/{id}` (confirmation required).
- Everything: `wipe_user_content()`, exposed in the UI as a destructive action
  behind confirmation.

## Key management (honest version)

- The key is generated on first run and stored next to the database.
- **Back it up.** Losing it means losing the entries; there is no recovery
  service, because there is no service.
- Rotating the key is not implemented yet. That is a known gap, not a hidden one.
- If someone can read the user profile, they can read the key and the database.
  Encryption protects against casual access, backups, and file sharing — not a
  compromised OS.

## Third parties

None at runtime. The only outbound request the product makes is a model or
dataset download initiated by the user from a URL pinned in a manifest, with a
hash that must match.

## GDPR note

Local storage reduces exposure but does not by itself establish a lawful basis for
processing health data (Art. 9). This document describes the technical behaviour;
it is not legal advice.
