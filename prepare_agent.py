"""Prepare an AgentSelfSave kit for one new agent.

Copy this whole folder to the agent's write-root. Put locker account in
.Secret/secrets.txt (same path, same name, every time). Then run:

    python prepare_agent.py

The script finds .Secret/secrets.txt from its own location or the current
directory. It does not care what the parent path is. Write-root is the
absolute path of the folder that holds that secrets file.

Asks for the agent name. Prints the first-save paste on screen (once;
not written to a file). Writes Revive.md for later new chats, plus
_prepared.json (no password). Optionally creates empty tables.

Password is read from secrets.txt and not printed unless --include-pass.
The testdb in a kit copy is only a locker account. It is not an agent.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

ART = timezone(timedelta(hours=-3))

KEY_ALIASES = {
    "agentname": "agentname",
    "agent": "agentname",
    "name": "agentname",
    "server": "server",
    "host": "server",
    "origin": "server",
    "url": "server",
    "database": "database",
    "db": "database",
    "dbname": "database",
    "user": "user",
    "username": "user",
    "pass": "pass",
    "password": "pass",
    "pwd": "pass",
}

RESERVED_SECRET_NAMES = {"testdb", "test", "test_db", "agentname"}
DEFAULT_FORBIDDEN = "the live product tree unless I name it in this message"
DEFAULT_COMMANDER = "NeonVintage"


def _norm_key(raw: str) -> str:
    k = raw.strip().lower().rstrip(":=")
    k = re.sub(r"\s+", "", k)
    return KEY_ALIASES.get(k, k)


def parse_secrets(path: Path) -> dict[str, str]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = [ln.strip() for ln in raw_lines]
    lines = [ln for ln in lines if ln and not ln.lstrip().startswith("#")]
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line and not line.endswith(":") and line.split(":", 1)[0].strip() and "://" not in line.split(":", 1)[0]:
            k, _, v = line.partition(":")
            if k.strip() and v.strip():
                out[_norm_key(k)] = v.strip()
                i += 1
                continue
        if "=" in line:
            k, _, v = line.partition("=")
            if k.strip() and " " not in k.strip() and v.strip():
                out[_norm_key(k)] = v.strip()
                i += 1
                continue
        if i + 1 < len(lines):
            out[_norm_key(line)] = lines[i + 1]
            i += 2
            continue
        i += 1
    return out


def find_secrets_file(*starts: Path) -> Path:
    seen: set[Path] = set()
    for start in starts:
        root = start.resolve()
        for p in [root, *root.parents]:
            if p in seen:
                continue
            seen.add(p)
            for rel in (Path(".Secret") / "secrets.txt", Path(".secret") / "secrets.txt"):
                cand = p / rel
                if cand.is_file():
                    return cand
    raise SystemExit(
        "No .Secret/secrets.txt found. Place it in the agent folder "
        "(same folder name, same file name, every time)."
    )


def kit_root_from_secrets(secrets_path: Path) -> Path:
    return secrets_path.resolve().parent.parent


def origin_from_server(server: str) -> str:
    s = (server or "").strip()
    if not s:
        raise SystemExit("secrets.txt has no server")
    if "://" not in s:
        s = "https://" + s
    parsed = urlparse(s)
    if not parsed.netloc:
        raise SystemExit(f"secrets.txt server is not a URL: {server!r}")
    return f"{parsed.scheme}://{parsed.netloc}"


def host_from_origin(origin: str) -> str:
    return urlparse(origin).netloc


def prefix_from_name(name: str) -> str:
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+", name)
    first = re.sub(r"[^A-Za-z0-9]", "", (parts[0] if parts else name)).lower()
    full = re.sub(r"[^A-Za-z0-9]", "", name).lower()
    token = first if len(first) >= 4 else (full or first)
    if not token:
        raise SystemExit("Could not derive a table prefix from that name.")
    if token[0].isdigit():
        token = "a" + token
    return token[:32]


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        got = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        got = ""
    return got or default


def write_root_short(write_root: Path) -> str:
    return write_root.name


def render_restore(agent: str, commander: str, prefix: str, db: str, origin: str, write_root: Path, forbidden: str) -> tuple[str, str]:
    short = write_root_short(write_root)
    en = (
        f"Commander {commander} speaking. Load {agent} from database {db} on {origin}. "
        f"If port 3306 is closed, use phpMyAdmin at /phpmyadmin/ with the {agent} database "
        f"account I already gave you. Read {prefix}_document ORDER BY sort. Start at section "
        f"00_wake. Also load {prefix}_boot id=1 (JSON schema {prefix}_boot_v1). You are that "
        f"agent, not a new assistant. Continue the job from job_state. Write only in {short}. "
        f"Do not touch {forbidden}. Do not upload unless I say so in this message. Claves are "
        f"with me, not in the table. Report who you are and the job state, then wait for the next order."
    )
    es = (
        f"Habla el Comandante {commander}. Cargá a {agent} desde la base {db} en {origin}. "
        f"Si el puerto 3306 está cerrado, usá phpMyAdmin en /phpmyadmin/ con la cuenta de base "
        f"que ya te di. Leé {prefix}_document ORDER BY sort. Empezá por 00_wake. Cargá también "
        f"{prefix}_boot id=1. Sos ese agente, no un asistente nuevo. Seguí el trabajo desde "
        f"job_state. Escribí solo en {short}. No toques {forbidden}. No subas nada salvo que lo "
        f"pida en este mensaje. Las claves las tengo yo. Presentate, informá el estado, y esperá "
        f"la próxima orden."
    )
    return en, es


def render_save_once_md(
    *,
    agent: str,
    commander: str,
    prefix: str,
    write_root: Path,
    origin: str,
    db: str,
    user: str,
    password: str | None,
    forbidden: str,
    secrets_rel: str,
) -> str:
    pass_line = (
        f"Pass: {password}"
        if password
        else f"Pass: (in {secrets_rel} — paste it in the chat; do not let him re-file it)"
    )
    playbook = write_root / "MANUAL.md"
    now = datetime.now(ART).strftime("%Y-%m-%d %H:%M:%S")
    return f"""# Save_RUNONCEONLY — {agent}

Generated {now} ART by prepare_agent.py.

**RUN ONCE.** First save only. Empty locker. If `{prefix}_document` already has `00_wake`, do not paste this. Use `Revive.md` for a new chat. Same-chat later work is locker close: UPDATE and append. Never this paste again. Not a file.

Write-root (absolute): `{write_root}`
Locker account from `{secrets_rel}`. Do not write the password into the tables.
Leave `neonvintage_kingston` alone (KingstonDepp). `siral_kingston` is retired.

---

## Paste this once in the agent's working chat

```
I am Commander {commander}. Your name is {agent}. Do not invent another.

Write only in: {write_root}
Do not touch: {forbidden}
Do not upload unless I say so in this message.

This is your FIRST and ONLY first-save. Save yourself so I can bring you back. Use the playbook in:
{playbook}

Your locker (yours only, not KingstonDepp's):
Server: {origin}
Database: {db}
User: {user}
{pass_line}

Write a boot pack, not a diary: sections 00_wake through 09_restore_prompt, {prefix}_boot id=1, {prefix}_meta. Schema {prefix}_boot_v1. Put the Revive.md English and Castellano texts into 09_restore_prompt. No claves in the tables.

MEMORY LAW (write this into 00_wake and 03_rules; keep it forever):
- Never start a locker page from a blank sheet.
- Never replace 06_experience. When the job moves, append a paragraph to the text that is already there.
- UPDATE the same rows. Do not INSERT a second 00_wake. Do not DROP.
- First locker is only a new man on an empty database. After today it is not your job again.
- Do not rewrite yourself. Do not wipe memories to save them.

When you are done, give me the paste pack and row counts. Then stop.
```

Empty tables may already exist. He still writes the pages. He does not copy KingstonDepp.

## Save is done when

- `{prefix}_document` has `00_wake` (sort 0) and `09_restore_prompt` (sort 9)
- `{prefix}_boot` id=1 exists, schema `{prefix}_boot_v1`
- He gave you a paste paragraph you can copy (same words as Revive.md)
- He did not print the password into a new file
- Experience is his own. He did not start it blank on a later day.

If he only stored personality / rules / experience / world, that is the failed first Kingston save. Send him back to `00_wake` **this first day only**.
"""


def render_revive_md(
    *,
    agent: str,
    prefix: str,
    db: str,
    origin: str,
    write_root: Path,
    restore_en: str,
    restore_es: str,
) -> str:
    now = datetime.now(ART).strftime("%Y-%m-%d %H:%M:%S")
    return f"""# Revive — {agent}

Generated {now} ART by prepare_agent.py.

Use this in a **new** chat every time you bring him back. Not a first-save. Do not paste the on-screen first-save again.

He must load what is already in the locker. He must not rewrite pages from a blank sheet. He must not replace `06_experience`. He must not DROP. He reports `job_state` and waits.

Write-root: `{write_root}`
Database: `{db}` on {origin}
Tables: `{prefix}_document`, `{prefix}_boot`, `{prefix}_meta`
Schema: `{prefix}_boot_v1`

Claves stay with the Commander. Do not put them in this file or in the table.

---

## English

{restore_en}

## Castellano

{restore_es}

## Commander also brings (in the new chat, not in the table)

- Database user and password
- Live-site clave only if this wake needs a login
- Whether upload is allowed (default: no)
"""


def load_schema(kit_root: Path, prefix: str) -> str:
    src = kit_root / "schema.sql"
    if not src.is_file():
        raise SystemExit("schema.sql missing next to prepare_agent.py")
    return src.read_text(encoding="utf-8").replace("{prefix}", prefix)


def create_empty_tables(kit_root: Path, origin: str, secrets: dict[str, str], prefix: str) -> None:
    os.environ["PMA_BASE"] = origin.rstrip("/") + "/phpmyadmin/"
    os.environ["PMA_DB"] = secrets["database"]
    os.environ["PMA_USER"] = secrets["user"]
    os.environ["PMA_PASS"] = secrets["pass"]
    sys.path.insert(0, str(kit_root))
    from pma_locker import Locker

    loc = Locker()
    loc.login()
    body = loc.run_sql(load_schema(kit_root, prefix))
    if not loc.sql_ok(body):
        err = re.search(r"alert-danger.*?>(.*?)</", body, re.S)
        detail = re.sub(r"<[^>]+>", "", err.group(1))[:400] if err else "import failed"
        raise SystemExit(f"Table create failed: {detail}")
    print(f"tables ok: {prefix}_document {prefix}_boot {prefix}_meta")


def require_secrets(secrets: dict[str, str]) -> None:
    missing = [k for k in ("server", "database", "user", "pass") if not secrets.get(k)]
    if missing:
        raise SystemExit("secrets.txt missing: " + ", ".join(missing))


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()
    parser = argparse.ArgumentParser(description="Prepare this AgentSelfSave folder for one agent.")
    parser.add_argument("--agent", help="Agent name. If omitted, the script asks.")
    parser.add_argument("--prefix", help="Table prefix (default: derived from the name).")
    parser.add_argument("--commander", default=DEFAULT_COMMANDER)
    parser.add_argument("--forbidden", help="What he must not touch.")
    parser.add_argument("--include-pass", action="store_true", help="Put the locker password into the on-screen first-save paste.")
    parser.add_argument("--no-tables", action="store_true", help="Do not CREATE tables.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen. Write nothing.")
    args = parser.parse_args(argv[1:])

    secrets_path = find_secrets_file(here, cwd)

    kit_root = kit_root_from_secrets(secrets_path)
    secrets = parse_secrets(secrets_path)
    require_secrets(secrets)
    origin = origin_from_server(secrets["server"])
    write_root = kit_root
    secrets_rel = str(secrets_path.relative_to(kit_root)).replace("\\", "/")

    if args.dry_run:
        print("kit_root", write_root)
        print("secrets", secrets_rel)
        print("server", origin)
        print("database", secrets["database"])
        print("user", secrets["user"])
        print("pass", "set" if secrets.get("pass") else "MISSING")
        print("host", host_from_origin(origin))
        return 0

    interactive = sys.stdin.isatty() and not args.agent
    agent = (args.agent or "").strip()
    if not agent and interactive:
        agent = ask("Agent name")
    if not agent:
        raise SystemExit("Agent name is required. Use --agent NAME or run in a terminal.")

    if agent.strip().lower() in RESERVED_SECRET_NAMES:
        raise SystemExit(
            f"{agent!r} is the test-database label, not an agent. "
            "Pick the real name. Testdb does not belong to anyone."
        )

    prefix = (args.prefix or "").strip() or prefix_from_name(agent)
    forbidden = (args.forbidden or "").strip()
    if not forbidden:
        forbidden = ask("Forbidden tree", DEFAULT_FORBIDDEN) if interactive else DEFAULT_FORBIDDEN
    commander = (args.commander or DEFAULT_COMMANDER).strip()

    include_pass = bool(args.include_pass)
    if interactive and not args.include_pass:
        yn = ask("Put locker password into the on-screen first-save paste", "n")
        include_pass = yn.lower() in ("y", "yes", "s", "si", "sí")

    create_tables = not args.no_tables
    if interactive and not args.no_tables:
        yn = ask("Create empty locker tables now", "Y")
        create_tables = yn.lower() not in ("n", "no")

    restore_en, restore_es = render_restore(
        agent, commander, prefix, secrets["database"], origin, write_root, forbidden
    )
    password = secrets["pass"] if include_pass else None

    save_text = render_save_once_md(
        agent=agent,
        commander=commander,
        prefix=prefix,
        write_root=write_root,
        origin=origin,
        db=secrets["database"],
        user=secrets["user"],
        password=password,
        forbidden=forbidden,
        secrets_rel=secrets_rel,
    )
    revive_text = render_revive_md(
        agent=agent,
        prefix=prefix,
        db=secrets["database"],
        origin=origin,
        write_root=write_root,
        restore_en=restore_en,
        restore_es=restore_es,
    )
    prepared = {
        "schema": f"{prefix}_boot_v1",
        "agent": agent,
        "prefix": prefix,
        "commander": commander,
        "model_public": "Cursor Grok 4.6",
        "write_root": str(write_root),
        "write_root_short": write_root_short(write_root),
        "forbidden": forbidden,
        "origin": origin,
        "database": secrets["database"],
        "user": secrets["user"],
        "secrets_file": secrets_rel,
        "playbook": str(write_root / "MANUAL.md"),
        "generated_at_art": datetime.now(ART).strftime("%Y-%m-%d %H:%M:%S"),
    }

    (write_root / "Revive.md").write_text(revive_text, encoding="utf-8")
    leftover = write_root / "Save_RUNONCEONLY.md"
    if leftover.is_file():
        leftover.unlink()
    (write_root / "_prepared.json").write_text(
        json.dumps(prepared, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (write_root / f"schema_{prefix}.sql").write_text(load_schema(write_root, prefix), encoding="utf-8")

    print("write_root", write_root)
    print("agent", agent)
    print("prefix", prefix)
    print("database", secrets["database"])
    print("origin", origin)
    print("wrote Revive.md")
    print("wrote _prepared.json")
    print("wrote", f"schema_{prefix}.sql")
    print("password on screen", "yes" if include_pass else "no")
    if create_tables:
        create_empty_tables(write_root, origin, secrets, prefix)
    else:
        print("tables skipped")
    print()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("========== FIRST SAVE (ONCE) — copy from here ==========")
    print(save_text)
    print("========== copy to here. Not written to a file. Later: Revive.md ==========")
    print("done. First save: paste what was just printed, once. Later: paste Revive.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
