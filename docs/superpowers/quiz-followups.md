# 株クイズ:公開後の宿題(後回しにした項目)

公開ページ: https://claude.ai/artifact/DMDicCsoM7pa4zZxS7gZzY (非公開。持ち主だけ)
ソース: `quiz/`(`index.html` `logic.js` `questions.js` `app.js` `views.js` `style.css`)。テスト: `node --test quiz/tests/logic.test.js quiz/tests/questions.test.js`(ディレクトリ指定は Node 22 で動かない)。

## 数字の更新(実在の数字の問題・約26問)
- 数字は WebSearch の結果で確認したもの。公式ページは直接開けていない。出典名に「(検索結果で確認)」と付いている。
- `checked` は「数字を最後に確認した日」(2026-10-25)。新しい統計が出たら `asof`・数字・`checked` を更新する。
- 早めに見直す: `robotics-adv-09`(JARA 受注。新しい四半期が10月下旬に出る。出典は報道なので、JARA の PDF に差し替えたい)、`energy-mid-07` `energy-adv-08`(賦課金。出典は解説サイト)、`health-mid-08`(薬価改定。出典は報道)。
- 国民医療費は令和5年度版。令和6年度版が出たら差し替える。

## 問題の細かい直し
- 正解だけ書き出し・終わり方が違う: `semi_ai-adv-05` `semi_ai-adv-06` `robotics-mid-01` `basics-mid-05`(言い換え) `robotics-basic-02`(言い換え) `robotics-basic-05`(言い換え) `robotics-adv-02`。
- 正解にも見える選択肢: `energy-mid-03`(言い換え) `robotics-adv-01` `robotics-adv-03` `robotics-adv-05`。
- 言い回し: `semi_ai-mid-04`(言い換え) `semi_ai-mid-05` `semi_ai-adv-03` `basics-basic-03` `health-adv-07`(言い換え)。
- 選択肢の書き直しは、1つのエージェントが約130問分を行い、最終レビューで確認済み。ただし人の目でのチェックはまだ。

## アプリの小さな点
- 数字の答えは、単位の言葉を見ない(「4033万ドル」でも数字が合えば○)。
- 卒業は「再出題で2回連続正解」なので、間隔は「翌日→3日後」まで。設計書の「7日後」は使われない。
- 同じレベルで問題を使い切ると、同じ問題を復習する(レベルは自動では変わらない)。
- スマホとPCで同時に使うと、片方の記録が上書きされることがある。
- 通知は来ない。毎日、自分でページを開く。
- 日をまたぐ「もっとやる」、年末→年始の分野の交代、360px幅の確認、本物の保存機能での確認は未実施(テストはすべて、ふりをするテスト用の部品で行った)。
