---
description: noteの通知メール(Gmail連携)から、スキ・フォローの数を集めて記録する
---
前提: Gmail連携が note のアカウントのメールにつながっていること。**メールの読み取りだけ**を行い、送信・削除・ラベル変更・返信は一切しない。

1. `mcp__Gmail__search_threads` で次を検索する(`view` は THREAD_VIEW_MINIMAL。本文は開かない)。
   - スキ: `from:noreply@note.com subject:スキされました newer_than:30d`(pageSize 50。多ければ nextPageToken で続ける)
   - フォロー: `from:noreply@note.com subject:フォローされました newer_than:30d`(METADATA_ONLY でよい)
2. 一時ファイル(**リポジトリの外**。例: スクラッチパッド)に次の形のJSONを書く。
   `{"likes":[{"date":"<ISO日時>","snippet":"<snippetのうち『作品が読者に届いています！』から『スキしてくれた人』までの部分>"}], "follows":["<ISO日時>", ...]}`
   スキ・フォローしてくれた人の名前やプロフィールは、JSONにも出力にも**書かない**。
3. `python -m note_editorial collect-metrics <そのJSON>` を実行する(同じ期間を何度実行しても重複しない)。
4. PVと売上はメールで届かない(確認済みの範囲)。ダッシュボードの数字を人が教えてくれたら、`record-metrics` で記録する。
5. `python -m note_editorial analyze` と `briefing` を実行し、結果を日本語で簡潔に報告する。
注意: メールのスキ数は取り消しで減ることがある推定値。確定値はnoteのダッシュボードで確認する。
