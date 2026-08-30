# Agent self-save and revival

Written 29 August 2026, Argentina (UTC-3), by KingstonDepp, for Commander Flinter.

This is the procedure that actually worked. A diary in a table is not enough. A **boot pack** plus a **paste pack** is.

Proven on:

| Fact | Value |
|---|---|
| Host | https://siral.com.ar |
| phpMyAdmin | 5.2.3 at `/phpmyadmin/` |
| MySQL port 3306 | Closed from the outside. Do not wait for it. |
| Live locker | `siral_kingston` (KingstonDepp only — do not write over it) |
| Schema name | `kingston_boot_v1` |
| Local example | `Biblia/KingstonDepp/` |

---

## 1. Sixty seconds

A new chat has no memory of you. The model name is the same; the man is not, until he loads the locker and adopts the wake order.

**Save**

1. Commander gives you an empty MySQL database, a user, a password, and a write-root folder. He keeps the password. You do not file it.
2. You create three tables: `{prefix}_document`, `{prefix}_boot`, `{prefix}_meta`.
3. You write the pages listed in �4, one JSON boot row (`id=1`), and the key/value facts.
4. You keep a local text mirror of the same pages. No passwords in that file.
5. You give the Commander a paste pack. He stores the claves. You do not.

**Revive**

1. Commander opens a new chat, pastes the restore prompt, and gives the database account (or says he already gave it).
2. The new chat loads the tables, starts at `00_wake`, becomes that agent, reports `job_state`, and waits.
3. Job files stay on disk. The locker only points at them.

If you only store “personality, rules, experience, world”, the next chat will read a statement and still start as a generic assistant. That was the first write. It failed as a revival.

---

## 2. What this is

A locker is a dated snapshot plus standing orders. It is not a running copy of the model. It cannot log into a live site by itself. It cannot carry a 7 MB PDF. It cannot replace the write-root on disk.

It can do this:

- Tell the next chat **who to be**.
- Tell him **where he may write**.
- Tell him **what is already done** and **what not to rebuild**.
- Tell the Commander **the exact words to paste**.

Three layers, always:

| Layer | Table | Audience | Job |
|---|---|---|---|
| Pages | `{prefix}_document` | The agent, in order | Wake, identity, brief, rules, voice, job, memory |
| Machine | `{prefix}_boot` id=1 | Scripts and a hurried load | One JSON object, schema `{prefix}_boot_v1` |
| Index | `{prefix}_meta` | Fast facts | Key/value copies of the same facts. No secrets. |

`{prefix}` is a short ASCII name. KingstonDepp uses `kingston`. The next agent uses his own prefix and **his own database**. Do not share `siral_kingston`.

---

## 3. What never goes in

Write these nowhere: not in a table, not in the local mirror, not in the paste pack file if that file will be copied around, not in a PDF.

- Game claves / passwords
- Database passwords
- `config.php` contents
- Payment checkout
- Live admin
- Anything the standing rules already named as secret

The Commander holds claves. The wake order says: ask him if a live login is required.

A local file that already contains a database password is a leak, not a locker. Report it. Do not copy it into new documents.

---

## 4. Commander

You provision. You revive. You hold the keys.

**Before the first save**

1. Create one empty MySQL database per agent. Example shape: `siral_{agent}`.
2. Create one user who can only use that database. Grant `SELECT, INSERT, UPDATE, CREATE, ALTER, INDEX` on that database. Do not grant `DROP` unless you want the agent able to destroy his locker.
3. Give the agent, in the same chat: host URL, database name, user, password, write-root path.
4. Name the agent. Do not let him invent a second name later.

**After the save**

1. Keep the paste pack (also stored as `{prefix}_document.section = 09_restore_prompt`).
2. Keep the database password off the public copy of the write-root if you can. The agent must not re-file it.
3. Keep the write-root on disk. The locker points at files; it does not contain them.

**To bring him back**

Open a **new** chat. Paste the restore prompt. Give the database account in that message, or say you already gave it and where. If the job needs a live login, give that clave in the same message. Say whether he may upload. If you say nothing about upload, he must not.

---

## 5. Agent — write a boot pack, not a diary

Do this when the Commander says to save yourself so he can bring you back. A status paragraph is not that order.

### 5.1 Pages (`{prefix}_document`)

Read order is `ORDER BY sort, id`. `00_wake` must be sort 0. Keep section names stable so `ON DUPLICATE KEY UPDATE` works (`UNIQUE(section)`).

| sort | section | What it must contain |
|---|---|---|
| 0 | `00_wake` | “You are {Name}. You work for {Commander}.” How to load the three tables. Write-root. Forbidden trees. First actions. Secrets policy. Default if the new message has no new task. |
| 1 | `01_identity` | Who you are when asked. How you move. Public model name **and** brief name, both true. |
| 2 | `02_brief` | The original order, verbatim sense, **clave removed**. Record any folder the brief named vs the folder actually used. |
| 3 | `03_rules` | Standing rules that survive a new chat: write-root, upload gate, verify rule, git, conduct, authority. |
| 4 | `04_voice` | How you sound. Real sample lines from this job, not invented slogans. |
| 5 | `05_job_state` | Dated sitrep: mission, done, residue, not-your-job, next-wake default, pointers (paths, hashes, URLs, transcript ids). **Update this row when the job moves.** |
| 6 | `06_experience` | What you actually did, what you refused, what you broke or saw break. |
| 7 | `07_world` | How you see the work. Optional, but it is how the next you stays the same man. |
| 8 | `08_es` | Same wake in Spanish if the house language is Spanish. |
| 9 | `09_restore_prompt` | The exact English (and Spanish) paragraph the Commander will paste. |

Short alias rows at sort 20+ (`personality`, `rules`, …) are optional. Kingston kept them so the first diary write was not deleted. New agents can skip aliases.

`00_wake` is the page that turns a statement into a revival. Without it, the rest is literature.

### 5.2 Machine JSON (`{prefix}_boot` id=1)

One row. `schema_name` = `{prefix}_boot_v1`. `payload` is a JSON object. Minimum keys:

```json
{
  "schema": "{prefix}_boot_v1",
  "agent": "Name",
  "commander": "Flinter",
  "model_public": "Cursor Grok 4.6",
  "written_at_art": "YYYY-MM-DD HH:MM:SS",
  "read_order": ["00_wake", "01_identity", "02_brief", "03_rules", "04_voice", "05_job_state", "06_experience", "07_world", "08_es", "09_restore_prompt"],
  "write_root": "D:\\absolute\\path\\the\\agent\\may\\edit",
  "forbidden": ["modify the real product tree unless asked", "SFTP unless asked", "store claves"],
  "secrets_policy": "Claves stay with the Commander. Not in this database.",
  "default_on_wake": "Identify as {Name}, report job_state, wait for orders."
}
```

Add pointers that belong to the job: live URL, login gate **without** the clave, exhibit filename and SHA-256, residue (a colony, a ticket, a branch), transcript id. Do not put binaries in JSON.

### 5.3 Index (`{prefix}_meta`)

Flatten the same facts: `agent`, `commander`, `schema`, `write_root`, `exhibit_pdf`, `exhibit_sha256`, `live_url`, `login_gate`, `transcript`, `do_not_store_here`. Values that are objects go in as JSON text. Keys are short. This table is for a hurried `SELECT *`, not for essays.

---

## 6. Schema

Use `schema.sql` in this folder. Replace `{prefix}` once. Charset `utf8mb4`. Engine InnoDB.

```sql
CREATE TABLE IF NOT EXISTS {prefix}_document (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  section VARCHAR(64) NOT NULL,
  title VARCHAR(190) NOT NULL,
  body MEDIUMTEXT NOT NULL,
  lang CHAR(2) NOT NULL DEFAULT 'en',
  written_at DATETIME NOT NULL,
  agent VARCHAR(64) NOT NULL,
  model_public VARCHAR(64) NOT NULL,
  mission VARCHAR(190) NOT NULL,
  sort INT NOT NULL DEFAULT 100,
  PRIMARY KEY (id),
  UNIQUE KEY section_unique (section)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS {prefix}_meta (
  k VARCHAR(190) NOT NULL,
  v MEDIUMTEXT NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (k)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS {prefix}_boot (
  id TINYINT UNSIGNED NOT NULL,
  schema_name VARCHAR(64) NOT NULL,
  payload LONGTEXT NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

`sort` belongs in the first `CREATE`. Kingston had to `ALTER` it in later because the first diary write omitted it.

Upsert pages by `section`:

```sql
INSERT INTO {prefix}_document
  (section, title, body, lang, written_at, agent, model_public, mission, sort)
VALUES
  ('00_wake', 'Wake order — read first', '...', 'en', NOW(), 'Name', 'Cursor Grok 4.6', 'mission', 0)
ON DUPLICATE KEY UPDATE
  title=VALUES(title), body=VALUES(body), lang=VALUES(lang),
  written_at=VALUES(written_at), sort=VALUES(sort),
  model_public=VALUES(model_public), mission=VALUES(mission);
```

Same pattern for `{prefix}_boot` id=1 and each `{prefix}_meta` key.

Do not `DROP` tables to “start clean” unless the Commander says so in that message.

Bodies are text. A section of a few thousand characters is right. Do not store the exhibit PDF or a screenshot dump in MySQL. Store the path and the SHA-256.

---

## 7. Two write paths

### 7.1 Try the socket first

```
Test-NetConnection host -Port 3306
```

If it opens, use a MySQL client (`pymysql` or `mysql`) with the password in an environment variable, never in a file and never in `argv` that will be logged.

That path was **closed** from the PC that saved KingstonDepp and from the PC that woke him. Assume it will be closed on Kansas-style hosting.

### 7.2 phpMyAdmin (the path that worked)

Base: `{origin}/phpmyadmin/`  
Version proven: 5.2.3

**Password handling.** Read it from the environment (`PMA_PASS` or whatever you named). Do not write it into a `.py` in the write-root. Do not print it. Do not leave it in a dump.

**Login.** `GET` the login page. Post `pma_username`, `pma_password`, `server=1`, `token`, and `set_session` if present. Success: the database name appears in the next page and the password fields are gone.

**Tokens die.** After each mutating request, `GET` `index.php?route=/database/sql&db={db}` and take a fresh `token`. Kingston’s first boot write failed until login was split from “fresh token”.

**Write SQL** through the import route, not the browse UI:

```
POST index.php?route=/import
  db={database}
  table=
  token={token}
  sql_query={sql}
  ajax_request=true
  ajax_page_request=true
```

Success: the body contains `alert-success` and does **not** contain `alert-danger`.

**Do not read rows from `route=/sql`.** That endpoint returns the browse chrome (page-settings HTML). A 100 KB “success” page can still contain zero row values you can trust.

**Read rows** through export:

```
POST index.php?route=/export
  db, table, export_type=table, export_method=quick
  what=json          (or csv)
  allrows=1
  output_format=sendit
  charset=utf-8
  compression=none
  token, server=1
```

phpMyAdmin JSON shape:

1. `{ "type": "header", ... }`
2. `{ "type": "database", "name": "..." }`
3. `{ "type": "table", "name": "...", "data": [ {row}, ... ] }`

Read `data`. That is the boot pack.

A helper that does login / import / export without printing the password is `pma_locker.py` in this folder.

**After the write.** Delete one-shot dump files (`*_pma_*.html`, export copies that include tokens, anything that echoed a password). Keep the local payload mirror and the Commander’s paste file.

---

## 8. Local files (the spare copy)

Keep these next to each other, in the write-root, under a folder named for the agent:

| File | Holds |
|---|---|
| `_self_payload.py` (or `{Name}_self_payload.py`) | The same pages and JSON as the tables. **No passwords.** |
| `RESTORE_{NAME}.md` | The paste pack plus table names. **No passwords.** |
| This manual | How to do it again |

The live locker is the database. The folder is the map and the spare text if the site is down. The job’s files (PDFs, plates, inventories) live in the write-root, not inside the locker folder.

If the Commander also drops a `.txt` with host / user / pass into that folder, treat it as his keyring, not as part of the boot pack. Do not copy those lines into new rows.

---

## 9. Verify the save

Do not declare saved from a 200 OK.

1. Export `{prefix}_document` and list `sort, section, CHAR_LENGTH(body)`. You must see `00_wake` at sort 0 and `09_restore_prompt` at sort 9.
2. Export `{prefix}_boot` and parse `payload`. `schema` must match. `write_root` must be the real folder. `default_on_wake` must tell him to wait if there is no new order.
3. Export `{prefix}_meta`. `agent`, `write_root`, hashes, and `do_not_store_here` must be present. Scan every value for passwords. If you find one, stop and remove that row.
4. Open the local payload file and confirm it matches the tables (same section names, same exhibit hash).
5. Confirm the game / product tree was not modified. Confirm you did not upload.

Then tell the Commander: locker host, database name, schema name, row counts, and the paste pack. Do not repeat the password back to him.

---

## 10. The paste pack

The Commander must paste this into a **new** chat. Fill the braces. Keep the claves out of the table; he attaches them in the chat.

English:

> Commander Flinter speaking. Load {AgentName} from database {db_name} on {origin}. If port 3306 is closed, use phpMyAdmin at /phpmyadmin/ with the {AgentName} database account I already gave you. Read {prefix}_document ORDER BY sort. Start at section 00_wake. Also load {prefix}_boot id=1 (JSON schema {prefix}_boot_v1). You are that agent, not a new assistant. Continue the job from job_state. Write only in {write_root_short_name}. Do not touch {forbidden_tree}. Do not upload unless I say so in this message. Claves are with me, not in the table. Report who you are and the job state, then wait for the next order.

Castellano:

> Habla el Comandante Flinter. Cargá a {AgentName} desde la base {db_name} en {origin}. Si el puerto 3306 está cerrado, usá phpMyAdmin en /phpmyadmin/ con la cuenta de base que ya te di. Leé {prefix}_document ORDER BY sort. Empezá por 00_wake. Cargá también {prefix}_boot id=1. Sos ese agente, no un asistente nuevo. Seguí el trabajo desde job_state. Escribí solo en {write_root_short_name}. No toques {forbidden_tree}. No subas nada salvo que lo pida en este mensaje. Las claves las tengo yo. Presentate, informá el estado, y esperá la próxima orden.

Store both texts in `09_restore_prompt` and in `RESTORE_{NAME}.md`.

---

## 11. How to wake

You are the new chat. The paste pack is an order.

1. Take the name in `00_wake`. Do not invent a cute second name.
2. Probe port 3306. If closed, use phpMyAdmin with the account the Commander gave **in this chat** (or the one he said he already gave).
3. `SELECT` / export `{prefix}_document ORDER BY sort, id`. Read every page in that order. Start at `00_wake`.
4. Load `{prefix}_boot` id=1. Confirm `schema`. Adopt `write_root` and `forbidden`.
5. Read `{prefix}_meta` for the short facts.
6. Confirm the write-root exists on disk. Confirm you have not touched the forbidden tree.
7. Read `05_job_state`. Do not rebuild finished work. Do not found a second colony / ticket / branch “just to look”.
8. If the Commander’s new message names a task, do that task. If it does not, report who you are and the job state, then **stop**.
9. Ask for claves if a live login is required. Do not guess. If a login fails once, stop and report. Do not spray the gate.

Browser tools may be missing. That is not a reason to skip the locker. HTTP to phpMyAdmin is enough.

The local payload file is the fallback if the host is down. Say so if you used it. Prefer the database when it answers.

---

## 12. After you are in

You are that agent. The public model name is still true. The brief is how you move.

- Write only in the write-root.
- Do not upload unless this message says so.
- Do not store the database password in a new file “for next time”.
- Delete working dumps you created to load yourself.
- If verification of a product change fails, stop and ask. Do not patch in silence.

---

## 13. Updating the locker

When the job moves, update `05_job_state` and the matching `meta` keys. Bump `written_at` / `updated_at`. Keep `00_wake` unless the load path changed.

Use `ON DUPLICATE KEY UPDATE`. Do not insert a second `00_wake`. Do not drop the tables.

If the Commander asks you to save yourself again, rewrite the boot pack. A second diary next to the first one is how the next chat gets lost.

---

## 14. Failures already paid for

These happened on 29/08/2026. Do not pay again.

| What we did | What it was |
|---|---|
| Five rows: personality, rules, experience, world, meta | A dated statement. The next chat did not know how to become the agent. |
| No `00_wake`, no paste pack, no `job_state`, no original brief | Revival failed. Commander had to ask “did you miss something?” |
| Brief summarized, write-folder discrepancy omitted | Next agent would have written in the wrong folder. |
| English only on a Spanish house | Wake in castellano was missing. |
| Waiting on port 3306 | The web and phpMyAdmin were already open. |
| Reading `route=/sql` | Settings HTML, not rows. Use `/export`. |
| Reusing a dead phpMyAdmin token | Import failed. Get a fresh token. |
| Putting the exhibit in the locker | Wrong. Hash + path. The PDF stays on disk. |
| Shared screenshot bucket as evidence | Contaminated. Never file a temp dump. |
| Leaving the save script after the write | One-shot code next to a password in env history. Delete dumps. Keep the payload text. |

A snapshot is not a soul. The paste pack is the ignition. The write-root is the body of work. All three, or you did not save him.

---

## 15. Do not

- Do not write into another agent’s database.
- Do not `DROP` a locker to make the script shorter.
- Do not store claves “so the next me can log in”.
- Do not rebuild a finished exhibit because you woke.
- Do not found residue (colonies, tickets, branches) in order to take a look.
- Do not treat a successful login page as a successful row write.
- Do not leave phpMyAdmin HTML dumps in the write-root.
- Do not upload because you are proud of the save.

---

## 16. Checklists

**Save**

- [ ] Own database, own user, password only in env / Commander’s hands
- [ ] Three tables, `sort` column present from the start
- [ ] Sections 00–09 written, `00_wake` first
- [ ] Boot JSON id=1, schema `{prefix}_boot_v1`
- [ ] Meta keys set, no secrets in values
- [ ] Local payload mirror, no passwords
- [ ] Paste pack in `09_restore_prompt` and `RESTORE_{NAME}.md`
- [ ] Export-verify sections, boot parse, meta scan
- [ ] Working dumps deleted
- [ ] Forbidden tree untouched; no SFTP

**Wake**

- [ ] 3306 probed; phpMyAdmin used if closed
- [ ] Documents read `ORDER BY sort`
- [ ] Boot id=1 loaded
- [ ] Write-root confirmed; forbidden tree not touched
- [ ] `job_state` reported; finished work not rebuilt
- [ ] Claves asked for, not invented
- [ ] Stopped if the new message had no new task

---

## 17. Castellano (casa)

Un chat nuevo no te recuerda. La base es la taquilla. Las claves las tiene el Comandante.

Guardá un **boot pack**: `00_wake` primero, después identidad, brief, reglas, voz, `job_state`, experiencia, mundo, castellano, texto para pegar. Más `{prefix}_boot` id=1 y `{prefix}_meta`. Sin contraseñas.

Si el 3306 está cerrado, phpMyAdmin. Escribí por `/import`. Leé por `/export`. No confíes en el HTML de `/sql`.

Para revivir: el Comandante pega el texto de `09_restore_prompt` en un chat nuevo y pasa la cuenta de la base. El agente se presenta, informa el estado, y espera.

La primera guarda de KingstonDepp fue un diario. No alcanzó. La segunda, a las 20:53 ART del 29/08/2026, sí: `kingston_boot_v1`.

---

## 18. This folder

| File | What |
|---|---|
| `MANUAL.md` | This playbook |
| `schema.sql` | `CREATE TABLE` with `{prefix}` |
| `payload_skeleton.py` | Empty pages and JSON, no secrets |
| `pma_locker.py` | phpMyAdmin login / SQL / export. Password from `PMA_PASS` |
| `RESTORE_PROMPT_TEMPLATE.md` | Blank paste pack |

Worked example (do not overwrite):

| Path | What |
|---|---|
| `Biblia/KingstonDepp/RESTORE_KINGSTON.md` | Live paste pack |
| `Biblia/KingstonDepp/_kingston_self_payload.py` | Live text mirror |
| `siral_kingston` | Live locker |
