"""phpMyAdmin locker helper (proven on 5.2.3).

Password from env PMA_PASS only. Never printed.

    set PMA_BASE=https://example.com/phpmyadmin/
    set PMA_DB=siral_agent
    set PMA_USER=siral_agent
    set PMA_PASS=...

    python pma_locker.py ping
    python pma_locker.py tables
    python pma_locker.py sql "CREATE TABLE ..."
    python pma_locker.py import-sql schema.sql
    python pma_locker.py export TABLE out.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.cookiejar import CookieJar


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict] = []
        self._cur: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self._cur = {"action": a.get("action", ""), "inputs": {}}
            self.forms.append(self._cur)
        elif tag == "input" and self._cur is not None:
            name = a.get("name")
            if name:
                self._cur["inputs"][name] = a.get("value", "")


def _env(name: str) -> str:
    v = os.environ.get(name) or ""
    if not v:
        raise SystemExit(f"{name} missing")
    return v


class Locker:
    def __init__(self) -> None:
        self.base = _env("PMA_BASE").rstrip("/") + "/"
        self.db = _env("PMA_DB")
        self.user = _env("PMA_USER")
        self.password = _env("PMA_PASS")
        jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self._logged = False

    def _fetch(self, url: str, data: dict | None = None, raw: bool = False):
        body = None
        headers = {
            "User-Agent": "Mozilla/5.0 AgentSelfSave/1",
            "Referer": self.base,
        }
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, headers=headers)
        with self.opener.open(req, timeout=120) as resp:
            blob = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            final = resp.geturl()
        if raw:
            return final, ctype, blob
        return final, ctype, blob.decode("utf-8", "replace")

    def login(self) -> None:
        if self._logged:
            return
        _, _, html = self._fetch(self.base)
        p = FormParser()
        p.feed(html)
        form = next((f for f in p.forms if "pma_username" in f["inputs"]), None)
        if form is None:
            if self.db in html:
                self._logged = True
                return
            raise SystemExit("no phpMyAdmin login form")
        action = form["action"] or "index.php"
        payload = dict(form["inputs"])
        payload["pma_username"] = self.user
        payload["pma_password"] = self.password
        payload.setdefault("server", "1")
        _, _, after = self._fetch(urllib.parse.urljoin(self.base, action), payload)
        if self.db not in after and "pma_username" in after:
            raise SystemExit("phpMyAdmin login failed")
        self._logged = True

    def token(self) -> str:
        self.login()
        url = urllib.parse.urljoin(
            self.base, f"index.php?route=/database/sql&db={urllib.parse.quote(self.db)}"
        )
        _, _, page = self._fetch(url)
        m = re.search(r'name="token" value="([^"]+)"', page) or re.search(
            r'token:"([^"]+)"', page
        )
        if not m:
            raise SystemExit("no phpMyAdmin token")
        return m.group(1)

    def run_sql(self, sql: str) -> str:
        token = self.token()
        url = urllib.parse.urljoin(self.base, "index.php?route=/import")
        _, _, body = self._fetch(
            url,
            {
                "db": self.db,
                "table": "",
                "token": token,
                "sql_query": sql,
                "ajax_request": "true",
                "ajax_page_request": "true",
                "server": "1",
            },
        )
        return body

    def sql_ok(self, body: str) -> bool:
        return "alert-success" in body and "alert-danger" not in body

    def export_table(self, table: str, kind: str = "json") -> bytes:
        token = self.token()
        url = urllib.parse.urljoin(self.base, "index.php?route=/export")
        data = {
            "db": self.db,
            "table": table,
            "export_type": "table",
            "export_method": "quick",
            "quick_or_custom": "quick",
            "what": kind,
            "allrows": "1",
            "output_format": "sendit",
            "filename_template": "@TABLE@",
            "charset": "utf-8",
            "compression": "none",
            "token": token,
            "server": "1",
        }
        if kind == "json":
            data["json_structure_or_data"] = "data"
        else:
            data["csv_separator"] = ","
            data["csv_enclosed"] = '"'
            data["csv_escaped"] = '"'
            data["csv_terminated"] = "AUTO"
            data["csv_null"] = "NULL"
            data["csv_columns"] = "something"
            data["csv_structure_or_data"] = "data"
        _, _, blob = self._fetch(url, data, raw=True)
        return blob


def table_rows(pma_json: bytes) -> list[dict]:
    data = json.loads(pma_json.decode("utf-8"))
    for x in data:
        if x.get("type") == "table":
            return list(x.get("data") or [])
    return []


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    loc = Locker()
    if cmd == "ping":
        loc.login()
        print("login_ok db", loc.db)
        return 0
    if cmd == "tables":
        body = loc.run_sql("SHOW TABLES")
        print("sql_ok", loc.sql_ok(body), "bytes", len(body))
        print("hint: use export to read rows; /sql browse HTML is not a result set")
        return 0 if loc.sql_ok(body) else 1
    if cmd == "sql":
        if len(argv) < 3:
            raise SystemExit("sql needs a statement")
        body = loc.run_sql(argv[2])
        print("sql_ok", loc.sql_ok(body), "bytes", len(body))
        if not loc.sql_ok(body):
            err = re.search(r"alert-danger.*?>(.*?)</", body, re.S)
            if err:
                print(re.sub(r"<[^>]+>", "", err.group(1))[:500])
            return 1
        return 0
    if cmd == "import-sql":
        if len(argv) < 3:
            raise SystemExit("import-sql needs a file")
        sql = open(argv[2], encoding="utf-8").read()
        body = loc.run_sql(sql)
        print("sql_ok", loc.sql_ok(body), "bytes", len(body))
        return 0 if loc.sql_ok(body) else 1
    if cmd == "export":
        if len(argv) < 4:
            raise SystemExit("export TABLE OUT.json")
        table, out = argv[2], argv[3]
        kind = "csv" if out.lower().endswith(".csv") else "json"
        blob = loc.export_table(table, kind)
        open(out, "wb").write(blob)
        print("wrote", out, "bytes", len(blob))
        if kind == "json":
            rows = table_rows(blob)
            print("rows", len(rows))
            if rows:
                print("keys", list(rows[0].keys()))
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
