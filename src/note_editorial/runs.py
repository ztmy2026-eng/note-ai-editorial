"""1回の実行(run)の管理。

runs/日付_連番/ に成果物と run.json(状態・承認)を置く。
- 順番を飛ばせない(リサーチ→企画→[承認1]→執筆→批評→修正→[承認2])
- 承認は人間がコマンドを実行したときだけ記録される
- このシステムはnote・SNSへ送信する機能を持たない。承認2後も「ファイルが準備される」だけ。
"""
from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from . import artifacts, limits
from .log import log_event

STATUS_BY_STEP = {
    "research": "research_done",
    "ideas": "ideas_done",
    "draft": "draft_done",
    "critique": "critique_done",
    "revised": "revised_done",
    "sns": "sns_done",
}
READY_FILE = "READY_TO_PUBLISH.md"


class RunError(Exception):
    """利用者に分かりやすく伝えたいエラー。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise RunError(f"設定ファイルを読めません({path.name}): {e}") from e


def load_themes(root: Path) -> list[dict]:
    return _read_yaml(Path(root) / "config" / "themes.yaml").get("themes", [])


def run_path(root: Path, run_id: str) -> Path:
    p = Path(root) / "runs" / run_id
    if not (p / "run.json").exists():
        raise RunError(f"実行が見つかりません: {run_id}")
    return p


def read_run(root: Path, run_id: str) -> dict:
    p = run_path(root, run_id)
    try:
        return json.loads((p / "run.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RunError(f"run.json が壊れています: {e}") from e


def _save(root: Path, run_id: str, data: dict) -> None:
    (Path(root) / "runs" / run_id / "run.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_run(root: Path, theme_id: str, today: date | None = None) -> str:
    root = Path(root)
    theme = next((t for t in load_themes(root) if t.get("id") == theme_id), None)
    if theme is None:
        raise RunError(f"テーマ '{theme_id}' は config/themes.yaml にありません")
    if not theme.get("active", True):
        raise RunError(f"テーマ '{theme_id}' は無効(active: false)です")
    cfg = _read_yaml(root / "config" / "limits.yaml")
    today = today or limits.today_local(root)
    runs_dir = root / "runs"
    runs_dir.mkdir(exist_ok=True)
    existing = [p for p in runs_dir.glob(f"{today.isoformat()}_*") if p.is_dir()]
    cap = int(cfg.get("max_runs_per_day", 3))
    if len(existing) >= cap:
        log_event(root, "run_blocked_by_limit", cap=cap)
        raise RunError(f"本日の実行上限({cap}回)に達しました。config/limits.yaml で変更できます")
    for reason in limits.reached(root, today):
        if "実行数" not in reason:  # 実行数は上のメッセージで案内済み
            log_event(root, "run_blocked_by_limit", reason=reason)
            raise RunError(f"{reason}。新しい実行は作りません(config/limits.yaml で変更、または投稿後に mark-posted)")
    run_id = f"{today.isoformat()}_{len(existing) + 1:03d}"
    (runs_dir / run_id).mkdir()
    data = {
        "run_id": run_id,
        "theme": theme_id,
        "theme_name": theme.get("name", theme_id),
        "created": _now(),
        "status": "created",
        "steps_done": [],
        "approvals": {"idea": None, "publish": None, "sns": None},
        "posted": None,
    }
    _save(root, run_id, data)
    log_event(root, "run_created", run_id=run_id, theme=theme_id)
    return run_id


def complete_step(root: Path, run_id: str, step: str) -> list[str]:
    """成果物を検査し、合格なら記録する。不合格なら問題リストを返す(記録しない)。"""
    root = Path(root)
    if step not in artifacts.STEPS:
        raise RunError(f"未知のステップです: {step}")
    data = read_run(root, run_id)
    done = data["steps_done"]
    idx = artifacts.STEPS.index(step)
    if step in done:
        raise RunError(f"'{step}' は完了済みです")
    if idx > 0 and artifacts.STEPS[idx - 1] not in done:
        raise RunError(f"先に '{artifacts.STEPS[idx - 1]}' を完了してください")
    if step == "draft" and not data["approvals"]["idea"]:
        raise RunError("【承認1】企画が未承認です。approve-idea で企画を採用してから執筆してください")
    rdir = run_path(root, run_id)
    problems = artifacts.validate(step, rdir / artifacts.FILES[step], rdir)
    if problems:
        log_event(root, "step_rejected", run_id=run_id, step=step, problems=problems)
        return problems
    done.append(step)
    if not (step == "sns" and data["approvals"]["publish"]):  # 公開承認済みの状態表示を上書きしない
        data["status"] = STATUS_BY_STEP[step]
    _save(root, run_id, data)
    log_event(root, "step_done", run_id=run_id, step=step)
    return []


def approve_idea(root: Path, run_id: str, number: int, by: str = "human") -> None:
    """【承認1】企画を採用する。人間が実行する操作。"""
    root = Path(root)
    data = read_run(root, run_id)
    if "ideas" not in data["steps_done"]:
        raise RunError("企画がまだ完了していません")
    if data["approvals"]["idea"]:
        raise RunError("企画はすでに承認済みです")
    total = artifacts.count_candidates(run_path(root, run_id) / artifacts.FILES["ideas"])
    if not 1 <= number <= total:
        raise RunError(f"候補番号は 1〜{total} で指定してください")
    data["approvals"]["idea"] = {"candidate": number, "at": _now(), "by": by}
    data["status"] = "idea_approved"
    _save(root, run_id, data)
    log_event(root, "idea_approved", run_id=run_id, candidate=number, by=by)


def approve_publish(root: Path, run_id: str, by: str = "human") -> Path:
    """【承認2】公開してよいと承認する。人間が実行する操作。

    【要入力】の空欄や「要確認」(未確認の情報)が残っていると承認できない。
    ここでは何も送信せず、修正履歴を除いた READY_TO_PUBLISH.md を作るだけ。
    """
    root = Path(root)
    data = read_run(root, run_id)
    if "revised" not in data["steps_done"]:
        raise RunError("修正版がまだ完了していません")
    rdir = run_path(root, run_id)
    revised = rdir / artifacts.FILES["revised"]
    left = artifacts.count_placeholders(revised)
    if left:
        raise RunError(f"{artifacts.FILES['revised']} に 【要入力】 が {left} 箇所残っています。あなたの体験・数字を入れてから承認してください")
    unverified = artifacts.count_unverified(revised)
    if unverified:
        raise RunError(f"{artifacts.FILES['revised']} に「要確認」が {unverified} 箇所残っています。一次情報で確認してから、確認済みの表記に直す(または削る)ことが必要です")
    ready = rdir / READY_FILE
    ready.write_text(artifacts.publishable_text(revised.read_text(encoding="utf-8")), encoding="utf-8")
    data["approvals"]["publish"] = {"at": _now(), "by": by}
    data["status"] = "publish_approved"
    _save(root, run_id, data)
    log_event(root, "publish_approved", run_id=run_id, by=by)
    return ready


def reopen(root: Path, run_id: str, step: str) -> Path:
    """指定ステップ以降をやり直す(第2ラウンド)。

    古い成果物は消さず runs/<id>/history/round_N/ に退避する。企画の承認(承認1)は保持。
    公開承認(承認2)は、記事が変わるので取り消される。
    """
    root = Path(root)
    if step not in ("draft", "critique", "revised", "sns"):
        raise RunError("やり直せるのは draft / critique / revised / sns からです")
    data = read_run(root, run_id)
    if step not in data["steps_done"]:
        raise RunError(f"'{step}' はまだ完了していないため、やり直す対象がありません")
    rdir = run_path(root, run_id)
    n = data.get("rounds", 1)
    dest = rdir / "history" / f"round_{n}"
    dest.mkdir(parents=True, exist_ok=True)
    idx = artifacts.STEPS.index(step)
    for s in artifacts.STEPS[idx:]:
        f = rdir / artifacts.FILES[s]
        if f.exists():
            shutil.move(str(f), dest / f.name)
    ready = rdir / READY_FILE
    if step != "sns" and ready.exists():  # 記事が変わるなら公開承認は取り消す
        shutil.move(str(ready), dest / ready.name)
    data["steps_done"] = artifacts.STEPS[:idx]
    if step != "sns":
        data["approvals"]["publish"] = None
    data["approvals"]["sns"] = None
    data["rounds"] = n + 1
    if step == "sns" and data["approvals"]["publish"]:
        data["status"] = "publish_approved"
    else:
        data["status"] = STATUS_BY_STEP[artifacts.STEPS[idx - 1]] if data["steps_done"][-1] != "ideas" else "idea_approved"
    _save(root, run_id, data)
    log_event(root, "run_reopened", run_id=run_id, from_step=step, archived_to=str(dest.relative_to(root)))
    return dest


def approve_sns(root: Path, run_id: str, by: str = "human") -> None:
    """【承認3】SNS投稿案の内容を確認して承認する。人間が実行する操作。

    記事の公開承認が済んでいて、SNS案に【要入力】「要確認」が残っていないことが条件。
    ここでも何も送信しない(投稿はあなたが手動で行う)。
    """
    root = Path(root)
    data = read_run(root, run_id)
    if "sns" not in data["steps_done"]:
        raise RunError("SNS投稿案がまだ完了していません")
    if not data["approvals"].get("publish"):
        raise RunError("先に【承認2】記事の公開承認が必要です(SNSは公開された記事を前提にするため)")
    sns = run_path(root, run_id) / artifacts.FILES["sns"]
    text = sns.read_text(encoding="utf-8")
    for token in (artifacts.PLACEHOLDER, "要確認"):
        n = text.count(token)
        if n:
            raise RunError(f"{artifacts.FILES['sns']} に「{token}」が {n} 箇所残っています")
    data["approvals"]["sns"] = {"at": _now(), "by": by}
    data["status"] = "sns_approved"
    _save(root, run_id, data)
    log_event(root, "sns_approved", run_id=run_id, by=by)


def mark_posted(root: Path, run_id: str, url: str = "") -> None:
    """あなたがnoteに投稿したことを記録する(人間の操作)。記録すると「未投稿の在庫」から外れ、次の記事を作れるようになる。"""
    root = Path(root)
    data = read_run(root, run_id)
    if not data["approvals"].get("publish"):
        raise RunError("公開承認(承認2)が済んでいない実行は、投稿済みにできません")
    data["posted"] = {"at": _now(), "url": url}
    _save(root, run_id, data)
    log_event(root, "marked_posted", run_id=run_id, url=url)
