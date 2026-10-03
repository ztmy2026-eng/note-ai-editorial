---
description: 過去記事を集計し、分析Agentで仮説台帳を更新する
---
1. `python -m note_editorial analyze` で `analytics/facts.md` を作る(計算はPython)
2. analyst に依頼して `analytics/hypotheses.md` を作成・更新する
3. `python -m note_editorial validate-hypotheses` で形式を検査する(不合格なら直させる)
4. `python -m note_editorial briefing` で朝のブリーフィングを更新し、内容を人間に報告する
