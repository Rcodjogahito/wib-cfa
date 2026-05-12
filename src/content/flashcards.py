"""
WIB CFA — Flashcard Bank
150+ concept flashcards covering all 10 CFA Level 1 topics.
"""

FLASHCARDS = [
    # ══════════════════════════════════════════════════════════
    # ETHICS & PROFESSIONAL STANDARDS
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Ethics & Professional Standards",
        "concept_en": "CFA Code of Ethics — Six Components",
        "definition_en": (
            "1. Act with integrity, competence, diligence, respect, and ethically. "
            "2. Place client interests before employer/personal interests. "
            "3. Use reasonable care and exercise independent judgment. "
            "4. Practice and encourage others to practice professionally. "
            "5. Promote the integrity and viability of global capital markets. "
            "6. Maintain and improve professional competence."
        ),
        "definition_fr": (
            "6 composantes : intégrité/compétence/diligence, primauté des clients, "
            "jugement indépendant, pratique professionnelle, intégrité des marchés, "
            "amélioration des compétences."
        ),
        "example_en": "A member who puts their own trading profits before client orders violates component 2.",
        "formula": "",
    },
    {
        "topic": "Ethics & Professional Standards",
        "concept_en": "Standard I(A) — Knowledge of the Law",
        "definition_en": (
            "Members must know and comply with all applicable laws and regulations. "
            "In case of conflict, follow the stricter rule. Dissociate from illegal activities."
        ),
        "definition_fr": "Connaître et respecter les lois applicables. En cas de conflit, appliquer la règle la plus stricte.",
        "example_en": "A member in a jurisdiction with weaker disclosure rules must still follow the stricter CFA Standards.",
        "formula": "",
    },
    {
        "topic": "Ethics & Professional Standards",
        "concept_en": "Standard II(A) — Material Nonpublic Information",
        "definition_en": (
            "Members cannot act on material nonpublic information (MNPI). "
            "Information is MATERIAL if it would affect the investment decision of a reasonable investor. "
            "Information is NONPUBLIC until it has been distributed to the investing public."
        ),
        "definition_fr": "Interdiction de trader sur des informations privilégiées matérielles et non publiques.",
        "example_en": "Overhearing a CEO discuss earnings before announcement — cannot trade.",
        "formula": "",
    },
    {
        "topic": "Ethics & Professional Standards",
        "concept_en": "Standard III(B) — Fair Dealing",
        "definition_en": (
            "Members must deal fairly and objectively with all clients when taking investment action. "
            "All clients must receive investment recommendations simultaneously; "
            "no client group may receive preferential treatment."
        ),
        "definition_fr": "Traitement équitable et simultané de tous les clients lors des recommandations.",
        "example_en": "Sending a buy recommendation to institutional clients 10 minutes before retail clients violates this standard.",
        "formula": "",
    },
    {
        "topic": "Ethics & Professional Standards",
        "concept_en": "GIPS — Global Investment Performance Standards",
        "definition_en": (
            "Voluntary, ethical standards for the presentation of investment firm performance. "
            "Goals: fair representation, full disclosure, comparability across firms. "
            "Compliance is firm-wide, not individual."
        ),
        "definition_fr": "Normes volontaires pour la présentation équitable des performances d'investissement.",
        "example_en": "A GIPS-compliant firm cannot cherry-pick its best-performing composites.",
        "formula": "",
    },
    # ══════════════════════════════════════════════════════════
    # QUANTITATIVE METHODS
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Quantitative Methods",
        "concept_en": "Future Value (FV)",
        "definition_en": "The value of an investment at a future date, accounting for compounding interest.",
        "definition_fr": "Valeur future d'un investissement après intérêts composés.",
        "example_en": "$1,000 at 5% for 3 years → FV = 1,000 × (1.05)³ = $1,157.63",
        "formula": "FV = PV × (1 + r)^n",
    },
    {
        "topic": "Quantitative Methods",
        "concept_en": "Present Value (PV)",
        "definition_en": "The current value of a future sum of money, discounted at a required rate of return.",
        "definition_fr": "Valeur actuelle d'un flux futur, actualisé au taux requis.",
        "example_en": "PV of $1,000 in 3 years at 5% = 1,000 / (1.05)³ = $863.84",
        "formula": "PV = FV / (1 + r)^n",
    },
    {
        "topic": "Quantitative Methods",
        "concept_en": "Annuity Present Value",
        "definition_en": "The present value of a series of equal payments made at regular intervals.",
        "definition_fr": "Valeur actuelle d'une série de paiements égaux périodiques.",
        "example_en": "$500/year for 5 years at 8% discount rate.",
        "formula": "PV = PMT × [1 - (1+r)^-n] / r",
    },
    {
        "topic": "Quantitative Methods",
        "concept_en": "Effective Annual Rate (EAR)",
        "definition_en": "The actual annual interest rate after accounting for compounding within the year.",
        "definition_fr": "Taux d'intérêt annuel effectif tenant compte de la composition infra-annuelle.",
        "example_en": "12% compounded monthly → EAR = (1 + 0.12/12)^12 - 1 = 12.68%",
        "formula": "EAR = (1 + r/m)^m - 1",
    },
    {
        "topic": "Quantitative Methods",
        "concept_en": "Normal Distribution Properties",
        "definition_en": (
            "Symmetric, bell-shaped distribution. "
            "±1σ: ~68% of observations. "
            "±2σ: ~95% of observations. "
            "±3σ: ~99% of observations. "
            "Mean = Median = Mode."
        ),
        "definition_fr": "Distribution symétrique en cloche. 68/95/99% des données dans ±1/2/3 écarts-types.",
        "example_en": "If returns are N(10%, 5%), ~95% of returns fall between 0% and 20%.",
        "formula": "Z = (X - μ) / σ",
    },
    {
        "topic": "Quantitative Methods",
        "concept_en": "Sharpe Ratio",
        "definition_en": "Measures excess return per unit of total risk (standard deviation). Higher is better.",
        "definition_fr": "Mesure le rendement excédentaire par unité de risque total.",
        "example_en": "Portfolio return 12%, Rf 3%, σ 6% → Sharpe = (12%-3%)/6% = 1.5",
        "formula": "Sharpe = (Rp - Rf) / σp",
    },
    {
        "topic": "Quantitative Methods",
        "concept_en": "Coefficient of Variation (CV)",
        "definition_en": "Risk per unit of return. Allows comparison of risk across investments with different returns.",
        "definition_fr": "Risque par unité de rendement. Permet de comparer des investissements différents.",
        "example_en": "CV = 20% / 10% = 2.0 means 2 units of risk per unit of return.",
        "formula": "CV = σ / μ",
    },
    {
        "topic": "Quantitative Methods",
        "concept_en": "Type I vs Type II Error",
        "definition_en": (
            "Type I Error (α): Rejecting a TRUE null hypothesis (false positive). "
            "Type II Error (β): Failing to reject a FALSE null hypothesis (false negative). "
            "Power of test = 1 - β."
        ),
        "definition_fr": "Type I : rejeter H0 vraie. Type II : ne pas rejeter H0 fausse.",
        "example_en": "Declaring a manager has skill when they don't (Type I) vs. missing a skilled manager (Type II).",
        "formula": "Power = 1 - P(Type II Error)",
    },
    # ══════════════════════════════════════════════════════════
    # ECONOMICS
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Economics",
        "concept_en": "GDP — Expenditure Approach",
        "definition_en": "GDP = Consumption + Investment + Government Spending + Net Exports (X-M).",
        "definition_fr": "PIB = Consommation + Investissement + Dépenses gouvernementales + Exportations nettes.",
        "example_en": "C=$10T, I=$2T, G=$3T, NX=-$0.5T → GDP = $14.5T",
        "formula": "GDP = C + I + G + (X - M)",
    },
    {
        "topic": "Economics",
        "concept_en": "Inflation — CPI vs. GDP Deflator",
        "definition_en": (
            "CPI: measures price change for a fixed basket of consumer goods. "
            "GDP Deflator: measures price change for all domestically produced goods. "
            "CPI is typically higher (fixed basket effect)."
        ),
        "definition_fr": "IPC : panier fixe de biens de consommation. Déflateur PIB : tous les biens produits.",
        "example_en": "CPI includes imports; GDP Deflator excludes them.",
        "formula": "GDP Deflator = (Nominal GDP / Real GDP) × 100",
    },
    {
        "topic": "Economics",
        "concept_en": "Monetary Policy Tools",
        "definition_en": (
            "1. Open Market Operations: buying/selling government bonds. "
            "2. Reserve Requirements: minimum % of deposits banks must hold. "
            "3. Discount Rate: rate charged to banks for borrowing from central bank. "
            "4. Quantitative Easing: large-scale asset purchases when rates are near zero."
        ),
        "definition_fr": "Opérations d'open market, réserves obligatoires, taux d'escompte, assouplissement quantitatif.",
        "example_en": "Fed purchases T-bills → money supply rises → interest rates fall.",
        "formula": "",
    },
    {
        "topic": "Economics",
        "concept_en": "IS-LM Framework",
        "definition_en": (
            "IS Curve: investment-savings equilibrium in goods market (downward sloping: lower r → higher Y). "
            "LM Curve: money market equilibrium (upward sloping: higher Y → higher r). "
            "Intersection gives equilibrium output (Y*) and interest rate (r*)."
        ),
        "definition_fr": "IS : équilibre marché des biens. LM : équilibre marché monétaire. Croisement = équilibre macroéconomique.",
        "example_en": "Fiscal stimulus shifts IS right → higher output and higher interest rates.",
        "formula": "",
    },
    {
        "topic": "Economics",
        "concept_en": "Phillips Curve",
        "definition_en": (
            "Short-run: inverse relationship between unemployment and inflation. "
            "Long-run: vertical at NAIRU (Natural Rate of Unemployment); no trade-off. "
            "Stagflation (1970s) disproved the stable short-run relationship."
        ),
        "definition_fr": "Court terme : arbitrage chômage-inflation. Long terme : verticale au NAIRU.",
        "example_en": "Lower unemployment → higher inflation in the short run.",
        "formula": "π = πe - α(u - u*) + supply shocks",
    },
    {
        "topic": "Economics",
        "concept_en": "Exchange Rate — Purchasing Power Parity (PPP)",
        "definition_en": (
            "Absolute PPP: exchange rate equalizes prices of identical goods across countries. "
            "Relative PPP: % change in exchange rate ≈ inflation differential."
        ),
        "definition_fr": "La parité de pouvoir d'achat prédit que les taux de change s'ajustent aux différentiels d'inflation.",
        "example_en": "If US inflation is 3% and EU inflation is 1%, EUR should appreciate ~2% vs USD.",
        "formula": "%ΔS(A/B) ≈ π_A - π_B",
    },
    # ══════════════════════════════════════════════════════════
    # FINANCIAL STATEMENT ANALYSIS
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Financial Statement Analysis",
        "concept_en": "DuPont Analysis — 3-Factor",
        "definition_en": "Decomposes ROE into three drivers: profitability, efficiency, and leverage.",
        "definition_fr": "Décompose le ROE en rentabilité, efficience et levier financier.",
        "example_en": "ROE = 5% × 1.5 × 2.0 = 15%",
        "formula": "ROE = Net Profit Margin × Asset Turnover × Equity Multiplier",
    },
    {
        "topic": "Financial Statement Analysis",
        "concept_en": "DuPont Analysis — 5-Factor",
        "definition_en": "Expands ROE decomposition to: Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Leverage.",
        "definition_fr": "Extension en 5 facteurs du ROE.",
        "example_en": "Used to identify whether ROE improvement is due to operations or financial engineering.",
        "formula": "ROE = (NI/EBT) × (EBT/EBIT) × (EBIT/Sales) × (Sales/Assets) × (Assets/Equity)",
    },
    {
        "topic": "Financial Statement Analysis",
        "concept_en": "Current Ratio vs. Quick Ratio",
        "definition_en": (
            "Current Ratio = Current Assets / Current Liabilities. "
            "Quick Ratio = (Cash + Marketable Securities + Receivables) / Current Liabilities. "
            "Quick ratio is more conservative — excludes inventories."
        ),
        "definition_fr": "Ratio courant vs ratio rapide (exclut les stocks).",
        "example_en": "Current ratio 2.0 but quick ratio 0.8 indicates slow-moving inventory.",
        "formula": "Quick Ratio = (CA - Inventories - Prepaid) / CL",
    },
    {
        "topic": "Financial Statement Analysis",
        "concept_en": "FIFO vs LIFO in Rising Prices",
        "definition_en": (
            "FIFO (First In First Out): older (cheaper) costs → COGS → higher gross profit, higher inventory. "
            "LIFO (Last In First Out): newer (more expensive) costs → COGS → lower gross profit, lower inventory. "
            "Note: LIFO not permitted under IFRS."
        ),
        "definition_fr": "FIFO : bénéfice plus élevé en période de hausse des prix. LIFO non autorisé sous IFRS.",
        "example_en": "In rising prices: FIFO net income > LIFO net income.",
        "formula": "LIFO Reserve = FIFO Inventory - LIFO Inventory",
    },
    {
        "topic": "Financial Statement Analysis",
        "concept_en": "Cash Conversion Cycle (CCC)",
        "definition_en": (
            "Measures how many days it takes for a company to convert investments into cash. "
            "Lower CCC = better working capital management."
        ),
        "definition_fr": "Délai de conversion des investissements en liquidités. Plus court = meilleure gestion.",
        "example_en": "If DSO=30, DIO=40, DPO=20 → CCC = 30+40-20 = 50 days",
        "formula": "CCC = DSO + DIO - DPO",
    },
    {
        "topic": "Financial Statement Analysis",
        "concept_en": "Interest Coverage Ratio",
        "definition_en": "Measures a company's ability to pay interest on its debt from operating earnings.",
        "definition_fr": "Capacité à payer les intérêts sur la dette à partir des bénéfices d'exploitation.",
        "example_en": "EBIT $100M, Interest $20M → coverage = 5.0x",
        "formula": "Interest Coverage = EBIT / Interest Expense",
    },
    {
        "topic": "Financial Statement Analysis",
        "concept_en": "Operating vs Financial Leverage",
        "definition_en": (
            "Operating Leverage (DOL): sensitivity of EBIT to change in sales (high fixed costs → high DOL). "
            "Financial Leverage (DFL): sensitivity of EPS to change in EBIT (high debt → high DFL). "
            "Total Leverage = DOL × DFL."
        ),
        "definition_fr": "Levier opérationnel : sensibilité EBIT/ventes. Levier financier : sensibilité EPS/EBIT.",
        "example_en": "DOL 3x means 1% increase in sales → 3% increase in EBIT.",
        "formula": "DOL = % Change EBIT / % Change Sales",
    },
    # ══════════════════════════════════════════════════════════
    # CORPORATE ISSUERS
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Corporate Issuers",
        "concept_en": "WACC — Weighted Average Cost of Capital",
        "definition_en": (
            "The blended cost of capital from all sources, weighted by their market-value proportions. "
            "Used as the hurdle rate for investment projects with the same risk as the firm."
        ),
        "definition_fr": "Coût moyen pondéré du capital. Taux d'actualisation des projets au même risque que la firme.",
        "example_en": "60% equity at 12%, 40% debt at 5% (tax 30%) → WACC = 0.6×12% + 0.4×5%×0.7 = 8.6%",
        "formula": "WACC = (E/V)×Re + (D/V)×Rd×(1-T)",
    },
    {
        "topic": "Corporate Issuers",
        "concept_en": "Modigliani-Miller — With Taxes",
        "definition_en": (
            "MM with corporate taxes: firm value increases with leverage due to interest tax shield. "
            "Value levered firm = Value unlevered + PV(Tax Shield). "
            "Optimal capital structure: 100% debt (practically limited by distress costs)."
        ),
        "definition_fr": "Avec impôts : la valeur augmente avec l'endettement grâce au bouclier fiscal.",
        "example_en": "Tax shield = D × Tc. $1M debt at 30% tax rate → $300K tax shield.",
        "formula": "VL = VU + T × D",
    },
    {
        "topic": "Corporate Issuers",
        "concept_en": "Net Present Value (NPV) vs IRR",
        "definition_en": (
            "NPV: sum of discounted future cash flows minus initial investment. Accept if NPV > 0. "
            "IRR: discount rate making NPV = 0. Accept if IRR > required return. "
            "When NPV and IRR conflict (mutually exclusive projects), use NPV."
        ),
        "definition_fr": "VAN vs TRI. En cas de conflit, la VAN est prioritaire.",
        "example_en": "If Project A has NPV=$500K, IRR=15% and Project B has NPV=$700K, IRR=12% (hurdle=10%) → choose B.",
        "formula": "NPV = Σ CF_t/(1+r)^t - CF0",
    },
    {
        "topic": "Corporate Issuers",
        "concept_en": "Dividend Policy — Irrelevance Theory",
        "definition_en": (
            "Miller & Modigliani: in perfect capital markets, dividend policy does not affect firm value. "
            "Investors can create 'homemade dividends' by selling shares. "
            "In practice, taxes, signaling effects, and clienteles make dividends matter."
        ),
        "definition_fr": "M&M : les dividendes n'affectent pas la valeur dans des marchés parfaits.",
        "example_en": "A firm that cuts dividends to invest in positive-NPV projects creates equal value.",
        "formula": "",
    },
    # ══════════════════════════════════════════════════════════
    # EQUITY INVESTMENTS
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Equity Investments",
        "concept_en": "Gordon Growth Model (GGM)",
        "definition_en": (
            "Intrinsic value of a stock assuming dividends grow at a constant rate forever. "
            "Requires: r > g. Used for stable, dividend-paying companies."
        ),
        "definition_fr": "Modèle de Gordon : valeur = D1/(r-g). Croissance constante des dividendes.",
        "example_en": "D1=$2, r=10%, g=5% → V = 2/(0.10-0.05) = $40",
        "formula": "V = D1 / (r - g)",
    },
    {
        "topic": "Equity Investments",
        "concept_en": "P/E Ratio — Justified",
        "definition_en": (
            "The justified (intrinsic) P/E based on fundamentals. "
            "Higher justified P/E when: high payout ratio, high growth, or low required return."
        ),
        "definition_fr": "PER justifié par les fondamentaux. P/E élevé si dividende élevé, croissance forte.",
        "example_en": "Payout 60%, r=10%, g=4% → P/E = 0.60/(0.10-0.04) = 10x",
        "formula": "Justified P/E = Payout Ratio / (r - g)",
    },
    {
        "topic": "Equity Investments",
        "concept_en": "Efficient Market Hypothesis (EMH) — Three Forms",
        "definition_en": (
            "Weak: prices reflect all past trading data. Technical analysis useless. "
            "Semi-strong: prices reflect all public information. Fundamental analysis useless. "
            "Strong: prices reflect all public AND private information. Insider trading useless."
        ),
        "definition_fr": "Forme faible/semi-forte/forte. Chaque forme élimine une forme d'analyse ou d'avantage informationnel.",
        "example_en": "Semi-strong: an analyst cannot consistently outperform using public earnings data.",
        "formula": "",
    },
    {
        "topic": "Equity Investments",
        "concept_en": "Enterprise Value (EV)",
        "definition_en": "Theoretical total acquisition cost of a company. Represents the value of operations regardless of financing.",
        "definition_fr": "Valeur totale de l'entreprise, indépendamment de sa structure de financement.",
        "example_en": "Market cap $500M, debt $200M, cash $50M → EV = $650M",
        "formula": "EV = Market Cap + Total Debt + Preferred Stock - Cash",
    },
    {
        "topic": "Equity Investments",
        "concept_en": "Multistage DDM",
        "definition_en": (
            "Values stocks with non-constant dividend growth. "
            "Phase 1: explicitly forecast dividends during high-growth period. "
            "Phase 2: apply GGM for terminal value at start of stable-growth phase. "
            "Then discount all cash flows back to PV."
        ),
        "definition_fr": "Évalue les actions avec plusieurs phases de croissance des dividendes.",
        "example_en": "5 years at 15% growth, then 4% forever. Calculate each year's dividend then terminal value.",
        "formula": "V = Σ [Dt/(1+r)^t] + [Dn+1/(r-g)] / (1+r)^n",
    },
    # ══════════════════════════════════════════════════════════
    # FIXED INCOME
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Fixed Income",
        "concept_en": "Bond Price-Yield Relationship",
        "definition_en": (
            "Inverse relationship: when yields rise, prices fall; when yields fall, prices rise. "
            "When YTM = coupon rate → par. "
            "When YTM > coupon rate → discount. "
            "When YTM < coupon rate → premium."
        ),
        "definition_fr": "Relation inverse prix-rendement. YTM=coupon→pair, YTM>coupon→décote, YTM<coupon→prime.",
        "example_en": "A 5% bond when market rates rise to 7% → priced below par.",
        "formula": "P = Σ [C/(1+y)^t] + [FV/(1+y)^n]",
    },
    {
        "topic": "Fixed Income",
        "concept_en": "Macaulay Duration",
        "definition_en": (
            "Weighted average time (in years) to receive a bond's cash flows, weighted by PV of each cash flow. "
            "Zero coupon bond: Macaulay duration = maturity. "
            "Higher coupon or yield → lower duration. Longer maturity → higher duration."
        ),
        "definition_fr": "Durée moyenne pondérée de perception des flux. Obligation zéro-coupon : durée = maturité.",
        "example_en": "A 10-year, 6% bond has Macaulay duration ~7.5 years.",
        "formula": "Macaulay D = Σ [t × PV(CFt)] / P",
    },
    {
        "topic": "Fixed Income",
        "concept_en": "Modified Duration",
        "definition_en": "Measures percentage price change for a 1% (100bp) change in yield.",
        "definition_fr": "Variation % du prix pour une variation de 1% du rendement.",
        "example_en": "Mod. Duration=5 → yield +1% → price changes ~-5%",
        "formula": "Modified Duration = Macaulay Duration / (1 + y/m)",
    },
    {
        "topic": "Fixed Income",
        "concept_en": "Convexity — Price Change Formula",
        "definition_en": (
            "Duration gives a linear approximation of price change. "
            "Convexity corrects for the curved price-yield relationship. "
            "Higher convexity is always beneficial (more price gain, less price loss)."
        ),
        "definition_fr": "La convexité corrige l'approximation linéaire de la duration pour les grands mouvements de taux.",
        "example_en": "For +1% yield change with duration 5 and convexity 40: ΔP% ≈ -5%(1%) + ½(40)(0.01)² = -4.98%",
        "formula": "%ΔP ≈ -MD × Δy + ½ × Convexity × (Δy)²",
    },
    {
        "topic": "Fixed Income",
        "concept_en": "Z-Spread vs OAS",
        "definition_en": (
            "Z-Spread: constant spread added to the spot rate curve to equate PV of cash flows to market price. "
            "OAS (Option-Adjusted Spread): Z-spread minus the option value. "
            "OAS isolates credit/liquidity risk by removing the option effect."
        ),
        "definition_fr": "Z-spread : écart sur la courbe spot. OAS = Z-spread moins la valeur de l'option.",
        "example_en": "Callable bond: Z-spread=150bp, option value=30bp → OAS=120bp.",
        "formula": "OAS = Z-spread - Option Value (bps)",
    },
    {
        "topic": "Fixed Income",
        "concept_en": "Credit Ratings — Investment Grade vs HY",
        "definition_en": (
            "Investment Grade: Baa3/BBB- and above (Moody's/S&P). Low default risk. "
            "High Yield (Junk): Ba1/BB+ and below. Higher default risk, higher spread. "
            "Fallen Angel: IG bond downgraded to HY. Rising Star: HY upgraded to IG."
        ),
        "definition_fr": "Investment grade : Baa3/BBB- et plus. Haut rendement : Ba1/BB+ et moins.",
        "example_en": "A BBB-rated bond is investment grade; a BB-rated bond is high yield.",
        "formula": "",
    },
    {
        "topic": "Fixed Income",
        "concept_en": "Bootstrapping — Spot Rates",
        "definition_en": (
            "A method to derive zero-coupon (spot) rates from par yield coupon bond prices. "
            "Start with the 1-year rate, then use that to solve for the 2-year spot rate, etc."
        ),
        "definition_fr": "Méthode pour dériver les taux spot (zéro-coupon) à partir des prix d'obligations à coupon.",
        "example_en": "1Y par rate = 4% → s1 = 4%. Use s1 and 2Y par bond to bootstrap s2.",
        "formula": "",
    },
    # ══════════════════════════════════════════════════════════
    # DERIVATIVES
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Derivatives",
        "concept_en": "Put-Call Parity",
        "definition_en": (
            "Fundamental no-arbitrage relationship between European call and put prices. "
            "C + PV(X) = P + S. "
            "Allows synthetic creation of any position from the other components."
        ),
        "definition_fr": "Parité put-call : C + VA(X) = P + S. Relation d'absence d'arbitrage.",
        "example_en": "C=$5, PV(X)=$95, S=$100 → P = $5+$95-$100 = $0 (ATM, near expiry)",
        "formula": "C + PV(X) = P + S",
    },
    {
        "topic": "Derivatives",
        "concept_en": "Black-Scholes Option Inputs",
        "definition_en": (
            "Five inputs to Black-Scholes: Underlying price (S), Exercise price (X), "
            "Time to expiration (T), Risk-free rate (r), Volatility (σ). "
            "Call value increases with: S↑, T↑, r↑, σ↑. Decreases with: X↑."
        ),
        "definition_fr": "5 inputs B-S : prix sous-jacent, prix d'exercice, temps, taux, volatilité.",
        "example_en": "Vega > 0 for both calls and puts — higher volatility always increases option value.",
        "formula": "C = S·N(d1) - X·e^(-rT)·N(d2)",
    },
    {
        "topic": "Derivatives",
        "concept_en": "Option Greeks Summary",
        "definition_en": (
            "Delta (Δ): price sensitivity to underlying. Call: 0 to 1. Put: -1 to 0. "
            "Gamma (Γ): rate of change of delta. Highest at-the-money. "
            "Theta (Θ): time decay — option value lost per day. "
            "Vega (ν): sensitivity to volatility. Positive for calls and puts. "
            "Rho (ρ): sensitivity to interest rate."
        ),
        "definition_fr": "Delta, Gamma, Theta (décroissance temporelle), Vega (volatilité), Rho (taux).",
        "example_en": "Delta of deep ITM call ≈ 1. Delta of ATM call ≈ 0.5.",
        "formula": "",
    },
    {
        "topic": "Derivatives",
        "concept_en": "Forward Price — Cost of Carry",
        "definition_en": (
            "Fair forward price = Spot price compounded at risk-free rate over the contract period. "
            "Adjustments: subtract PV of dividends or convenience yield; add storage costs."
        ),
        "definition_fr": "Prix forward = prix spot composé au taux sans risque, ajusté pour dividendes/coûts de stockage.",
        "example_en": "Spot = $100, r = 5%, T = 1 year, no dividends → F = 100 × e^0.05 = $105.13",
        "formula": "F = S × e^(r-q)T  [where q = dividend yield]",
    },
    {
        "topic": "Derivatives",
        "concept_en": "Interest Rate Swap — Valuation",
        "definition_en": (
            "A swap can be valued as a long position in one bond and a short position in another. "
            "Fixed-rate payer: short fixed-rate bond + long floating-rate bond. "
            "Floating-rate payer: long fixed-rate bond + short floating-rate bond."
        ),
        "definition_fr": "Un swap peut être valorisé comme une position longue dans une obligation et courte dans une autre.",
        "example_en": "If fixed rates rise, the fixed-rate payer gains value (their fixed rate looks cheap).",
        "formula": "V_swap = V_floating - V_fixed (for fixed-rate payer)",
    },
    # ══════════════════════════════════════════════════════════
    # ALTERNATIVE INVESTMENTS
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Alternative Investments",
        "concept_en": "Private Equity — Return Metrics",
        "definition_en": (
            "IRR: internal rate of return based on cash flows (most common PE metric). "
            "TVPI: Total Value to Paid-In = (Distributions + Residual Value) / Paid-In. "
            "DPI: Distributions to Paid-In = cumulative distributions / paid-in capital. "
            "RVPI: Residual Value to Paid-In = remaining value / paid-in capital."
        ),
        "definition_fr": "TRI, TVPI (valeur totale/capital engagé), DPI (distributions/capital), RVPI (valeur résiduelle/capital).",
        "example_en": "TVPI of 2.5x means investors received 2.5× their invested capital (total).",
        "formula": "TVPI = (Distributions + NAV) / Paid-In Capital",
    },
    {
        "topic": "Alternative Investments",
        "concept_en": "Hedge Fund — Fee Structure",
        "definition_en": (
            "'2 and 20': 2% management fee on AUM annually + 20% performance fee on profits. "
            "High-water mark: manager only earns incentive fees after recovering prior losses. "
            "Hurdle rate: minimum return before performance fees apply."
        ),
        "definition_fr": "2% frais gestion + 20% performance. High-water mark : récupérer les pertes avant de prélever les frais.",
        "example_en": "Fund loses 10% then gains 15%: with HWM, no performance fee until NAV exceeds prior peak.",
        "formula": "Performance Fee = 20% × max(Return - Hurdle, 0) × AUM",
    },
    {
        "topic": "Alternative Investments",
        "concept_en": "Real Estate — Cap Rate",
        "definition_en": "Capitalization rate: measures the yield of a property based on NOI. Used for direct comparisons.",
        "definition_fr": "Taux de capitalisation : mesure le rendement d'un bien immobilier basé sur le NOI.",
        "example_en": "Property value $2M, NOI $120K → Cap Rate = 6%",
        "formula": "Cap Rate = NOI / Property Value",
    },
    {
        "topic": "Alternative Investments",
        "concept_en": "Commodities — Futures Return Components",
        "definition_en": (
            "1. Spot return: change in underlying commodity spot price. "
            "2. Roll return: gain/loss from rolling expiring futures to next contract. "
               "(Positive in backwardation; negative in contango.) "
            "3. Collateral return: interest earned on T-bill collateral."
        ),
        "definition_fr": "Rendement total = rendement spot + rendement de roll + rendement du collatéral.",
        "example_en": "In backwardation (futures < spot), rolling futures generates positive roll return.",
        "formula": "Total Return = Spot Return + Roll Return + Collateral Return",
    },
    # ══════════════════════════════════════════════════════════
    # PORTFOLIO MANAGEMENT
    # ══════════════════════════════════════════════════════════
    {
        "topic": "Portfolio Management",
        "concept_en": "Capital Market Line (CML)",
        "definition_en": (
            "The line from the risk-free asset tangent to the efficient frontier. "
            "All rational investors hold a mix of the risk-free asset and the tangency portfolio. "
            "CML applies to efficient (well-diversified) portfolios only."
        ),
        "definition_fr": "Droite allant du taux sans risque au portefeuille tangent. Valide pour les portefeuilles efficients.",
        "example_en": "A 60/40 mix of market portfolio and T-bills lies on the CML.",
        "formula": "E(Rp) = Rf + [(E(Rm) - Rf) / σm] × σp",
    },
    {
        "topic": "Portfolio Management",
        "concept_en": "Security Market Line (SML) — CAPM",
        "definition_en": (
            "Plots expected return vs. systematic risk (beta) for all securities. "
            "Securities above SML are undervalued (positive alpha). "
            "Securities below SML are overvalued (negative alpha)."
        ),
        "definition_fr": "Droite marché des titres : rendement espéré vs bêta. Au-dessus = sous-évalué.",
        "example_en": "Stock expected return 14%, CAPM expected return 10% → alpha = +4%",
        "formula": "E(Ri) = Rf + βi × [E(Rm) - Rf]",
    },
    {
        "topic": "Portfolio Management",
        "concept_en": "Jensen's Alpha",
        "definition_en": "Measures the excess return of a portfolio above CAPM expected return. Risk-adjusted outperformance.",
        "definition_fr": "Alpha de Jensen : excès de rendement par rapport au MEDAF. Surperformance ajustée au risque.",
        "example_en": "Rp=14%, Rf=3%, β=1.2, Rm=10% → Alpha = 14% - [3%+1.2×7%] = 14%-11.4% = 2.6%",
        "formula": "α = Rp - [Rf + βp × (Rm - Rf)]",
    },
    {
        "topic": "Portfolio Management",
        "concept_en": "Treynor Ratio vs Sharpe Ratio",
        "definition_en": (
            "Treynor = (Rp - Rf) / βp → uses systematic risk. Use for diversified portfolios. "
            "Sharpe = (Rp - Rf) / σp → uses total risk. Use for standalone or non-diversified portfolios."
        ),
        "definition_fr": "Treynor : rendement/risque systématique (portefeuille diversifié). Sharpe : rendement/risque total.",
        "example_en": "For a well-diversified fund, Treynor is more appropriate; for a hedge fund with idiosyncratic risk, use Sharpe.",
        "formula": "Treynor = (Rp - Rf) / β;  Sharpe = (Rp - Rf) / σ",
    },
    {
        "topic": "Portfolio Management",
        "concept_en": "Portfolio Variance — Two Assets",
        "definition_en": "Portfolio variance is reduced when asset correlation is less than 1. Diversification benefit.",
        "definition_fr": "La variance du portefeuille diminue quand la corrélation < 1. Effet de diversification.",
        "example_en": "If ρ=-1, two assets can be combined to achieve σ=0.",
        "formula": "σ²p = w₁²σ₁² + w₂²σ₂² + 2w₁w₂σ₁σ₂ρ₁₂",
    },
    {
        "topic": "Portfolio Management",
        "concept_en": "Value at Risk (VaR)",
        "definition_en": (
            "Minimum expected loss at a given confidence level over a given time horizon. "
            "VaR at 95% confidence = mean - 1.65σ. "
            "VaR at 99% confidence = mean - 2.33σ. "
            "Limitation: does not describe the magnitude of losses beyond VaR."
        ),
        "definition_fr": "Perte minimale attendue à un niveau de confiance donné. Ne mesure pas les pertes au-delà.",
        "example_en": "Annual VaR at 95%: mean 10%, σ 15% → VaR = 10% - 1.65×15% = -14.75% (max loss 95% of the time)",
        "formula": "VaR (95%) = μ - 1.65σ;  VaR (99%) = μ - 2.33σ",
    },
]
