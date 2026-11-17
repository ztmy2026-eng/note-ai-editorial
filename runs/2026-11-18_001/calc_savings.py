"""03_draft.md の試算(仮の例)。python calc_savings.py で再計算できる。
前提: 元本100万円、年1回の複利、税引後=表示利率x0.8(目安)、期間10年、金利と物価は変わらないと仮定。
"""
principal = 1_000_000
years = 10
cases = {"普通預金 0.40%": 0.0040, "定期1年 0.700%": 0.0070}
cpi = 0.021
factor = (1 + cpi) ** years
finals = {}
for name, rate in cases.items():
    net = rate * 0.8
    final = principal * (1 + net) ** years
    finals[name] = final
    print(f"{name}: 税引後利率 {net:.4%} -> 10年後 {final:,.0f}円 (増加 {final - principal:,.0f}円)")
    # 読者が自分の貯金額に掛ける倍率(利息つき)
    print(f"  {name}: 10年後の倍率 {(1 + net) ** years:.4f}")

print(f"物価 +2.1%/年が10年続く仮定: 同じ物の値段は {factor:.3f}倍 -> 100万円の物は {principal * factor:,.0f}円")
print(f"(利息ゼロの場合)100万円で買える量(今の物の値段で): {principal / factor:,.0f}円分")

# 利息つきの購買力: 税引後の残高 ÷ 物価の倍率(今のお金でいくら分の買い物ができるか)
for name, final in finals.items():
    print(f"{name}: 10年後の残高を今のお金に直すと {final / factor:,.0f}円分")

diff = finals["定期1年 0.700%"] - finals["普通預金 0.40%"]
print(f"定期と普通預金の差(10年後の残高): {diff:,.0f}円")
