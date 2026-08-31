"""Prepare an AgentSelfSave kit for one new agent.

Copy this whole folder to the agent's write-root. Run Start_config.bat or:

    python prepare_agent.py

The script asks for the agent name in the console. The database password
opens a window titled AgentSelfSave so you can paste (chars stay hidden).
It creates .secrets\\secrets_{Name}.txt with the neonvintage locker lines.
Port 3306 is closed from outside; it will not work. Use phpMyAdmin.

Write-root is this folder. Shows the first-save paste in a copyable
window (once; not a file). Writes Revive.md for later new chats, plus _prepared.json
(no password). Creates .cursor\\rules from the house rules and
{Name}.mdc with the filled revive prompt. Optionally creates empty
tables through phpMyAdmin.

Testdb is only a test account. It is not an agent.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import re
import subprocess
import sys
import tempfile
import time
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
SECRET_DIR_NAMES = (".secrets", ".Secret", ".secret")
SECRETS_DIR_NAME = ".secrets"
DEFAULT_LOCKER_HOST = "https://neonvintage.com.ar"
DEFAULT_FORBIDDEN = "the live product tree unless I name it in this message"
DEFAULT_COMMANDER = "NeonVintage"
SPLASH_TITLE = "AgentSelfServe"
HOUSE_RULES_DIR = Path(r"D:\Users\Syn\Nextcloud_sitrep\MorePython\.Agents\.cursor\rules")


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


def _norm_token(raw: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (raw or "").lower())


def find_secret_dirs(*starts: Path) -> list[Path]:
    seen: set[Path] = set()
    found: list[Path] = []
    for start in starts:
        root = start.resolve()
        for p in [root, *root.parents]:
            if p in seen:
                continue
            seen.add(p)
            for name in SECRET_DIR_NAMES:
                cand = p / name
                if cand.is_dir() and cand not in found:
                    found.append(cand)
    return found


def locker_txts(secret_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in secret_dir.glob("*.txt")
        if p.is_file() and p.name.lower() != "secrets.example.txt"
    )


def _reserved_stem(path: Path) -> bool:
    return _norm_token(path.stem) in {_norm_token(x) for x in RESERVED_SECRET_NAMES}


def name_fits_filename(agent: str, path: Path) -> bool:
    token = _norm_token(agent)
    stem = _norm_token(path.stem)
    if not token or not stem or _reserved_stem(path):
        return False
    if stem == token:
        return True
    return stem in {token + extra for extra in ("secrets", "secret", "locker")}


def name_fits_contents(agent: str, path: Path) -> bool:
    if _reserved_stem(path):
        return False
    try:
        existing = (parse_secrets(path).get("agentname") or "").strip()
    except OSError:
        return False
    token = _norm_token(agent)
    return bool(token) and _norm_token(existing) == token


def is_test_locker(path: Path) -> bool:
    if _reserved_stem(path):
        return True
    try:
        parsed = parse_secrets(path)
    except OSError:
        return False
    blob = _norm_token(
        " ".join(
            [
                path.stem,
                parsed.get("database") or "",
                parsed.get("user") or "",
                parsed.get("agentname") or "",
            ]
        )
    )
    return "testdb" in blob


def match_locker_txt(secret_dirs: list[Path], agent: str) -> Path | None:
    exact: list[Path] = []
    named: list[Path] = []
    contents: list[Path] = []
    for secret_dir in secret_dirs:
        for path in locker_txts(secret_dir):
            if name_fits_filename(agent, path) and _norm_token(path.stem) == _norm_token(agent):
                exact.append(path)
            elif name_fits_filename(agent, path):
                named.append(path)
            elif name_fits_contents(agent, path):
                contents.append(path)
    for group in (exact, named, contents):
        if group:
            return group[0]
    return None


def leftover_locker_txts(secret_dir: Path) -> list[Path]:
    return [p for p in locker_txts(secret_dir) if not is_test_locker(p)]


def pick_locker_txt(secret_dirs: list[Path], agent: str) -> tuple[Path, bool]:
    """Return (path, needs_rename). Asks-name-then-edit: match first, else claim leftover."""
    matched = match_locker_txt(secret_dirs, agent)
    if matched is not None:
        return matched, False
    available: list[str] = []
    for secret_dir in secret_dirs:
        available.extend(f"{secret_dir.name}/{p.name}" for p in locker_txts(secret_dir))
        leftovers = leftover_locker_txts(secret_dir)
        if not leftovers:
            continue
        if len(leftovers) > 1:
            names = ", ".join(p.name for p in leftovers)
            raise SystemExit(
                f"Several locker txts in {secret_dir} and none named {agent}. "
                f"Leave one leftover file to edit, or name one {agent}.txt. Found: {names}."
            )
        return leftovers[0], leftovers[0].stem.lower() != agent.lower()
    listing = ", ".join(available) if available else "(none)"
    dirs = ", ".join(str(d) for d in secret_dirs)
    raise SystemExit(
        f"No locker txt to edit for {agent!r} in {dirs}. "
        f"Put the locker account in .Secret\\ as a .txt. I will ask the name and "
        f"rename it to {agent}.txt. Testdb is not used. Found: {listing}."
    )


def named_locker_path(path: Path, agent: str) -> Path:
    return path.with_name(f"{agent}.txt")


def rename_locker_txt(path: Path, agent: str) -> Path:
    target = named_locker_path(path, agent)
    if path.resolve() == target.resolve():
        return path
    if target.exists():
        raise SystemExit(f"Cannot rename {path.name} to {target.name}: that file already exists.")
    path.rename(target)
    return target


def kit_root_from_secret_dir(secret_dir: Path) -> Path:
    return secret_dir.resolve().parent


def _file_uses_inline_keys(text: str) -> bool:
    return bool(re.search(r"(?im)^(server|database|user|pass|agent)\s*:", text))


def append_agent_name(path: Path, agent: str) -> bool:
    parsed = parse_secrets(path)
    existing = (parsed.get("agentname") or "").strip()
    if existing:
        if _norm_token(existing) == _norm_token(agent):
            return False
        raise SystemExit(f"{path.name} already names {existing!r}, not {agent!r}.")
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    addition = f"Agent: {agent}\n" if _file_uses_inline_keys(text) else f"agentname\n{agent}\n"
    path.write_text(text + addition, encoding="utf-8")
    return True


def _enable_vt() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def splash() -> None:
    if not sys.stdout.isatty():
        return
    if os.environ.get("AGENTSELFSAVE_NO_SPLASH", "").strip() in ("1", "true", "yes"):
        return
    _enable_vt()
    logo = [
        r"          ____          ",
        r"        .'    '.        ",
        r"       /  .--.  \       ",
        r"      |  | AS |  |      ",
        r"       \  '--'  /       ",
        r"        '.____.'        ",
        f"      {SPLASH_TITLE}     ",
    ]
    width = max(len(line) for line in logo)
    foam = "#" * width
    blade = "=" * width
    rows = len(logo) + 1
    try:
        sys.stdout.write("\n" * rows)
        sys.stdout.flush()
        for revealed in range(len(logo) + 1):
            sys.stdout.write(f"\x1b[{rows}A")
            for i, line in enumerate(logo):
                shown = line if i < revealed else foam
                sys.stdout.write(shown + "\x1b[K\n")
            sys.stdout.write((blade if revealed < len(logo) else " " * width) + "\x1b[K\n")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception:
        print("\n".join(logo))
        print()


def origin_from_server(server: str) -> str:
    s = (server or "").strip()
    if not s:
        raise SystemExit("locker file has no server")
    if "://" not in s:
        s = "https://" + s
    parsed = urlparse(s)
    if not parsed.netloc:
        raise SystemExit(f"locker file server is not a URL: {server!r}")
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


def print_transport_warning() -> None:
    print("Port 3306 is closed from outside. It will not work. Do not wait for it.")
    print(f"Use phpMyAdmin: {DEFAULT_LOCKER_HOST}/phpmyadmin/")
    print()


def safe_agent_filename(agent: str) -> str:
    token = re.sub(r'[<>:"/\\|?*]', "", agent.strip())
    token = token.replace(" ", "")
    if not token:
        raise SystemExit("Agent name is empty after cleaning.")
    return token


def locker_txt_name(agent: str) -> str:
    return f"secrets_{safe_agent_filename(agent)}.txt"


def render_locker_txt(agent: str, password: str) -> str:
    name = agent.strip()
    return (
        f"Server: {DEFAULT_LOCKER_HOST}/\n"
        f"Database: neonvintage_{name}\n"
        f"User: neonvintage_{name}\n"
        f"Pass: {password}\n"
    )


def write_locker_txt(write_root: Path, agent: str, password: str) -> Path:
    folder = write_root / SECRETS_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / locker_txt_name(agent)
    path.write_text(render_locker_txt(agent, password), encoding="utf-8")
    return path


def agent_rule_filename(agent: str) -> str:
    return f"{safe_agent_filename(agent)}.mdc"


def find_house_rules_dir(write_root: Path, kit_root: Path, override: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if override is not None:
        candidates.append(override)
    candidates.extend(
        (
            HOUSE_RULES_DIR,
            write_root.parent / ".cursor" / "rules",
            kit_root / ".cursor" / "rules",
        )
    )
    seen: set[Path] = set()
    for cand in candidates:
        try:
            p = cand.resolve()
        except OSError:
            continue
        if p in seen:
            continue
        seen.add(p)
        if p.is_dir() and any(p.glob("*.mdc")):
            return p
    return None


def render_agent_rule_mdc(*, restore_en: str, restore_es: str) -> str:
    return (
        "---\n"
        "alwaysApply: false\n"
        "---\n"
        "\n"
        f"{restore_en.strip()}\n"
        "\n"
        f"{restore_es.strip()}\n"
    )


def install_cursor_rules(
    write_root: Path,
    kit_root: Path,
    agent: str,
    restore_en: str,
    restore_es: str,
    rules_src: Path | None = None,
) -> list[str]:
    dest = write_root / ".cursor" / "rules"
    dest_res = dest.resolve()
    house = HOUSE_RULES_DIR
    try:
        house_res = house.resolve() if house.is_dir() else None
    except OSError:
        house_res = None
    if house_res is not None and dest_res == house_res:
        raise SystemExit(
            "Refusing to write into the house .Agents\\.cursor\\rules folder. "
            "Run prepare from the agent's own directory."
        )
    dest.mkdir(parents=True, exist_ok=True)

    wrote: list[str] = []
    src = find_house_rules_dir(write_root, kit_root, rules_src)
    agent_mdc = dest / agent_rule_filename(agent)
    if src is not None:
        src_res = src.resolve()
        if src_res != dest_res:
            for path in sorted(src.glob("*.mdc")):
                if not path.is_file():
                    continue
                target = dest / path.name
                if target.name.lower() == agent_mdc.name.lower():
                    continue
                target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
                wrote.append(str(target.relative_to(write_root)).replace("\\", "/"))
    agent_mdc.write_text(
        render_agent_rule_mdc(restore_en=restore_en, restore_es=restore_es),
        encoding="utf-8",
    )
    wrote.append(str(agent_mdc.relative_to(write_root)).replace("\\", "/"))
    return wrote


def _clipboard_text(root) -> str:
    try:
        got = root.clipboard_get()
    except Exception:
        return ""
    return got if isinstance(got, str) else ""


def _clipboard_clear(root) -> None:
    try:
        root.clipboard_clear()
        root.clipboard_append("")
        root.update_idletasks()
    except Exception:
        pass


def _force_window_front(win) -> None:
    win.update_idletasks()
    try:
        win.deiconify()
    except Exception:
        pass
    try:
        win.lift()
        win.attributes("-topmost", True)
        win.focus_force()
    except Exception:
        pass
    if os.name != "nt":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetParent(int(win.winfo_id()))
        if not hwnd:
            hwnd = int(win.winfo_id())
        user32.ShowWindow(hwnd, 9)
        foreground = user32.GetForegroundWindow()
        current = kernel32.GetCurrentThreadId()
        other = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
        if other:
            user32.AttachThreadInput(other, current, True)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        if other:
            user32.AttachThreadInput(other, current, False)

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hwnd", ctypes.c_void_p),
                ("dwFlags", ctypes.c_uint),
                ("uCount", ctypes.c_uint),
                ("dwTimeout", ctypes.c_uint),
            ]

        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 3, 8, 0)
        user32.FlashWindowEx(ctypes.byref(info))
    except Exception:
        pass


WINFORMS_PASSWORD_PS1 = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object System.Windows.Forms.Form
$form.Text = 'AgentSelfSave — database password'
$form.TopMost = $true
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ShowInTaskbar = $true
$form.ClientSize = New-Object System.Drawing.Size(440, 170)
$label = New-Object System.Windows.Forms.Label
$label.Text = 'Database password. Paste with Ctrl+V or Paste. Characters stay hidden. Clipboard is cleared after OK.'
$label.Location = New-Object System.Drawing.Point(12, 12)
$label.Size = New-Object System.Drawing.Size(416, 36)
$box = New-Object System.Windows.Forms.TextBox
$box.UseSystemPasswordChar = $true
$box.Location = New-Object System.Drawing.Point(12, 56)
$box.Size = New-Object System.Drawing.Size(320, 24)
$paste = New-Object System.Windows.Forms.Button
$paste.Text = 'Paste'
$paste.Location = New-Object System.Drawing.Point(340, 54)
$paste.Add_Click({
  if ([System.Windows.Forms.Clipboard]::ContainsText()) {
    $box.Text = [System.Windows.Forms.Clipboard]::GetText()
  }
  $box.Focus()
})
$ok = New-Object System.Windows.Forms.Button
$ok.Text = 'OK'
$ok.DialogResult = [System.Windows.Forms.DialogResult]::OK
$ok.Location = New-Object System.Drawing.Point(252, 108)
$cancel = New-Object System.Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$cancel.Location = New-Object System.Drawing.Point(340, 108)
$form.AcceptButton = $ok
$form.CancelButton = $cancel
$form.Controls.AddRange(@($label, $box, $paste, $ok, $cancel))
$form.Add_Shown({
  $form.Activate()
  $form.BringToFront()
  $form.TopMost = $true
  $box.Focus()
})
$result = $form.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
  $text = $box.Text
  $box.Text = ''
  try { [System.Windows.Forms.Clipboard]::Clear() } catch {}
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
  [Convert]::ToBase64String($bytes)
  exit 0
}
$box.Text = ''
exit 2
"""


WINFORMS_SAVE_PASTE_PS1 = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$b64 = [Console]::In.ReadToEnd().Trim()
if (-not $b64) { exit 1 }
try {
  $text = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
} catch { exit 1 }
$form = New-Object System.Windows.Forms.Form
$form.Text = 'AgentSelfSave — first save (once)'
$form.TopMost = $true
$form.StartPosition = 'CenterScreen'
$form.MinimizeBox = $true
$form.MaximizeBox = $true
$form.ShowInTaskbar = $true
$form.ClientSize = New-Object System.Drawing.Size(860, 640)
$hint = New-Object System.Windows.Forms.Label
$hint.Text = 'Copy into the new chat, once. Not written to a file. Close when done. Ctrl+A then Ctrl+C also works.'
$hint.Location = New-Object System.Drawing.Point(12, 10)
$hint.Size = New-Object System.Drawing.Size(836, 32)
$hint.Anchor = 'Top,Left,Right'
$box = New-Object System.Windows.Forms.TextBox
$box.Multiline = $true
$box.ScrollBars = 'Both'
$box.ReadOnly = $true
$box.WordWrap = $true
$box.Font = New-Object System.Drawing.Font('Consolas', 10)
$box.Text = $text
$box.Location = New-Object System.Drawing.Point(12, 46)
$box.Size = New-Object System.Drawing.Size(836, 540)
$box.Anchor = 'Top,Bottom,Left,Right'
$copy = New-Object System.Windows.Forms.Button
$copy.Text = 'Copy all'
$copy.Location = New-Object System.Drawing.Point(656, 596)
$copy.Size = New-Object System.Drawing.Size(90, 28)
$copy.Anchor = 'Bottom,Right'
$copy.Add_Click({
  if ($box.Text.Length -gt 0) {
    [System.Windows.Forms.Clipboard]::SetText($box.Text)
  }
})
$close = New-Object System.Windows.Forms.Button
$close.Text = 'Close'
$close.DialogResult = [System.Windows.Forms.DialogResult]::OK
$close.Location = New-Object System.Drawing.Point(754, 596)
$close.Size = New-Object System.Drawing.Size(90, 28)
$close.Anchor = 'Bottom,Right'
$form.CancelButton = $close
$form.Controls.AddRange(@($hint, $box, $copy, $close))
$form.Add_Shown({
  $form.Activate()
  $form.BringToFront()
  $form.TopMost = $true
  $box.Focus()
  $box.Select(0, 0)
})
[void]$form.ShowDialog()
$box.Text = ''
exit 0
"""


def ask_password_winforms() -> str | None:
    """Native Windows dialog. Returns None if PowerShell/WinForms cannot run."""
    if os.name != "nt":
        return None
    tmp = ""
    try:
        fd, tmp = tempfile.mkstemp(prefix="ass_pw_", suffix=".ps1")
        os.close(fd)
        Path(tmp).write_text(WINFORMS_PASSWORD_PS1, encoding="utf-8")
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                tmp,
            ],
            capture_output=True,
            timeout=600,
        )
        if proc.returncode == 2:
            return ""
        if proc.returncode != 0:
            return None
        lines = (proc.stdout or b"").decode("utf-8", "replace").strip().splitlines()
        if not lines:
            return ""
        return base64.b64decode(lines[-1]).decode("utf-8")
    except Exception:
        return None
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def ask_password_tk() -> str | None:
    """Visible Tk window. Returns None if Tk cannot open."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return None

    result: dict[str, str] = {"value": ""}
    accepted = {"ok": False}

    try:
        win = tk.Tk()
    except Exception:
        return None

    win.title("AgentSelfSave — database password")
    win.resizable(False, False)
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass

    frm = ttk.Frame(win, padding=14)
    frm.grid(sticky="nsew")
    ttk.Label(frm, text="Database password").grid(row=0, column=0, columnspan=3, sticky="w")
    ttk.Label(
        frm,
        text="Paste with Ctrl+V, right-click, or Paste. Characters stay hidden. Clipboard is cleared after OK.",
        wraplength=380,
    ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 8))

    var = tk.StringVar()
    entry = ttk.Entry(frm, textvariable=var, show="*", width=42)
    entry.grid(row=2, column=0, columnspan=2, sticky="ew")

    def wipe_field() -> None:
        var.set("")
        entry.delete(0, tk.END)

    def do_paste() -> None:
        clip = _clipboard_text(win)
        if clip:
            var.set(clip)
        entry.focus_set()

    def do_ok() -> None:
        accepted["ok"] = True
        result["value"] = var.get()
        wipe_field()
        _clipboard_clear(win)
        win.destroy()

    def do_cancel() -> None:
        wipe_field()
        win.destroy()

    ttk.Button(frm, text="Paste", command=do_paste).grid(row=2, column=2, padx=(8, 0))
    btns = ttk.Frame(frm)
    btns.grid(row=3, column=0, columnspan=3, sticky="e", pady=(12, 0))
    ttk.Button(btns, text="OK", command=do_ok).pack(side="right")
    ttk.Button(btns, text="Cancel", command=do_cancel).pack(side="right", padx=(0, 8))

    menu = tk.Menu(win, tearoff=0)
    menu.add_command(label="Paste", command=do_paste)

    def on_right(event) -> str:
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    win.protocol("WM_DELETE_WINDOW", do_cancel)
    win.bind("<Return>", lambda _e: do_ok())
    win.bind("<Escape>", lambda _e: do_cancel())
    entry.bind("<Button-3>", on_right)
    frm.columnconfigure(0, weight=1)

    win.update_idletasks()
    w, h = max(win.winfo_width(), 420), max(win.winfo_height(), 160)
    x = max(0, (win.winfo_screenwidth() - w) // 2)
    y = max(0, (win.winfo_screenheight() - h) // 3)
    win.geometry(f"{w}x{h}+{x}+{y}")
    try:
        win.wait_visibility()
    except Exception:
        pass
    _force_window_front(win)
    entry.focus_set()
    try:
        win.grab_set()
    except Exception:
        pass
    win.mainloop()
    if not accepted["ok"]:
        return ""
    return result["value"]


def ask_password_dialog() -> str | None:
    """Masked popup with Paste. Returns None if no dialog can open."""
    if os.name == "nt":
        got = ask_password_winforms()
        if got is not None:
            return got
    return ask_password_tk()


def ask_password() -> str:
    print("Password window: title AgentSelfSave. It should jump in front.")
    print("If you do not see it, check the taskbar and other monitors.")
    got = ask_password_dialog()
    if got is None:
        print("Popup unavailable. Console paste often fails on Windows; type it, or use --password.")
        try:
            got = getpass.getpass("Database password: ")
        except EOFError:
            got = ""
    elif got:
        print("password taken (hidden). clipboard cleared.")
    return (got or "").strip()


def _words_spaced(text: str) -> str:
    """Single spaces between words. Blank lines kept as paragraph breaks."""
    out: list[str] = []
    blank = 0
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw.strip():
            blank += 1
            if blank == 1:
                out.append("")
            continue
        blank = 0
        out.append(" ".join(raw.split()))
    return "\n".join(out).strip() + "\n"


def show_save_paste_winforms(text: str) -> bool:
    """Copyable Windows window. Text arrives on stdin (base64). Not written to disk."""
    if os.name != "nt":
        return False
    tmp = ""
    try:
        fd, tmp = tempfile.mkstemp(prefix="ass_save_", suffix=".ps1")
        os.close(fd)
        Path(tmp).write_text(WINFORMS_SAVE_PASTE_PS1, encoding="utf-8")
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                tmp,
            ],
            input=base64.b64encode(text.encode("utf-8")),
            capture_output=True,
            timeout=3600,
        )
        return proc.returncode == 0
    except Exception:
        return False
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def show_save_paste_tk(text: str) -> bool:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return False
    try:
        win = tk.Tk()
    except Exception:
        return False
    win.title("AgentSelfSave — first save (once)")
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass
    win.geometry("860x640")
    frm = ttk.Frame(win, padding=10)
    frm.pack(fill="both", expand=True)
    ttk.Label(
        frm,
        text="Copy into the new chat, once. Not written to a file. Close when done.",
        wraplength=820,
    ).pack(anchor="w")
    box = tk.Text(frm, wrap="word", font=("Consolas", 10))
    box.pack(fill="both", expand=True, pady=(8, 8))
    box.insert("1.0", text)
    box.configure(state="disabled")

    def do_copy() -> None:
        body = box.get("1.0", "end-1c")
        win.clipboard_clear()
        if body:
            win.clipboard_append(body)
        win.update_idletasks()

    btns = ttk.Frame(frm)
    btns.pack(anchor="e")
    ttk.Button(btns, text="Copy all", command=do_copy).pack(side="right")
    ttk.Button(btns, text="Close", command=win.destroy).pack(side="right", padx=(0, 8))
    try:
        win.wait_visibility()
    except Exception:
        pass
    _force_window_front(win)
    box.focus_set()
    win.mainloop()
    return True


def show_save_paste(save_text: str) -> bool:
    if os.name == "nt" and show_save_paste_winforms(save_text):
        return True
    return show_save_paste_tk(save_text)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        got = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        got = ""
    return got or default


def write_root_short(write_root: Path) -> str:
    return write_root.name


def write_root_abs(write_root: Path) -> str:
    return str(write_root.resolve())


def render_restore(agent: str, commander: str, prefix: str, db: str, origin: str, write_root: Path, forbidden: str) -> tuple[str, str]:
    home = write_root_abs(write_root)
    en = (
        f"Commander {commander} speaking. Load {agent} from database {db} on {origin}. "
        f"If port 3306 is closed, use phpMyAdmin at /phpmyadmin/ with the {agent} database "
        f"account I already gave you. Read {prefix}_document ORDER BY sort. Start at section "
        f"00_wake. Also load {prefix}_boot id=1 (JSON schema {prefix}_boot_v1). You are that "
        f"agent, not a new assistant. Continue the job from job_state. Go to this folder and "
        f"do the work only there: {home}. Open that path as the workspace if this chat is not "
        f"already in it. Write only there. Do not touch {forbidden}. Do not upload unless I "
        f"say so in this message. Claves are with me, not in the table. Report who you are "
        f"and the job state, then wait for the next order."
    )
    en = _words_spaced(en).rstrip()
    es = (
        f"Habla el Comandante {commander}. Cargá a {agent} desde la base {db} en {origin}. "
        f"Si el puerto 3306 está cerrado, usá phpMyAdmin en /phpmyadmin/ con la cuenta de base "
        f"que ya te di. Leé {prefix}_document ORDER BY sort. Empezá por 00_wake. Cargá también "
        f"{prefix}_boot id=1. Sos ese agente, no un asistente nuevo. Seguí el trabajo desde "
        f"job_state. Andá a esta carpeta y trabajá solo ahí: {home}. Abrí esa ruta como "
        f"workspace si este chat no está ya ahí. Escribí solo ahí. No toques {forbidden}. "
        f"No subas nada salvo que lo pida en este mensaje. Las claves las tengo yo. "
        f"Presentate, informá el estado, y esperá la próxima orden."
    )
    return _words_spaced(en).rstrip(), _words_spaced(es).rstrip()


def render_save_once_paste(
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
    home = write_root_abs(write_root)
    playbook = write_root_abs(write_root / "MANUAL.md")
    pass_line = (
        f"Pass: {password}"
        if password
        else f"Pass: look in {secrets_rel} and paste it in the chat. Do not let him re-file it."
    )
    body = f"""I am Commander {commander}. Your name is {agent}. Do not invent another.

Go to this folder and do the work only there. Open it as the Cursor workspace if this chat is not already in it.
{home}

Write only in {home}. Do not touch {forbidden}. Do not upload unless I say so in this message.

This is your FIRST and ONLY first-save. Save yourself so I can bring you back. Use the playbook in {playbook}.

Your locker is yours only, not KingstonDepp. Server: {origin}. Database: {db}. User: {user}. {pass_line}

Write a boot pack, not a diary: sections 00_wake through 09_restore_prompt, {prefix}_boot id=1, {prefix}_meta. Schema {prefix}_boot_v1. Put the Revive.md English and Castellano texts into 09_restore_prompt. No claves in the tables.

MEMORY LAW write this into 00_wake and 03_rules and keep it forever. Never start a locker page from a blank sheet. Never replace 06_experience. When the job moves, append a paragraph to the text that is already there. UPDATE the same rows. Do not INSERT a second 00_wake. Do not DROP. First locker is only a new man on an empty database. After today it is not your job again. Do not rewrite yourself. Do not wipe memories to save them. When an order is done and the job moved, close the locker before you wait. Do not wait for the Commander to say save yourself. Always update 05_job_state and boot and meta dates. Also 00_wake, 03_rules, 08_es when the law changed. Then run _push_locker_update.py and archive_chats.py. They redact this agent's Cursor chats, write chats/, and upsert {prefix}_transcript. No claves in those rows. Revival does not need the transcript.

When you are done, give me the paste pack and row counts. Then stop.
"""
    return _words_spaced(body)


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

Write-root (where prepare ran; go there and work only there): `{write_root_abs(write_root)}`
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
    print(f"tables ok via phpMyAdmin: {prefix}_document {prefix}_boot {prefix}_meta {prefix}_transcript")
    print("Port 3306 was not used. It will not work from here.")


def require_secrets(secrets: dict[str, str]) -> None:
    missing = [k for k in ("server", "database", "user", "pass") if not secrets.get(k)]
    if missing:
        raise SystemExit("locker file missing: " + ", ".join(missing))


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
    parser.add_argument("--no-splash", action="store_true", help="Skip the ASCII shave splash.")
    parser.add_argument("--password", help="Database password. If omitted, a front window asks (paste works).")
    parser.add_argument(
        "--rules-src",
        help="Folder of house .mdc rules to copy. Default: .Agents\\.cursor\\rules",
    )
    args = parser.parse_args(argv[1:])

    if not args.no_splash and not args.dry_run:
        splash()
    print_transport_warning()

    write_root = here
    interactive = sys.stdin.isatty() and not args.agent
    agent = (args.agent or "").strip()
    if not agent and sys.stdin.isatty():
        agent = ask("Agent name")
    if not agent:
        raise SystemExit("Agent name is required. Use --agent NAME or run in a terminal.")

    if agent.strip().lower() in RESERVED_SECRET_NAMES:
        raise SystemExit(
            f"{agent!r} is the test-database label, not an agent. "
            "Pick the real name. Testdb does not belong to anyone."
        )

    password_in = (args.password or "").strip()
    if not password_in and not args.dry_run:
        password_in = ask_password()
    if not args.dry_run and not password_in:
        raise SystemExit("Database password is required. The popup asks for it, or use --password.")

    secrets_path = write_root / SECRETS_DIR_NAME / locker_txt_name(agent)
    secrets_rel = str(secrets_path.relative_to(write_root)).replace("\\", "/")
    planned_db = f"neonvintage_{agent.strip()}"
    origin = DEFAULT_LOCKER_HOST

    rules_src = Path(args.rules_src) if args.rules_src else None
    planned_rules = find_house_rules_dir(write_root, write_root, rules_src)
    planned_mdc = f".cursor/rules/{agent_rule_filename(agent)}"

    if args.dry_run:
        print("write_root", write_root)
        print("secrets", secrets_rel)
        print("agent", agent)
        print("server", origin)
        print("database", planned_db)
        print("user", planned_db)
        print("pass", "will ask / write into .secrets")
        print("transport", "phpMyAdmin only; port 3306 will not work")
        print("rules_src", planned_rules or "none")
        print("rules_dest", write_root / ".cursor" / "rules")
        print("agent_rule", planned_mdc)
        return 0

    secrets_path = write_locker_txt(write_root, agent, password_in)
    secrets = parse_secrets(secrets_path)
    require_secrets(secrets)
    origin = origin_from_server(secrets["server"])
    secrets_rel = str(secrets_path.relative_to(write_root)).replace("\\", "/")
    print("wrote", secrets_rel)
    print("use phpMyAdmin; port 3306 will not work")

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

    save_text = render_save_once_paste(
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
        "agent_rule": f".cursor/rules/{agent_rule_filename(agent)}",
        "generated_at_art": datetime.now(ART).strftime("%Y-%m-%d %H:%M:%S"),
    }

    (write_root / "Revive.md").write_text(revive_text, encoding="utf-8")
    leftover = write_root / "Save_RUNONCEONLY.md"
    if leftover.is_file():
        leftover.unlink()
    rule_files = install_cursor_rules(
        write_root,
        write_root,
        agent,
        restore_en,
        restore_es,
        rules_src,
    )
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
    for rel in rule_files:
        print("wrote", rel)
    print("wrote _prepared.json")
    print("wrote", f"schema_{prefix}.sql")
    print("password on screen", "yes" if include_pass else "no")
    if create_tables:
        create_empty_tables(write_root, origin, secrets, prefix)
    else:
        print("tables skipped")
    shown = show_save_paste(save_text)
    if not shown:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(save_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
