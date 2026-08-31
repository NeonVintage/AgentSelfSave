# Chat archive

Cursor can delete a thread. The locker pages are enough to revive the man. This archive keeps a redacted copy of **this agent's** chats so the talk itself is not lost.

## What to do

From the write-root (or the kit, with `--write-root`):

```
python archive_chats.py
```

It will:

1. Find Cursor `agent-transcripts` that belong to this agent (this workspace, ids already in the boot pack, or a wake line that names him).
2. Keep user and assistant text. Drop tool dumps.
3. Replace locker passwords from `.Secret/` / `.secret/` / `.secrets/` with `[REDACTED:locker-pass]`.
4. Write `chats/<id>/redacted.md` and `chats/index.json` (SHA-256). No unredacted copy.
5. `CREATE TABLE IF NOT EXISTS {prefix}_transcript` and upsert those rows in Kansas.

`--dry-run` prints counts. `--no-push` writes local files only.

## Law

- Kansas gets redacted text only. Claves stay with the Commander.
- A hash cannot give a password back. Retrieve the clave from `.Secret/`, not from the table.
- Do not archive another agent's chats.
- If a clave is still visible after redaction, that chat is skipped.
- Revival does not read this table. `00_wake` first, then `job_state`.
- Locker close: after a finished order, run `_push_locker_update.py` then this script. Do not wait for the Commander to say save.

## Local folder

`chats/` is custody on disk. Do not commit it to a public repo.
