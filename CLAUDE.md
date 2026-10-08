# note AI編集部 — 作業の約束(Claudeが毎回読む)

このリポジトリは、noteの副業のための「AI編集部」です。持ち主は、プログラミング初心者です。**日本語で、短く、やさしく**説明してください(何をしたか・なぜか・次に何をするか)。
スマホ(Claudeアプリの Code タブ、クラウド側のセッション)から、PCが切れた状態で頼まれることがあります。そのときも、下の約束で動いてください。

## 絶対に守ること
- **noteにもSNSにも、メールにも、投稿・送信しない。** 投稿は、必ず持ち主が手で行う。
- **承認2(`approve-publish`)は、持ち主が「承認2してよい」と書いたときだけ実行する。** 承認なしモードの `auto-approve` は、毎朝の自動実行のためのもの。対話のセッションでは、持ち主の明示の指示なしに、承認系のコマンドを実行しない。
- **持ち主の体験・意見・数字を創作しない。** 体験の空欄(【要入力:…】)は、持ち主が書いた言葉だけで埋める。「適当に付け加えて」と頼まれたときは、3案を出し、**付け足した部分を「Claudeの提案(未確認)」と記録**してから、持ち主が選んだ案だけを使う(`runs/<ID>/experience_options.md` と `author_notes.md`)。
- **秘密情報(キー・トークン・パスワード)をGitに入れない。** 見つけたら、すぐ知らせる。
- `config/limits.yaml` の上限値は、勝手に変えない。Gitの履歴を書き換える操作(rebase・force push)はしない。衝突したら、マージで合流する(`git pull --no-rebase`)。
- 未確認の数字・事実は、記事に書かない。出典(URLと日付)があるものだけ。

## 「今日」は日本時間
- 日付・「今日の実行」・上限は、日本時間(Asia/Tokyo)で数える。クラウドの時計(世界時)は、日本の朝7:45では、まだ前の日。環境の `date` で判断せず、`check-limits --new-run` や `today-plan` の出力に従う。

## 作業の終わりに必ずやること
- 変更したら、**コミットして、ブランチ `claude/ai-note-editorial-system-2u1vuq` に push する**(PCが切れていると、そうしないと変更が失われる)。コミットメッセージは英語の1行+短い説明でよい。
- コードを変えたら、先に `python -m pytest -q` を実行して、全部通ることを確認する。
- 実行に失敗したら、隠さず、そのまま報告する。

## 環境のメモ(クラウド)
- 最初に `pip install -e ".[dev]"`。それでも `python -m note_editorial` が見つからなければ、`export PYTHONPATH=src` を付けて実行する。
- クラウドのネットワークは、設定した公的機関などのサイトにだけつながる。つながらないサイトは、無理に回避しない(「通信制限で開けなかった」と報告する)。
- 画像づくり(`make-images` `make-figures`)は、ブラウザが要る。クラウドで動かないときは、「画像はPCで作り直す」と伝える(すでにある画像は `runs/<ID>/images/` にある)。

## スマホでよく来る頼みと、やること
| 頼み | やること |
|---|---|
| 「今日の状況」「何が待ってる?」 | `python -m note_editorial briefing` と `status` を見て、持ち主がやることだけを、短く伝える |
| ダッシュボードが生成した「実行 <ID> の記事…の空欄を埋めます。【…】<本文>…」 | その<本文>を、`runs/<ID>/05_revised.md` の空欄に**そのまま**反映する。書かれていないことは足さない。「書くとよい失敗の例」の案内文は消す。機械の検査(空欄が残っていないか)を通し、結果と本文を見せる。**承認2はしない**(「承認2してよい」が来るまで)。コミット・push |
| 「適当に付け加えて、3案」 | 上の約束どおり、3案を出し、記録する。選ばれた案だけを反映する |
| 「承認2してよい」 | `approve-publish <ID>` → `export-note <ID>` を実行する。タイトルと本文を、**コードブロックでチャットに出す**(スマホでコピーできるように)。本文の中の【画像:…】の行は、画像を入れる位置の印なので、その旨を伝える。コミット・push |
| 「投稿用の文を出して」 | `runs/<ID>/note_post/title.txt` と `body.md` を、コードブロックで出す。SNS案は `06_sns.md`(URLが決まっていれば `06_sns_ready.md`)から出す。【記事URL】が残っている案は、URLをもらってから置き換える |
| 「投稿した。URLは〜」 | `mark-posted <ID> --url <URL>` を実行する(URLは、https:// で始まるnoteの記事URL)。SNS案のURLを埋めたファイルができる。コミット・push |
| 「数字を入れて(インプ・PV・スキ)」 | `record-metrics <ID> --impressions … --pv … --likes …`。コミット・push |
| 「ダッシュボードを更新して」 | `.claude/commands/sync-metrics.md` の手順。**`ArtifactData` が使えない環境なら、「ダッシュボードの更新はPCが入っているときにします」と伝えて止める**(更新したことにしない)。ほかの作業はダッシュボードなしでできる |
| 「見送りにして」 | `mark-skipped <ID> --reason …`(ファイルは消さない)。コミット・push |

## 場所
- 手順書: `.claude/commands/`(`daily-run` `weekly-plan` `sync-metrics` `collect-metrics` `analyze` `editorial-run`)。担当Agent: `.claude/agents/`。
- 記事の方針: `config/weekly_policy.md`(タイトル・体験を作らない・今週の特別方針)、`config/editorial_rules.md`。
- 週次企画: `plans/<週の月曜>/plan.yaml`。企画案: `plans/ideas/`。
- ダッシュボード(非公開のページ。持ち主が見る): https://claude.ai/artifact/QKDCrkrJ6MNY3VHRu9uixv (ソース `dashboard/index.html`)。
- 操作ガイド: `docs/mobile_guide.md`。
