---
description: 1日分の編集部の仕事(記事1本分)を、承認なしモードで上限まで進める。投稿は人間が手動
---
前提: `config/limits.yaml` の `auto_approve: true`。noteやSNSへ送信する操作は一切しない。
**新しい実行を作る前**は `python -m note_editorial check-limits --new-run`、**Agentを呼ぶ前**は毎回 `python -m note_editorial check-limits`
(作業中の実行の続きの確認。実行数は見ない)を実行し、終了コードが1(上限到達)なら、新しい作業を始めずに手順9へ進む。

1. `python -m note_editorial check-limits --new-run` (上限なら 9 へ)
2. `python -m note_editorial today-plan` で今日の週次企画を確認する。
   - あれば `new-run --plan` で実行を作る(00_plan.md・下書き・週次の画像が実行フォルダに入る)。以降の全Agentは 00_plan.md と `config/weekly_policy.md` に従う。
   - 無ければ従来どおり `next-theme` でテーマを決め、`new-run --theme <id>` で実行を作る。
   - 失敗したら理由を記録して 9 へ
3. check-limits → researcher → `complete <ID> research`
4. check-limits → planner → `complete <ID> ideas` → `auto-approve <ID>`
5. check-limits → writer → `complete <ID> draft`(config/editorial_rules.md の「自動モード」に従い、空欄を残さない。週次企画の実行では体験の欄だけ【要記入】で残す)
6. check-limits → critic → `complete <ID> critique`
7. check-limits → editor → `complete <ID> revised` → `auto-approve <ID>`
   (「停止:…」と出たら、その記事は止める。1回だけ editor に直させて再試行し、駄目なら 9 へ)
8. check-limits → sns → `complete <ID> sns` → `auto-approve <ID>` → `export-note <ID>` → `make-images <ID>`
   週次企画の実行(00_plan.md がある)では、さらに図を用意する:`images/plan/` に週次の画像が無ければ、`config/weekly_policy.md` の仕様で
   `runs/<ID>/figures.json`(見出し画像1枚+図2〜3枚)を書いて `make-figures <ID>` を実行し、Readで1枚ずつ目視して崩れがあれば直す。
   記事中の【画像:…】の名前と、画像ファイル名を合わせる。
9. **日曜日だけ**:`.claude/commands/weekly-plan.md` に従って翌週の週次企画を作る(上限で記事が作れなかった日も行う)。
10. `python -m note_editorial briefing` を実行し、結果(作った記事、止まった理由、あなたがやること)を日本語で簡潔に報告する

不合格(`[不合格]`)は理由に従って担当Agentにやり直させる(最大2回)。それでも駄目なら止めて報告する。
投稿後に人間が `mark-posted <ID> --url <記事URL>` を実行すると、次の記事を作れるようになる。
