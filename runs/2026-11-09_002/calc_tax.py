"""年末調整の改正(令和8年分)の、所得税の差の仮の例。給与のみ・独身・扶養なし・社会保険料などその他の控除なし。復興特別所得税は含まない。
給与所得控除(令和8・9年分): 〜220万円=74万円(改正前=65万円の最低保障) / 〜360万円: 収入×30%+8万 / 〜660万: ×20%+44万 / 〜850万: ×10%+110万 / 850万超: 195万
基礎控除(合計所得による。改正前→改正後): 〜132万 95→104 / 〜336万 88→104 / 〜489万 68→104 / 〜655万 63→67 / 〜2350万 58→62 (単位万円)
税率(速算表): 〜195万 5% / 〜330万 10%-9.75万 / 〜695万 20%-42.75万 / 〜900万 23%-63.6万 / 〜1800万 33%-153.6万
"""
def kyuyo_ctrl(s, new):
    if s <= 220: return 74 if new else (65 if s <= 162.5 else s * .4 - 0)  # 改正前は 収入×40%-10万(最低65万)
    if s <= 360: return s * .3 + 8
    if s <= 660: return s * .2 + 44
    if s <= 850: return s * .1 + 110
    return 195
def old_ctrl(s):
    if s <= 162.5: return 65
    if s <= 180: return s * .4 - 10
    if s <= 360: return s * .3 + 8
    if s <= 660: return s * .2 + 44
    if s <= 850: return s * .1 + 110
    return 195
def basic(g, new):
    if g <= 132: return 104 if new else 95
    if g <= 336: return 104 if new else 88
    if g <= 489: return 104 if new else 68
    if g <= 655: return 67 if new else 63
    if g <= 2350: return 62 if new else 58
    return 0
def tax(t):  # 課税所得(万円)→税額(万円)
    t = max(0, t)
    if t <= 195: return t * .05
    if t <= 330: return t * .10 - 9.75
    if t <= 695: return t * .20 - 42.75
    if t <= 900: return t * .23 - 63.6
    return t * .33 - 153.6
for s in (200, 300, 400, 500, 600, 700, 1000):
    g_old = s - old_ctrl(s); g_new = s - (kyuyo_ctrl(s, True) if s > 220 else 74)
    t_old = g_old - basic(g_old, False); t_new = g_new - basic(g_new, True)
    a, b = tax(t_old) * 10000, tax(t_new) * 10000
    print(f"年収{s}万: 給与所得 {g_old:.0f}→{g_new:.0f}万 / 課税所得 {t_old:.0f}→{t_new:.0f}万 / 税 {a:,.0f}→{b:,.0f}円 / 差 {a-b:,.0f}円")
