#!/usr/bin/env python3
"""
Batch 3 — explications items 34-49 (les derniers).
Lancer: python scripts/batch3_explanations.py
"""
import sys, tomllib
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open(Path(__file__).parent.parent / ".streamlit" / "secrets.toml", "rb") as f:
    s = tomllib.load(f)
from supabase import create_client
sb = create_client(s["supabase"]["SUPABASE_URL"], s["supabase"]["SUPABASE_SERVICE_KEY"])

PATCHES = {
    "0b07060b-9ce1-4828-9b9b-5386f9971a1f": {
        "explanation_en": (
            "Geometric mean = [(1.104)(1.081)(1.032)(1.15)]^0.25 - 1 = (1.4235)^0.25 - 1 = 9.1%. "
            "The geometric mean is always lower than or equal to the arithmetic mean (9.175% here) "
            "and correctly captures the compounding effect over multiple periods. Use the geometric "
            "mean whenever measuring multi-period investment performance."
        ),
    },
    "f3da2f17-dba9-4557-870b-394e427d22c8": {
        "correct_answer": "A",
        "explanation_en": (
            "Leading P/E = (1 - Retention Rate) / (k - g) = (1 - 0.60) / (0.10 - 0.05) = 0.40 / 0.05 = 8.0x. "
            "Option B (10.0x) uses an incorrect denominator. This formula links the justified P/E "
            "directly to growth, required return, and dividend policy via the Gordon Growth Model. "
            "A higher growth rate or lower required return raises the justified multiple."
        ),
    },
    "aad1adf9-87a4-41a4-bdc5-00b891741b19": {
        "correct_answer": "B",
        "explanation_en": (
            "Compound annual return = (1 + HPR)^(1/n) - 1 = (1 + 1.70)^(1/20) - 1 = (2.70)^0.05 - 1 = 5.09%. "
            "Option A (2.69%) incorrectly uses HPR/n (simple division), which ignores compounding. "
            "The compound formula properly accounts for the geometric growth that produced the "
            "170% total holding period return over 20 years."
        ),
    },
    "9825b255-48ba-4823-8f60-e0317179da25": {
        "explanation_en": (
            "A stop sell order becomes a market order when price falls to or below the trigger ($72), "
            "ensuring execution. A limit sell order at $72 only executes at $72 or above; if price "
            "drops below $72 without a matching buyer, the order goes unfilled. A stop-limit adds "
            "a floor price, risking non-execution in a fast-falling market."
        ),
    },
    "68f5ca29-b364-491e-8b78-d399c09836f8": {
        "explanation_en": (
            "Valuing with spot rates: V = 3/1.025 + 3/(1.030)^2 + 103/(1.040)^3 = 2.927 + 2.826 + 91.567 = 97.32. "
            "Spot-rate valuation is more precise than a single YTM because each cash flow is discounted "
            "at its own maturity-specific zero-coupon yield, correctly reflecting the full term structure."
        ),
    },
    "fb0a8656-eb2e-43a1-903f-d86a5fc628e8": {
        "explanation_en": (
            "With 60% initial margin, equity per share = $40 x 0.60 = $24. "
            "HPR = (50 - 40) / 24 = 41.7%, closest to option C (40%). "
            "Leverage amplifies returns: the unlevered gain is only 25% (option B), but borrowing "
            "40% of the purchase price magnifies the return on equity."
        ),
    },
    "679a618f-e5bc-4cb1-b405-eecf2ae952c4": {
        "explanation_en": (
            "Perpetual preferred stock value = Annual dividend / Required return = $5.00 / 0.08 = $62.50. "
            "Preferred stock pays a fixed dividend indefinitely with no maturity, so it is priced as a "
            "perpetuity. Option A ($60.00) is the current market price, not intrinsic value. "
            "Option B ($40.00) results from using the wrong required return."
        ),
    },
    "d8ae7659-3bdb-44b7-8114-5052599b84b0": {
        "explanation_en": (
            "Current ratio = Current Assets / Current Liabilities = $1,660 / $550 = 3.018 for 2004. "
            "A ratio of 3.0 means the company holds $3 of current assets per $1 of current liabilities, "
            "indicating strong short-term liquidity. Option A (0.331) inverts the formula; "
            "option B (2.018) uses incorrect balance sheet figures."
        ),
    },
    "59226802-88d4-4802-b295-94f850ee8743": {
        "explanation_en": (
            "DuPont decomposition: ROE = Net Profit Margin x Asset Turnover x Financial Leverage. "
            "This separates profitability, efficiency, and leverage into analysable drivers. "
            "Option B incorrectly replaces Asset Turnover with Equity Turnover. "
            "Option C uses Gross Profit Margin and Return on Assets, which are not standard DuPont components."
        ),
    },
    "ac9501a0-5710-4ec9-b4c7-d2b7db301e05": {
        "explanation_en": (
            "Form 8-K (Current Report) must be filed with the SEC within 4 business days of material "
            "corporate events, including acquisitions. Footnotes appear only in periodic filings "
            "(10-K/10-Q) submitted weeks later. Proxy statements (DEF 14A) relate to shareholder "
            "voting, not M&A transaction disclosures."
        ),
    },
    "33986486-4f16-4f67-be96-d8aa77fb21ef": {
        "explanation_en": (
            "IOSCO's three core objectives: protecting investors, ensuring fair/efficient/transparent "
            "markets, and reducing systemic risk. Reducing unsystematic risk is NOT an IOSCO objective; "
            "unsystematic (firm-specific) risk is managed by investors through diversification, not by "
            "regulators. IOSCO targets market-wide systemic risk, not individual security volatility."
        ),
    },
    "2d4eb637-dc52-4d13-bf34-fa7ed0b2e0c0": {
        "explanation_en": (
            "Both the World Bank (IBRD) and the European Investment Bank (EIB) are supranational "
            "institutions that actively issue bonds in international capital markets to fund development "
            "projects. Their bonds carry high credit ratings backed by member nations. Neither is "
            "restricted from issuing bonds; bond issuance is a primary funding mechanism for both."
        ),
    },
    "2184522e-d2b7-4ac9-bc67-26dc2f5c399f": {
        "explanation_en": (
            "Market efficiency requires many participants, low transaction costs, and free information "
            "flow. Country A has few participants, high costs, and a short-selling ban -- all signs of "
            "inefficiency. Semi-strong form requires rapid assimilation of all public information; "
            "strong form requires all information (including private) to be reflected in prices. "
            "Country A satisfies neither condition."
        ),
    },
    "9b9142c1-aaee-4479-a09f-b8eca4dd15a3": {
        "explanation_en": (
            "Step 1 -- Holding period yield: HPY = (100 - 98.30) / 98.30 = 1.73%. "
            "Step 2 -- Effective annual yield: EAY = (1 + 0.0173)^(365/70) - 1 = 9.35%. "
            "Option A (1.73%) is only the HPY, not annualised. Annualising compounds the sub-period "
            "return across a full year rather than simply multiplying."
        ),
    },
    "5a2834c1-b877-4ff4-9491-b5e2cb187932": {
        "explanation_en": (
            "A residual plot showing spread that increases (or decreases) as fitted values increase "
            "indicates heteroskedasticity -- a violation of the constant-variance assumption. "
            "A curved pattern signals a linearity violation; systematic clustering by time indicates "
            "autocorrelation (independence violation). Heteroskedasticity does not bias OLS coefficients "
            "but makes standard errors unreliable, distorting hypothesis tests."
        ),
    },
    "360b05d3-afde-463e-a3ac-cc435c30e8c4": {
        "correct_answer": "C",
        "explanation_en": (
            "Capital budgeting uses incremental after-tax cash flows, not accounting income. "
            "Net income includes non-cash items (depreciation) and ignores working capital changes. "
            "Operating profit is pre-tax. Only after-tax free cash flows capture the true economic "
            "costs and benefits of a project, including terminal cash flows and the time value of money."
        ),
    },
}

done = errors = 0
for qid, patch in PATCHES.items():
    try:
        sb.table("questions").update(patch).eq("id", qid).execute()
        done += 1
        print(f"  {qid[:8]} OK", flush=True)
    except Exception as e:
        print(f"  {qid[:8]} ERROR: {e}", flush=True)
        errors += 1

print(f"\nBatch 3 done: {done} updated, {errors} errors")
