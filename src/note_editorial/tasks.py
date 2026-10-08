"""スマホのダッシュボード用に、「いま人がやること」を書き出す(AIは使わない)。

投稿前の実行(承認待ち・空欄あり・投稿待ち)ごとに、次の一手・埋める空欄・noteに貼る文・SNS案を1件にまとめる。
内容の判断は chief.next_action に任せ、ここでは集めて整えるだけ。書き換えはしない。
"""
from __future__ import annotations

import base64
import json
import re
from datetime import date
from pathlib import Path

from . import artifacts, chief, export, images, limits, runs

BLANK_RE = re.compile(r"【要入力[::]?([^】]*)】")


def _split_posts(block: str | None) -> list[str]:
    """「- 」で始まる行ごとに投稿案を分ける(Threadsのように複数行の投稿案は、次の「- 」まで1件)。"""
    if not block:
        return []
    posts, cur = [], None
    for line in block.splitlines():
        if re.match(r"^-\s+", line):
            if cur is not None:
                posts.append(cur)
            cur = re.sub(r"^-\s+", "", line)
        elif cur is not None:
            cur += "\n" + line
    if cur is not None:
        posts.append(cur)
    return ["\n".join(ln.strip() for ln in p.splitlines()).strip() for p in posts if p.strip()]


def _note_text(rdir: Path, data: dict, public: str) -> tuple[str, str, bool]:
    """(タイトル, 本文, noteに貼ってよい状態か)。承認2の後は READY_TO_PUBLISH.md、前は05_revised.md の公開本文。"""
    ready = rdir / runs.READY_FILE
    approved = bool(data["approvals"].get("publish")) and ready.exists()
    source = ready.read_text(encoding="utf-8") if approved else public
    try:
        title, body = export.split_note(source)
    except runs.RunError:
        return str((data.get("plan") or {}).get("title") or ""), "", False
    return title, body, approved


def export_tasks(root: Path, today: date | None = None) -> dict:
    root = Path(root)
    use = limits.usage(root, today)
    items = []
    for path in sorted((root / "runs").glob("*/run.json")):
        rid = path.parent.name
        data = runs.read_run(root, rid)
        if data.get("posted") or data.get("skipped"):
            continue
        action, human = chief.next_action(root, rid)
        rdir = runs.run_path(root, rid)
        revised = rdir / artifacts.FILES["revised"]
        public = artifacts.publishable_text(revised.read_text(encoding="utf-8")) if revised.exists() else ""
        blanks = [b.strip() for b in BLANK_RE.findall(public)]
        if "revised" in data["steps_done"] and not data["approvals"].get("publish") and not blanks and not human:
            # 承認なしモードなら次の自動実行で通る段階。ただし、人が止めている(承認2は私が確認してから、など)間は、人の確認待ちとして出す
            human = True
            action = "公開前の確認待ち(承認2)。本文を読んで、よければ「承認2してよい」と返信してください"
        title, body, ready = _note_text(rdir, data, public)
        if ready and not data.get("posted"):
            # 公開承認(承認2)が済んだら、あとは人がnoteに貼って投稿する段階(SNS案の承認は、投稿には要らない)
            human = True
            action = "noteに貼り付けて投稿してください。投稿したら、記事のURLを入れて「投稿したと記録」します"
        sns_path = rdir / "06_sns_ready.md"
        if not sns_path.exists():
            sns_path = rdir / artifacts.FILES["sns"]
        sns_text = sns_path.read_text(encoding="utf-8") if sns_path.exists() else ""
        items.append({
            "id": rid,
            "title": title,
            "theme": data.get("theme_name", ""),
            "status": data.get("status", ""),
            "steps_done": [s for s in artifacts.STEPS if s in data["steps_done"]],
            "next_action": action,
            "needs_human": human,
            "blanks": blanks,
            "unverified": public.count("要確認"),
            "note_ready": ready,
            "note_body": body,
            "x_posts": _split_posts(artifacts.section(sns_text, "X投稿案")),
            "threads_posts": _split_posts(artifacts.section(sns_text, "Threads投稿案")),
            "has_images": (rdir / "images").is_dir(),
        })
    return {"limits": {"runs": list(use["runs"]), "steps": list(use["steps"]), "queue": list(use["queue"])}, "tasks": items}


def export_image_docs(root: Path, run_id: str) -> list[dict]:
    """ダッシュボードの「画像」に載せる、画像の書類(1枚=1書類)。スマホで、そのままコピー・保存できるようにするため。

    note用(本文の【画像:…】の並び順)→ 文字だけの見出し画像 → Instagram の順。画像は base64 で書類に入れる(小さい画像だけ)。
    """
    rdir = runs.run_path(Path(root), run_id)
    imgdir = rdir / "images"
    if not imgdir.is_dir():
        return []
    revised = rdir / artifacts.FILES["revised"]
    text = artifacts.publishable_text(revised.read_text(encoding="utf-8")) if revised.exists() else ""
    titles = {}
    spec = rdir / "figures.json"
    if spec.exists():
        try:
            titles = {s.get("name"): s.get("title", "") for s in json.loads(spec.read_text(encoding="utf-8"))}
        except (json.JSONDecodeError, AttributeError):
            titles = {}
    docs, used = [], set()

    def add(path: Path, label: str, group: str, order: int) -> None:
        w, h = images.png_size(path)
        docs.append({"id": f"{run_id}__{path.stem}", "run_id": run_id, "file": path.name, "label": label, "group": group,
                     "order": order, "mime": "image/png", "width": w, "height": h, "bytes": path.stat().st_size,
                     "data": base64.b64encode(path.read_bytes()).decode("ascii")})
        used.add(path)

    fig_no = 0
    for i, name in enumerate(re.findall(r"【画像:([^】]+)】", text)):
        # 記事の中の名前に日付が付いていて、ファイル名には無い(その逆も)ことがあるので、日付を外した名前でも探す
        short = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", name)
        path = next((p for nm in (name, short) for p in (imgdir / "figures" / nm, imgdir / nm) if p.exists()), None)
        if path is None or path in used:
            continue
        if "cover" in name:
            label = "見出し画像"
        else:
            fig_no += 1
            title = titles.get(path.stem, "")
            label = f"図{fig_no}" + (f"：{title}" if title else "")
        add(path, label, "note", i)
    eye = imgdir / "note_eyecatch.png"
    if eye.exists() and eye not in used:
        add(eye, "見出し画像(文字だけの簡易版)", "other", 0)
    slides = sorted(imgdir.glob("instagram_*.png"))
    for n, path in enumerate(slides, 1):
        add(path, f"Instagram {n}/{len(slides)}", "instagram", n)
    return docs
