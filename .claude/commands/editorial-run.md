---
description: 1回分の編集部パイプライン(リサーチ→企画→[承認1]→執筆→批評→修正→[承認2])を進める
argument-hint: <テーマID 例: ai-work> [phase1|phase2 候補番号と体験メモ]
---
引数: $ARGUMENTS

`python -m note_editorial` を使い、次の手順で進める。各Agentには Agent ツールで依頼し、
サブエージェント(researcher / planner / writer / critic / editor)として動かす。
**1つの成果物が合格するまで次へ進まない。外部への公開・送信は絶対にしない。**

## phase1(企画まで)
1. `python -m note_editorial new-run --theme <テーマID>` で実行IDを得る
2. researcher → `01_research.md` → `complete <実行ID> research`
3. planner → `02_ideas.md` → `complete <実行ID> ideas`
4. **ここで止まる(承認1)。** 候補5件とおすすめ・質問を人間に提示し、
   人間が `approve-idea <実行ID> <番号>` を指示するまで待つ

## phase2(承認1の後)
5. writer → `03_draft.md` → `complete <実行ID> draft`(人間の体験メモがあれば渡す)
6. critic → `04_critique.md` → `complete <実行ID> critique`
7. editor → `05_revised.md` → `complete <実行ID> revised`
8. **ここで止まる(承認2)。** 【要入力】の残りを人間に示し、承認は人間のみが
   `approve-publish <実行ID>` で行う

不合格(`[不合格]`)が出たら、理由に従って担当Agentにやり直させる(最大2回。それでも駄目なら人間に報告)。

## phase3(承認2の後)
9. sns → `06_sns.md` → `complete <実行ID> sns`
10. **ここで止まる(承認3)。** 人間のみが `approve-sns <実行ID>` で承認する。投稿は人間が手動で行う
