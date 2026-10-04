# VS Code(Windows 11)への移行プロンプト

使い方:①下の「事前準備」をやる → ②VS Codeでこのリポジトリのフォルダを開く → ③Claude Codeに「ここから下のプロンプト」を貼り付ける。

## 事前準備(あなたがやること。プロンプトの前に)
1. **インストール**:Git for Windows / Python 3.11以上(インストーラで「Add python.exe to PATH」にチェック)/ VS Code / Claude Code(VS Code拡張、またはCLI)/ Google Chrome か Microsoft Edge。
2. **GitHubにログイン**できる状態にする(ブラウザでのログインでよい)。**リポジトリが非公開(Private)であること**を、GitHubの設定で確認する(過去記事のデータが入るため)。
3. 好きな場所(例:`C:\Users\<あなた>\work`)に、次を実行して取得する。
   ```
   git clone https://github.com/ztmy2026-eng/note-ai-editorial.git
   cd note-ai-editorial
   git checkout claude/ai-note-editorial-system-2u1vuq
   ```
   (今はこのブランチにしか内容がありません。)
4. VS Codeで、そのフォルダを開き、Claude Codeを起動して、**クラウド版と同じClaudeアカウント**でログインする。

---

## ここから下を、Claude Codeに貼り付ける

あなたは、私(Windows 11、プログラミング初心者)の「note AI編集部システム」を、クラウドからこのPC(VS Code)に移行する担当です。
このフォルダが、そのリポジトリです(`ztmy2026-eng/note-ai-editorial`、ブランチ `claude/ai-note-editorial-system-2u1vuq`)。

### 0. 先にこれを守ってください
- 私は初心者です。コードを作る・変えるときは、「何をしたか/なぜ必要か/どう動くか/次に何をするか」を短く説明してください。長い講座は不要です。
- **私の承認なしに、次のことをしない**:大規模な変更、有料契約・課金、外部への送信・投稿(note・SNS・メールなど)、`config/limits.yaml` の上限値の変更、Gitの履歴の書き換え(force push・rebase)。
- 秘密情報(APIキー、トークン、パスワード)をコードやGitに入れない。見つけたら、すぐ私に知らせる。
- 小さく進め、各段階で動作確認(テストの実行結果)を見せてください。わからないことを勝手に決めず、質問してください。
- まず `README.md`、`config/editorial_rules.md`、`config/weekly_policy.md`、`docs/automation_options.md` を読んで、全体像を把握してください(読むだけ。この時点では何も変更しない)。

### 1. このシステムは何か(経緯の要約)
- noteの副業のための、AI編集部です。**AIは下書きと批評まで。noteやSNSへの投稿は、必ず私が手動で行う**(送信機能は無い)。
- 流れ:リサーチ → 企画 →[承認1]→ 執筆 → 批評 → 修正 →[承認2]→ SNS案 →[承認3]。成果物は `runs/<日付_連番>/` に1ファイルずつ保存される。
- 役割分担:考える・書く部分は `.claude/agents/*.md`(researcher / planner / writer / critic / editor / sns / analyst)。検品・承認・ログ・上限・集計・画像・進行管理は、`src/note_editorial/` のPythonコード(AIは使わない)。
- 手順書は `.claude/commands/`(`/daily-run`、`/weekly-plan`、`/editorial-run`、`/collect-metrics`、`/sync-metrics`、`/analyze`)。
- 設定は `config/`(`limits.yaml`:1日の上限と承認なしモード、`themes.yaml`:テーマ、`images.yaml`:画像の見た目、`weekly_policy.md`:週次企画の方針)。
- 現在の運用設定:`auto_approve: true`(承認1〜3を自動で通す。ただし検品は有効)/ 1日1本 / Agent作業は1日30まで / 未投稿の公開準備済みが3件で新規作成を止める。
- **【要入力】が本文に残っていると、承認2は止まる**(体験の欄は私が埋めてから `approve-publish`)。「(要確認)」も残せない。
- 過去記事のデータは `data/past_articles/`(実データ。サンプルは `data/samples/`)。他の人の記事の分析用データは、私が手で集める `data/market/items.csv`。

### 2. 移行でやること(順番に。各段階で私に結果を報告)
**A. 環境の確認と準備**
1. `git status`、`git log --oneline -5`、現在のブランチを確認して報告。
2. Python環境:`py --version`(または `python --version`)、`pip install -e ".[dev]"` を実行。
3. Windows特有の問題を先に潰す:
   - **文字コード**:日本語がコマンドの出力で化けたり、`UnicodeEncodeError` が出ないか確認。出る場合は、環境変数 `PYTHONUTF8=1` をVS Codeのターミナル設定(またはユーザー環境変数)に入れる方法を、私に分かりやすく案内。
   - ファイルパスの区切り(`\` と `/`)や、`/tmp` など Linux前提の記述がコード・手順書に無いか `grep` で確認。あれば直して報告。
   - **タイムゾーン**:`config/limits.yaml` の `timezone: Asia/Tokyo` が動くか(`tzdata` が入っているか)を確認。
4. `python -m pytest -q` を実行し、**全件合格(現時点で95件)** を確認。落ちたら、原因を調べて報告(勝手に直さず、まず原因の説明)。
5. 動作確認コマンド:`python -m note_editorial themes` / `check-limits` / `briefing` / `check-plan --week 2026-10-05`(合格するはず)/ `status`。

**B. 画像の作成(ブラウザ)**
6. `make-images` と `make-figures` は、ブラウザ(Chrome/Edge)で画像を作る。このPCで動くか確認する。
   - `config/images.yaml` の `browser_path`(空なら自動検出)を、必要なら私のPCのChrome/EdgeのパスにしてOKか、私に確認してから設定。
   - `make-figures` は Playwright が必要:`pip install playwright` の後、**このPCでは** `python -m playwright install chromium` を実行してよい(私のPCなので)。ダウンロードの前に、一言知らせて。
   - フォント:図やカードの日本語が文字化け(豆腐)しないか、実際に1枚作って目で確認。
   - 確認用には、過去の実行(`runs/` の既存フォルダ)を使い、**新しい記事は作らない**。

**C. Claude Code側の設定**
7. このフォルダの `.claude/agents/` と `.claude/commands/` が、Claude Codeに認識されているか確認(スラッシュコマンドの一覧に `/daily-run` などが出るか)。
8. **Gmail連携**(note通知メールからスキ・フォローを集める `/collect-metrics` 用):このClaude Codeで、Gmailのコネクタが使えるか確認。使えない場合は、私がやる設定手順を案内。**メールは読み取りだけ。送信・削除・ラベル変更は絶対にしない。**
9. **許可設定(permissions)**:毎回の確認ダイアログを減らすための許可ルールは、**私に提案して承認を得てから**追加。外部送信や削除につながるコマンドは、許可に入れない。

**D. 自動実行(毎朝)をどうするか** — ここは決めるのは私です。先に比較して提案してください。
10. 現在、**クラウドのRoutines(毎朝 日本時間7:45に `/daily-run`)が動いている**。このPCで自動実行する場合の選択肢を、利点・欠点つきで説明:
    - (a)Windowsのタスクスケジューラ + `claude -p "/daily-run"`(PCの電源が入っていてスリープしていないことが必要)。
    - (b)自動実行はクラウドのまま、VS Codeでは手動運用(`/daily-run` を自分で実行)。
    - **重要**:クラウドとPCの**両方で毎朝実行すると、同じブランチへのpushが衝突し、記事が二重に作られる**。どちらか一方にする。クラウドを止める場合は、私に「停止してよいか」確認してから、手順を案内。
11. 無人実行する場合の安全面(許可するツールの範囲、外部送信の防止、上限の維持)を、具体的に提案。

**E. データとブランチの整理**
12. クラウドで増えた成果物(`runs/`、`data/`、`analytics/`、`plans/`、`briefing/`)が、このクローンに揃っているか `git pull` で確認。
13. 作業ブランチの運用方針を提案(例:`main` に統合するか、現ブランチのまま使うか)。**マージやブランチ操作は、私の承認後に**。

### 3. 引き継ぐ未解決の事項(忘れず、私に聞くか、状況を報告してください)
- **noteの利用規約**:自動でnoteのページを読んでよいか、未確認。現在、noteのページの自動取得は**止めてある**(`.claude/commands/weekly-plan.md`)。私が規約を確認して許可するまで、戻さない。
- **クラウド自動実行のpush権限**:クラウド側で「リポジトリへのpushが403で拒否される」問題があり、解決を確認できていない。
- **ダッシュボード**(インプ・PV・スキを見る/直すページ)は、claude.aiのArtifactとして作ってある(`dashboard/index.html` がソース)。VS Code側のClaude Codeでは更新できないかもしれない。できるか確認して、できなければ「クラウド側で更新する」と私に伝える。
- **市場データの分析**(`data/market/items.csv`、`analyze-market`):記事30件未満の間は傾向として扱わない。私が手で集める。
- **週次企画**:`plans/2026-10-05/` は未承認のまま。未承認でも自動モードでは使われる設計。

### 4. 終わったら報告してほしいこと
- 実行したコマンドと、それぞれの結果(テストの件数、`check-plan` の合否、画像を作れたか)。
- Windowsで直したこと(あれば、何をなぜ)。
- 私に残っている作業(インストール、設定、判断が必要な点)を、チェックリストで。
- 変更したファイルは、私に確認してから `git commit` し、push も私の承認後に。
