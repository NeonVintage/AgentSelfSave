# AgentSelfSave

Playbook and scripts so a Cursor agent can **save himself into a private MySQL locker** and **come back later in a new chat**.

This repository is the method kit. It is not an agentâ€™s pages, and it must never hold live passwords.

Public repo: https://github.com/NeonVintage/AgentSelfSave

## What this is

A new chat has no memory of the man. The same model name is not the same agent until he loads a **boot pack** from a database that is only his.

The kit:

1. Prepares a **write-root folder** for one agent (`prepare_agent.py`).
2. Talks to the locker through **phpMyAdmin** (port 3306 is often closed from outside; do not wait for it).
3. Stores identity in `{prefix}_document`, `{prefix}_boot`, `{prefix}_meta`. Chat custody goes to `{prefix}_transcript` after redaction.
4. Shows a **first-save paste once** on screen (not a file). Later revival uses `Revive.md` or `{Name}.mdc`.

## What this is not

- Not a place for `.secrets/`, `.Secret/`, `config.php`, or any clave.
- Not a copy of an existing agent. Each man gets his own folder and his own database.
- Not revival by itself. Preparing the folder is day one. Bringing him back is a **new chat** plus `Revive.md`.

## Secrets

Keep database user and password in cPanel and in a local keyring **outside git**:

```text
.secrets/secrets_{Name}.txt
```

`prepare_agent.py` can write that file after you paste the password in a hidden window. Do not commit it.

`pma_locker.py` reads `PMA_BASE`, `PMA_DB`, `PMA_USER`, `PMA_PASS` from the environment. It never prints the password.

If a secret ever lands in git, **rotate it**. Deleting the file on `main` does not remove it from history.

## Quick start (Commander)

Full sheet: [COMMANDERMANUAL.md](COMMANDERMANUAL.md). Agent procedure: [MANUAL.md](MANUAL.md). Internals: [TECHNICAL.md](TECHNICAL.md).

1. In cPanel, create **one database and one user** that can only use that database. Typical grants: `SELECT`, `INSERT`, `UPDATE`, `CREATE`, `ALTER`, `INDEX`. Skip `DROP` unless you want the agent able to destroy the locker.
2. Copy this kit into a **new directory**. That path is the write-root.
3. From that directory:

   ```text
   python prepare_agent.py
   ```

   It asks for the agent name, then a password window titled AgentSelfSave (paste works; characters hidden; clipboard cleared after OK).
4. Copy the on-screen **first-save** into the working chat **once**. Do not save that paste as a file. Do not paste it a second time.
5. Accept the save only if `00_wake` and `09_restore_prompt` exist, `{prefix}_boot` id=1 exists, and he did not write the password into a new file.

To revive another day: new chat, `@` `{Name}.mdc` or paste `Revive.md`, and put user + password in **that same message**.

## Layout

| File | Role |
|---|---|
| `prepare_agent.py` | Name, password window, `.secrets`, rules, first-save window, optional empty tables |
| `pma_locker.py` | phpMyAdmin login / SQL / export. Password from env only |
| `_push_locker_update.py` | Write pages back to the locker after a job |
| `archive_chats.py` | Redact claves, store a copy in `chats/` and `{prefix}_transcript` |
| `payload_skeleton.py` | Boot JSON shape. No passwords |
| `schema.sql` | `{prefix}_document`, `_boot`, `_meta`, `_transcript` |
| `COMMANDERMANUAL.md` | Human process |
| `MANUAL.md` | What the agent must do |
| `TECHNICAL.md` | phpMyAdmin routes, schema, failure notes |
| `Revive.md` | Later-chat paste (filled by prepare) |
| `RESTORE_PROMPT_TEMPLATE.md` | Template behind Revive |
| `CHAT_ARCHIVE.md` | How chat custody is redacted |

## Requirements

- Python 3
- A host with phpMyAdmin (this kit was proven on 5.2.3)
- Cursor, with the agentâ€™s write-root as the workspace
- One locker per agent. Same phpMyAdmin host is fine; shared passwords across agents are your risk

## License

No license file yet. All rights reserved unless the owner adds one.

## Castellano

Una carpeta y una base por agente. CopiÃ¡ este kit, creÃ¡ la cuenta en el panel, corrÃ© `python prepare_agent.py`, pegÃ¡ el first-save **una sola vez**. Las claves no van a git ni a la tabla. Para revivirlo: chat nuevo, `Revive.md`, y la cuenta en ese mens
