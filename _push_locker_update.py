# One-shot locker update. Reads .secrets / .secret and the local payload.
# Password is never printed.
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from archive_chats import collect_secrets  # noqa: E402
from pma_locker import Locker  # noqa: E402

ART = timezone(timedelta(hours=-3))
NOW = datetime.now(ART).strftime("%Y-%m-%d %H:%M:%S")
DOC_SECTIONS = (
    ("00_wake", "WAKE"),
    ("03_rules", "RULES"),
    ("05_job_state", "JOB_STATE"),
    ("06_experience", "EXPERIENCE"),
    ("08_es", "ES"),
)


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def load_pack():
    customs = sorted(
        p for p in HERE.glob("*_self_payload.py") if p.name != "payload_skeleton.py"
    )
    path = customs[0] if customs else HERE / "payload_skeleton.py"
    if not path.is_file():
        raise SystemExit("no payload_skeleton.py or *_self_payload.py in this folder")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path.name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def set_pma_from_secrets() -> dict[str, str]:
    fields, _ = collect_secrets(HERE)
    missing = [k for k in ("server", "database", "user", "pass") if not fields.get(k)]
    if missing:
        raise SystemExit("locker file missing: " + ", ".join(missing))
    server = (fields["server"] or "").rstrip("/")
    if "://" not in server:
        server = "https://" + server
    origin = f"{urlparse(server).scheme}://{urlparse(server).netloc}"
    os.environ["PMA_BASE"] = origin.rstrip("/") + "/phpmyadmin/"
    os.environ["PMA_DB"] = fields["database"]
    os.environ["PMA_USER"] = fields["user"]
    os.environ["PMA_PASS"] = fields["pass"]
    return fields


def main() -> int:
    if not os.environ.get("PMA_PASS"):
        set_pma_from_secrets()
    pack = load_pack()
    prefix = (getattr(pack, "PREFIX", None) or "").strip()
    if not prefix:
        raise SystemExit("payload has no PREFIX")
    loc = Locker()
    doc = f"{prefix}_document"
    for section, attr in DOC_SECTIONS:
        body = getattr(pack, attr, None)
        if not body:
            print("doc", section, "skip")
            continue
        sql = (
            f"UPDATE {doc} SET body = "
            + sql_str(body)
            + ", written_at = "
            + sql_str(NOW)
            + " WHERE section = "
            + sql_str(section)
        )
        resp = loc.run_sql(sql)
        ok = loc.sql_ok(resp)
        print("doc", section, "ok" if ok else "FAIL", "bytes", len(resp))
        if not ok:
            return 1

    boot = dict(getattr(pack, "BOOT", {}))
    boot["written_at_art"] = NOW
    sql = (
        f"UPDATE {prefix}_boot SET payload = "
        + sql_str(json.dumps(boot, ensure_ascii=False))
        + ", updated_at = "
        + sql_str(NOW)
        + " WHERE id = 1"
    )
    resp = loc.run_sql(sql)
    print("boot", "ok" if loc.sql_ok(resp) else "FAIL", "bytes", len(resp))
    if not loc.sql_ok(resp):
        return 1

    meta = dict(getattr(pack, "META", {}))
    meta["written_at_art"] = NOW
    meta.setdefault(
        "locker_close",
        "After a finished order, UPDATE every locker page that order changed. "
        "Append to experience; do not replace the page. Then archive_chats.py. "
        "Do not wait to be told save. Never wipe.",
    )
    for k, v in meta.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        sql = (
            f"INSERT INTO {prefix}_meta (k, v, updated_at) VALUES ("
            + sql_str(str(k))
            + ", "
            + sql_str(str(v))
            + ", "
            + sql_str(NOW)
            + ") ON DUPLICATE KEY UPDATE v = VALUES(v), updated_at = VALUES(updated_at)"
        )
        resp = loc.run_sql(sql)
        print("meta", k, "ok" if loc.sql_ok(resp) else "FAIL")
        if not loc.sql_ok(resp):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
