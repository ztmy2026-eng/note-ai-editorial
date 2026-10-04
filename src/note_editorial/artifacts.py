"""成果物(Agentが書いたMarkdown)の形式検査。

AIが書く部分は自由だが、「出典がある」「問題点が具体的」など最低限の約束は機械で確認する。
これは内容の良し悪しの判定ではなく、手抜きや形式崩れを弾くための検品。
"""
from __future__ import annotations

import re
from pathlib import Path

STEPS = ["research", "ideas", "draft", "critique", "revised", "sns"]
FILES = {
    "research": "01_research.md",
    "ideas": "02_ideas.md",
    "draft": "03_draft.md",
    "critique": "04_critique.md",
    "revised": "05_revised.md",
    "sns": "06_sns.md",
}
PLACEHOLDER = "【要入力"
NO_SOURCE_NOTE = "外部の情報源は使用していません"
SEVERITY = ("【重大】", "【中】", "【軽微】")
IDEA_LABELS = ("タイトル案", "想定読者", "読者の悩み", "切り口", "構成", "CTA", "過去記事との関係")
URL_RE = re.compile(r"https?://\S+")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def section(text: str, heading: str) -> str | None:
    """「## 見出し」から次の「## 」までの本文を返す。見出しが無ければ None。"""
    m = re.search(rf"^##\s*{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def _items(block: str) -> list[str]:
    return [ln for ln in block.splitlines() if re.match(r"\s*(?:[-*]|\d+[.)])\s+\S", ln)]


def idea_blocks(text: str) -> list[str]:
    return re.findall(r"^###\s*候補\s*\d+.*?(?=^###\s*候補|^##\s|\Z)", text, re.M | re.S)


def count_candidates(path: Path) -> int:
    return len(idea_blocks(Path(path).read_text(encoding="utf-8")))


def _research(text: str) -> list[str]:
    errs = []
    facts = section(text, "事実")
    guess = section(text, "推測")
    sources = section(text, "情報源")
    if facts is None:
        errs.append("「## 事実」の章がありません")
    else:
        items = _items(facts)
        if not items:
            errs.append("「## 事実」に項目がありません")
        errs += [f"事実に出典番号[S1]等がありません: {i.strip()[:30]}…" for i in items if not re.search(r"\[S\d+\]", i)]
    if guess is None:
        errs.append("「## 推測・意見」の章がありません(事実と分けて書くこと)")
    if sources is None:
        errs.append("「## 情報源」の章がありません")
    else:
        good = [i for i in _items(sources) if URL_RE.search(i) and DATE_RE.search(i)]
        if len(good) < 3:
            errs.append(f"URLと日付つきの情報源が3件未満です({len(good)}件)")
    return errs


def _ideas(text: str) -> list[str]:
    errs = []
    blocks = idea_blocks(text)
    if len(blocks) < 5:
        errs.append(f"企画候補が5件未満です({len(blocks)}件)")
    for i, b in enumerate(blocks, 1):
        missing = [lb for lb in IDEA_LABELS if lb not in b]
        if missing:
            errs.append(f"候補{i}に項目が足りません: {', '.join(missing)}")
    if not any("【実験枠】" in b for b in blocks):
        errs.append("未検証の新テーマ【実験枠】が1件もありません")
    rec = section(text, "おすすめ")
    if rec is None or not re.search(r"候補\s*\d+", rec):
        errs.append("「## おすすめ」に候補番号の指定がありません")
    ask = section(text, "あなたに聞きたいこと")
    if ask is None or len(_items(ask)) < 3:
        errs.append("「## あなたに聞きたいこと」に3項目以上必要です")
    return errs


def _article_common(text: str) -> list[str]:
    errs = []
    if not re.search(r"^#\s+\S", text, re.M):
        errs.append("記事タイトル(# …)がありません")
    src = section(text, "情報源")
    if src is None:
        errs.append("「## 情報源」の章がありません")
    elif NO_SOURCE_NOTE not in src and not any(URL_RE.search(i) for i in _items(src)):
        errs.append(f"「## 情報源」にURLがありません(外部情報を使っていない場合は「{NO_SOURCE_NOTE}」と明記)")
    return errs


def _draft(text: str) -> list[str]:
    errs = _article_common(text)
    if section(text, "執筆メモ") is None:
        errs.append("「## 執筆メモ」(事実・推測・体験の区別)がありません")
    if len(text) < 1000:
        errs.append("本文が短すぎます(1000文字未満)")
    return errs


def _critique(text: str) -> list[str]:
    errs = []
    problems = section(text, "問題点")
    if problems is None:
        errs.append("「## 問題点」の章がありません")
    else:
        items = [i for i in _items(problems) if any(s in i for s in SEVERITY)]
        if len(items) < 3:
            errs.append(f"重大度つき(【重大】【中】【軽微】)の問題点が3件未満です({len(items)}件)")
    if not re.search(r"スコア[::]\s*\d+\s*/\s*100", text):
        errs.append("「スコア:NN/100」がありません")
    for h in ("有料記事としての可能性", "AIっぽさ"):
        if section(text, h) is None:
            errs.append(f"「## {h}」の章がありません")
    return errs


def _problem_count(critique_text: str) -> int:
    block = section(critique_text, "問題点") or ""
    return len([i for i in _items(block) if any(s in i for s in SEVERITY)])


def _revised(text: str, run_dir: Path | None) -> list[str]:
    errs = _article_common(text)
    log = section(text, "修正履歴")
    if log is None:
        errs.append("「## 修正履歴」がありません")
    elif run_dir is not None:
        crit = Path(run_dir) / FILES["critique"]
        if crit.exists():
            n = _problem_count(crit.read_text(encoding="utf-8"))
            missing = [k for k in range(1, n + 1) if not re.search(rf"問題\s*{k}(?!\d)", log)]
            if missing:
                errs.append("修正履歴で言及されていない批評の問題点: " + ", ".join(f"問題{k}" for k in missing))
    return errs



# 文字数の上限(X=日本語は全角140字まで。Threads=500字。Instagramキャプション=2,200字)
X_LIMIT = 140
THREADS_LIMIT = 500
CAPTION_LIMIT = 2200
LINK_TOKEN = "【記事URL】"


def _post_len(item: str) -> int:
    body = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", item).replace(LINK_TOKEN, "").strip()
    return len(body)


def _sns(text: str, run_dir: Path | None = None) -> list[str]:
    errs = []
    # 記事に未確認(要確認)の情報が残っている間は、その出典に触れる投稿を作らせない
    if run_dir is not None:
        revised = Path(run_dir) / FILES["revised"]
        if revised.exists() and "要確認" in publishable_text(revised.read_text(encoding="utf-8")):
            body = re.split(r"^##\s*確認メモ", text, flags=re.M)[0]
            for word in ("白書", "総務省"):
                if word in body:
                    errs.append(f"記事に「要確認」が残っているのに、投稿案が「{word}」に触れています(確認後に追記する)")
    for heading, minimum, limit in (("X投稿案", 3, X_LIMIT), ("Threads投稿案", 2, THREADS_LIMIT)):
        block = section(text, heading)
        if block is None:
            errs.append(f"「## {heading}」の章がありません")
            continue
        items = _items(block)
        if len(items) < minimum:
            errs.append(f"{heading}は{minimum}件以上必要です({len(items)}件)")
        errs += [f"{heading}の{i}件目が{limit}字を超えています({_post_len(it)}字)" for i, it in enumerate(items, 1) if _post_len(it) > limit]
    if not (section(text, "Instagram投稿案") or "").strip():
        errs.append("「## Instagram投稿案」の章がないか、空です")
    cap = (section(text, "Instagramキャプション") or "").strip()
    if not cap:
        errs.append("「## Instagramキャプション」の章がないか、空です")
    elif len(cap) > CAPTION_LIMIT:
        errs.append(f"Instagramキャプションが{CAPTION_LIMIT}字を超えています({len(cap)}字)")
    if section(text, "確認メモ") is None:
        errs.append("「## 確認メモ」(未確認の数字・体験に依存する投稿の注意)がありません")
    return errs


def validate(step: str, path: Path, run_dir: Path | None = None) -> list[str]:
    """問題のリストを返す。空リストなら合格。"""
    if step not in STEPS:
        return [f"未知のステップです: {step}"]
    path = Path(path)
    if not path.exists():
        return [f"ファイルがありません: {path.name}"]
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return ["ファイルが空です"]
    if step == "research":
        return _research(text)
    if step == "ideas":
        return _ideas(text)
    if step == "draft":
        return _draft(text)
    if step == "critique":
        return _critique(text)
    if step == "sns":
        return _sns(text, run_dir)
    return _revised(text, run_dir)


def drop_section(text: str, heading: str) -> str:
    """「## 見出し」の章を、次の「## 」の手前まで取り除く。"""
    return re.sub(rf"^##\s*{re.escape(heading)}[^\n]*\n.*?(?=^##\s|\Z)", "", text, flags=re.M | re.S)


def publishable_text(text: str) -> str:
    """公開用の本文。編集向けの「修正履歴」の章は取り除く。"""
    return re.sub(r"^##\s*修正履歴[^\n]*\n.*?(?=^##\s|\Z)", "", text, flags=re.M | re.S).rstrip() + "\n"


def count_placeholders(path: Path) -> int:
    """公開本文に残っている【要入力】の数(修正履歴の中の言及は数えない)。"""
    return publishable_text(Path(path).read_text(encoding="utf-8")).count(PLACEHOLDER)


def count_unverified(path: Path) -> int:
    """公開本文に残っている「要確認」(未確認の数字・事実)の数。"""
    return publishable_text(Path(path).read_text(encoding="utf-8")).count("要確認")

