"""
WIB CFA — Global CSS styles injection.
Call inject_styles() at the top of every page.
"""

import streamlit as st


# ── Question rendering helpers (defined first for easy import) ────────────────

def render_question(question_text: str) -> None:
    """Render question with full Markdown support (enables table rendering)."""
    if '\n' in question_text:
        parts = question_text.split('\n', 1)
        first = parts[0].strip()
        rest = parts[1].strip()
        if first:
            st.markdown(f"**{first}**")
        if rest:
            st.markdown(rest)
    else:
        st.markdown(f"**{question_text}**")


def question_first_line(question_text: str, max_chars: int = 120) -> str:
    """Return only the first prose line of a question for compact displays."""
    first = question_text.split('\n')[0].strip()
    return (first[:max_chars] + "…") if len(first) > max_chars else first


# ── CSS injection ─────────────────────────────────────────────────────────────

def inject_styles():
    st.markdown(
        """
        <style>
        /* ── Google Fonts ─────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

        /* ── CSS Variables ────────────────────────────────────────────── */
        :root {
            --navy:   #0B2545;
            --gold:   #C9A84C;
            --gold-light: #E8C97A;
            --bg:     #F8F9FB;
            --bg2:    #EEF0F5;
            --text:   #1A1A2E;
            --white:  #FFFFFF;
            --green:  #1B7F4F;
            --red:    #B52B2B;
            --green-bg: #E8F5EE;
            --red-bg:   #FDECEC;
            --shadow: 0 2px 12px rgba(11,37,69,0.10);
        }

        /* ── Base ─────────────────────────────────────────────────────── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: var(--text);
            background-color: var(--bg);
        }

        h1, h2, h3 {
            font-family: 'Playfair Display', serif;
            color: var(--navy);
        }

        /* ── Hide auto-generated page nav (custom sidebar links used instead) */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* ── Sidebar ──────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background-color: var(--navy) !important;
        }
        section[data-testid="stSidebar"] * {
            color: var(--white) !important;
        }
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stSlider label {
            color: var(--gold) !important;
            font-weight: 600;
        }

        /* ── Buttons ──────────────────────────────────────────────────── */
        .stButton > button {
            background-color: var(--navy) !important;
            color: var(--gold) !important;
            border: 2px solid var(--gold) !important;
            border-radius: 6px !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
            transition: background-color 0.2s, color 0.2s;
            padding: 0.45rem 1.2rem;
        }
        .stButton > button:hover {
            background-color: var(--gold) !important;
            color: var(--navy) !important;
        }
        .stButton > button:active {
            transform: scale(0.98);
        }

        /* ── Cards ────────────────────────────────────────────────────── */
        .wib-card {
            background: var(--white);
            border-left: 4px solid var(--gold);
            border-radius: 8px;
            padding: 1.4rem 1.6rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }
        .wib-card h3 {
            margin-top: 0;
            font-size: 1.1rem;
            color: var(--navy);
        }

        /* ── Metric cards ─────────────────────────────────────────────── */
        .metric-card {
            background: var(--navy);
            color: var(--white);
            border-radius: 10px;
            padding: 1.2rem 1.4rem;
            text-align: center;
            box-shadow: var(--shadow);
        }
        .metric-card .metric-value {
            font-family: 'Playfair Display', serif;
            font-size: 2.4rem;
            font-weight: 700;
            color: var(--gold);
            line-height: 1.1;
        }
        .metric-card .metric-label {
            font-size: 0.82rem;
            color: rgba(255,255,255,0.75);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-top: 4px;
        }

        /* ── Hero banner ──────────────────────────────────────────────── */
        .wib-hero {
            background: linear-gradient(135deg, var(--navy) 0%, #163a6b 100%);
            border-radius: 12px;
            padding: 2rem 2.5rem;
            margin-bottom: 1.5rem;
            color: var(--white);
        }
        .wib-hero .brand {
            font-family: 'Playfair Display', serif;
            font-size: 2.8rem;
            font-weight: 700;
            color: var(--gold);
            letter-spacing: 2px;
        }
        .wib-hero .tagline {
            font-size: 1.05rem;
            color: rgba(255,255,255,0.85);
            margin-top: 4px;
        }

        /* ── Ticker ───────────────────────────────────────────────────── */
        .ticker-wrapper {
            background: var(--navy);
            color: var(--gold);
            padding: 6px 0;
            overflow: hidden;
            border-radius: 6px;
            margin-bottom: 1.5rem;
            font-family: 'Inter', monospace;
            font-size: 0.82rem;
            font-weight: 500;
        }
        .ticker-inner {
            display: inline-block;
            white-space: nowrap;
            animation: ticker-scroll 28s linear infinite;
        }
        @keyframes ticker-scroll {
            0%   { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        .ticker-item { margin-right: 3rem; }
        .ticker-up   { color: #5DDE91; }
        .ticker-down { color: #FF6B6B; }

        /* ── Progress bars ────────────────────────────────────────────── */
        .stProgress > div > div > div > div {
            background-color: var(--gold) !important;
        }

        /* ── Answer feedback ──────────────────────────────────────────── */
        .answer-correct {
            background-color: var(--green-bg);
            border-left: 4px solid var(--green);
            border-radius: 6px;
            padding: 1rem 1.2rem;
            color: var(--green);
            font-weight: 600;
        }
        .answer-wrong {
            background-color: var(--red-bg);
            border-left: 4px solid var(--red);
            border-radius: 6px;
            padding: 1rem 1.2rem;
            color: var(--red);
            font-weight: 600;
        }
        .explanation-box {
            background: var(--bg2);
            border-radius: 6px;
            padding: 1rem 1.2rem;
            margin-top: 0.8rem;
            font-size: 0.93rem;
            line-height: 1.6;
        }

        /* ── Flashcard ────────────────────────────────────────────────── */
        .flashcard-front {
            background: linear-gradient(135deg, var(--navy) 0%, #1a4a8a 100%);
            color: var(--white);
            border-radius: 12px;
            padding: 2.5rem 2rem;
            min-height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            box-shadow: var(--shadow);
        }
        .flashcard-front .concept {
            font-family: 'Playfair Display', serif;
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--gold);
        }
        .flashcard-back {
            background: var(--white);
            border: 2px solid var(--gold);
            border-radius: 12px;
            padding: 1.8rem 2rem;
            box-shadow: var(--shadow);
        }
        .formula-box {
            background: var(--navy);
            color: var(--gold);
            font-family: 'Courier New', monospace;
            border-radius: 6px;
            padding: 0.7rem 1rem;
            font-size: 0.95rem;
            margin-top: 0.8rem;
        }

        /* ── Tables (dataframe + markdown) ───────────────────────────── */
        .dataframe thead tr th {
            background-color: var(--navy) !important;
            color: var(--gold) !important;
            font-family: 'Inter', sans-serif;
        }
        .dataframe tbody tr:nth-child(even) {
            background-color: var(--bg2);
        }

        /* Markdown tables inside st.markdown() — question data tables */
        [data-testid="stMarkdownContainer"] table {
            border-collapse: collapse;
            width: auto;
            margin: 0.7rem 0 0.9rem 0;
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(11,37,69,0.10);
        }
        [data-testid="stMarkdownContainer"] table th {
            background-color: var(--navy) !important;
            color: var(--gold) !important;
            padding: 7px 16px;
            text-align: left;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        [data-testid="stMarkdownContainer"] table td {
            border: 1px solid #dde0e8;
            padding: 7px 16px;
            background-color: var(--white);
            color: var(--text);
        }
        [data-testid="stMarkdownContainer"] table tr:nth-child(even) td {
            background-color: var(--bg2);
        }

        /* ── Section headers ──────────────────────────────────────────── */
        .section-header {
            border-bottom: 2px solid var(--gold);
            padding-bottom: 6px;
            margin-bottom: 1rem;
            font-family: 'Playfair Display', serif;
            color: var(--navy);
            font-size: 1.3rem;
            font-weight: 700;
        }

        /* ── Topic badge ──────────────────────────────────────────────── */
        .topic-badge {
            display: inline-block;
            background: var(--navy);
            color: var(--gold);
            border-radius: 20px;
            padding: 3px 12px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.4px;
            margin-right: 4px;
        }
        .difficulty-easy   { background: #d4edda; color: #155724; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; }
        .difficulty-medium { background: #fff3cd; color: #856404; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; }
        .difficulty-hard   { background: #f8d7da; color: #721c24; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; }

        /* ── Pass/Fail banners ────────────────────────────────────────── */
        .pass-banner {
            background: linear-gradient(135deg, #1B7F4F, #2ecc71);
            color: white;
            text-align: center;
            padding: 1.5rem;
            border-radius: 10px;
            font-family: 'Playfair Display', serif;
            font-size: 1.8rem;
            font-weight: 700;
        }
        .fail-banner {
            background: linear-gradient(135deg, #B52B2B, #e74c3c);
            color: white;
            text-align: center;
            padding: 1.5rem;
            border-radius: 10px;
            font-family: 'Playfair Display', serif;
            font-size: 1.8rem;
            font-weight: 700;
        }

        /* ── Responsive ───────────────────────────────────────────────── */
        @media (max-width: 768px) {
            .wib-hero .brand { font-size: 2rem; }
            .metric-card .metric-value { font-size: 1.8rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_ticker():
    st.markdown(
        """
        <div class="ticker-wrapper">
          <div class="ticker-inner">
            <span class="ticker-item">CAC 40 &nbsp;<strong>5,234</strong>&nbsp;<span class="ticker-up">▲ 1.2%</span></span>
            <span class="ticker-item">S&amp;P 500 &nbsp;<strong>5,678</strong>&nbsp;<span class="ticker-up">▲ 0.8%</span></span>
            <span class="ticker-item">EUR/USD &nbsp;<strong>1.0823</strong>&nbsp;<span class="ticker-down">▼ 0.1%</span></span>
            <span class="ticker-item">Brent Crude &nbsp;<strong>$82.4</strong>&nbsp;<span class="ticker-down">▼ 0.3%</span></span>
            <span class="ticker-item">10Y UST &nbsp;<strong>4.35%</strong>&nbsp;<span class="ticker-up">▲ 2bp</span></span>
            <span class="ticker-item">Gold &nbsp;<strong>$2,318</strong>&nbsp;<span class="ticker-up">▲ 0.5%</span></span>
            <span class="ticker-item">USD/JPY &nbsp;<strong>154.2</strong>&nbsp;<span class="ticker-down">▼ 0.2%</span></span>
            <span class="ticker-item">DAX &nbsp;<strong>18,450</strong>&nbsp;<span class="ticker-up">▲ 0.6%</span></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(subtitle: str = "Who Wants to Be an Investment Banker?"):
    st.markdown(
        f"""
        <div class="wib-hero">
            <div class="brand">WIB</div>
            <div class="tagline">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(value: str, label: str):
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


