# note AI編集部

note副業のための、複数のAIエージェントが役割分担して記事を作る仕組みです。
**AIは「下書きと批評」まで。公開・投稿は必ず人間が行います**(このシステムにはnoteやSNSへ送信する機能がありません)。

## 今できること

```
リサーチ → 企画 →【承認1:企画を採用】→ 執筆 → 批評 → 修正 →【承認2:公開してよいか】→ SNS案 →【承認3:SNS内容の確認】
```

分析は別ライン:`過去記事 →(Python集計)→ 分析Agentの仮説台帳 → 次の企画へフィードバック`
編集長(進行管理)はAIではなくプログラムで、毎朝の `briefing` を作ります。

| 担当 | 場所 | 役割 |
|---|---|---|
| Researcher / Planner / Writer / Critic / Editor / SNS / Analyst | `.claude/agents/*.md` | 考える・書く(Claude Codeのサブエージェント) |
| 編集長(`chief.py`) | `src/note_editorial/` | 次の一手・承認待ち・上限・品質シグナル(**AIは使わない**) |
| 検品・承認・ログ・集計 | `src/note_editorial/` | 形式検査、順番と承認の管理、数値計算(**AIは使わない**) |

- APIキーは**不要**です(Claude Code上で動かします)。
- 成果物は `runs/<日付_連番>/` に1ファイルずつ保存されます(`01_research.md` … `05_revised.md`、`run.json`)。

## 使い方

```bash
pip install -e ".[dev]"                    # 初回だけ
python -m note_editorial themes            # テーマ一覧
python -m note_editorial check-articles    # 過去記事の読み込み確認
python -m note_editorial new-run --theme ai-work
```

Claude Code では `/editorial-run ai-work` で、リサーチ→企画(承認1の手前)まで進みます。

承認は人間が実行するコマンドだけです。

```bash
python -m note_editorial approve-idea <実行ID> <候補番号>   # 承認1
python -m note_editorial approve-publish <実行ID>          # 承認2(【要入力】が残っていると拒否される)
python -m note_editorial approve-sns <実行ID>              # 承認3(承認2の後。「要確認」「要入力」が残ると拒否)
python -m note_editorial status                            # 状態確認
python -m note_editorial reopen <実行ID> draft             # 体験を足して第2ラウンド(古い版は history/ に退避)
python -m note_editorial analyze                           # 過去記事の集計 → analytics/facts.md
python -m note_editorial validate-hypotheses               # 仮説台帳の形式検査
python -m note_editorial briefing                          # 編集長の朝のブリーフィング → briefing/
python -m pytest                                           # テスト
```

## 過去記事の取り込み

`data/past_articles/` に、1記事=1つの `.md` ファイルで置きます。先頭の情報は空でも構いません(空は「データなし」扱い)。

```markdown
---
title: "記事タイトル"
url: "https://note.com/..."
published: 2026-01-10
theme: ai-work            # config/themes.yaml の id
pv: 1840                  # 分からなければ空欄でOK
likes: 96
revenue: 0
followers_gained: 12
cta: "フォロー誘導"
---
本文をここに貼る
```

`data/past_articles/` が空の間は、架空の `data/samples/` を使います。

> ⚠ Gitに載せたデータはGitHub上に保存されます。**リポジトリを非公開(Private)にしてください。**

## テーマの変更

`config/themes.yaml` を編集します(追加・並べ替え・`active: false` で無効化)。
1日の実行回数などの上限は `config/limits.yaml` です。

## ルール(`config/editorial_rules.md`)

事実・推測・体験を区別する / 体験を創作しない(空欄にする) / 出典を残す / 著作権・個人情報に注意 / 投資は断定しない / 外部へ送信しない。

## ロードマップ

1. ✅ 段階1:5 Agentで1回通しの実行
2. ✅ SNS Agent / Analytics / 編集長(進行管理)
3. 半自動 → 定期実行 → クラウド常時稼働(APIキーが必要になる段階で、費用と代替案を提示してから進める)

## 開発メモ

- 秘密情報(APIキー等)は `.env` に置き、コードに書かない(`.gitignore` 済み)。
- ログは `logs/events.jsonl`(成功・失敗・上限到達を記録)。
