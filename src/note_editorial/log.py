"""実行ログ。1イベント=1行のJSONで logs/events.jsonl に追記する。

「なぜ失敗したか」を後から分析できるように、成功も失敗も残す。
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def log_event(root: Path, event: str, **fields) -> None:
    logs = Path(root) / "logs"
    logs.mkdir(exist_ok=True)
    record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event, **fields}
    with open(logs / "events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
