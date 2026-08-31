# Commander ? save and revive an agent

For Commander NeonVintage. Claves stay with you. Never in his table.
`prepare_agent.py` defaults the commander name to NeonVintage. Override with `--commander` only if you mean someone else.

Proven in the field (29?30 August 2026, ART):

| Fact | Value |
|---|---|
| Transport | phpMyAdmin 5.2.3 at `/phpmyadmin/` |
| Port 3306 | Closed from outside. Do not wait for it. |
| KingstonDepp live locker | `neonvintage_kingston` on https://neonvintage.com.ar ? leave it alone |
| Retired locker | `siral_kingston` on https://siral.com.ar ? do not write a new man there |
| Schema | `{prefix}_boot_v1` |
| Public method repo | https://github.com/NeonVintage/AgentSelfSave (playbook only, no claves) |

This folder is a **kit**. You copy it to a new directory for each agent. That directory is his write-root. You run `Start_config.bat` or `prepare_agent.py` **before** you point him at it. The first-save paste is shown in a copyable window (not a file). `Revive.md` is written for later.

---

## 0. Standard process (do this every time)

1. In Kansas / cPanel, make a locker that is only his.
   - One database, one user who can only use that database.
   - Rights: `SELECT`, `INSERT`, `UPDATE`, `CREATE`, `ALTER`, `INDEX`.
   - Do not grant `DROP` unless you want him able to destroy the locker.
   - Do not reuse `neonvintage_kingston` or `siral_kingston`.
2. Create a **new directory**. That path is the absolute write-root.
3. Copy this whole AgentSelfSave kit into that directory.
4. In Kansas / cPanel the database and user must already exist as `neonvintage_{AgentName}` (same name you will type). You still create those in the panel. Then run the script. It asks the agent name in the console. The database password opens a window titled AgentSelfSave (in front; check the taskbar if you miss it) so you can paste. Clipboard is cleared after OK. It creates `.secrets/secrets_{Name}.txt` itself:

   ```
   Server: https://neonvintage.com.ar/
   Database: neonvintage_{Name}
   User: neonvintage_{Name}
   Pass: (what you typed)
   ```

   Port 3306 is closed from outside. It will not work. Use phpMyAdmin at `/phpmyadmin/`.

   A `Testdb` / `neonvintage_testdb` name is only a test account. It does not belong to any agent.
5. From that directory run `Start_config.bat`, or:

   ```
   python prepare_agent.py
   ```

   It asks for the agent name, then a password window titled AgentSelfSave (paste works; chars hidden), writes `.secrets/secrets_{Name}.txt`, creates `.cursor/rules/` from the house rules, writes `{Name}.mdc` with the filled revive prompt, and uses phpMyAdmin (not port 3306). Write-root is this folder. It shows the first-save paste in a copyable window (Copy all; not a file), writes `Revive.md`, writes `_prepared.json` (no password), writes `schema_{prefix}.sql`, and can create the empty tables.
6. Copy the on-screen first-save paste **once** into his working chat. Point the chat at that directory. Do not save that paste as a file. Never paste it again.
7. Accept the save only if the checklist in that on-screen block is true.
8. To get him back another day: new chat, @ `{Name}.mdc` or paste `Revive.md`, give user + password in that same message.

You do not write SQL by hand. The script and then the agent do. You still create the empty database and user in the panel first, or he has nowhere to write.

---

## 1. First save ? on screen, once

**Once.** Empty locker. If `00_wake` already exists, stop. Use `Revive.md`.

After `prepare_agent.py`, the window titled AgentSelfSave ? first save (once) shows only the paste. No warnings around it. Copy all. Words are spaced. Not a file. If you included the locker password, close the window after you copy.

If you only drop the folder and a password, with no name, no write-root, and no first-save order, he will sit or write a diary. Same as the first Kingston save.

Do not paste that on-screen block a second time. A second first-save is how memories get wiped.

---

## 2. Save is done when

- `{prefix}_document` has `00_wake` (sort 0) and `09_restore_prompt` (sort 9)
- `{prefix}_boot` id=1 exists, schema `{prefix}_boot_v1`
- He gave you a paste paragraph you can copy (same words as `Revive.md`)
- He did not print the password into a new file

If he only stored personality / rules / experience / world, send him back to `00_wake` **this first day only**.

He must not copy KingstonDepp into the new man. The new man writes his own brief and `job_state`.

---

## 3. Bring him back ? Revive.md

That save is a snapshot. It is not revival.

1. Open a **new** chat.
2. @ `{Name}.mdc` in `.cursor/rules/`, or paste `Revive.md` (also stored as `{prefix}_document` section `09_restore_prompt`).
3. Put database user + password in **that same message**.
4. If he needs a live login, give that clave there too.
5. Say whether he may upload. If you say nothing, he must not.

He should present himself, report `job_state`, and wait. He loads what is already there. He does not rewrite. He does not replace experience.

Same chat, job moved, account already in the chat: no paste. He closes the locker himself. You do not have to say save. He UPDATEs what changed, **appends** to experience, then archives his redacted chats (`_push_locker_update.py` and `archive_chats.py`).

---

## 4. What you keep in a notebook (not in his table)

- Agent name
- Database / user / password
- Write-root path
- His revive paste (`Revive.md`)

Three lockers means three databases. Same server and phpMyAdmin is fine. Same password across agents is your risk, not the method.

---

## 5. What the files do not do

- They do not copy KingstonDepp into the new man.
- They do not carry PDFs or screenshots. Those stay in his write-root.
- They do not revive him the day you prepare the folder. Revival is `Revive.md`, another day.
- They do not authorize a second first-save.
- They do not write the first-save paste to disk.
- After each finished task he closes the locker and runs `archive_chats.py`. You do not have to tell him to save. `_push_locker_update.py` writes the pages. `archive_chats.py` keeps a redacted copy of **his** Cursor chats in `chats/` and `{prefix}_transcript`. Claves stay with you. Revival does not need that table.
- `.secrets/secrets_{Name}.txt` is your keyring. It is not part of the boot pack. He may read it once to reach phpMyAdmin. He must not copy those lines into new rows.

LLM procedure (not this sheet): `MANUAL.md` in this folder. How the machine works: `TECHNICAL.md`.

---

## Castellano

Una carpeta por agente. Copi? este kit. Pon? la cuenta en `.Secret/` (`secrets.txt` sirve). El script pide el nombre y edita ese archivo. Corr? `Start_config.bat` o `python prepare_agent.py`. Peg? el first-save que sale en pantalla **una sola vez**. No lo guardes en un archivo. `neonvintage_kingston` no se toca. `siral_kingston` est? jubilada.

Acept?s la guarda solo si hay `00_wake`, `09_restore_prompt`, `{prefix}_boot` id=1, y un texto para pegar ? sin contrase?a en un archivo nuevo.

Para revivirlo: chat **nuevo**, @ `{Name}.mdc` o pegas `Revive.md`, y le das la cuenta en ese mensaje. Si no decis que suba, no sube. No vuelvas a pegar el first-save. No se reescribe. No se borra la experiencia. Despues de cada tarea el cierra la taquilla y archiva chats; no hace falta que le digas save. Las claves las tenes vos.
