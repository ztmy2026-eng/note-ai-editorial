import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

RESEARCH = """# リサーチ
## 事実(出典つき)
- 例の事実A [S1]
- 例の事実B [S2]
## 推測・意見
- これはAIの推測です
## 情報源
- [S1] 例1 | https://example.com/1 | 公開日:2026-01-01 | 取得日:2026-10-03
- [S2] 例2 | https://example.com/2 | 公開日:2026-01-02 | 取得日:2026-10-03
- [S3] 例3 | https://example.com/3 | 公開日:2026-01-03 | 取得日:2026-10-03
"""


def idea(n, exp=False):
    tag = "【実験枠】" if exp else ""
    return f"""### 候補{n}:{tag}案{n}
- **タイトル案**: t
- **想定読者**: r
- **読者の悩み**: p
- **切り口**: a
- **構成**: s
- **CTA**: c
- **過去記事との関係**: x
"""


IDEAS = "# 企画\n" + "".join(idea(i, i == 5) for i in range(1, 6)) + """
## おすすめ
候補1 理由
## あなたに聞きたいこと
- Q1
- Q2
- Q3
"""

DRAFT = "# 記事タイトル\n" + "本文です。" * 300 + """
## 情報源
- https://example.com/1
## 執筆メモ
- 事実は[S1]
"""

CRITIQUE = """# 批評
## 問題点
1. 【重大】根拠が弱い
2. 【中】導入が長い
3. 【軽微】表記ゆれ
## AIっぽさ
あり
## 有料記事としての可能性
低い
## 総合評価
スコア:55/100
"""

REVISED = DRAFT + """
## 修正履歴
- 問題1: 根拠を追加
- 問題2: 導入を短縮
- 問題3: 表記統一
"""


@pytest.fixture
def root(tmp_path):
    """本物の config を使う、空の作業フォルダ。"""
    shutil.copytree(REPO / "config", tmp_path / "config")
    return tmp_path


def write(root, run_id, name, text):
    (root / "runs" / run_id / name).write_text(text, encoding="utf-8")


SNS = """# SNS投稿案
## X投稿案
- 議事録はAIに任せても、日付と担当は元メモと照合しています 【記事URL】
- メールの下書きもAIで作れます。入れてよい情報かだけ先に確認を
- チェック表を記事で配っています 【記事URL】
## Threads投稿案
- Threads用の投稿その1です。
- Threads用の投稿その2です。
## Instagram投稿案
1枚目: タイトル / 2枚目: チェック表
## Instagramキャプション
キャプション本文です。
## 確認メモ
- 数字は使っていません
"""
