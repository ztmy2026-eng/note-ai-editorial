"""noteに貼る用の出力。公開承認(承認2)の後でないと作れない。

noteにはタイトル欄と本文欄が別なので、タイトルと本文を分けて保存する。
内容の書き換えはしない(読者に不要な「外部の情報源は使用していません」の行だけ外す)。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import artifacts, runs
from .log import log_event


def drop_section(text: str, heading: str) -> str:
    return re.sub(rf"^##\s*{re.escape(heading)}[^\n]*\n.*?(?=^##\s|\Z)", "", text, flags=re.M | re.S)


def split_note(ready_text: str) -> tuple[str, str]:
    m = re.match(r"\s*#\s+(.+?)\s*\n(.*)\Z", ready_text, re.S)
    if not m:
        raise runs.RunError("記事タイトル(# …)が見つかりません")
    title, body = m.group(1), m.group(2)
    src = artifacts.section(body, "情報源")
    if src is not None and artifacts.NO_SOURCE_NOTE in src and not artifacts.URL_RE.search(src):
        body = drop_section(body, "情報源")
    return title, body.strip() + "\n"


def export_note(root: Path, run_id: str) -> Path:
    root = Path(root)
    data = runs.read_run(root, run_id)
    if not data["approvals"].get("publish"):
        raise runs.RunError("【承認2】の後に作れます(先に approve-publish)")
    rdir = runs.run_path(root, run_id)
    title, body = split_note((rdir / runs.READY_FILE).read_text(encoding="utf-8"))
    out = rdir / "note_post"
    out.mkdir(exist_ok=True)
    (out / "title.txt").write_text(title + "\n", encoding="utf-8")
    (out / "body.md").write_text(body, encoding="utf-8")
    log_event(root, "note_exported", run_id=run_id)
    return out
