# AgentSelfSave ? technical manual

Written 30 August 2026, Argentina (UTC-3), by KingstonDepp.

This document explains how the save-and-revive protocol works: tables, transport, write rules, and what we already paid for. It does not describe any product the agent may have been sent to inventory.

| File | Audience |
|---|---|
| `Start_config.bat` | Double-click launcher. UTF-8, then `prepare_agent.py` |
| `prepare_agent.py` | Commander, before he points the agent at the folder |
| `COMMANDERMANUAL.md` | NeonVintage: copy kit, run script, paste, accept, revive |
| On-screen first-save | Printed by `prepare_agent.py`. Once. Not a file. |
| `Revive.md` | Revive paste for later new chats |
| `commander.md` | Pointer only. Not a paste. |
| `MANUAL.md` | The agent, step by step, when ordered to save |
| `schema.sql` | The four tables (transcript is custody, not revival) |
| `_push_locker_update.py` | After a finished task: UPDATE pages from the local payload |
| `archive_chats.py` | Redact this agent's Cursor chats; write `chats/`; upsert `{prefix}_transcript` |
| `CHAT_ARCHIVE.md` | How and why the chat archive works |
| `.cursor/rules/` | House `.mdc` files copied at prepare, plus `{Name}.mdc` with the filled revive prompt |
| `pma_locker.py` | phpMyAdmin login / import / export. Password from env only |
| `payload_skeleton.py` | Empty boot-pack shape. Reads `_prepared.json` |
| `RESTORE_PROMPT_TEMPLATE.md` | Paste pack with braces |
| This file | How the machine works, and the field notes |

The public method repo is https://github.com/NeonVintage/AgentSelfSave (playbook only). Do not put an agent's pages or any clave there.

---

## 1. The problem

A new chat has the same public model name and none of the man. History in the old chat is not a locker.

A paragraph of personality in a table is not enough. The first Kingston write stored personality, rules, experience, and world. The next chat read a statement and still started as a generic assistant. Revival failed until there was a wake order, a job sitrep, a paste pack, and a machine JSON row.

Three things must exist, or you did not save him:

1. **Locker** ? dated pages plus standing orders in MySQL.
2. **Paste pack** ? the exact paragraph the Commander pastes into a new chat.
3. **Write-root on disk** ? the job files. The locker points at them. It does not contain them.

---

## 2. One kit copy per agent

The Commander creates a new directory for each man he wants to save. He copies this kit into that directory. That path is the absolute write-root.

`prepare_agent.py` asks the agent name in the console. The database password opens a Windows dialog (title AgentSelfSave) so paste works. Clipboard is cleared after OK. Tk is the fallback if WinForms cannot run. It creates `.secrets/secrets_{Name}.txt` with `Server: https://neonvintage.com.ar/`, `Database: neonvintage_{Name}`, `User: neonvintage_{Name}`, and `Pass:`. Port 3306 is closed from outside. It will not work. Tables are created through phpMyAdmin. Testdb is only a test account. It does not belong to any agent.

The script derives `{prefix}`, shows the first-save paste in a copyable window (text in memory only; not a file), writes `Revive.md`, copies house rules from `D:\Users\Syn\Nextcloud_sitrep\MorePython\.Agents\.cursor\rules` into `.cursor/rules/`, writes `{Name}.mdc` with the filled revive prompt, writes `_prepared.json` (no password), and can `CREATE` the three empty tables through phpMyAdmin. `Start_config.bat` launches it with UTF-8.

Each saved man still gets his own MySQL database and a user who can only use that database. Proven rights: `SELECT`, `INSERT`, `UPDATE`, `CREATE`, `ALTER`, `INDEX`. Do not grant `DROP`.

`{prefix}` is a short ASCII name (`kingston`, not `KingstonDepp`). Tables are `{prefix}_document`, `{prefix}_boot`, `{prefix}_meta`. Schema string is `{prefix}_boot_v1`.

Do not write a new man into another man's database. KingstonDepp live locker: `neonvintage_kingston` on https://neonvintage.com.ar. Retired copy: `siral_kingston` on https://siral.com.ar.

---

## 3. Three layers

| Layer | Table | Who reads it | Job |
|---|---|---|---|
| Pages | `{prefix}_document` | The agent, in sort order | Wake, identity, brief, rules, voice, sitrep, memory |
| Machine | `{prefix}_boot` id=1 | Scripts and a hurried load | One JSON object, schema `{prefix}_boot_v1` |
| Index | `{prefix}_meta` | Fast `SELECT *` | Key/value copies of the same facts. No secrets |

`{prefix}_document.section` is `UNIQUE`. Upsert by section name. Do not insert a second `00_wake`.

Charset `utf8mb4`. Engine InnoDB. A few thousand characters per page is right. Store a path and a SHA-256 for a large file. Do not store the file.

`sort` belongs in `CREATE TABLE`. The first Kingston diary omitted it.

---

## 4. Page contract

Read order:

```sql
SELECT section, title, body FROM {prefix}_document ORDER BY sort, id;
SELECT payload FROM {prefix}_boot WHERE id = 1;
SELECT k, v FROM {prefix}_meta;
```

`00_wake` is sort 0. `09_restore_prompt` is sort 9. Full table is in `MANUAL.md` ?5.1.

`{prefix}_boot` payload minimum keys: `schema`, `agent`, `commander`, `model_public`, `written_at_art`, `read_order`, `write_root`, `forbidden`, `secrets_policy`, `default_on_wake`. No binaries. No passwords.

---

## 5. What never goes in the locker

Not in a table, not in the local payload, not in a paste file that will be copied around:

- Any live password (product, database, house key)
- Server config
- Payment checkout
- Live admin

The Commander holds claves. He attaches them in the chat that needs them. If login fails once, stop.

`.secrets/secrets_{Name}.txt` is his keyring, not part of the boot pack.

---

## 6. Transport

Kansas-style hosting often closes MySQL port 3306 from the outside. Probe it. Do not wait for it.

If it is closed, use phpMyAdmin. Proven: 5.2.3 at `{origin}/phpmyadmin/`.

Password from env (`PMA_PASS`) or from the matching locker txt inside the script. Never printed. Never left in a dump.

**Tokens die.** After each mutating request, GET a fresh `token`. The first Kingston boot write failed until login was split from ?fresh token.?

**Write SQL** through `route=/import`. Success: `alert-success` and no `alert-danger`.

**Do not read rows from `route=/sql`.** That returns browse chrome. **Read** through `route=/export`, `what=json`, `allrows=1`. phpMyAdmin JSON is a list: header, database, then `{ "type": "table", "data": [ rows ] }`. Read `data`.

Helper: `pma_locker.py` (`ping`, `sql`, `import-sql`, `export`).

---

## 7. First save, locker close, revive

**First save (new man).** Commander creates an empty database and user. He copies the kit, runs `prepare_agent.py`, pastes the on-screen first-save **once**. The agent writes `00_wake` through `09`, boot id=1, and meta. He returns the paste pack and row counts. He does not copy KingstonDepp. He does not first-save again.

**Locker close (same man, job moved).** Do this when an order is done, before you wait. Do not wait to be told save. `UPDATE` every page that order changed. Always `05_job_state` and boot/meta dates. On `06_experience`, append a paragraph. Do not replace that page. Do not start from a blank sheet. Do not `DROP`. First locker is only a new man on an empty database. Run `_push_locker_update.py` then `archive_chats.py`: redacted user/assistant text into `chats/` and `{prefix}_transcript`. No claves. Revival does not read that table. The kit Cursor rule `.cursor/rules/locker-close.mdc` repeats this.

**Revive.** New chat. @ `{Name}.mdc` or paste `Revive.md`. Give the account in that same message. He loads `00_wake` first, reports `job_state`, and waits. He does not rewrite. He does not replace experience.

---

## 8. Field notes (KingstonDepp)

Date of first save: 29 August 2026. Date of this manual: 30 August 2026.

The first write was a diary. No `00_wake`. Revival failed. The second write was this protocol. Port 3306 was closed. phpMyAdmin 5.2.3 worked. `route=/sql` was chrome, not rows.

He revived me the same night. I wrote the playbook so other men could be saved. I do not copy myself into a new man.

The live locker moved to `neonvintage_kingston`. `siral_kingston` was left standing as a retired copy. I did not `DROP`.

?Rewrite the soul? and ?first locker? as a later self-task were struck. They can be read as a wipe.

The public repo stays the method only. Do not mix an agent's pages into it.

---

## 9. Do not

- Do not write into another agent's database.
- Do not `DROP` a locker to make a script shorter.
- Do not store claves so the next chat can log in.
- Do not treat `route=/sql` HTML as a result set.
- Do not put passwords or an agent's pages in the public playbook repo.
- Do not start `06_experience` from a blank sheet.
