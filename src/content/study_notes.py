"""
WIB CFA — Study Notes
Structured study notes for all 10 CFA Level 1 topics.
Each note includes key concepts, formulas, and exam tips.
"""

STUDY_NOTES = {
    "Ethics & Professional Standards": {
        "weight": "15-20%",
        "overview": (
            "Ethics is the highest-weighted topic on the CFA exam and is foundational. "
            "You must understand both the letter and spirit of the Code and Standards. "
            "The 7 Standards are grouped into categories covering professionalism, "
            "capital markets integrity, duties to clients and employers, investment practice, "
            "and responsibilities as a CFA member."
        ),
        "sections": [
            {
                "title": "Code of Ethics — 6 Components",
                "content": (
                    "1. Act with integrity, competence, diligence, respect, and in an ethical manner.\n"
                    "2. Place the integrity of the investment profession and clients' interests above personal interests.\n"
                    "3. Use reasonable care and exercise independent professional judgment.\n"
                    "4. Practice and encourage others to practice in a professional and ethical manner.\n"
                    "5. Promote the integrity and viability of global capital markets for the benefit of society.\n"
                    "6. Maintain and improve professional competence and strive to maintain competence of others."
                ),
            },
            {
                "title": "Standard I — Professionalism",
                "content": (
                    "I(A) Knowledge of the Law: Know and comply with all applicable laws. In conflicts, follow the stricter rule. "
                    "Dissociate from and report violations.\n\n"
                    "I(B) Independence and Objectivity: Do not accept gifts/benefits that compromise objectivity. "
                    "Modest gifts permitted. Travel paid by issuers requires heightened scrutiny.\n\n"
                    "I(C) Misrepresentation: No false statements about qualifications, services, or performance. "
                    "Plagiarism is prohibited.\n\n"
                    "I(D) Misconduct: No acts involving dishonesty, fraud, or deceit."
                ),
            },
            {
                "title": "Standard II — Integrity of Capital Markets",
                "content": (
                    "II(A) Material Nonpublic Information (MNPI): Cannot trade or cause others to trade on MNPI. "
                    "Material = affects reasonable investor's decision. "
                    "Mosaic theory: combining non-material public + non-material nonpublic info is OK.\n\n"
                    "II(B) Market Manipulation: Prohibited. Includes actions that create false price impressions "
                    "or deceptive trading volume."
                ),
            },
            {
                "title": "Standards III–VII Summary",
                "content": (
                    "III(A) Loyalty, Prudence, Care: Act for benefit of clients; place client interests first.\n"
                    "III(B) Fair Dealing: Treat all clients fairly; simultaneous dissemination of recommendations.\n"
                    "III(C) Suitability: Assess client risk/return profile; suitable in context of total portfolio.\n"
                    "III(D) Performance Presentation: No misrepresentation of performance records.\n"
                    "III(E) Preservation of Confidentiality: Keep client info confidential.\n\n"
                    "IV(A) Loyalty to Employer: Act in employer's interest; no misuse of employer resources.\n"
                    "IV(B) Additional Compensation Arrangements: Disclose to employer any outside compensation.\n"
                    "IV(C) Responsibilities of Supervisors: Prevent subordinates from violating Standards.\n\n"
                    "V(A) Diligence and Reasonable Basis: Thorough research backing all recommendations.\n"
                    "V(B) Communication: Distinguish fact from opinion; disclose investment process.\n"
                    "V(C) Record Retention: Maintain records supporting analysis (7 years recommended).\n\n"
                    "VI(A) Disclosure of Conflicts: Disclose all material conflicts to clients and employers.\n"
                    "VI(B) Priority of Transactions: Client transactions before employer/personal.\n"
                    "VI(C) Referral Fees: Disclose any compensation for client referrals.\n\n"
                    "VII(A) CFA Institute Conduct: Cooperate with CFA Institute investigations.\n"
                    "VII(B) Reference to CFA: Use CFA designation correctly as an adjective, not a noun."
                ),
            },
        ],
        "exam_tips": [
            "Always choose the most conservative option that serves clients first.",
            "Mosaic theory is the key to II(A) — combining public info is allowed.",
            "When uncertain: dissociate, report internally, and document everything.",
            "GIPS compliance is firm-wide, not individual.",
            "Performance fees, referral fees, and gifts must always be disclosed.",
        ],
    },

    "Quantitative Methods": {
        "weight": "8-12%",
        "overview": (
            "Quantitative Methods provides the mathematical and statistical toolkit used throughout the CFA curriculum. "
            "Key areas: time value of money, statistics, probability distributions, hypothesis testing, and regression."
        ),
        "sections": [
            {
                "title": "Time Value of Money",
                "content": (
                    "Key relationships:\n"
                    "• FV = PV × (1 + r)^n\n"
                    "• PV = FV / (1 + r)^n\n"
                    "• Annuity PV = PMT × [1 - (1+r)^-n] / r\n"
                    "• Perpetuity PV = PMT / r\n"
                    "• EAR = (1 + r/m)^m - 1\n\n"
                    "Continuous compounding: FV = PV × e^(rT)\n"
                    "Annuity due vs ordinary annuity: annuity due payments at start of period (multiply by 1+r)."
                ),
            },
            {
                "title": "Descriptive Statistics",
                "content": (
                    "Measures of central tendency: mean, median, mode.\n"
                    "Dispersion: variance (σ²), standard deviation (σ), range, MAD.\n\n"
                    "Skewness:\n"
                    "• Positive skew: Mean > Median > Mode (long right tail)\n"
                    "• Negative skew: Mean < Median < Mode (long left tail)\n\n"
                    "Kurtosis: excess kurtosis = kurtosis - 3.\n"
                    "• Leptokurtic (> 0): fat tails, peaked. More extreme outliers.\n"
                    "• Platykurtic (< 0): thin tails, flat.\n\n"
                    "Coefficient of Variation (CV) = σ / mean. Risk per unit of return.\n"
                    "Sharpe Ratio = (Rp - Rf) / σp. Return per unit of total risk."
                ),
            },
            {
                "title": "Probability & Distributions",
                "content": (
                    "Rules: P(A or B) = P(A) + P(B) - P(A and B)\n"
                    "Conditional: P(A|B) = P(A and B) / P(B)\n"
                    "Bayes' Theorem: P(A|B) = P(B|A) × P(A) / P(B)\n\n"
                    "Normal Distribution:\n"
                    "• Symmetric, mean = median = mode\n"
                    "• 68% within ±1σ, 95% within ±2σ, 99% within ±3σ\n"
                    "• Z = (X - μ) / σ\n\n"
                    "Student's t-distribution: used when population variance unknown; heavier tails than normal.\n"
                    "Lognormal: asset prices are lognormally distributed (cannot go below zero)."
                ),
            },
            {
                "title": "Hypothesis Testing",
                "content": (
                    "Steps: State hypotheses → select test statistic → determine critical value → calculate test statistic → decide.\n\n"
                    "Type I Error (α): reject TRUE H₀ (false positive)\n"
                    "Type II Error (β): fail to reject FALSE H₀ (false negative)\n"
                    "Power = 1 - β\n\n"
                    "Common tests:\n"
                    "• z-test: known population variance or large sample (n > 30)\n"
                    "• t-test: unknown variance, small sample\n"
                    "• F-test: comparing two variances\n"
                    "• Chi-square: testing variance of a single population\n\n"
                    "p-value < significance level → reject H₀."
                ),
            },
            {
                "title": "Regression Analysis",
                "content": (
                    "Simple linear regression: Yi = b₀ + b₁Xi + εi\n"
                    "b₁ = Cov(X,Y) / Var(X)\n"
                    "R² = SSR/SST = proportion of Y variance explained by X\n\n"
                    "Multiple regression: assumes no perfect multicollinearity.\n"
                    "Violations to know:\n"
                    "• Heteroskedasticity: non-constant error variance\n"
                    "• Serial correlation: correlated residuals over time\n"
                    "• Multicollinearity: high correlation between predictors\n\n"
                    "F-statistic tests overall regression significance.\n"
                    "t-statistic tests individual coefficient significance."
                ),
            },
        ],
        "exam_tips": [
            "Know TVM on your calculator cold — this saves time on every topic.",
            "EAR is always higher than the stated rate for m > 1 compounding periods.",
            "Positive skew: mean > median > mode (right tail pulls mean up).",
            "Type I error = false positive = significance level (α).",
            "R² alone does not confirm model validity — check for violations.",
        ],
    },

    "Economics": {
        "weight": "8-12%",
        "overview": (
            "Economics covers micro and macroeconomics relevant to investment analysis. "
            "Key areas: supply/demand, firm behavior, business cycles, fiscal/monetary policy, "
            "international trade, and foreign exchange."
        ),
        "sections": [
            {
                "title": "Demand, Supply & Market Equilibrium",
                "content": (
                    "Law of Demand: inverse price-quantity relationship (ceteris paribus).\n"
                    "Law of Supply: direct price-quantity relationship.\n"
                    "Equilibrium: quantity demanded = quantity supplied.\n\n"
                    "Price elasticity of demand (PED) = %ΔQd / %ΔP\n"
                    "• |PED| > 1: elastic (luxury goods)\n"
                    "• |PED| < 1: inelastic (necessities)\n"
                    "• |PED| = 1: unit elastic\n\n"
                    "Consumer surplus = area above price, below demand curve.\n"
                    "Producer surplus = area below price, above supply curve."
                ),
            },
            {
                "title": "Market Structures",
                "content": (
                    "Perfect Competition: many sellers, homogeneous product, free entry.\n"
                    "→ P = MR = MC in long run; zero economic profit.\n\n"
                    "Monopolistic Competition: differentiated products, free entry.\n"
                    "→ Short-run profit possible; zero economic profit in long run.\n\n"
                    "Oligopoly: few large firms, interdependent pricing.\n"
                    "→ Nash equilibrium, Cournot/Stackelberg models.\n\n"
                    "Monopoly: single seller, barriers to entry.\n"
                    "→ MR < P; MR = MC for profit maximization; deadweight loss.\n\n"
                    "Natural Monopoly: declining LRATC; utilities, infrastructure."
                ),
            },
            {
                "title": "GDP and Business Cycles",
                "content": (
                    "GDP Expenditure: Y = C + I + G + (X - M)\n"
                    "GDP Income: wages + rent + interest + profit\n"
                    "GDP Production: sum of value added\n\n"
                    "Nominal GDP: current prices. Real GDP: constant base year prices.\n"
                    "GDP Deflator = (Nominal GDP / Real GDP) × 100\n\n"
                    "Business Cycle Phases: expansion → peak → contraction → trough\n\n"
                    "Leading indicators: stock prices, building permits, credit spreads\n"
                    "Lagging indicators: unemployment rate, CPI, commercial loans\n"
                    "Coincident: industrial production, personal income"
                ),
            },
            {
                "title": "Monetary and Fiscal Policy",
                "content": (
                    "Monetary Policy Tools:\n"
                    "1. Open Market Operations (primary tool): buy = expansionary, sell = contractionary\n"
                    "2. Policy Rate (Fed funds rate/ECB rate)\n"
                    "3. Reserve Requirements\n"
                    "4. Quantitative Easing (QE): large-scale asset purchases at ZLB\n\n"
                    "Fiscal Policy:\n"
                    "Expansionary: increase G or cut taxes → increase AD\n"
                    "Contractionary: decrease G or raise taxes → decrease AD\n"
                    "Fiscal Multiplier = 1 / (1 - MPC)\n\n"
                    "Crowding out: government borrowing raises interest rates, reducing private investment."
                ),
            },
            {
                "title": "International Trade & FX",
                "content": (
                    "Absolute Advantage: produces more of a good with same resources.\n"
                    "Comparative Advantage: produces at lower opportunity cost. Basis for trade.\n\n"
                    "FX Conventions: Price / Base currency (e.g., USD/EUR = 1.08 means $1.08 per €1)\n"
                    "Appreciation of base currency → higher exchange rate number.\n\n"
                    "Purchasing Power Parity (PPP):\n"
                    "Absolute: identical goods same price in all countries after FX.\n"
                    "Relative: %ΔS ≈ inflation_domestic - inflation_foreign\n\n"
                    "Interest Rate Parity (IRP): covered IRP → no arbitrage via FX forwards.\n"
                    "Forward rate premium: higher-yielding currency trades at forward discount.\n\n"
                    "J-Curve: trade balance worsens then improves after currency depreciation."
                ),
            },
        ],
        "exam_tips": [
            "Perfect competition: P = MR = MC = minimum LRATC in long-run equilibrium.",
            "Open market PURCHASE = expansionary = money supply up = rates down.",
            "GDP expenditure: memorize C + I + G + (X - M).",
            "PPP: high-inflation currency depreciates over time.",
            "J-curve: depreciation worsens trade balance short-term before improving.",
        ],
    },

    "Financial Statement Analysis": {
        "weight": "13-17%",
        "overview": (
            "FSA is one of the highest-weighted topics. It covers the mechanics and interpretation of "
            "financial statements (income statement, balance sheet, cash flow statement), "
            "key ratios, quality of earnings, and IFRS vs US GAAP differences."
        ),
        "sections": [
            {
                "title": "Income Statement",
                "content": (
                    "Revenue recognition (IFRS 15 / ASC 606): 5-step model.\n"
                    "1. Identify contract. 2. Identify performance obligations. 3. Determine transaction price.\n"
                    "4. Allocate price to obligations. 5. Recognize when/as obligation satisfied.\n\n"
                    "Gross Profit = Revenue - COGS\n"
                    "Operating Income (EBIT) = Gross Profit - SG&A - D&A\n"
                    "EBT = EBIT - Interest Expense\n"
                    "Net Income = EBT × (1 - Tax Rate)\n\n"
                    "EPS (basic) = (Net Income - Preferred Dividends) / Weighted Avg Shares\n"
                    "Diluted EPS: includes dilutive options/convertibles."
                ),
            },
            {
                "title": "Balance Sheet",
                "content": (
                    "Assets = Liabilities + Equity\n\n"
                    "Key items:\n"
                    "Current assets: cash, AR, inventory, prepaid\n"
                    "Non-current: PP&E, goodwill, intangibles, LT investments\n\n"
                    "Goodwill = Purchase Price - Fair Value of Net Identifiable Assets\n"
                    "Under IFRS: goodwill impairment only (no amortization)\n"
                    "Under US GAAP: goodwill impairment only (no amortization)\n\n"
                    "Inventory methods (rising prices):\n"
                    "FIFO: higher NI, higher ending inventory, higher taxes\n"
                    "LIFO: lower NI, lower ending inventory, lower taxes (US GAAP only)\n"
                    "LIFO Reserve = FIFO Inventory - LIFO Inventory"
                ),
            },
            {
                "title": "Cash Flow Statement",
                "content": (
                    "Three sections:\n"
                    "Operating (CFO): cash from core business operations.\n"
                    "Investing (CFI): purchases/sales of long-term assets.\n"
                    "Financing (CFF): debt/equity issuance, repurchases, dividends.\n\n"
                    "Indirect method (CFO): Start with Net Income, adjust for:\n"
                    "+ Non-cash charges (D&A, impairment)\n"
                    "+ Changes in working capital:\n"
                    "  ↑ AR → subtract (not yet collected)\n"
                    "  ↑ Inventory → subtract (used cash)\n"
                    "  ↑ AP → add (received benefit, not yet paid)\n\n"
                    "IFRS vs US GAAP (cash flow classification):\n"
                    "Interest received: CFO (IFRS) or CFO (GAAP)\n"
                    "Interest paid: CFO or CFF (IFRS); always CFO (GAAP)\n"
                    "Dividends received: CFO or CFI (IFRS); CFO (GAAP)\n"
                    "Dividends paid: CFO or CFF (IFRS); CFF (GAAP)"
                ),
            },
            {
                "title": "Financial Ratios",
                "content": (
                    "LIQUIDITY:\n"
                    "Current Ratio = CA / CL\n"
                    "Quick Ratio = (Cash + Marketable Sec + Receivables) / CL\n"
                    "Cash Ratio = (Cash + Marketable Sec) / CL\n\n"
                    "SOLVENCY:\n"
                    "D/E = Total Debt / Total Equity\n"
                    "Interest Coverage = EBIT / Interest Expense\n"
                    "Debt/Assets = Total Debt / Total Assets\n\n"
                    "PROFITABILITY:\n"
                    "Gross Margin = Gross Profit / Revenue\n"
                    "Operating Margin = EBIT / Revenue\n"
                    "Net Margin = Net Income / Revenue\n"
                    "ROA = Net Income / Average Total Assets\n"
                    "ROE = Net Income / Average Equity\n\n"
                    "EFFICIENCY:\n"
                    "Asset Turnover = Revenue / Average Total Assets\n"
                    "Receivables Turnover = Revenue / Average AR\n"
                    "DSO = 365 / Receivables Turnover\n"
                    "Inventory Turnover = COGS / Average Inventory\n"
                    "DIO = 365 / Inventory Turnover\n\n"
                    "DuPont (3-factor): ROE = Net Margin × Asset Turnover × Equity Multiplier"
                ),
            },
        ],
        "exam_tips": [
            "LIFO only under US GAAP. IFRS requires FIFO or weighted average.",
            "Rising prices: FIFO → higher NI, higher inventory, higher taxes.",
            "Indirect CFO: add back D&A, adjust WC changes carefully.",
            "DuPont: ROE = Margin × Turnover × Leverage — identify which driver improved ROE.",
            "Operating CF > Net Income over time indicates high earnings quality.",
        ],
    },

    "Corporate Issuers": {
        "weight": "8-10%",
        "overview": (
            "Corporate Issuers covers capital structure decisions, cost of capital, capital budgeting, "
            "working capital management, dividends, and corporate governance."
        ),
        "sections": [
            {
                "title": "Capital Structure Theory",
                "content": (
                    "Modigliani-Miller (no taxes): firm value independent of capital structure.\n"
                    "MM with taxes: VL = VU + T×D (debt adds value via interest tax shield).\n"
                    "Trade-off theory: balance tax shield vs. distress costs.\n"
                    "Optimal D/E where WACC is minimized and firm value is maximized.\n\n"
                    "Pecking Order Theory: firms prefer internal funds, then debt, then equity.\n"
                    "Signaling: equity issuance signals stock may be overvalued."
                ),
            },
            {
                "title": "WACC and Cost of Capital",
                "content": (
                    "WACC = (E/V)×Re + (D/V)×Rd×(1-T)\n\n"
                    "Cost of Equity — CAPM: Re = Rf + β × (Rm - Rf)\n"
                    "Cost of Equity — DDM: Re = D1/P0 + g\n\n"
                    "Cost of Debt = YTM × (1 - Tax Rate)\n\n"
                    "WACC is appropriate discount rate when project risk = firm risk.\n"
                    "For different risk projects, use adjusted hurdle rate."
                ),
            },
            {
                "title": "Capital Budgeting",
                "content": (
                    "NPV = Σ CFt/(1+r)^t - CF0. Accept if NPV > 0.\n"
                    "IRR: rate where NPV=0. Accept if IRR > required return.\n"
                    "Payback Period: time to recover initial investment. Simple but ignores TVM.\n"
                    "Discounted Payback: uses discounted cash flows.\n\n"
                    "Relevant cash flows:\n"
                    "✓ Incremental operating cash flows\n"
                    "✓ Cannibalization effects\n"
                    "✓ Opportunity costs\n"
                    "✓ Terminal value and salvage\n"
                    "✗ Sunk costs (irrelevant)\n"
                    "✗ Financing costs (captured in WACC)\n\n"
                    "NPV vs IRR conflict: use NPV (reinvestment rate assumption is more realistic)."
                ),
            },
            {
                "title": "Dividends and Share Repurchases",
                "content": (
                    "Dividend types: cash dividend, stock dividend, stock split.\n"
                    "Regular cash dividends signal financial stability.\n"
                    "Special dividend: one-time, non-recurring.\n\n"
                    "Share repurchases:\n"
                    "• Same economic impact as cash dividend (MM dividend irrelevance)\n"
                    "• May signal shares are undervalued\n"
                    "• Reduces shares outstanding → increases EPS\n"
                    "• More tax-efficient in jurisdictions where cap gains < dividend tax\n\n"
                    "Dividend payout ratio = DPS / EPS\n"
                    "Retention ratio (plowback) = 1 - payout ratio\n"
                    "Sustainable growth rate = ROE × Retention Ratio"
                ),
            },
            {
                "title": "Corporate Governance",
                "content": (
                    "Agency problem: managers (agents) may not act in shareholders' (principals') best interests.\n\n"
                    "Governance mechanisms:\n"
                    "• Independent board of directors\n"
                    "• Executive compensation aligned with shareholder value\n"
                    "• Shareholder voting rights\n"
                    "• Audit committees and external auditors\n"
                    "• Hostile takeover threat\n\n"
                    "Stakeholder theory: firms should consider all stakeholders (employees, creditors, community).\n"
                    "Shareholder primacy: maximize shareholder value above all."
                ),
            },
        ],
        "exam_tips": [
            "Sunk costs are always irrelevant to investment decisions.",
            "When NPV and IRR give conflicting accept/reject signals, use NPV.",
            "Interest tax shield = D × Rd × T. This is the benefit of debt in MM with taxes.",
            "Dividend irrelevance holds in perfect markets; taxes and signaling make it relevant.",
            "Sustainable growth = ROE × (1 - payout ratio).",
        ],
    },

    "Equity Investments": {
        "weight": "10-12%",
        "overview": (
            "Equity Investments covers the structure of equity markets, equity valuation models, "
            "industry analysis, and market efficiency. Key valuation models: DDM, FCFE, and relative valuation."
        ),
        "sections": [
            {
                "title": "Equity Market Structure",
                "content": (
                    "Primary market: issuance of new securities (IPOs, follow-on offerings).\n"
                    "Secondary market: trading of existing securities between investors.\n\n"
                    "Market types: quote-driven (dealer market), order-driven (auction market), brokered market.\n"
                    "Order types: market order, limit order, stop-loss order.\n\n"
                    "Short selling: borrow shares → sell → repurchase to close.\n"
                    "Short seller profits when price falls.\n"
                    "Margin account: borrowed funds used to purchase securities."
                ),
            },
            {
                "title": "Equity Valuation — Dividend Discount Models",
                "content": (
                    "Gordon Growth Model (GGM): V = D1 / (r - g)\n"
                    "Requires: r > g. Best for stable, mature dividend-paying firms.\n\n"
                    "Multistage DDM: explicit growth phase + terminal GGM value.\n"
                    "V = Σ [Dt/(1+r)^t] + [Dn+1/(r-gL)] / (1+r)^n\n\n"
                    "FCFE (Free Cash Flow to Equity):\n"
                    "FCFE = Net Income - (1-δ) × (FCInv - Dep) - (1-δ) × ΔWC\n"
                    "Where δ = debt financing ratio\n\n"
                    "Justified P/E = Payout Ratio / (r - g)"
                ),
            },
            {
                "title": "Relative Valuation Multiples",
                "content": (
                    "P/E (Price-to-Earnings):\n"
                    "Trailing P/E = Price / EPS_LTM\n"
                    "Forward P/E = Price / EPS_NTM\n"
                    "Limitation: EPS can be negative; affected by accounting choices.\n\n"
                    "P/B (Price-to-Book): Price / Book Value per share\n"
                    "Useful for financials, asset-heavy firms.\n\n"
                    "P/S (Price-to-Sales): Price / Revenue per share\n"
                    "Useful when earnings are negative.\n\n"
                    "EV/EBITDA: Enterprise Value / EBITDA\n"
                    "Capital structure-neutral; useful for leveraged companies.\n\n"
                    "EV = Market Cap + Total Debt + Preferred - Cash"
                ),
            },
            {
                "title": "Efficient Market Hypothesis (EMH)",
                "content": (
                    "Weak Form: prices reflect ALL historical price/volume data.\n"
                    "→ Technical analysis cannot generate consistent excess returns.\n\n"
                    "Semi-strong Form: prices reflect ALL public information.\n"
                    "→ Fundamental analysis cannot generate consistent excess returns.\n\n"
                    "Strong Form: prices reflect ALL information (public and private).\n"
                    "→ Even insider information provides no advantage.\n\n"
                    "Market Anomalies (challenge EMH):\n"
                    "• Size effect (small cap premium)\n"
                    "• Value effect (low P/B outperforms)\n"
                    "• Momentum effect\n"
                    "• Calendar effects (January effect)"
                ),
            },
        ],
        "exam_tips": [
            "GGM: V = D1/(r-g). D1 is next year's dividend, NOT the current one.",
            "EV = Market Cap + Net Debt (total debt - cash). EV is capital-structure neutral.",
            "P/S ratio useful when earnings are negative; used for early-stage firms.",
            "Semi-strong EMH: stock prices already incorporate all public info, including earnings releases.",
            "EMH anomalies are well-documented but may reflect risk premiums, not market inefficiency.",
        ],
    },

    "Fixed Income": {
        "weight": "10-12%",
        "overview": (
            "Fixed Income is heavily quantitative and formula-intensive. "
            "Key areas: bond pricing, yield measures, term structure of interest rates, "
            "duration and convexity, credit analysis, and structured products (MBS, ABS)."
        ),
        "sections": [
            {
                "title": "Bond Basics & Pricing",
                "content": (
                    "Bond Price = PV of coupons + PV of par value\n"
                    "P = Σ [C/(1+y)^t] + [FV/(1+y)^n]\n\n"
                    "Price rules:\n"
                    "YTM = coupon rate → P = par\n"
                    "YTM > coupon rate → P < par (discount)\n"
                    "YTM < coupon rate → P > par (premium)\n\n"
                    "As bonds approach maturity, price approaches par (pull-to-par).\n\n"
                    "Accrued Interest: buyer pays seller accrued interest since last coupon.\n"
                    "Dirty Price = Clean Price + Accrued Interest"
                ),
            },
            {
                "title": "Yield Measures",
                "content": (
                    "YTM: IRR of all cash flows at current market price.\n"
                    "Assumes: held to maturity, all coupons reinvested at YTM.\n\n"
                    "Current Yield = Annual Coupon / Price\n"
                    "YTC (Yield to Call): IRR using call date and call price.\n"
                    "YTW (Yield to Worst): minimum of YTM, YTC.\n\n"
                    "Spread Measures:\n"
                    "G-spread: yield over government bond yield (same maturity)\n"
                    "I-spread: yield over swap rate\n"
                    "Z-spread: constant spread over entire spot curve\n"
                    "OAS = Z-spread - Option Value (removes effect of embedded option)"
                ),
            },
            {
                "title": "Duration and Convexity",
                "content": (
                    "Macaulay Duration: weighted average time to receive cash flows (in years).\n"
                    "Modified Duration = Macaulay Duration / (1 + y/m)\n"
                    "→ % price change ≈ -MD × Δy\n\n"
                    "Properties:\n"
                    "• Zero-coupon bond: duration = maturity\n"
                    "• Higher coupon → lower duration\n"
                    "• Higher yield → lower duration\n"
                    "• Longer maturity → higher duration (for coupon bonds)\n\n"
                    "Convexity: measures curvature of price-yield relationship.\n"
                    "%ΔP ≈ -MD×Δy + ½×Convexity×(Δy)²\n\n"
                    "Positive convexity: good for investors (more upside gain, less downside loss).\n"
                    "Callable bonds have negative convexity at low yields (price compression).\n\n"
                    "Dollar Duration (DV01) = Modified Duration × Price / 10,000\n"
                    "→ dollar price change for 1bp change in yield"
                ),
            },
            {
                "title": "Term Structure of Interest Rates",
                "content": (
                    "Spot rate (zero rate): yield on zero-coupon bond of that maturity.\n"
                    "Forward rate: implied future short-term rate.\n"
                    "(1+s2)² = (1+s1) × (1+f(1,2))\n\n"
                    "Theories:\n"
                    "Pure Expectations: long rates = geometric avg of expected short rates.\n"
                    "Liquidity Preference: long rates include a liquidity premium → upward bias.\n"
                    "Market Segmentation: supply/demand in specific maturity segments.\n"
                    "Preferred Habitat: extensions of market segmentation; investors will move for sufficient premium.\n\n"
                    "Bootstrapping: derive spot rates from par bond prices.\n"
                    "Par curve, spot curve, forward curve — all interconnected."
                ),
            },
            {
                "title": "Credit Analysis & Structured Products",
                "content": (
                    "Credit Risk = Default Probability × Loss Given Default (LGD)\n"
                    "LGD = 1 - Recovery Rate\n\n"
                    "4 Cs of Credit (corporate):\n"
                    "Capacity (ability to repay), Collateral, Covenants, Character.\n\n"
                    "Rating agencies: Moody's, S&P, Fitch.\n"
                    "Investment grade: Baa3/BBB- and above.\n"
                    "High yield (junk): Ba1/BB+ and below.\n\n"
                    "MBS: pools of residential mortgages.\n"
                    "Prepayment risk: borrowers refinance when rates fall (extension risk when rates rise).\n"
                    "Sequential-pay vs PAC tranches.\n\n"
                    "ABS: backed by auto loans, credit cards, student loans.\n"
                    "CDO: structured security backed by pool of fixed income assets."
                ),
            },
        ],
        "exam_tips": [
            "Duration: remember the inverse relationship with coupon rate and yield.",
            "YTM assumes all coupons reinvested at the YTM rate.",
            "Callable bonds: lower convexity (negative at low yields) because price is capped at call price.",
            "Z-spread > G-spread for the same bond because it uses the full spot curve.",
            "Prepayment risk in MBS: when rates fall, borrowers prepay → extension risk when rates rise.",
        ],
    },

    "Derivatives": {
        "weight": "5-8%",
        "overview": (
            "Derivatives covers options, futures, forwards, and swaps. "
            "Key concepts: option pricing, put-call parity, payoff diagrams, hedging strategies, "
            "and no-arbitrage pricing."
        ),
        "sections": [
            {
                "title": "Options Fundamentals",
                "content": (
                    "Call option: right (not obligation) to BUY at strike price K.\n"
                    "Put option: right (not obligation) to SELL at strike price K.\n\n"
                    "Payoff at expiration:\n"
                    "Long call: max(S-K, 0)\n"
                    "Long put: max(K-S, 0)\n"
                    "Short call: -max(S-K, 0)\n"
                    "Short put: -max(K-S, 0)\n\n"
                    "In-the-money: call when S > K; put when S < K\n"
                    "At-the-money: S = K\n"
                    "Out-of-the-money: call when S < K; put when S > K\n\n"
                    "Time value = Option premium - Intrinsic value\n"
                    "Intrinsic value = payoff if exercised immediately (floor at 0)"
                ),
            },
            {
                "title": "Put-Call Parity",
                "content": (
                    "For European options on non-dividend-paying stocks:\n"
                    "C + PV(K) = P + S\n"
                    "Or: P = C + PV(K) - S\n"
                    "Or: C = P + S - PV(K)\n\n"
                    "Applications:\n"
                    "• Synthetic call = long put + long stock + short bond\n"
                    "• Synthetic put = long call + short stock + long bond\n"
                    "• Covered call = long stock + short call ≡ short put + long bond\n"
                    "• Protective put = long stock + long put ≡ long call + long bond\n\n"
                    "Note: Put-call parity does NOT hold for American options."
                ),
            },
            {
                "title": "Black-Scholes and Option Pricing",
                "content": (
                    "Inputs: S (spot), K (strike), T (time), r (risk-free rate), σ (volatility)\n\n"
                    "Effect of each input on CALL value:\n"
                    "S↑ → C↑ (delta positive)\n"
                    "K↑ → C↓\n"
                    "T↑ → C↑ (more time value)\n"
                    "r↑ → C↑ (PV of strike lower)\n"
                    "σ↑ → C↑ (vega positive)\n\n"
                    "Option Greeks:\n"
                    "Delta: dC/dS. Call delta: 0 to +1. Put delta: -1 to 0.\n"
                    "Gamma: rate of delta change. Maximum at ATM.\n"
                    "Theta: time decay (negative for long options).\n"
                    "Vega: sensitivity to σ. Positive for both calls and puts.\n"
                    "Rho: sensitivity to interest rate."
                ),
            },
            {
                "title": "Futures, Forwards, and Swaps",
                "content": (
                    "Forward vs Futures:\n"
                    "Forwards: OTC, customized, settled at maturity, credit risk.\n"
                    "Futures: exchange-traded, standardized, mark-to-market daily, clearinghouse.\n\n"
                    "Forward price (no dividends): F = S × (1+r)^T or F = S × e^(rT)\n"
                    "With dividend yield q: F = S × e^(r-q)T\n"
                    "With convenience yield y and storage costs u: F = S × e^(r+u-y)T\n\n"
                    "Interest Rate Swap (plain vanilla):\n"
                    "Fixed-rate payer: pays fixed, receives floating.\n"
                    "Benefits from rising rates (floating receipts increase).\n"
                    "Swap = long floating bond + short fixed bond (for fixed-rate payer)\n\n"
                    "Currency Swap: exchange cash flows in different currencies.\n"
                    "Total Return Swap: one party receives total return; other pays fixed rate."
                ),
            },
        ],
        "exam_tips": [
            "Long call + long put = long straddle (profit from high volatility).",
            "Short call + short put = short straddle (profit from low volatility).",
            "Futures differ from forwards: exchange-traded, standardized, marked to market daily.",
            "Vega > 0 for both calls and puts — higher volatility always increases option value.",
            "Fixed-rate swap payer benefits when floating rates rise (receives more, pays same).",
        ],
    },

    "Alternative Investments": {
        "weight": "5-8%",
        "overview": (
            "Alternative Investments covers private equity, hedge funds, real estate, commodities, "
            "and infrastructure. These investments offer diversification and typically have lower liquidity "
            "and less transparency than traditional assets."
        ),
        "sections": [
            {
                "title": "Private Equity",
                "content": (
                    "Stages: Venture Capital (early stage) → Growth equity → LBO (mature company)\n\n"
                    "LBO structure: acquire company with large debt (60-80%); "
                    "target IRR 20-25%; exit via IPO or strategic sale.\n\n"
                    "Key PE metrics:\n"
                    "IRR: time-weighted internal rate of return on capital flows.\n"
                    "TVPI = (Distributions + Residual Value) / Paid-In Capital\n"
                    "DPI = Cumulative Distributions / Paid-In Capital (realized multiple)\n"
                    "RVPI = Residual Value / Paid-In Capital (unrealized multiple)\n\n"
                    "J-curve effect: PE funds show negative returns early (fees + no exits), "
                    "then positive as investments mature and are exited."
                ),
            },
            {
                "title": "Hedge Funds",
                "content": (
                    "Fee structure: '2 and 20' = 2% management + 20% performance fee.\n"
                    "High-water mark: performance fees only on new profits above prior peak.\n"
                    "Hurdle rate: minimum return before performance fees apply.\n\n"
                    "Major strategies:\n"
                    "L/S Equity: long undervalued + short overvalued stocks.\n"
                    "Global Macro: directional bets on macro themes (FX, rates, commodities).\n"
                    "Market Neutral: zero market beta, pure alpha.\n"
                    "Event-Driven: M&A arbitrage, distressed debt.\n"
                    "Convertible Arbitrage: exploit mispricing in convertible bonds.\n"
                    "Managed Futures (CTA): systematic trend-following.\n\n"
                    "Biases in hedge fund databases:\n"
                    "Survivorship bias → overstates returns (failed funds excluded).\n"
                    "Backfill bias → fund adds historical track record when joining database."
                ),
            },
            {
                "title": "Real Estate",
                "content": (
                    "Direct investment: residential/commercial property, mortgage lending.\n"
                    "Indirect investment: REITs, real estate limited partnerships.\n\n"
                    "REIT: exchange-traded company owning income-producing real estate.\n"
                    "Must distribute 90%+ of taxable income as dividends (US).\n"
                    "Equity REIT: owns properties. Mortgage REIT: owns mortgages/MBS.\n\n"
                    "Valuation metrics:\n"
                    "Cap Rate = NOI / Property Value\n"
                    "Value = NOI / Cap Rate\n"
                    "P/FFO: Price / Funds From Operations (REIT equivalent of P/E)\n"
                    "FFO = Net Income + D&A - Gains on property sales"
                ),
            },
            {
                "title": "Commodities and Infrastructure",
                "content": (
                    "Commodity futures total return = Spot return + Roll return + Collateral return\n\n"
                    "Contango: futures price > spot (normal). Rolling contracts at a loss.\n"
                    "Backwardation: futures price < spot. Rolling contracts at a gain.\n"
                    "Convenience yield: benefit of holding physical commodity.\n\n"
                    "Infrastructure characteristics:\n"
                    "• Long-lived assets (30-50+ years)\n"
                    "• Stable, predictable cash flows (often inflation-linked)\n"
                    "• Monopolistic or oligopolistic markets\n"
                    "• High capital intensity, low variable costs\n"
                    "• Low correlation with equity markets (diversification benefit)\n\n"
                    "Categories: transport (roads, airports), utilities, social (hospitals, schools), energy."
                ),
            },
        ],
        "exam_tips": [
            "Survivorship bias overstates hedge fund performance (failed funds removed from databases).",
            "PE J-curve: early years show negative returns; improve as portfolio matures.",
            "Backwardation: futures < spot → positive roll return from rolling contracts.",
            "REIT must distribute 90%+ of taxable income; taxed like regular equities.",
            "Infrastructure: stable cash flows, inflation-linked, monopolistic — low correlation with equities.",
        ],
    },

    "Portfolio Management": {
        "weight": "5-8%",
        "overview": (
            "Portfolio Management covers modern portfolio theory (MPT), CAPM, efficient frontiers, "
            "risk-return tradeoffs, portfolio construction, and performance evaluation."
        ),
        "sections": [
            {
                "title": "Modern Portfolio Theory (MPT)",
                "content": (
                    "Diversification reduces unsystematic risk (not systematic/market risk).\n\n"
                    "Portfolio Variance (2 assets):\n"
                    "σ²p = w₁²σ₁² + w₂²σ₂² + 2w₁w₂ρ₁₂σ₁σ₂\n\n"
                    "Minimum variance portfolio (2 assets):\n"
                    "w₁* = (σ₂² - ρσ₁σ₂) / (σ₁² + σ₂² - 2ρσ₁σ₂)\n\n"
                    "Efficient Frontier: set of optimal portfolios offering highest expected return for given risk.\n"
                    "Minimum Variance Frontier: includes all portfolios with minimum variance at each return.\n"
                    "Global Minimum Variance (GMV) portfolio: point of lowest possible variance.\n\n"
                    "Capital Market Line (CML): line from Rf to the tangency (market) portfolio.\n"
                    "All investors hold the same risky portfolio (market portfolio) in CAPM."
                ),
            },
            {
                "title": "Capital Asset Pricing Model (CAPM)",
                "content": (
                    "E(Ri) = Rf + βi × [E(Rm) - Rf]\n\n"
                    "Beta: systematic (market) risk measure.\n"
                    "β = Cov(Ri, Rm) / Var(Rm) = ρim × σi / σm\n\n"
                    "β = 1: moves with market\n"
                    "β > 1: more volatile than market (aggressive)\n"
                    "β < 1: less volatile than market (defensive)\n"
                    "β = 0: uncorrelated with market (e.g., T-bills)\n\n"
                    "Security Market Line (SML): plots E(R) vs. beta for all securities.\n"
                    "Alpha = Actual Return - CAPM Required Return\n"
                    "α > 0: undervalued (above SML) → buy signal\n"
                    "α < 0: overvalued (below SML) → sell signal"
                ),
            },
            {
                "title": "Performance Evaluation",
                "content": (
                    "Sharpe Ratio = (Rp - Rf) / σp  [total risk; for non-diversified portfolios]\n"
                    "Treynor Ratio = (Rp - Rf) / βp  [systematic risk; for diversified portfolios]\n"
                    "Jensen's Alpha = Rp - [Rf + β(Rm-Rf)]  [risk-adjusted excess return]\n"
                    "Information Ratio = Active Return / Tracking Error\n\n"
                    "M² (Modigliani-squared): leveraged/deleveraged portfolio's Sharpe comparison.\n\n"
                    "TWR (Time-Weighted Return): measures manager skill; removes effect of client deposits/withdrawals.\n"
                    "MWR (IRR / Dollar-Weighted Return): measures actual investor experience including timing.\n"
                    "For manager evaluation, use TWR. For investor experience, use MWR."
                ),
            },
            {
                "title": "Investment Policy Statement (IPS)",
                "content": (
                    "IPS components:\n"
                    "1. Return Objective: required or desired return.\n"
                    "2. Risk Tolerance: ability (financial) and willingness (psychological) to bear risk.\n"
                    "3. Time Horizon: investment period.\n"
                    "4. Liquidity Needs: near-term cash requirements.\n"
                    "5. Tax Concerns: tax rates and strategies.\n"
                    "6. Legal and Regulatory: constraints (e.g., ERISA for pension funds).\n"
                    "7. Unique Circumstances: ESG, ethical restrictions.\n\n"
                    "Strategic Asset Allocation: long-run target weights based on IPS.\n"
                    "Tactical Asset Allocation: short-term deviations based on market views.\n"
                    "Rebalancing: restoring portfolio to SAA targets."
                ),
            },
        ],
        "exam_tips": [
            "Diversification eliminates ONLY unsystematic risk. Beta (systematic) risk remains.",
            "CAPM: use SML for individual securities; CML for efficient portfolios only.",
            "Treynor uses beta → best for evaluating a diversified portfolio (e.g., a mutual fund).",
            "Sharpe uses sigma → best for evaluating a standalone or concentrated portfolio.",
            "TWR is the GIPS-required measure for evaluating manager performance.",
        ],
    },
}
