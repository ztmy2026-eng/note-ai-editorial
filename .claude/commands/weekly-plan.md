---
description: 翌週(月〜日)7本分の週次企画を作る(日曜に実行)。記事本文は書かない。毎朝の daily-run が1本ずつ書く
---
前提: `config/weekly_policy.md` を最初に読む。noteやSNSへ送信する操作は一切しない。ユーザーは不在の想定なので承認待ちで止まらず、
`approved: false`(未承認)のまま企画を保存する。

1. 来週の月曜日を週の開始日(以下 W)とする。`plans/<W>/plan.yaml` が既にあれば、作り直さずに 5 へ進む。
2. 前週分析:`analytics/` と `data/past_articles/`、`python -m note_editorial check-articles` の結果から、今週の各記事のビュー・スキ・フォロー増が分かれば使う。
   数字が無ければ分析は省略し、weekly-plan.md に「7日目に集める数字」のチェックリストを載せる。
3. リサーチ(researcher の指示書に従う):
   - WebSearch で、今週・今月のお金の話題を集める(値上げ、制度改正、税、NISA・iDeCo、保険、住宅ローン金利、転職、季節イベント)。数字は WebFetch で一次情報に近いページを確認する。
   - **noteのページ(タグ・ランキングなど)は自動で読まない。** noteの規約で自動収集が認められているかを、まだ確認できていないため
     (確認できて、人が許可したら、この手順を戻す)。代わりに、人が集めた `data/market/items.csv` と、それを分析した `analytics/market_insights.md` を読む
     (`python -m note_editorial analyze-market` で更新できる)。
   - 市場データの記事数が30件未満なら、傾向として扱わない。使うなら「実験枠の仮説」にとどめ、企画の根拠にはしない。
   - 話題になっているが、noteでは手薄な切り口を探す。
   - 結果を `plans/<W>/research.md` に保存する(事実には出典URLと取得日を付ける)。
4. 企画(planner の役割):7本を作り、次の2つのファイルに書く。
   - `plans/<W>/plan.yaml`(機械で検査される。形式は下記)
   - `plans/<W>/weekly-plan.md`:冒頭に「未承認」と明記する。中身は、企画表(投稿日/タイトル/狙い/失敗パターン/入れる図)、
     リサーチの要約、7日目(日曜)に集める数字(各記事のビュー・スキ・フォロー増)のチェックリスト。
5. `python -m note_editorial check-plan --week <W>` を実行し、不合格なら直す(最大2回)。それでも駄目なら止めて理由を報告する。
6. 報告:来週のテーマ7本(日付・タイトル)と、ユーザーがやること(weekly-plan.md を読んで承認する場合は plan.yaml の `approved: true`。
   修正したい企画は plan.yaml を直す)を短く書く。

## plan.yaml の形式

```yaml
week_start: 2026-10-05        # W(月曜)
approved: false               # ユーザーが承認したら true
items:                        # 7本。date は W〜W+6 を1日1本
  - date: 2026-10-05
    theme: saving-insurance   # config/themes.yaml の有効な id
    ai: false                 # AIに関する記事なら true(週に1本以上)
    title: "コンビニ通いを見直す5つのコツ"   # 30字以内(超えると check-plan が不合格にする)
    alt_titles: ["予備案1", "予備案2"]
    aim: "狙い(なぜ今この読者に)"
    failures: ["失敗パターン1", "失敗パターン2", "失敗パターン3"]
    figures: ["見出し画像", "fig1: 棒グラフ…", "fig2: タイムライン…", "fig3: チェックリスト…"]
    affiliate: "保険見直し相談系"   # 入れない場合は空文字
    read_minutes: 5               # 任意。タイトルに「5分で読める」「3分でわかる」と書くときだけ必須(本文を 分数×500字 以内にする)。1週間に3本まで
    notes: ["確認済みの数字と出典URLなど、書くときに使うメモ"]   # 任意
    draft: drafts/2026-10-05_xxx.md                        # 任意。週次で下書きまで作った場合だけ
```
