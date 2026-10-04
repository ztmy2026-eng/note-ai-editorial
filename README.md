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
- 画像は**AI画像生成を使わず**、文字入りカードをブラウザ(Chrome/Edge)で画像化します(費用なし・著作権の心配が少ない)。色や名前は `config/images.yaml` で変更できます。
- 成果物は `runs/<日付_連番>/` に1ファイルずつ保存されます(`01_research.md` … `05_revised.md`、`run.json`)。

## 使い方

```bash
pip install -e ".[dev]"                    # 初回だけ
python -m note_editorial themes            # テーマ一覧
python -m note_editorial check-articles    # 過去記事の読み込み確認
python -m note_editorial new-run --theme ai-work
```

Claude Code では `/editorial-run ai-work`(手動承認で1ステップずつ)か、`/daily-run`(承認なしモードで上限まで自動)を使います。
自動実行の場所(クラウド / PC)の比較は `docs/automation_options.md` を見てください。

承認は人間が実行するコマンドだけです。

```bash
python -m note_editorial approve-idea <実行ID> <候補番号>   # 承認1
python -m note_editorial approve-publish <実行ID>          # 承認2(【要入力】が残っていると拒否される)
python -m note_editorial approve-sns <実行ID>              # 承認3(承認2の後。「要確認」「要入力」が残ると拒否)
python -m note_editorial export-note <実行ID>               # note貼り付け用(タイトル欄・本文欄に分けて出力。承認2の後)
python -m note_editorial make-images <実行ID>              # note見出し画像・Instagram画像を自動作成
python -m note_editorial check-limits                      # 1日の上限の使用状況(上限なら終了コード1)
python -m note_editorial auto-approve <実行ID>             # 承認なしモード(config/limits.yaml の auto_approve: true のとき)
python -m note_editorial mark-posted <実行ID> --url <URL>  # noteに投稿したことを記録(次の記事を作れるようになる)
python -m note_editorial next-theme                        # 次に作るテーマを選ぶ
python -m note_editorial status                            # 状態確認
python -m note_editorial reopen <実行ID> draft             # 体験を足して第2ラウンド(古い版は history/ に退避)
python -m note_editorial analyze                           # 過去記事の集計 → analytics/facts.md
python -m note_editorial validate-hypotheses               # 仮説台帳の形式検査
python -m note_editorial briefing                          # 編集長の朝のブリーフィング → briefing/
python -m pytest                                           # テスト
```

## ダッシュボード(インプ・PV・スキを見る/直す)

https://claude.ai/artifact/R7dbtDrFCm9tiYRUCR8T1r (ソース: `dashboard/index.html`)
数字はその場で書き換えられ、共有データに保存されます。`/sync-metrics` で、システムの記録(`data/past_articles/`)と相互に反映します。
手入力の数字は、メールからの自動収集より優先されます。

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

## 週次企画(日曜に翌週7本分を企画 → 毎朝1本ずつ仕上げる)

以前は Cowork の週次タスク(日曜に7本書く)と、この daily-run(毎朝1本)が別々に動いていました。今はここに一本化しています。

- **日曜**:daily-run の最後に `.claude/commands/weekly-plan.md` を実行し、`plans/<翌週の月曜>/` に企画(plan.yaml)・リサーチ・weekly-plan.md を作る(未承認のまま)。
- **毎朝**:`today-plan` で今日の企画があれば `new-run --plan` で実行を作り、その企画で1本仕上げる。無ければ従来どおり `next-theme`。
- 書き方・画像の仕様は `config/weekly_policy.md`(editorial_rules.md より優先)。体験の欄は【要記入】で残し、投稿前にあなたが埋める。
- 図は `runs/<ID>/figures.json` を書いて `make-figures <ID>`(Playwright が必要。無ければ `pip install playwright`)。

| コマンド | 何をするか |
|---|---|
| `today-plan` | 今日の週次企画を表示(無ければ終了コード1) |
| `new-run --plan` | 今日の週次企画で実行を作る(00_plan.md・下書き・週次の画像をコピー) |
| `check-plan --week YYYY-MM-DD` | 週次企画の形式検査 |
| `make-figures <ID>` | 本文の図・見出し画像を作る |

承認するときは `plans/<週>/plan.yaml` の `approved: true` にする(未承認でも自動モードでは進みます。ブリーフィングに状態が出ます)。
