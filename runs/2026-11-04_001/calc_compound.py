"""1億円に必要な毎月の積立額(試算)。前提つき・目安・将来を保証しない。
式: 毎月末にPを積立、月利 r=年利/12(名目年利÷12)、n=年数*12か月
  将来額 FV = P * ((1+r)**n - 1) / r   (r=0 なら P*n)
  必要額 P = 目標 * r / ((1+r)**n - 1)
税なし版: 手数料・税を考えない。
税あり版(単純化): 最後に全額売却し、利益(FV-元本)に20.315%を課税した手取りが目標になるPを求める。
  NISA枠・手数料・売却の分割などは考えない単純モデル。
"""
TARGET = 100_000_000
TAX = 0.20315


def fv_factor(rate_year, years):
    n = years * 12
    r = rate_year / 12
    return n if r == 0 else ((1 + r) ** n - 1) / r


def need_monthly_no_tax(rate, years):
    return TARGET / fv_factor(rate, years)


def need_monthly_after_tax(rate, years):
    # 手取り = FV - TAX*(FV - 元本) = FV*(1-TAX) + TAX*P*n  = P*(f*(1-TAX) + TAX*n)
    n = years * 12
    f = fv_factor(rate, years)
    return TARGET / (f * (1 - TAX) + TAX * n)


if __name__ == "__main__":
    print("年利,年数,税なし月額(円),総払込(円),税あり月額(円),総払込(円)")
    for years in (10, 20, 30, 40):
        for rate in (0.0, 0.03, 0.05, 0.07):
            a = need_monthly_no_tax(rate, years)
            b = need_monthly_after_tax(rate, years)
            print(f"{rate*100:.0f}%,{years},{a:,.0f},{a*years*12:,.0f},{b:,.0f},{b*years*12:,.0f}")
    # つみたて投資枠の上限 月10万円・成長投資枠込み 月30万円(年360万円)での到達
    print("\n月10万円(つみたて投資枠の年間上限120万円÷12)を積み立てた場合の将来額")
    for years in (20, 30):
        for rate in (0.0, 0.03, 0.05, 0.07):
            print(f"{rate*100:.0f}%,{years}年,{100_000*fv_factor(rate, years):,.0f}円")
    print("\n月3万円・月5万円の場合(30年)")
    for p in (30_000, 50_000):
        for rate in (0.0, 0.03, 0.05, 0.07):
            print(f"月{p:,}円,{rate*100:.0f}%,30年,{p*fv_factor(rate, 30):,.0f}円")
    print("\n非課税保有限度額1,800万円 / 年360万円 =", 18_000_000 / 3_600_000, "年")
