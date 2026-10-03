"""承認なしモード(config/limits.yaml の auto_approve: true のときだけ使える)。

承認1〜3を人間の代わりに自動で通す。ただし:
- 機械の検品(【要入力】「要確認」が残っていないか等)は、人間の承認と全く同じ条件で効く。引っかかれば止まる。
- 記録には by: "auto" が残る(人間の承認と区別できる)。
- noteやSNSへの投稿は、モードに関係なく常に人間が手動で行う(このシステムに送信機能は無い)。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import artifacts, limits, runs


def recommended_candidate(ideas_text: str) -> int | None:
    rec = artifacts.section(ideas_text, "おすすめ") or ""
    m = re.search(r"候補\s*(\d+)", rec)
    return int(m.group(1)) if m else None


def auto_approve(root: Path, run_id: str) -> list[str]:
    root = Path(root)
    if not limits.load(root)["auto_approve"]:
        raise runs.RunError("承認なしモードは無効です(config/limits.yaml の auto_approve: true で有効化)")
    done: list[str] = []
    data = runs.read_run(root, run_id)
    ap, steps = data["approvals"], data["steps_done"]
    rdir = runs.run_path(root, run_id)
    try:
        if "ideas" in steps and not ap["idea"]:
            n = recommended_candidate((rdir / artifacts.FILES["ideas"]).read_text(encoding="utf-8"))
            if n is None:
                raise runs.RunError("「おすすめ」の候補番号が読み取れないため、企画を自動採用できません")
            runs.approve_idea(root, run_id, n, by="auto")
            done.append(f"【承認1】おすすめの候補{n}を自動採用")
        if "revised" in steps and not ap["publish"]:
            runs.approve_publish(root, run_id, by="auto")
            done.append("【承認2】公開準備(READY_TO_PUBLISH.md)を自動で作成")
        data = runs.read_run(root, run_id)
        if "sns" in data["steps_done"] and data["approvals"]["publish"] and not data["approvals"].get("sns"):
            runs.approve_sns(root, run_id, by="auto")
            done.append("【承認3】SNS案を自動承認")
    except runs.RunError as e:
        done.append(f"停止: {e}")
    return done
