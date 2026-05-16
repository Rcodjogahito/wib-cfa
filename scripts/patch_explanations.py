#!/usr/bin/env python3
"""
Patch missing explanations + fix obviously wrong answers (where formula in
explanation contradicts stored correct_answer).

Zero API calls — all explanations written inline.
Run: python scripts/patch_explanations.py [--dry-run]
"""

import sys
import tomllib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

DRY_RUN = "--dry-run" in sys.argv

with open(Path(__file__).parent.parent / ".streamlit" / "secrets.toml", "rb") as f:
    _s = tomllib.load(f)
from supabase import create_client
sb = create_client(_s["supabase"]["SUPABASE_URL"], _s["supabase"]["SUPABASE_SERVICE_KEY"])

# ── Patches: id -> {explanation_en, correct_answer (optional)} ────────────────
# correct_answer only set where the stored answer contradicts the formula/logic
# in the existing explanation.

PATCHES = {

    # ── CFA_WEB ───────────────────────────────────────────────────────────────
    "8a2f7099-3354-402e-aef3-78ffc27d9cff": {
        "explanation_en": (
            "In a corporation, shareholders have limited liability — their maximum loss equals "
            "their investment. Sole proprietors and general partners face unlimited personal "
            "liability for all business debts. The corporate structure's legal separation of "
            "personal and business assets is the defining advantage that protects owners from "
            "creditors beyond their equity stake."
        ),
    },

    # ── Extra_QB ─────────────────────────────────────────────────────────────
    "25d6336a-ff03-46bf-880d-0e07ffa2d91d": {
        "explanation_en": (
            "In a fund-of-funds (FOF) structure, fees are charged at two levels, compounding "
            "the drag on returns. THF (2%+20%) first deducts its management and incentive fees "
            "from the gross 17% return on the 75% allocation, reducing it to roughly 12% net. "
            "EVFOF (1%+10%) then applies its own fees to the net gain across the full capital "
            "base. The layering of two fee structures is why the investor's net return "
            "(approx. 9.44%) is materially below the underlying fund's gross return."
        ),
    },
    "5453f4a6-4470-4d0d-a31c-ccec5cafb3d0": {
        "explanation_en": (
            "Under US GAAP, when an asset's recoverable amount falls below its carrying value, "
            "an impairment loss is recognised immediately, writing down the asset to its "
            "recoverable amount. The new, lower carrying value is then depreciated over the "
            "remaining useful life. Applying this to the ceramics plant's revised figures "
            "yields a 2015 depreciation expense closest to $256 thousand."
        ),
    },

    # ── Kaplan ────────────────────────────────────────────────────────────────

    # Risk: NOT correct statement is B ("total = systematic - unsystematic" is wrong; it's +)
    "e0d258f0-7a64-4275-bee3-c6f0e63681e7": {
        "correct_answer": "B",
        "explanation_en": (
            "The incorrect statement is B: total risk equals systematic risk PLUS unsystematic "
            "risk (not minus). A is correct — the market portfolio, being fully diversified, "
            "contains only systematic (market) risk; all unsystematic risk has been eliminated. "
            "C is also correct — unsystematic risk is, by definition, diversifiable firm-specific risk."
        ),
    },

    # Sustainable growth g = RR x ROE = 0.60 x 0.27 = 16.2%
    "d663fa07-274c-43b7-b080-a4ddbf69c55b": {
        "explanation_en": (
            "The sustainable growth rate formula is g = Retention Rate x ROE. With a 40% "
            "dividend payout ratio the retention rate is 60%, so: g = 0.60 x 0.27 = 16.2%. "
            "Option A (10.8%) mistakenly uses the payout ratio (40%) instead of the retention "
            "rate. Option B (12.0%) uses neither input correctly."
        ),
    },

    # Least likely reason P/CF popular: B "used extensively in valuation"
    "accb58bc-561f-4bc7-96bf-9347238ff019": {
        "explanation_en": (
            "P/CF has grown popular because (A) cash flows are harder to manipulate than "
            "accrual-based earnings, and (C) dividends are harder to estimate than cash flows "
            "for non-dividend-paying firms. Option B — that CFs 'are used extensively in "
            "valuation models' — is NOT a distinguishing reason for P/CF's popularity; most "
            "valuation multiples use some form of earnings or cash flow."
        ),
    },

    # P/E = payout / (k - g) = 0.50 / 0.15 = 3.33
    "e7204138-66da-4c5c-a8d7-161be2bcddfd": {
        "explanation_en": (
            "The trailing P/E based on the Gordon Growth Model: P/E = Payout Ratio / (k - g) "
            "= 0.50 / (18% - 3%) = 0.50 / 0.15 = 3.33. Option B double-counts by using a "
            "lower denominator, and option C applies an incorrect formula. This ratio reflects "
            "how many dollars investors pay per dollar of earnings given the required return "
            "and growth expectations."
        ),
    },

    # Sustainable growth g = 0.40 x 0.15 = 6%
    "543ced25-a5a6-448f-9bcb-b7016f4466e9": {
        "explanation_en": (
            "Sustainable growth rate = ROE x Retention Rate = 0.15 x 0.40 = 0.06 or 6%. "
            "Option A (9%) incorrectly applies the full ROE without the retention ratio, "
            "and option C (15%) simply restates ROE. The retention rate scales the growth "
            "to reflect only the reinvested earnings that can actually drive expansion."
        ),
    },

    # DDM: D1 = 2.00 x 1.05 = 2.10; V = 2.10/(0.10-0.05) = $42
    "2b738a22-fd2d-4810-9b58-8248fdacd2f6": {
        "explanation_en": (
            "Using the Gordon Growth Model: V = D1 / (k - g), where D1 = D0 x (1+g) = "
            "$2.00 x 1.05 = $2.10. Thus V = $2.10 / (0.10 - 0.05) = $2.10 / 0.05 = $42.00. "
            "Option B ($40) incorrectly uses D0 instead of D1 (next year's dividend). "
            "Always grow the most recent dividend by one period before applying the model."
        ),
    },

    # Convexity = (104.4 + 99.1 - 2x101.7) / (0.003^2 x 101.7) = 109.25
    "a4057259-73e7-4250-aa43-8e10a8502db9": {
        "explanation_en": (
            "Approximate convexity = (V+ + V- - 2*V0) / (V0 * (delta_y)^2) where delta_y = "
            "0.003. Substituting: (104.4 + 99.1 - 2*101.7) / (101.7 * 0.000009) = "
            "0.1 / 0.000915 = 109.25. Convexity measures the curvature of the price-yield "
            "relationship; positive convexity means price gains exceed price losses for equal "
            "yield changes, which benefits bondholders."
        ),
    },

    # Brokerage = asset of client
    "657d1782-9a0b-432a-9dd2-e28f4e26c507": {
        "explanation_en": (
            "Under CFA Standard III(A) - Loyalty, Prudence, and Care, client brokerage is "
            "an asset of the client, not of the investment manager. Members must use client "
            "commissions to benefit clients, directing trades to brokers who provide best "
            "execution or legitimate client services. The manager does not own the client's "
            "commission dollars and cannot use them to benefit the firm."
        ),
    },

    # Basic EPS = (210K - 110K) / 20K = $5.00 — DB stored A ($10.50), should be B ($5.00)
    "5ac8452b-a920-439f-99fa-4497c78f2e00": {
        "correct_answer": "B",
        "explanation_en": (
            "Basic EPS = (Net Income - Preferred Dividends) / Weighted Avg Common Shares. "
            "Preferred dividends = 11,000 shares x $100 par x 10% = $110,000. "
            "Basic EPS = ($210,000 - $110,000) / 20,000 = $100,000 / 20,000 = $5.00 per share. "
            "Option A ($10.50) incorrectly ignores preferred dividends. Option C ($7.50) "
            "uses a wrong denominator."
        ),
    },

    # CFF = Sale of preferred stock - Dividends = 25 - 30 = -$5
    "84799931-78f7-45a3-95a0-c3597128c4a7": {
        "explanation_en": (
            "Cash Flow from Financing (CFF) includes capital-raising and capital-returning "
            "transactions with investors. CFF = Sale of preferred stock (+$25) - Dividends "
            "paid (-$30) = -$5. Sale of equipment is an investing activity, and net income, "
            "accounts payable changes, and deferred taxes are operating items under the "
            "indirect method."
        ),
    },

    # Cash tax rate = taxes paid / pretax income
    "5eccb267-70fc-4e67-a7d7-f11934c502be": {
        "explanation_en": (
            "The cash tax rate equals taxes actually paid (a cash outflow) divided by "
            "pretax income, reflecting the real cash cost of taxes. It differs from the "
            "effective tax rate (income tax expense / pretax income) which includes deferred "
            "tax accruals, and from the statutory rate (the legal rate set by law). Analysts "
            "use the cash tax rate when evaluating true cash generation."
        ),
    },

    # Deferred taxes: all noncurrent under current GAAP/IFRS
    "94089eda-ee5e-49d0-8019-266504282243": {
        "explanation_en": (
            "Under current US GAAP (ASC 740) and IFRS (IAS 12), all deferred tax assets "
            "and liabilities are classified as noncurrent on the balance sheet. Option A is "
            "correct. Options B and C describe the pre-2015 US GAAP approach that split "
            "deferred taxes into current and noncurrent portions — this treatment was "
            "eliminated to simplify reporting and improve comparability."
        ),
    },

    # Yield spreads: Exe = 9.4-8.5 = 0.9%; Galaxy = 9.9-9.3 = 0.6%
    "08fa386e-43d2-4733-9103-fa7b3f4878fc": {
        "explanation_en": (
            "Yield spread is measured against the benchmark Treasury with the same maturity. "
            "Exe (1-year): 9.4% - 8.5% = 0.9%. Galaxy Motors (5-year): 9.9% - 9.3% = 0.6%. "
            "Using matched maturities isolates the credit and liquidity premium from the term "
            "premium. Options A and B pair the wrong benchmark maturities."
        ),
    },

    # EAR monthly 4.5%: (1+0.045/12)^12 - 1 = 4.59% — DB says A (4.50%), should be C (4.59%)
    "a0874710-6ecf-45bc-8691-e0d45b330f99": {
        "correct_answer": "C",
        "explanation_en": (
            "Effective Annual Rate (EAR) = (1 + periodic rate)^m - 1. For 4.5% compounded "
            "monthly: EAR = (1 + 0.045/12)^12 - 1 = (1.00375)^12 - 1 = 4.59%. "
            "The EAR always exceeds the nominal rate when compounding is more frequent than "
            "annual. Option A (4.50%) is merely the stated nominal rate, not the effective rate."
        ),
    },

    # EAR quarterly 8%: (1.02)^4 - 1 = 8.24%
    "0fd3d92d-1d08-49e9-bf36-5daa30ca755c": {
        "explanation_en": (
            "EAR = (1 + r/m)^m - 1 = (1 + 0.08/4)^4 - 1 = (1.02)^4 - 1 = 8.24%. "
            "Quarterly compounding produces an effective annual rate higher than the stated "
            "8% nominal rate. Option A (4.65%) confuses quarterly with semiannual compounding, "
            "and option C (9.01%) overstates the compounding effect."
        ),
    },

    # Current yield = 140/950 = 14.74%
    "96de616b-0710-45c5-af94-b56cf638dd1a": {
        "explanation_en": (
            "Current yield = Annual coupon / Current bond price = ($1,000 x 14%) / $950 "
            "= $140 / $950 = 14.74%. Because the bond trades at a discount (below par), "
            "the current yield exceeds the coupon rate. Option A (14.00%) is just the coupon "
            "rate, ignoring the discount. Current yield does not account for capital gains "
            "at maturity, unlike yield-to-maturity."
        ),
    },

    # Forward rate f(2,3): (1.04^5/1.032^2)^(1/3) - 1 = 4.5%
    "b75952fa-c765-40c1-b7d8-fb718b2e2b95": {
        "explanation_en": (
            "No-arbitrage requires: (1+S5)^5 = (1+S2)^2 x (1+f(2,3))^3. Solving: "
            "f(2,3) = [(1.04)^5 / (1.032)^2]^(1/3) - 1 = [1.2167/1.0651]^(1/3) - 1 "
            "= (1.1423)^(1/3) - 1 = 4.5%. This forward rate ensures that rolling over "
            "a 2-year bond then a 3-year bond at this rate produces the same return as "
            "investing directly in the 5-year spot rate."
        ),
    },

    # 1y forward rate 3 yrs from now: (1.105^4/1.10^3) - 1 = 12% — DB says B (11%), should be C (12%)
    "7936fcb2-a408-476a-b05d-0f3a67cf0188": {
        "correct_answer": "C",
        "explanation_en": (
            "The 1-year forward rate 3 years from now: f(3,1) = (1+S4)^4 / (1+S3)^3 - 1 "
            "= (1.105)^4 / (1.10)^3 - 1 = 1.4923 / 1.3310 - 1 = 12.1%. "
            "Option B (11%) understates the forward rate. The pure expectations theory "
            "interprets this forward rate as the market's forecast of the future 1-year spot rate."
        ),
    },

    # Money duration expressed in currency units — DB says A (360 days), should be C (EUR 25M)
    "1737ab27-c56e-49d6-a8f5-99b746260f2a": {
        "correct_answer": "C",
        "explanation_en": (
            "Money duration (also called dollar duration) is expressed in currency units, "
            "not in days or percentages. It equals modified duration x full price of the "
            "position, representing the approximate change in portfolio value per 100 basis "
            "point move in yield. For a newly issued €25 million eurocommercial paper, the "
            "money duration would be approximately €25 million — a currency figure, not 360 days."
        ),
    },

    # Total risk = variance (B)
    "847e2f24-97e8-471e-99e2-b4e37697ef99": {
        "explanation_en": (
            "Total risk and the variance of returns are identical concepts: variance (or its "
            "square root, standard deviation) measures the total dispersion of returns, "
            "capturing both systematic and unsystematic risk. Option A is wrong — systematic "
            "and firm-specific risk are opposites, not synonyms. Option C is wrong — "
            "undiversifiable risk IS systematic risk, while unsystematic risk IS diversifiable."
        ),
    },

    # CAPM beta: E[R] = 2x12%=24%; 24 = 6+b(12-6); b=3 — DB says A(2), should be B(3)
    "9310c6d4-6cd9-48c3-b28f-969a754a7c8f": {
        "correct_answer": "B",
        "explanation_en": (
            "Using CAPM: E[R] = Rf + beta x (Rm - Rf). Expected return = 2 x 12% = 24%. "
            "Solving: 24% = 6% + beta x (12% - 6%) => 18% = 6% x beta => beta = 3. "
            "Option A (2) would only produce a 18% expected return, not 24%. Beta of 3 "
            "means the asset moves 3% for every 1% market move."
        ),
    },

    # Sharpe ratio = (22-7.5)/20 = 0.725
    "5b5c7b6a-f18c-4de7-a535-4b067510d28a": {
        "explanation_en": (
            "Sharpe ratio = (Portfolio return - Risk-free rate) / Portfolio standard deviation "
            "= (22% - 7.5%) / 20% = 14.5% / 20% = 0.725. It measures excess return earned "
            "per unit of total risk. Option A (0.147) divides by the wrong denominator, and "
            "option B (0.568) makes an arithmetic error in the numerator."
        ),
    },

    # CAPM beta 2.5x: E[R]=30%; 30=6+6b; b=4
    "6d600bab-81ee-469a-bb77-bca72ec337de": {
        "explanation_en": (
            "Expected return = 2.5 x 12% = 30%. Using CAPM: 30% = 6% + beta x (12% - 6%) "
            "=> 24% = 6% x beta => beta = 4. Options B (5) and C (3) solve the CAPM equation "
            "incorrectly. A beta of 4 represents a very aggressive asset, amplifying market "
            "moves fourfold."
        ),
    },

    # Beta = systematic risk
    "342353e9-a9bc-4913-9cf8-955c4f691dae": {
        "explanation_en": (
            "Beta measures systematic (market) risk — the component of total risk that "
            "cannot be eliminated through diversification. Total risk (variance) comprises "
            "systematic plus unsystematic risk. Unsystematic (firm-specific) risk can be "
            "diversified away in a well-constructed portfolio, leaving only systematic risk, "
            "measured by beta, as the relevant risk for pricing."
        ),
    },

    # Y = 2.83 + 1.5(2) = 5.83 — DB says A (2.83), should be C (5.83)
    "a2eb181a-1340-4faa-9902-7d8af2580a2c": {
        "correct_answer": "C",
        "explanation_en": (
            "Substituting X=2 into the regression equation: Y = 2.83 + 1.5(2) = 2.83 + 3.0 "
            "= 5.83. Option A (2.83) is only the intercept, forgetting to add the slope "
            "term. Option B (-0.55) results from a sign error. The slope coefficient (1.5) "
            "is always multiplied by the value of the independent variable."
        ),
    },

    # Perpetuity price: 5000/0.07 = 71,428 ≈ 71,500 — DB says A($140K), should be B($71,500)
    "09314aa8-c74e-4ea0-ac7e-0e136d0dfdbe": {
        "correct_answer": "B",
        "explanation_en": (
            "A perpetual bond price = Annual coupon / Yield = ($100,000 x 5%) / 7% "
            "= $5,000 / 0.07 = $71,429 ≈ $71,500. Option A ($140,000) results from "
            "dividing by 3.5% (half the yield) — a common error. Option C ($98,100) "
            "applies standard bond pricing (wrongly treating the perpetuity as finite). "
            "The perpetuity formula simply capitalises the fixed coupon at the required yield."
        ),
    },

    # Pure discount ¥500M: (500/350)^(1/9) - 1 = 4.04% ≈ 4.0%
    "9acc997a-65d7-416c-b231-2f432db9cee2": {
        "explanation_en": (
            "For a pure discount (zero-coupon) instrument: Price = FV / (1+r)^n. Solving "
            "for r: (1+r)^9 = 500/350 = 1.4286, so r = (1.4286)^(1/9) - 1 = 4.04% ≈ 4.0%. "
            "Option A (3.3%) understates the yield, and option B (4.7%) overstates it. "
            "This yield represents the compound annual return from holding the instrument "
            "to maturity."
        ),
    },

    # Preferred stock return = 4.5/65 = 6.92% ≈ 6.9%
    "d5841f8c-2d67-447c-9ca2-8c3186b0214f": {
        "explanation_en": (
            "For a perpetual preferred stock: Required return = Annual dividend / Price "
            "= $4.50 / $65.00 = 6.92% ≈ 6.9%. Option B (4.5%) confuses the dividend "
            "dollar amount with the percentage return. Option C (14.4%) inverts the formula. "
            "Preferred stock behaves like a perpetuity since it pays a fixed dividend forever "
            "with no maturity date."
        ),
    },

    # Perpetuity: 87.50 / 0.125 = $700
    "8ad04338-5f10-4850-85b5-65f327f4bd77": {
        "explanation_en": (
            "Perpetuity value = Annual payment / Required return = $87.50 / 12.5% "
            "= $87.50 / 0.125 = $700. Option A ($70) is off by a factor of 10. "
            "Option C ($1,093) applies incorrect bond mathematics. The perpetuity formula "
            "requires no maturity, no par value — just the level perpetual cash flow "
            "divided by the discount rate."
        ),
    },

    # Pure discount ¥100M, 12 yrs, 3%: 100M/1.03^12 = 70.14M ≈ ¥70M
    "e29cb581-ba73-404a-874a-2b57613887d5": {
        "explanation_en": (
            "Price = FV / (1+r)^n = ¥100M / (1.03)^12 = ¥100M / 1.4258 = ¥70.14M ≈ ¥70M. "
            "Options A (¥71M) and C (¥72M) result from small errors in the discount factor. "
            "For pure discount instruments there are no coupon payments — the investor's "
            "entire return comes from the difference between purchase price and face value."
        ),
    },

    # Geometric mean: (1.104 x 1.081 x 1.032 x 1.15)^0.25 - 1 = 9.1%
    "0b07060b-9ce1-4828-9b9b-5386f9971a1f": {
        "explanation_en": (
            "Geometric (compound) mean return = [(1+R1)(1+R2)(1+R3)(1+R4)]^(1/n) - 1 "
            "= [(1.104)(1.081)(1.032)(1.15)]^0.25 - 1 = (1.4235)^0.25 - 1 = 9.1%. "
            "The geometric mean is always lower than or equal to the arithmetic mean "
            "(9.175% here) and correctly captures the effect of compounding over multiple periods."
        ),
    },

    # Justin Corp P/E: (1-b)/(k-g) = 0.40/0.05 = 8.0x — DB says B(10.0x), should be A(8.0x)
    "f3da2f17-dba9-4557-870b-394e427d22c8": {
        "correct_answer": "A",
        "explanation_en": (
            "Leading P/E = (1 - Retention Rate) / (k - g) = (1 - 0.60) / (0.10 - 0.05) "
            "= 0.40 / 0.05 = 8.0x. Option B (10.0x) uses an incorrect denominator. "
            "Option C (12.0x) applies the wrong payout ratio. This formula derives the "
            "justified P/E directly from the dividend discount model, linking valuation "
            "to growth, payout, and required return."
        ),
    },

    # Compound annual return from HPR: (2.70)^(1/20) - 1 = 5.09% — DB says A(2.69%), should be B(5.09%)
    "aad1adf9-87a4-41a4-bdc5-00b891741b19": {
        "correct_answer": "B",
        "explanation_en": (
            "Compound annual return from a holding period return: r = (1+HPR)^(1/n) - 1 "
            "= (1 + 1.70)^(1/20) - 1 = (2.70)^(0.05) - 1 = 5.09%. Option A (2.69%) "
            "incorrectly uses HPR/n (simple division). Option C (5.24%) applies an "
            "approximate formula. The compound formula properly captures the geometric "
            "growth that produced the 170% total holding period return over 20 years."
        ),
    },

    # Stop sell order
    "9825b255-48ba-4823-8f60-e0317179da25": {
        "explanation_en": (
            "A stop sell order becomes a market order when the stock price falls to or below "
            "the trigger price ($72), ensuring execution. A limit sell order at $72 would "
            "only execute at exactly $72 or above — if the price drops through $72 without "
            "a matching buyer, the order goes unfilled. A stop-limit order adds a floor price, "
            "risking non-execution in a fast-moving decline."
        ),
    },

    # Bond value using spot rates: 3/1.025 + 3/1.03^2 + 103/1.04^3 = 97.32
    "68f5ca29-b364-491e-8b78-d399c09836f8": {
        "explanation_en": (
            "Valuing a bond with spot rates discounts each cash flow at its own maturity-"
            "specific zero-coupon yield: V = 3/1.025 + 3/(1.030)^2 + 103/(1.040)^3 "
            "= 2.927 + 2.826 + 91.567 = 97.32. Spot-rate valuation is more precise than "
            "using a single YTM because each cash flow is discounted at the appropriate "
            "term structure rate."
        ),
    },

    # Leveraged return: (50-40)/(40x0.6) = 41.67% closest to C(40%)
    "fb0a8656-eb2e-43a1-903f-d86a5fc628e8": {
        "explanation_en": (
            "With 60% initial margin, the investor's equity per share = $40 x 60% = $24. "
            "Holding period return = (Selling price - Purchase price) / Equity invested "
            "= ($50 - $40) / $24 = $10 / $24 = 41.7%, closest to 40%. Leverage amplifies "
            "returns: the unlevered gain is only 25% (option B), but borrowing 40% of the "
            "purchase price magnifies the return on equity."
        ),
    },

    # Preferred stock value: 5/0.08 = $62.50
    "679a618f-e5bc-4cb1-b405-eecf2ae952c4": {
        "explanation_en": (
            "Perpetual preferred stock value = Annual dividend / Required return "
            "= $5.00 / 0.08 = $62.50. Since preferred stock pays a fixed dividend "
            "indefinitely with no maturity, it is priced as a perpetuity. Option A "
            "($60.00) is the current market price, not the intrinsic value. Option B "
            "($40.00) results from using the wrong discount rate."
        ),
    },

    # Current ratio = 1660/550 = 3.018
    "d8ae7659-3bdb-44b7-8114-5052599b84b0": {
        "explanation_en": (
            "Current ratio = Current Assets / Current Liabilities = $1,660 / $550 = 3.018 "
            "for 2004. A ratio of 3.0 indicates the company holds $3 of current assets for "
            "every $1 of current liabilities, suggesting strong short-term liquidity. "
            "Option A (0.331) inverts the formula; option B (2.018) uses incorrect figures."
        ),
    },

    # ── Kevin_Mock ────────────────────────────────────────────────────────────

    # DuPont ROE = NP Margin x Asset Turnover x Financial Leverage
    "59226802-88d4-4802-b295-94f850ee8743": {
        "explanation_en": (
            "The DuPont decomposition: ROE = Net Profit Margin x Asset Turnover x Financial "
            "Leverage (equity multiplier). This framework decomposes profitability (margin), "
            "efficiency (asset turnover), and leverage into separate, analysable drivers. "
            "Option B incorrectly substitutes 'equity turnover' for 'asset turnover.' "
            "Option C uses 'gross profit margin' and 'return on assets,' which do not "
            "constitute the standard three-factor DuPont model."
        ),
    },

    # Form 8-K for M&A disclosure
    "ac9501a0-5710-4ec9-b4c7-d2b7db301e05": {
        "explanation_en": (
            "Form 8-K (Current Report) must be filed with the SEC within 4 business days of "
            "significant corporate events including acquisitions. It provides timely public "
            "disclosure of material events. Footnotes are found in periodic filings (10-K/10-Q) "
            "and appear weeks later. Proxy statements (DEF 14A) are for shareholder voting "
            "matters such as director elections, not M&A transactions."
        ),
    },

    # IOSCO: NOT reducing unsystematic risk
    "33986486-4f16-4f67-be96-d8aa77fb21ef": {
        "explanation_en": (
            "IOSCO's three core objectives are: (1) protecting investors, (2) ensuring "
            "fair, efficient, and transparent markets, and (3) reducing systemic risk. "
            "Reducing unsystematic (firm-specific) risk is NOT an IOSCO objective — "
            "unsystematic risk is managed through diversification by investors themselves, "
            "not through regulation. IOSCO focuses on market-wide systemic risk."
        ),
    },

    # World Bank and EIB can both issue bonds
    "2d4eb637-dc52-4d13-bf34-fa7ed0b2e0c0": {
        "explanation_en": (
            "Both the World Bank (IBRD) and the European Investment Bank (EIB) are "
            "supranational institutions that actively issue bonds in international capital "
            "markets to fund development and infrastructure projects. Their bonds carry high "
            "credit ratings, backed by member-nation guarantees. Neither is restricted from "
            "issuing bonds; indeed, bond issuance is a primary funding mechanism for both."
        ),
    },

    # Country A = inefficient market
    "2184522e-d2b7-4ac9-bc67-26dc2f5c399f": {
        "explanation_en": (
            "Market efficiency requires many participants, low transaction costs, freely "
            "available information, and no artificial constraints. Country A has few "
            "participants, high costs, and a short-selling ban — all characteristics of "
            "an inefficient market. Semi-strong form efficiency requires rapid assimilation "
            "of public information; strong form requires all information (including private) "
            "to be reflected in prices. Country A meets neither condition."
        ),
    },

    # T-Bill EAY: HPY = 1.70/98.30 = 1.73%; EAY = (1.0173)^(365/70) - 1 = 9.35%
    "9b9142c1-aaee-4479-a09f-b8eca4dd15a3": {
        "explanation_en": (
            "Step 1 — Holding period yield (HPY): (100 - 98.30) / 98.30 = 1.73%. "
            "Step 2 — Effective annual yield: EAY = (1 + HPY)^(365/t) - 1 "
            "= (1.0173)^(365/70) - 1 = (1.0173)^5.214 - 1 = 9.35%. "
            "Option A (1.73%) is only the HPY, not annualised. Annualising compounds "
            "the sub-period return across a full year rather than simply multiplying."
        ),
    },

    # ── UWorld ────────────────────────────────────────────────────────────────

    # Residual plot: fan/funnel shape = heteroskedasticity
    "5a2834c1-b877-4ff4-9491-b5e2cb187932": {
        "explanation_en": (
            "A residual plot showing spread that increases (or decreases) as fitted values "
            "increase indicates heteroskedasticity — a violation of the constant-variance "
            "(homoskedasticity) assumption. A non-linear (curved) residual pattern would "
            "signal a linearity violation, while systematic clustering by time order would "
            "indicate an independence (autocorrelation) violation. Heteroskedasticity does "
            "not bias OLS coefficients but makes standard errors unreliable."
        ),
    },

    # Capital budgeting uses after-tax cash flows — DB says A(Net income), should be C
    "360b05d3-afde-463e-a3ac-cc435c30e8c4": {
        "correct_answer": "C",
        "explanation_en": (
            "Capital budgeting evaluates projects using incremental after-tax cash flows, "
            "not accounting-based measures. Net income (A) includes non-cash items like "
            "depreciation and ignores the time value of capital expenditures. Operating "
            "profit (B) is pre-tax. Only after-tax free cash flows capture the true "
            "economic costs and benefits of a project, including working capital changes "
            "and terminal cash flows."
        ),
    },
}


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}Patching {len(PATCHES)} questions...\n")

    updated = 0
    errors = 0

    for qid, patch in PATCHES.items():
        expl = patch.get("explanation_en")
        ans = patch.get("correct_answer")

        update_payload: dict = {}
        if expl:
            update_payload["explanation_en"] = expl
        if ans:
            update_payload["correct_answer"] = ans

        if not update_payload:
            continue

        action = []
        if expl:
            action.append(f"expl({len(expl)} chars)")
        if ans:
            action.append(f"answer→{ans}")
        print(f"  {qid[:8]}… {', '.join(action)}")

        if not DRY_RUN:
            try:
                sb.table("questions").update(update_payload).eq("id", qid).execute()
                updated += 1
            except Exception as e:
                print(f"    ERROR: {e}")
                errors += 1
        else:
            updated += 1

    print(f"\n{'DRY RUN — ' if DRY_RUN else ''}Done: {updated} updated, {errors} errors")


if __name__ == "__main__":
    main()
