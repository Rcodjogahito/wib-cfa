#!/usr/bin/env python3
"""Patch 28 UWorld questions: insert missing Markdown tables into question_en."""
import sys, re, tomllib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open(Path(__file__).parent.parent / ".streamlit" / "secrets.toml", "rb") as f:
    s = tomllib.load(f)
from supabase import create_client
sb = create_client(s["supabase"]["SUPABASE_URL"], s["supabase"]["SUPABASE_SERVICE_KEY"])

COLON_SPLIT_RE = re.compile(
    r"(the following[^:]*:\s*)"
    r"(Based on|Given the|Using the|From the|According to|What is|"
    r"Calculate|Determine|Which|If|The)",
    re.IGNORECASE,
)

# Each entry: (qid, table_markdown)
# Table will be inserted at the colon split point in the DB question_en.
TABLES = {
    # ── 3.01 Portfolio Risk ──────────────────────────────────────────────────
    "8db6e2cb-171e-44d4-9617-c9bf2c5876fd": (
        "| | US equity | European equity | Japanese equity | Indian equity |\n"
        "|---|---|---|---|---|\n"
        "| US equity | 1.00 | | | |\n"
        "| European equity | 0.74 | 1.00 | | |\n"
        "| Japanese equity | 0.67 | 0.59 | 1.00 | |\n"
        "| Indian equity | 0.61 | 0.55 | 0.47 | 1.00 |"
    ),
    # ── 4.04 Working Capital (5 questions, same table) ───────────────────────
    "23808f3f-5e3f-43c6-ba81-402bb6e09a13": (
        "| Selected Financial Data | CNY millions |\n"
        "|---|---|\n"
        "| Credit sales | 15,000 |\n"
        "| Cost of goods sold | 12,000 |\n"
        "| Accounts receivable | 2,000 |\n"
        "| Inventory, beginning balance | 1,500 |\n"
        "| Inventory, ending balance | 1,000 |\n"
        "| Accounts payable | 3,000 |"
    ),
    "fbef96f0-6d54-40ba-ba56-201e9ea3a909": (
        "| Selected Financial Data | CNY millions |\n"
        "|---|---|\n"
        "| Credit sales | 15,000 |\n"
        "| Cost of goods sold | 12,000 |\n"
        "| Accounts receivable | 2,000 |\n"
        "| Inventory, beginning balance | 1,500 |\n"
        "| Inventory, ending balance | 1,000 |\n"
        "| Accounts payable | 3,000 |"
    ),
    "be428262-8166-405f-b64e-2d11d0ee6233": (
        "| Selected Financial Data | CNY millions |\n"
        "|---|---|\n"
        "| Credit sales | 15,000 |\n"
        "| Cost of goods sold | 12,000 |\n"
        "| Accounts receivable | 2,000 |\n"
        "| Inventory, beginning balance | 1,500 |\n"
        "| Inventory, ending balance | 1,000 |\n"
        "| Accounts payable | 3,000 |"
    ),
    "9753f54b-9261-41c4-889a-f6af979ca59d": (
        "| Selected Financial Data | CNY millions |\n"
        "|---|---|\n"
        "| Credit sales | 15,000 |\n"
        "| Cost of goods sold | 12,000 |\n"
        "| Accounts receivable | 2,000 |\n"
        "| Inventory, beginning balance | 1,500 |\n"
        "| Inventory, ending balance | 1,000 |\n"
        "| Accounts payable | 3,000 |"
    ),
    "15eca81e-9345-4e94-9ee3-8a841a6aaca5": (
        "| Selected Financial Data | CNY millions |\n"
        "|---|---|\n"
        "| Credit sales | 15,000 |\n"
        "| Cost of goods sold | 12,000 |\n"
        "| Accounts receivable | 2,000 |\n"
        "| Inventory, beginning balance | 1,500 |\n"
        "| Inventory, ending balance | 1,000 |\n"
        "| Accounts payable | 3,000 |"
    ),
    # ── 4.04 Working Capital – multi-company AR ──────────────────────────────
    "9c51aa0b-2104-46cd-869f-7cfc2d0a2ede": (
        "| Company | Credit Sales ($ millions) | Cost of Goods Sold ($ millions) | Accounts Receivable Average Balance ($ millions) |\n"
        "|---|---|---|---|\n"
        "| 1 | 9.0 | 5.0 | 2.5 |\n"
        "| 2 | 10.0 | 7.3 | 4.0 |\n"
        "| 3 | 7.0 | 5.0 | 2.3 |"
    ),
    # ── 4.06 Capital Structure – WACC/CAPM ───────────────────────────────────
    "17e887d4-ee3a-4a24-a29a-e80296187806": (
        "| | Common Stock | Preferred Stock |\n"
        "|---|---|---|\n"
        "| Shares outstanding | 1,000,000 | 800,000 |\n"
        "| Issue price | £20.00 | £25.00 |\n"
        "| Current price | £47.60 | £28.00 |\n"
        "| Dividend | £1.00 | £1.80 |\n"
        "| Equity beta | 1.2 | — |\n"
        "| Risk-free rate | 3% | — |\n"
        "| Equity risk premium (ERP) | 5% | — |\n"
        "| Tax rate | 20% | — |"
    ),
    # ── 5.02 Income Statements – diluted EPS ─────────────────────────────────
    "8d11898d-09a9-4c89-8388-47ee7f17a8cd": (
        "| | |\n"
        "|---|---|\n"
        "| Net income | €12.25 million |\n"
        "| Preferred dividends | €0.25 million |\n"
        "| Exercise price | €20 |\n"
        "| Weighted average common shares outstanding | 15 million |\n"
        "| Employee stock options outstanding | 2 million |"
    ),
    # ── 5.05 Cash Flows II – FCFE ────────────────────────────────────────────
    "e0ca3a8a-ed50-47f0-a7ef-5d01a271f8bb": (
        "| Selected Data (SGD millions) | Prior Year | Current Year |\n"
        "|---|---|---|\n"
        "| Net income | 200 | 215 |\n"
        "| Depreciation | 5 | 8 |\n"
        "| Interest expense | 20 | 20 |\n"
        "| Net working capital | 44 | 55 |\n"
        "| Long-term debt | 300 | 295 |\n"
        "| Capital expenditures | 40 | 30 |"
    ),
    # ── 5.05 Cash Flows II – FCFF ────────────────────────────────────────────
    "f3aebf7d-ea7e-479b-b186-ae777d673f69": (
        "| Selected Data (BRL millions) | Prior Year | Current Year |\n"
        "|---|---|---|\n"
        "| Net income | 500 | 550 |\n"
        "| Depreciation | 25 | 40 |\n"
        "| Interest expense | 50 | 50 |\n"
        "| Net working capital | 150 | 170 |\n"
        "| Long-term debt | 100 | 100 |"
    ),
    # ── 5.11 Financial Analysis – LIFO/FIFO ──────────────────────────────────
    "974f206c-25b6-49f5-9a44-9923ad0a5abb": (
        "| Selected Items from Financial Statements | 20X7 | 20X6 |\n"
        "|---|---|---|\n"
        "| Current assets (USD millions) | 1,400 | 1,660 |\n"
        "| Current liabilities (USD millions) | 333 | 400 |"
    ),
    # ── 5.11 Financial Analysis – profitability ratios ───────────────────────
    "3d8e8129-8629-4a6b-b9a7-20d655143003": (
        "| Profitability Ratio (%) | 20X1 | 20X2 | 20X3 |\n"
        "|---|---|---|---|\n"
        "| Gross profit margin | 31.00 | 31.70 | 32.10 |\n"
        "| Operating profit margin | 10.10 | 10.00 | 8.90 |\n"
        "| Pretax margin | 9.90 | 9.90 | 6.90 |"
    ),
    # ── 5.11 Financial Analysis – efficiency vs industry ─────────────────────
    "74e53ac8-ad99-495a-ae73-b07f8b8de771": (
        "| | Company | Industry Average |\n"
        "|---|---|---|\n"
        "| Days of sales outstanding | 45.10 | 30.09 |\n"
        "| Total asset turnover | 1.20 | 1.15 |\n"
        "| Days of inventory on hand | 25.42 | 29.77 |"
    ),
    # ── 6.04 Equity Securities – ROE ─────────────────────────────────────────
    "4098e617-1ba9-40ad-ba8d-b853814ab0ba": (
        "| (GBP millions) | 20X1 | 20X2 | 20X3 |\n"
        "|---|---|---|---|\n"
        "| EBITDA | 45 | 50 | 40 |\n"
        "| Net income | 40 | 35 | 45 |\n"
        "| Assets | 500 | 480 | 500 |\n"
        "| Liabilities | 200 | 200 | 230 |\n"
        "| Market value of equity | 450 | 405 | 687 |"
    ),
    # ── 6.08 Equity Valuation – justified P/E (overvalued?) ──────────────────
    "2909c31e-2ebf-4182-9767-3389073ce98a": (
        "| Selected Data | |\n"
        "|---|---|\n"
        "| Return on equity | 7% |\n"
        "| Dividend payout ratio | 20% |\n"
        "| Required rate of return | 6% |\n"
        "| Weighted average cost of capital | 5% |\n"
        "| Current market price of stock | CNY 52 |\n"
        "| Next year's projected earnings | CNY 1 |"
    ),
    # ── 6.08 Equity Valuation – two-stage DDM ────────────────────────────────
    "3d950279-5d1a-4b5b-818f-9a3b183ce555": (
        "| Selected Data | |\n"
        "|---|---|\n"
        "| Current dividend | €1 |\n"
        "| Annual dividend growth rate, Years 1–3 | 6% |\n"
        "| Annual dividend growth rate, Years 4+ | 3% |\n"
        "| Required rate of return | 4% |"
    ),
    # ── 6.08 Equity Valuation – EV to equity (CHF) ───────────────────────────
    "3dd022f4-ab26-4829-8c17-b0931836c404": (
        "| (CHF millions) | |\n"
        "|---|---|\n"
        "| Market value of preferred stock | 4 |\n"
        "| Short-term investments | 6 |\n"
        "| Market value of debt | 500 |\n"
        "| Cash equivalents | 1 |\n"
        "| Enterprise value | 1,567 |"
    ),
    # ── 6.08 Equity Valuation – EV/EBITDA (€ millions) ───────────────────────
    "96b2e751-28aa-40c6-b8a1-83d2ce8bae66": (
        "| (€ millions) | |\n"
        "|---|---|\n"
        "| Market Value of Preferred Stock | 2,050 |\n"
        "| Short-term Investments | 7,500 |\n"
        "| Market Value of Debt | 90,500 |\n"
        "| Cash Equivalents | 9,000 |\n"
        "| EBITDA | 10,200 |"
    ),
    # ── 6.08 Equity Valuation – justified forward P/E → growth rate ──────────
    "cf241f9a-3699-4f31-8d1b-3deadbbbcf91": (
        "| Selected Data | |\n"
        "|---|---|\n"
        "| Earnings retention ratio | 55% |\n"
        "| Long-term economic growth rate | 4% |\n"
        "| Required rate of return | 9% |\n"
        "| Weighted average cost of capital | 4% |\n"
        "| Company justified forward P/E | 30 |"
    ),
    # ── 7.06 Fixed Income – maturity effect ──────────────────────────────────
    "387e313d-c128-4048-91c6-ae252df6ee2b": (
        "| Bond | Coupon | Maturity (years) | YTM |\n"
        "|---|---|---|---|\n"
        "| A | 0% | 20 | 20% |\n"
        "| B | 0% | 30 | 20% |\n"
        "| C | 10% | 20 | 20% |\n"
        "| D | 10% | 30 | 20% |\n"
        "| E | 25% | 20 | 20% |\n"
        "| F | 25% | 30 | 20% |"
    ),
    # ── 7.07 Yield Spreads – G-spread / I-spread ─────────────────────────────
    "ef6d6cf6-d678-4c62-8de8-f793dcbd5920": (
        "| | Coupon Rate | Price (per 100 Par Value) |\n"
        "|---|---|---|\n"
        "| Two-year government benchmark bond | 4.25% | 98.50 |\n"
        "| Two-year corporate bond | 6.50% | 99.75 |"
    ),
    # ── 7.07 Yield Spreads – I-spread calculation ────────────────────────────
    "770170b4-ce40-486c-8ae2-a0ad70aefeaa": (
        "| Selected Benchmark Data (%) | |\n"
        "|---|---|\n"
        "| 5-year government bond yield | 2.10 |\n"
        "| 5-year interbank lending rate | 4.83 |"
    ),
    # ── 7.14 Credit Risk – notching ──────────────────────────────────────────
    "63c47551-0e39-456c-9205-ceba066509a9": (
        "| Selected Data | |\n"
        "|---|---|\n"
        "| Maturity (years) | 12 |\n"
        "| Coupon (%) | 5 |\n"
        "| Price | 100 |\n"
        "| Modified duration | 8.94 |\n"
        "| Convexity | 80 |"
    ),
    # ── 7.16 Credit Analysis – three companies ───────────────────────────────
    "24fd91bb-7534-4305-89e8-ead9addc2e5a": (
        "| | Total debt/total capital | Total debt/EBITDA | EBITDA/interest expense |\n"
        "|---|---|---|---|\n"
        "| Company X | 84% | 1.80 | 4.46 |\n"
        "| Company Y | 73% | 1.30 | 4.71 |\n"
        "| Company Z | 67% | 1.20 | 8.04 |"
    ),
    # ── 7.19 MBS – mortgage pass-through ─────────────────────────────────────
    "60aedd73-90de-4fee-81a4-31b035604952": (
        "| Mortgage | Remaining balance ($ thousands) | Mortgage rates (%) | Months of maturity remaining |\n"
        "|---|---|---|---|\n"
        "| A | 80 | 4.5 | 48 |\n"
        "| B | 100 | 5.0 | 60 |\n"
        "| C | 120 | 4.7 | 72 |"
    ),
    # ── 1.04 Probability Trees – CEO compensation ────────────────────────────
    "1af08d3f-b8ac-4fa7-abf1-651a97c253dc": (
        "| Event | Probability |\n"
        "|---|---|\n"
        "| Probability that company's EPS does not increase | 0.60 |\n"
        "| Probability that CEO's compensation does not increase given EPS does not increase | 0.90 |\n"
        "| Probability that CEO's compensation increases given EPS increases | 0.80 |"
    ),
    # ── 1.10 Simple Linear Regression – crude oil / gross margin ─────────────
    "a86e4c7c-2cd9-4f38-9cbb-90390b4d7236": (
        "| Regression statistics | |\n"
        "|---|---|\n"
        "| Coefficient of determination (R²) | 0.541 |\n"
        "| Standard error (Sε) | 1.841 |\n"
        "| Observations (quarters) (n) | 12 |\n"
        "\n"
        "| Coefficients | |\n"
        "|---|---|\n"
        "| Intercept | 9.358 |\n"
        "| Crude oil | 0.581 |\n"
        "\n"
        "| Descriptive statistics (Crude oil) | |\n"
        "|---|---|\n"
        "| Mean (X̄) | 55.408 |\n"
        "| Standard deviation (Sx) | 3.397 |"
    ),
}

# ── Fetch current question_en for all 28 questions ────────────────────────────
qids = list(TABLES.keys())
rows = sb.table("questions").select("id,question_en").in_("id", qids).execute().data
by_id = {r["id"]: r["question_en"] for r in rows}

done = errors = skipped = 0
for qid, table in TABLES.items():
    q_en = by_id.get(qid)
    if not q_en:
        print(f"  {qid[:8]} NOT IN DB")
        skipped += 1
        continue

    # Skip if table already inserted
    if "|---|" in q_en:
        print(f"  {qid[:8]} already has table — skip")
        skipped += 1
        continue

    m = COLON_SPLIT_RE.search(q_en)
    if not m:
        print(f"  {qid[:8]} NO SPLIT POINT found in: {q_en[:80]!r}")
        skipped += 1
        continue

    split_pos = m.start(2)
    new_q = q_en[:split_pos].rstrip() + "\n\n" + table + "\n\n" + q_en[split_pos:]

    try:
        sb.table("questions").update({"question_en": new_q}).eq("id", qid).execute()
        done += 1
        print(f"  {qid[:8]} OK ({len(table)} chars table)")
    except Exception as e:
        print(f"  {qid[:8]} ERROR: {e}")
        errors += 1

print(f"\nDone: {done} updated, {skipped} skipped, {errors} errors")
