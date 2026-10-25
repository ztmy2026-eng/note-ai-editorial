# 株クイズアプリ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** スマホで開く、毎日5問の株・投資クイズ(連続日数・不正解リスト再出題つき)を作って公開する。

**Architecture:** 純粋なロジック(`quiz/logic.js`)・問題データ(`quiz/questions.js`)・画面(`quiz/index.html`)の3つに分ける。ロジックは副作用なしの関数で、Node の `node:test` でテストする。画面はアーティファクトとして公開し、進捗は保存機能(使えなければブラウザ保存)に置く。

**Tech Stack:** プレーンな HTML/CSS/JavaScript(ビルドなし)、Node 22 の `node:test`、Artifact ツール。

**Spec:** `docs/superpowers/specs/2026-10-25-stock-quiz-design.md`

## Global Constraints

- 日付は日本時間(Asia/Tokyo)。0時で日付が変わる。
- 毎日5問。レベルは `basic|mid|adv`。分野は `basics|semi_ai|energy|health|robotics`。
- 卒業は再出題で**2回連続正解**。間隔は 翌日 → 3日後 → 7日後。
- 数字つき問題は `asof`(YYYY-MM-DD)と `source`(名前+URL)が必須。出典を確認できない数字は入れない。`asof` が90日より古いと「古い数字」表示。
- 画面に常時「勉強用であり、投資の助言ではありません」。特定銘柄の売買を勧める問題は作らない。
- 「もっとやる」(追加5問)は連続日数を増やさない。
- 秘密情報をコミットしない。コミット後は `claude/ai-note-editorial-system-2u1vuq` に push(衝突時は `git pull --no-rebase`)。

## Review Focus

- 日本時間0時またぎ(UTC前日の15:00〜24:00)でも「今日」が正しい。
- 2日以上空けたあとに開くと、連続日数が0になり、不正解リストは残る。
- 不正解リストの期日到来が2問より多いとき、5問を超えない。
- 新規問題が足りない(レベル・分野を使い切った)とき、落ちずに復習問題で埋める。
- 保存データが壊れている/空のとき、初期状態で起動する。

---

### Task 1: 日付と連続日数

**Files:**
- Create: `quiz/logic.js`, `quiz/tests/logic.test.js`

**Interfaces:**
- Produces: `jstDate(now: Date): string`(`YYYY-MM-DD`、日本時間)、`daysBetween(a: string, b: string): number`、`updateStreak(state, today: string): state`(`state.streak`, `state.lastDoneDate`)、`currentStreak(state, today): number`(今日未完了でも昨日までなら継続中として返す。2日以上空いていれば0)。
- `logic.js` は末尾で `if (typeof module !== 'undefined') module.exports = {...}` とし、ブラウザでは `window.QuizLogic` に載せる。

- [ ] **Step 1: 失敗するテストを書く** — `jstDate(new Date('2026-10-24T15:00:00Z')) === '2026-10-25'`、`jstDate(new Date('2026-10-24T14:59:59Z')) === '2026-10-24'`、`updateStreak` が連続日で+1・同日で据え置き・2日空きで1に戻る、`currentStreak` が2日空きで0。
- [ ] **Step 2: 実行して失敗を確認** — `node --test quiz/tests/` → FAIL(関数なし)。
- [ ] **Step 3: 実装** — `Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Tokyo'})` で日付を作る。
- [ ] **Step 4: 通ることを確認** — `node --test quiz/tests/` → PASS。
- [ ] **Step 5: コミット** — `git add quiz && git commit -m "Add streak and JST date logic"`

### Task 2: 不正解リスト(卒業ルール)

**Files:** Modify: `quiz/logic.js`, `quiz/tests/logic.test.js`

**Interfaces:**
- Consumes: Task 1 の `daysBetween`。
- Produces: `recordAnswer(state, q: {id}, correct: boolean, today: string): state`。`state.wrongList` は `[{id, stage, nextDue, okInRow}]`。`dueWrong(state, today): entry[]`(期日到来、`nextDue` の古い順)。

- [ ] **Step 1: テスト** — 新規で間違う→リスト入り(`stage 0`, `nextDue = 翌日`, `okInRow 0`)/再出題で正解→`okInRow 1`、`stage` 進行(翌日→3日→7日)/2回連続正解→リストから消える/再び間違い→`okInRow 0`、`stage` を0に戻す/リスト外の問題を正解してもリストに入らない。
- [ ] **Step 2: 失敗を確認** — `node --test quiz/tests/`。
- [ ] **Step 3: 実装** — `STAGE_DAYS = [1, 3, 7]`。`stage` が末尾を超えたら 7 日のまま。
- [ ] **Step 4: 通ることを確認**。
- [ ] **Step 5: コミット** — `git commit -m "Add wrong-answer list with graduation rule"`

### Task 3: 今日の5問を選ぶ

**Files:** Modify: `quiz/logic.js`, `quiz/tests/logic.test.js`

**Interfaces:**
- Consumes: `dueWrong`、問題データ `Q[]`(`{id, level, field, type, question, choices, answer, explain, term, asof?, source?, variants?}`)、`state.stats`、`state.level`。
- Produces: `pickDaily(state, Q, today: string, n = 5, rng = Math.random): Question[]`。期日到来の不正解から**最大2問**+現在のレベルの新規(未出題)+足りなければ既出の復習。同じ問題を重複させない。毎日交互に `basics` と分野を優先。苦手分野(正答率が低い)を多めに。

- [ ] **Step 1: テスト** — 5問返る/期日到来が5件あっても不正解枠は2問まで(Review Focus)/重複なし/新規が尽きても5問に埋める(Review Focus)/全問題が3問しかなければ3問返して落ちない/`rng` を固定すると結果が決まる。
- [ ] **Step 2: 失敗を確認**。
- [ ] **Step 3: 実装** — 並べ替えは `rng` を使う関数に統一。
- [ ] **Step 4: 通ることを確認**。
- [ ] **Step 5: コミット**。

### Task 4: 再出題の見た目を変える

**Files:** Modify: `quiz/logic.js`, `quiz/tests/logic.test.js`

**Interfaces:**
- Produces: `present(q, isRetry: boolean, rng): {id, question, choices, correctIndex}`。`choices` は毎回シャッフルし、`correctIndex` を返す。`isRetry` で `q.variants` があれば、`variants` から(前回と別の)言い換えを選ぶ。数値問題は `choices` なし。

- [ ] **Step 1: テスト** — 正解の文字列が `choices[correctIndex]` と一致/`rng` を変えると並びが変わる/`isRetry` で `variants` があれば元と違う文面/`variants` がなくても動く。
- [ ] **Step 2〜4:** 失敗確認→実装→通過確認。
- [ ] **Step 5: コミット**。

### Task 5: 成績・レベル調整・バッジ

**Files:** Modify: `quiz/logic.js`, `quiz/tests/logic.test.js`

**Interfaces:**
- Produces: `addStat(state, q, correct): state`(`state.stats[field][level] = {right, total}`)、`suggestLevel(state): 'basic'|'mid'|'adv'|null`(直近20問が8割超で次レベルを提案)、`badgesFor(state): string[]`(7日/30日連続、初回、100問)、`numberAnswerOk(input: string, answer: number, tol: number): boolean`(全角数字・カンマ・「倍」「%」を許す)、`isStale(q, today): boolean`(`asof` が90日より古い)。

- [ ] **Step 1: テスト** — 各関数の境界(正答率80.0%はちょうど提案しない・81%で提案/`numberAnswerOk('１５．２', 15.2, 0.1)`/`isStale` が90日・91日)。
- [ ] **Step 2〜4:** 失敗確認→実装→通過確認。
- [ ] **Step 5: コミット**。

### Task 6: 保存(壊れていても起動)

**Files:** Modify: `quiz/logic.js`, `quiz/tests/logic.test.js`

**Interfaces:**
- Produces: `emptyState(): state`、`loadState(raw: string | null): state`(`JSON.parse` 失敗・欠けたキー・型違いは `emptyState()` で補う)、`serialize(state): string`。

- [ ] **Step 1: テスト** — `loadState(null)`・`'{broken'`・`'{"streak":"x"}'` がすべて有効な状態を返す(Review Focus)/`serialize`→`loadState` で元に戻る。
- [ ] **Step 2〜4:** 失敗確認→実装→通過確認。
- [ ] **Step 5: コミット**。

### Task 7: 問題データ(初期版・実在数字)

**Files:** Create: `quiz/questions.js`, `quiz/tests/questions.test.js`

**Interfaces:**
- Produces: `QUESTIONS: Question[]`(`window.QUIZ_QUESTIONS` と `module.exports`)。形式は Task 3 の `Question`。

- [ ] **Step 1: データ検査のテスト** — `id` が重複しない/`level`・`field`・`type` が許可値/`choice` は4択で、`answer` が `choices` の中にある/数字を含む問題(`asof` か `source` のどちらかがあるもの)は両方揃っている/`asof` が未来でない/`explain` が空でない/各(分野×レベル)に最低3問(合計約120問)。
- [ ] **Step 2: 失敗を確認**。
- [ ] **Step 3: 問題を作る** — 数字は WebSearch/WebFetch で出典(JPX、各社IR、官公庁など)を確認してから入れる。確認できないものは数字なしの概念問題にする。投資の基礎(PER・PBR・ROE・配当利回り・金利と株価・分散投資・決算の読み方)、半導体・AI、エネルギー・資源、医薬・ヘルスケア、ロボティクスの各レベル。一部に計算問題(`number`)と読み解き問題、再出題用の `variants` を付ける。特定銘柄の売買を勧めない。
- [ ] **Step 4: 通ることを確認** — `node --test quiz/tests/`。
- [ ] **Step 5: コミット**(確認できなかった数字があれば、そのことをコミット本文に書く)。

### Task 8: 画面

**Files:** Create: `quiz/index.html`

**Interfaces:**
- Consumes: `QuizLogic`、`QUIZ_QUESTIONS`。保存は `window.claude` の保存機能が使えるか、事前に `artifact-capabilities` スキルを読んで確認。使えなければ `localStorage`(try/catch)。保存できないときは画面に出す。

- [ ] **Step 1: スキルを読む** — `artifact-design`、`artifact-capabilities`(保存の宣言方法)。
- [ ] **Step 2: ホーム** — 大きな🔥連続日数、今日の状態(未は赤・経過時間、完了は完了時刻)、直近のカレンダー。`currentStreak` と `jstDate` を使う。
- [ ] **Step 3: クイズ** — 4択/数値入力。回答直後に正解・解説・基準日・出典(`isStale` なら「古い数字」)。「この問題が変」ボタン(記録のみ)。5問終わったら完了を記録し、「もっとやる」を出す(連続日数は増えない)。
- [ ] **Step 4: 不正解リスト・成績・用語帳・バッジ** の各画面。常時「勉強用であり、投資の助言ではありません」。
- [ ] **Step 5: 動作確認** — 小さい画面幅(スマホ)で、ブラウザで開いて、1日分を通しで操作する(Playwright が使えれば使う)。日付を進めて連続日数・再出題を確認。確認できなかった点は、そう報告する。
- [ ] **Step 6: コミット**。

### Task 9: 公開

**Files:** なし(公開のみ)

- [ ] **Step 1:** `python -m pytest -q` と `node --test quiz/tests/` が通る。
- [ ] **Step 2:** Artifact ツールで公開(`quiz/index.html`、`logic.js`・`questions.js` は `files` で同梱)。公開前に Artifact の規約(タイトル2〜4語、ダーク対応、スマホ幅)を確認。
- [ ] **Step 3:** リンクを持ち主に伝える。使い方(毎日1回開く)と、数字の更新・問題追加はClaudeに頼むことを伝える。push する。

---

## 自己チェック
- 仕様との対応:連続日数=T1/T8、不正解リスト・卒業=T2、5問の内訳・分野交代・苦手重点=T3、再出題の変化=T4、レベル調整・バッジ・計算問題・古い数字=T5、保存=T6/T8、問題・実在数字・出典=T7、画面・用語帳・もっとやる・免責=T8。
- スマホ通知は仕様どおり範囲外。
