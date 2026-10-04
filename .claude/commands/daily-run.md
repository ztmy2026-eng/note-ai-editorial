---
description: 1日分の編集部の仕事(記事1本分)を、承認なしモードで上限まで進める。投稿は人間が手動
---
前提: `config/limits.yaml` の `auto_approve: true`。noteやSNSへ送信する操作は一切しない。
**新しい実行を作る前**は `python -m note_editorial check-limits --new-run`、**Agentを呼ぶ前**は毎回 `python -m note_editorial check-limits`
(作業中の実行の続きの確認。実行数は見ない)を実行し、終了コードが1(上限到達)なら、新しい作業を始めずに手順9へ進む。

1. `python -m note_editorial check-limits --new-run` (上限なら 9 へ)
2. `python -m note_editorial next-theme` でテーマを決め、`new-run --theme <id>` で実行を作る(失敗したら理由を記録して 9 へ)
3. check-limits → researcher → `complete <ID> research`
4. check-limits → planner → `complete <ID> ideas` → `auto-approve <ID>`
5. check-limits → writer → `complete <ID> draft`(config/editorial_rules.md の「自動モード」に従い、空欄を残さない)
6. check-limits → critic → `complete <ID> critique`
7. check-limits → editor → `complete <ID> revised` → `auto-approve <ID>`
   (「停止:…」と出たら、その記事は止める。1回だけ editor に直させて再試行し、駄目なら 9 へ)
8. check-limits → sns → `complete <ID> sns` → `auto-approve <ID>` → `export-note <ID>` → `make-images <ID>`
9. `python -m note_editorial briefing` を実行し、結果(作った記事、止まった理由、あなたがやること)を日本語で簡潔に報告する

不合格(`[不合格]`)は理由に従って担当Agentにやり直させる(最大2回)。それでも駄目なら止めて報告する。
投稿後に人間が `mark-posted <ID> --url <記事URL>` を実行すると、次の記事を作れるようになる。
