"""Export this agent's Cursor chats, redact claves, write chats/, upsert locker.

Revival still starts at 00_wake. This archive is custody for when Cursor
deletes the thread. Kansas gets redacted text only. Claves stay with the
Commander in .Secret/. A hash cannot give a password back.

    python archive_chats.py
    python archive_chats.py --dry-run
    python archive_chats.py --no-push

Finds chats in this write-root's Cursor project, plus ids already in the
boot pack, plus threads whose wake line names this agent. Not other men.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ART = timezone(timedelta(hours=-3))
CHUNK_CHARS = 400_000
SECRET_DIR_NAMES = (".Secret", ".secret", ".secrets")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
INLINE_KEY_RE = re.compile(
    r"(?i)\b(server|host|origin|url|database|db|dbname|user|username|pass|password|pwd|pma_pass|agentname|agent|name)\s*[:=]\s*(\S+)"
)
PASS_KEYS = {"pass", "password", "pwd", "pma_pass"}
MIN_SECRET_LEN = 6

TRANSCRIPT_SQL = """
CREATE TABLE IF NOT EXISTS {prefix}_transcript (
  chat_id VARCHAR(64) NOT NULL,
  chunk_no INT UNSIGNED NOT NULL DEFAULT 0,
  title VARCHAR(190) NOT NULL DEFAULT '',
  sha256 CHAR(64) NOT NULL,
  bytes INT UNSIGNED NOT NULL,
  source VARCHAR(190) NOT NULL DEFAULT '',
  body MEDIUMTEXT NOT NULL,
  written_at DATETIME NOT NULL,
  PRIMARY KEY (chat_id, chunk_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def now_art() -> str:
    return datetime.now(ART).strftime("%Y-%m-%d %H:%M:%S")


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _norm_key(raw: str) -> str:
    k = raw.strip().lower().rstrip(":=")
    k = re.sub(r"\s+", "", k)
    aliases = {
        "host": "server",
        "origin": "server",
        "url": "server",
        "db": "database",
        "dbname": "database",
        "username": "user",
        "password": "pass",
        "pwd": "pass",
        "pma_pass": "pass",
        "agent": "agentname",
        "name": "agentname",
    }
    return aliases.get(k, k)


def parse_secret_text(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in INLINE_KEY_RE.finditer(text):
        out[_norm_key(m.group(1))] = m.group(2).strip().strip("\"'")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not ln.lstrip().startswith("#")]
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line and not line.endswith(":") and "://" not in line.split(":", 1)[0]:
            k, _, v = line.partition(":")
            if k.strip() and v.strip() and " " not in k.strip():
                key = _norm_key(k)
                if key not in out:
                    out[key] = v.strip()
                i += 1
                continue
        if i + 1 < len(lines) and " " not in line and ":" not in line and "=" not in line:
            key = _norm_key(line)
            if key not in out:
                out[key] = lines[i + 1]
            i += 2
            continue
        i += 1
    return out


def collect_secrets(write_root: Path) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Return (locker fields, list of (label, secret) to redact). Never print secrets."""
    fields: dict[str, str] = {}
    redactions: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, value: str) -> None:
        v = (value or "").strip()
        if len(v) < MIN_SECRET_LEN or v in seen:
            return
        if v.lower() in {"replace-me", "password", "secret", "example"}:
            return
        seen.add(v)
        redactions.append((label, v))

    for name in SECRET_DIR_NAMES:
        folder = write_root / name
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.txt")):
            if path.name.lower() == "secrets.example.txt":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            parsed = parse_secret_text(text)
            for k, v in parsed.items():
                fields.setdefault(k, v)
                if k in PASS_KEYS or "pass" in k:
                    add("locker-pass", v)
            for m in re.finditer(r"(?i)\bpass(?:word)?\s*[:=]\s*(\S+)", text):
                add("locker-pass", m.group(1).strip().strip("\"'"))
    env_pass = os.environ.get("PMA_PASS") or ""
    add("locker-pass", env_pass)
    if env_pass and "pass" not in fields:
        fields["pass"] = env_pass
    return fields, redactions


def redact(text: str, redactions: list[tuple[str, str]]) -> str:
    out = text
    for label, secret in sorted(redactions, key=lambda x: len(x[1]), reverse=True):
        token = f"[REDACTED:{label}]"
        if secret and secret in out:
            out = out.replace(secret, token)
    return out


def secrets_still_present(text: str, redactions: list[tuple[str, str]]) -> list[str]:
    return [label for label, secret in redactions if secret and secret in text]


def extract_message_text(obj: dict) -> str:
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content")
    parts: list[str] = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
    return "\n".join(p for p in parts if p.strip())


def jsonl_to_readable(raw: str) -> str:
    chunks: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = str(obj.get("role") or "unknown")
        text = extract_message_text(obj)
        if not text.strip():
            continue
        chunks.append(f"## {role}\n\n{text.strip()}\n")
    return "\n".join(chunks).strip() + ("\n" if chunks else "")


def chat_id_from_path(path: Path) -> str:
    if UUID_RE.match(path.stem):
        return path.stem.lower()
    if UUID_RE.match(path.parent.name):
        return path.parent.name.lower()
    return path.stem.lower()


def cursor_projects_root() -> Path:
    override = os.environ.get("CURSOR_PROJECTS")
    if override:
        return Path(override)
    return Path.home() / ".cursor" / "projects"


def known_ids_from_text(*texts: str) -> set[str]:
    found: set[str] = set()
    pat = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.I,
    )
    for text in texts:
        for m in pat.finditer(text or ""):
            found.add(m.group(0).lower())
    return found


def agent_owns_text(text: str, agent: str, write_root: Path) -> bool:
    if not text:
        return False
    name = agent.strip()
    if re.search(rf"Load {re.escape(name)}\b", text):
        return True
    if re.search(rf"You are {re.escape(name)}\b", text):
        return True
    if re.search(rf"Cargá a {re.escape(name)}\b", text, re.I):
        return True
    wr = str(write_root)
    if wr and wr in text:
        return True
    return False


def find_jsonl(write_root: Path, agent: str, extra_ids: set[str]) -> list[Path]:
    root = cursor_projects_root()
    found: dict[str, Path] = {}
    if not root.is_dir():
        return []
    for path in root.rglob("*.jsonl"):
        if "agent-transcripts" not in path.parts:
            continue
        cid = chat_id_from_path(path)
        claimed = cid in extra_ids
        if not claimed:
            try:
                sample = path.read_text(encoding="utf-8", errors="replace")[:200_000]
            except OSError:
                continue
            claimed = agent_owns_text(sample, agent, write_root)
        if claimed:
            found[cid] = path
    return [found[k] for k in sorted(found)]


def load_identity(write_root: Path) -> dict[str, str]:
    out: dict[str, str] = {
        "agent": write_root.name,
        "prefix": re.sub(r"[^a-z0-9]", "", write_root.name.lower())[:32] or "agent",
        "write_root": str(write_root),
        "origin": "",
        "database": "",
        "user": "",
    }
    prep = write_root / "_prepared.json"
    if prep.is_file():
        data = json.loads(prep.read_text(encoding="utf-8"))
        for k in ("agent", "prefix", "write_root", "origin", "database", "user"):
            if data.get(k):
                out[k] = str(data[k])
    for name in (
        f"_{out['prefix']}_self_payload.py",
        "_kingston_self_payload.py",
        "_codelio_self_payload.py",
    ):
        payload = write_root / name
        if not payload.is_file():
            continue
        text = payload.read_text(encoding="utf-8", errors="replace")
        for key, pat in (
            ("agent", r'\bAGENT\s*=\s*"([^"]+)"'),
            ("prefix", r'\bPREFIX\s*=\s*"([^"]+)"'),
            ("database", r'\bLOCKER_DB\s*=\s*"([^"]+)"'),
            ("origin", r'\bLOCKER_ORIGIN\s*=\s*"([^"]+)"'),
        ):
            m = re.search(pat, text)
            if m:
                out[key] = m.group(1)
        if '"locker_db"' in text:
            m = re.search(r'"locker_db":\s*"([^"]+)"', text)
            if m:
                out["database"] = m.group(1)
        if '"locker_origin"' in text:
            m = re.search(r'"locker_origin":\s*"([^"]+)"', text)
            if m:
                out["origin"] = m.group(1)
        if '"agent": "KingstonDepp"' in text:
            out["agent"] = "KingstonDepp"
            out["prefix"] = "kingston"
        extra = known_ids_from_text(text)
        out["_known_ids"] = " ".join(sorted(extra))
        break
    return out


def origin_from_server(server: str) -> str:
    s = (server or "").strip()
    if not s:
        return ""
    if "://" not in s:
        s = "https://" + s
    parsed = urlparse(s)
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def first_title(readable: str, chat_id: str) -> str:
    for line in readable.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:180]
    return chat_id


def write_local(chats_dir: Path, chat_id: str, readable: str, source: str) -> dict:
    folder = chats_dir / chat_id
    folder.mkdir(parents=True, exist_ok=True)
    md_path = folder / "redacted.md"
    md_path.write_text(readable, encoding="utf-8")
    digest = hashlib.sha256(readable.encode("utf-8")).hexdigest()
    meta = {
        "chat_id": chat_id,
        "sha256": digest,
        "bytes": len(readable.encode("utf-8")),
        "source": source,
        "written_at_art": now_art(),
        "chunks": max(1, (len(readable) + CHUNK_CHARS - 1) // CHUNK_CHARS) if readable else 1,
    }
    (folder / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return meta


def chunks_of(text: str) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)]


def push_transcripts(
    kit_root: Path,
    origin: str,
    secrets: dict[str, str],
    prefix: str,
    rows: list[dict],
    written_at: str,
) -> None:
    os.environ["PMA_BASE"] = origin.rstrip("/") + "/phpmyadmin/"
    os.environ["PMA_DB"] = secrets["database"]
    os.environ["PMA_USER"] = secrets["user"]
    os.environ["PMA_PASS"] = secrets["pass"]
    if str(kit_root) not in sys.path:
        sys.path.insert(0, str(kit_root))
    from pma_locker import Locker

    loc = Locker()
    loc.login()
    created = loc.run_sql(TRANSCRIPT_SQL.format(prefix=prefix).strip())
    if not loc.sql_ok(created):
        raise SystemExit(f"Could not create {prefix}_transcript")
    table = f"{prefix}_transcript"
    for row in rows:
        body = row["body"]
        parts = chunks_of(body)
        for i, part in enumerate(parts):
            sql = (
                f"INSERT INTO {table} (chat_id, chunk_no, title, sha256, bytes, source, body, written_at) VALUES ("
                + sql_str(row["chat_id"])
                + ", "
                + str(i)
                + ", "
                + sql_str(row["title"][:190])
                + ", "
                + sql_str(row["sha256"])
                + ", "
                + str(row["bytes"])
                + ", "
                + sql_str(row["source"][:190])
                + ", "
                + sql_str(part)
                + ", "
                + sql_str(written_at)
                + ") ON DUPLICATE KEY UPDATE title = VALUES(title), sha256 = VALUES(sha256), "
                "bytes = VALUES(bytes), source = VALUES(source), body = VALUES(body), "
                "written_at = VALUES(written_at)"
            )
            resp = loc.run_sql(sql)
            if not loc.sql_ok(resp):
                raise SystemExit(f"transcript upsert failed {row['chat_id']} chunk {i}")
            print("locker", row["chat_id"], "chunk", i, "ok")
    last = rows[-1]["chat_id"] if rows else ""
    policy = (
        f"Redacted Cursor chats in chats/ and {prefix}_transcript. "
        "No claves. Not required for revival."
    )
    for k, v in (
        ("last_transcript_id", last),
        ("transcript_count", str(len(rows))),
        ("transcript_policy", policy),
    ):
        sql = (
            f"INSERT INTO {prefix}_meta (k, v, updated_at) VALUES ("
            + sql_str(k)
            + ", "
            + sql_str(v)
            + ", "
            + sql_str(written_at)
            + ") ON DUPLICATE KEY UPDATE v = VALUES(v), updated_at = VALUES(updated_at)"
        )
        if not loc.sql_ok(loc.run_sql(sql)):
            raise SystemExit(f"meta {k} failed")


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()
    parser = argparse.ArgumentParser(description="Redact and archive this agent's Cursor chats.")
    parser.add_argument("--write-root", help="Agent folder. Default: this script's folder.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-push", action="store_true", help="Write local chats/ only.")
    parser.add_argument("--agent")
    parser.add_argument("--prefix")
    args = parser.parse_args(argv[1:])

    write_root = Path(args.write_root).resolve() if args.write_root else here
    ident = load_identity(write_root)
    agent = (args.agent or ident.get("agent") or write_root.name).strip()
    prefix = (args.prefix or ident.get("prefix") or "agent").strip()
    locker_fields, redactions = collect_secrets(write_root)
    extra_ids = known_ids_from_text(ident.get("_known_ids", ""))
    for name in (
        f"_{prefix}_self_payload.py",
        "_kingston_self_payload.py",
        "_codelio_self_payload.py",
        "RESTORE_KINGSTON.md",
        f"RESTORE_{agent.upper()}.md",
    ):
        p = write_root / name
        if p.is_file():
            extra_ids |= known_ids_from_text(p.read_text(encoding="utf-8", errors="replace"))

    paths = find_jsonl(write_root, agent, extra_ids)
    print("agent", agent)
    print("prefix", prefix)
    print("write_root", write_root)
    print("chats_found", len(paths))
    print("redaction_secrets", len(redactions))

    chats_dir = write_root / "chats"
    written_at = now_art()
    index_rows: list[dict] = []
    push_rows: list[dict] = []

    for path in paths:
        cid = chat_id_from_path(path)
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print("skip", cid, "read_fail")
            continue
        readable = jsonl_to_readable(raw)
        redacted = redact(readable, redactions)
        leftover = secrets_still_present(redacted, redactions)
        if leftover:
            print("skip", cid, "clave_still_present")
            continue
        source = str(path)
        if args.dry_run:
            print("would_write", cid, "chars", len(redacted))
            continue
        meta = write_local(chats_dir, cid, redacted, source)
        index_rows.append(meta)
        push_rows.append(
            {
                "chat_id": cid,
                "title": first_title(redacted, cid),
                "sha256": meta["sha256"],
                "bytes": meta["bytes"],
                "source": cid,
                "body": redacted,
            }
        )
        print("local", cid, "sha256", meta["sha256"][:12], "bytes", meta["bytes"])

    if args.dry_run:
        return 0

    index = {
        "agent": agent,
        "prefix": prefix,
        "written_at_art": written_at,
        "policy": "Redacted user/assistant text only. No claves. Not required for revival.",
        "chats": index_rows,
    }
    chats_dir.mkdir(parents=True, exist_ok=True)
    (chats_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("wrote", chats_dir / "index.json")

    if args.no_push:
        print("locker skipped")
        return 0

    database = locker_fields.get("database") or ident.get("database") or ""
    user = locker_fields.get("user") or ident.get("user") or ""
    password = locker_fields.get("pass") or ""
    origin = origin_from_server(locker_fields.get("server") or ident.get("origin") or "")
    if not (database and user and password and origin):
        print("locker skipped: locker account incomplete")
        return 0
    if not push_rows:
        print("locker skipped: no redacted chats")
        return 0
    kit = here if (here / "pma_locker.py").is_file() else write_root
    push_transcripts(
        kit,
        origin,
        {"database": database, "user": user, "pass": password},
        prefix,
        push_rows,
        written_at,
    )
    print("locker ok", prefix + "_transcript", "rows", len(push_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
