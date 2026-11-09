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


def tables_to_lists(text: str) -> str:
    """Markdownの表(| … |)を、箇条書きに直す(2026-11-09 持ち主の指示:noteに貼ると列がぐちゃぐちゃになるため、本文に表は置かない)。
    表のデータ行ごとに「・1列目:見出し 値、見出し 値…」にする。表は、図(画像)にして載せる。"""
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rest = "、".join(f"{head[k] if k < len(head) else ''} {c}".strip() for k, c in enumerate(cells) if k > 0 and c)
                first = cells[0]
                if head and head[0] and re.fullmatch(r"\d{1,2}", first):  # 「1」「2」だけの行名は、「例1」のように見出しを付ける
                    first = f"{head[0]}{first}"
                out.append(f"・{first}:{rest}" if rest else f"・{first}")
                i += 1
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def split_note(ready_text: str) -> tuple[str, str]:
    m = re.match(r"\s*#\s+(.+?)\s*\n(.*)\Z", ready_text, re.S)
    if not m:
        raise runs.RunError("記事タイトル(# …)が見つかりません")
    title, body = m.group(1), m.group(2)
    src = artifacts.section(body, "情報源")
    if src is not None and artifacts.NO_SOURCE_NOTE in src and not artifacts.URL_RE.search(src):
        body = drop_section(body, "情報源")
    if artifacts.section(body, "図の指示") is not None:  # 編集向けの章(図の指示)は、noteに貼る文に入れない
        body = drop_section(body, "図の指示")
    body = tables_to_lists(body)
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


def clean_url(url: str) -> str:
    """共有用のおまけ(?sub_rt=… など)を外した、記事の素のURL。"""
    url = url.strip()
    if not re.match(r"https?://", url):
        raise runs.RunError("URL は https:// で始まる形で指定してください")
    return url.split("?", 1)[0].split("#", 1)[0]


def fill_article_url(root: Path, run_id: str, url: str) -> Path | None:
    """承認済みのSNS案(06_sns.md)の【記事URL】を実際のURLに置き換えて、06_sns_ready.md に保存する。元のファイルは変えない。"""
    rdir = runs.run_path(Path(root), run_id)
    src = rdir / artifacts.FILES["sns"]
    if not src.exists():
        return None
    out = rdir / "06_sns_ready.md"
    out.write_text(src.read_text(encoding="utf-8").replace(artifacts.LINK_TOKEN, clean_url(url)), encoding="utf-8")
    log_event(Path(root), "sns_url_filled", run_id=run_id)
    return out
