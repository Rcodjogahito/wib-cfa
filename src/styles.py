"""
WIB CFA — Global CSS styles injection.
Call inject_styles() at the top of every page.
"""

import streamlit as st
import streamlit.components.v1 as _components


# ── Question rendering helpers ────────────────────────────────────────────────

def render_question(question_text: str) -> None:
    """Render question with full Markdown support (enables table rendering)."""
    safe = question_text.replace('$', r'\$')
    if '\n' in safe:
        parts = safe.split('\n', 1)
        first = parts[0].strip()
        rest = parts[1].strip()
        if first:
            st.markdown(f"**{first}**")
        if rest:
            st.markdown(rest)
    else:
        st.markdown(f"**{safe}**")


def question_first_line(question_text: str, max_chars: int = 120) -> str:
    """Return only the first prose line of a question for compact displays."""
    first = question_text.split('\n')[0].strip()
    return (first[:max_chars] + "…") if len(first) > max_chars else first


# ── CSS injection ─────────────────────────────────────────────────────────────

def inject_styles():
    st.markdown(
        """
        <style>
        /* ── Hide Streamlit Cloud toolbar (Fork / Share / ⋮) ──────────── */
        header[data-testid="stHeader"]   { display: none !important; }
        [data-testid="stDecoration"]     { display: none !important; }
        #MainMenu                        { display: none !important; }
        footer                           { display: none !important; }

        /* ── Fonts ─────────────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        /* ── Design tokens ─────────────────────────────────────────────── */
        :root {
            /* Brand navy */
            --navy-950:  #04101F;
            --navy-900:  #071426;
            --navy-800:  #0C1D3A;
            --navy-700:  #142E58;
            --navy-600:  #1C3F78;
            --navy-100:  #EEF3FA;
            /* Brand gold */
            --gold-500:  #C9A84C;
            --gold-400:  #DFC06E;
            --gold-300:  #EDD08E;
            --gold-100:  #F9F0D6;
            /* Neutrals */
            --white:     #FFFFFF;
            --gray-25:   #FAFBFC;
            --gray-50:   #F4F6FA;
            --gray-100:  #E8ECF3;
            --gray-200:  #CDD3DE;
            --gray-400:  #8A95A8;
            --gray-600:  #4A5568;
            --gray-800:  #1A2337;
            /* Semantic */
            --success:        #0D5E35;
            --success-bg:     #EBF7F2;
            --success-border: #1B9E5C;
            --error:          #8B1C1C;
            --error-bg:       #FDF0F0;
            --error-border:   #CC3333;
            /* Shape */
            --radius-sm: 3px;
            --radius:    6px;
            --radius-lg: 10px;
            /* Shadows */
            --shadow-xs: 0 1px 3px rgba(7,20,38,0.07);
            --shadow-sm: 0 2px 8px rgba(7,20,38,0.10);
            --shadow-md: 0 4px 18px rgba(7,20,38,0.14);
        }

        /* ── Base ─────────────────────────────────────────────────────── */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--gray-800);
            background-color: var(--gray-25);
        }
        .main .block-container {
            padding-top: 1.75rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3 {
            font-family: 'Cormorant Garamond', Georgia, serif;
            color: var(--navy-800);
            letter-spacing: -0.01em;
        }

        /* ── Hide Streamlit auto-nav ───────────────────────────────────── */
        [data-testid="stSidebarNav"] { display: none !important; }

        /* ── Sidebar ──────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background-color: var(--navy-900) !important;
            border-right: 1px solid rgba(201,168,76,0.12) !important;
        }
        section[data-testid="stSidebar"] * {
            color: rgba(255,255,255,0.82) !important;
        }
        section[data-testid="stSidebar"] a {
            color: rgba(255,255,255,0.65) !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.02em !important;
            transition: color 0.15s !important;
            text-decoration: none !important;
        }
        section[data-testid="stSidebar"] a:hover {
            color: var(--gold-400) !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.08) !important;
            margin: 0.75rem 0 !important;
        }
        /* ── Sidebar buttons (Sign out, etc.) ────────────────────────── */
        section[data-testid="stSidebar"] .stButton > button {
            background-color: rgba(255,255,255,0.07) !important;
            color: rgba(255,255,255,0.80) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            border-left: 3px solid transparent !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] .stButton > button p,
        section[data-testid="stSidebar"] .stButton > button span,
        section[data-testid="stSidebar"] .stButton > button div {
            color: rgba(255,255,255,0.80) !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: rgba(201,168,76,0.18) !important;
            color: var(--gold-400) !important;
            border-left-color: var(--gold-500) !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover p,
        section[data-testid="stSidebar"] .stButton > button:hover span {
            color: var(--gold-400) !important;
        }

        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stRadio label {
            color: var(--gold-300) !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
        }

        /* ── Buttons — default (answer panels + secondary actions) ───── */
        .stButton > button {
            background-color: var(--white) !important;
            color: var(--gray-800) !important;
            border: 1px solid var(--gray-200) !important;
            border-left: 3px solid transparent !important;
            border-radius: var(--radius) !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.005em !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding: 0.7rem 1.25rem !important;
            min-height: 48px !important;
            width: 100% !important;
            transition: border-color 0.15s, background-color 0.15s, box-shadow 0.15s !important;
            box-shadow: var(--shadow-xs) !important;
        }
        /* Force left-align on ALL inner Streamlit button elements */
        .stButton > button p,
        .stButton > button span,
        .stButton > button div {
            text-align: left !important;
            color: inherit !important;
            justify-content: flex-start !important;
        }
        .stButton > button:hover {
            border-left-color: var(--gold-500) !important;
            background-color: var(--gold-100) !important;
            color: var(--navy-800) !important;
            box-shadow: var(--shadow-sm) !important;
        }
        .stButton > button:hover p,
        .stButton > button:hover span,
        .stButton > button:hover div {
            color: var(--navy-800) !important;
        }
        /* Kill Streamlit's gold focus-color on non-primary buttons */
        .stButton > button:focus,
        .stButton > button:focus-visible,
        .stButton > button:focus p,
        .stButton > button:focus span {
            color: var(--gray-800) !important;
            outline: 2px solid var(--gold-300) !important;
            outline-offset: 2px !important;
            box-shadow: none !important;
        }
        .stButton > button:active {
            transform: translateY(1px) !important;
        }
        .stButton > button:disabled {
            opacity: 0.38 !important;
            cursor: not-allowed !important;
        }

        /* ── Buttons — primary (CTA actions) ─────────────────────────── */
        [data-testid="baseButton-primary"],
        .stButton > button[kind="primary"] {
            background-color: var(--navy-800) !important;
            color: var(--gold-500) !important;
            border: none !important;
            border-left: 3px solid transparent !important;
            font-weight: 600 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            font-size: 0.76rem !important;
            text-align: center !important;
            justify-content: center !important;
            box-shadow: var(--shadow-sm) !important;
        }
        [data-testid="baseButton-primary"] p,
        [data-testid="baseButton-primary"] span,
        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span {
            color: var(--gold-500) !important;
            text-align: center !important;
        }
        [data-testid="baseButton-primary"]:hover,
        .stButton > button[kind="primary"]:hover {
            background-color: var(--navy-700) !important;
            color: var(--gold-400) !important;
            box-shadow: var(--shadow-md) !important;
        }

        /* ── Form inputs ──────────────────────────────────────────────── */
        .stSelectbox [data-baseweb="select"] > div,
        .stTextInput > div > div > input {
            border-color: var(--gray-200) !important;
            border-radius: var(--radius) !important;
            background-color: var(--white) !important;
            font-size: 0.875rem !important;
            color: var(--gray-800) !important;
        }
        .stSelectbox [data-baseweb="select"] > div:focus-within,
        .stTextInput > div > div > input:focus {
            border-color: var(--gold-500) !important;
            box-shadow: 0 0 0 3px rgba(201,168,76,0.15) !important;
        }
        .stCheckbox label {
            font-size: 0.875rem !important;
            color: var(--gray-600) !important;
        }

        /* ── Cards ────────────────────────────────────────────────────── */
        .wib-card {
            background: var(--white);
            border: 1px solid var(--gray-100);
            border-top: 3px solid var(--gold-500);
            border-radius: var(--radius-lg);
            padding: 1.5rem 1.75rem;
            box-shadow: var(--shadow-sm);
            margin-bottom: 1rem;
        }
        .wib-card h3 {
            margin-top: 0;
            font-size: 1.1rem;
            color: var(--navy-800);
        }

        /* ── Metric cards ─────────────────────────────────────────────── */
        .metric-card {
            background: var(--navy-800);
            border: 1px solid rgba(201,168,76,0.18);
            border-radius: var(--radius-lg);
            padding: 1.25rem 1.5rem;
            text-align: center;
            box-shadow: var(--shadow-sm);
            position: relative;
            overflow: hidden;
        }
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--gold-500), var(--gold-300));
        }
        .metric-card .metric-value {
            font-family: 'IBM Plex Mono', 'Courier New', monospace;
            font-size: 2.1rem;
            font-weight: 500;
            color: var(--gold-500);
            line-height: 1.1;
            letter-spacing: -0.02em;
        }
        .metric-card .metric-label {
            font-size: 0.68rem;
            color: rgba(255,255,255,0.50);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-top: 6px;
            font-weight: 600;
        }

        /* ── Page header (inner pages) ────────────────────────────────── */
        .wib-page-header {
            padding: 0.75rem 0 1.25rem 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--gray-100);
        }
        /* Brand identity row: WIB · Who wants to be an Investment Banker? */
        .wib-page-header .brand-identity {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 0 0.40rem;
            margin-bottom: 8px;
        }
        .wib-page-header .brand-mark-word {
            font-family: 'Cormorant Garamond', serif;
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--gold-500);
            letter-spacing: 0.12em;
        }
        .wib-page-header .brand-sep {
            font-size: 0.72rem;
            color: rgba(201,168,76,0.42);
            font-weight: 400;
        }
        .wib-page-header .brand-fullname {
            font-family: 'Cormorant Garamond', serif;
            font-size: 0.88rem;
            font-weight: 400;
            font-style: italic;
            color: var(--gray-600);
            letter-spacing: 0.005em;
            text-transform: none !important;
        }
        .wib-page-header .page-title {
            font-family: 'Cormorant Garamond', serif;
            font-size: 2.1rem;
            font-weight: 400;
            color: var(--navy-800);
            line-height: 1.1;
            letter-spacing: -0.01em;
        }
        .wib-page-header .page-subtitle {
            font-size: 0.80rem;
            color: var(--gray-400);
            margin-top: 6px;
            font-weight: 400;
            letter-spacing: 0.01em;
        }

        /* ── Hero (home page) ────────────────────────────────────────── */
        .wib-hero {
            background: var(--navy-900);
            border-radius: var(--radius-lg);
            padding: 2rem 2.5rem;
            margin-bottom: 1.75rem;
            position: relative;
            overflow: hidden;
        }
        .wib-hero::after {
            content: '';
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 1.5px;
            background: linear-gradient(90deg, var(--gold-500) 0%, transparent 55%);
        }
        /* Single thin gold rule above wordmark */
        .wib-hero .brand-rule { margin-bottom: 16px; }
        .wib-hero .brand-rule::after {
            content: ''; display: block;
            height: 1px; width: 38px;
            background: rgba(201,168,76,0.45);
        }
        .wib-hero .brand {
            font-family: 'EB Garamond', 'Cormorant Garamond', serif;
            font-size: 3.1rem;
            font-weight: 500;
            color: #FFFFFF;
            letter-spacing: 0.16em;
            text-indent: 0.16em;
            line-height: 1;
        }
        .wib-hero .tagline {
            font-size: 0.66rem;
            color: rgba(201,168,76,0.62);
            margin-top: 14px;
            font-weight: 400;
            letter-spacing: 0.20em;
            text-indent: 0.20em;
            text-transform: none !important;
        }

        /* ── Ticker ───────────────────────────────────────────────────── */
        .ticker-wrapper {
            background: var(--navy-950);
            border: 1px solid rgba(201,168,76,0.14);
            padding: 7px 0;
            overflow: hidden;
            border-radius: var(--radius);
            margin-bottom: 1.5rem;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.76rem;
            font-weight: 400;
        }
        .ticker-inner {
            display: inline-block;
            white-space: nowrap;
            animation: ticker-scroll 34s linear infinite;
        }
        @keyframes ticker-scroll {
            0%   { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        .ticker-item { margin-right: 3.5rem; color: rgba(255,255,255,0.55); }
        .ticker-item strong { color: var(--white); font-weight: 500; }
        .ticker-up   { color: #4ADE80; }
        .ticker-down { color: #F87171; }

        /* ── Progress bar ─────────────────────────────────────────────── */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, var(--navy-700), var(--gold-500)) !important;
        }

        /* ── Question card wrapper ────────────────────────────────────── */
        .question-card {
            background: var(--white);
            border: 1px solid var(--gray-100);
            border-radius: var(--radius-lg);
            padding: 1.5rem 1.75rem 1.25rem 1.75rem;
            margin-bottom: 1rem;
            box-shadow: var(--shadow-xs);
            font-size: 0.95rem;
            line-height: 1.7;
            color: var(--gray-800);
        }
        .question-card strong, .question-card b {
            color: var(--navy-800);
            font-weight: 600;
        }

        /* ── Answer section label ──────────────────────────────────────── */
        .answer-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: var(--gray-400);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.5rem;
            margin-top: 0.25rem;
        }

        /* ── Progress label ────────────────────────────────────────────── */
        .progress-label {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.78rem;
            font-weight: 500;
            color: var(--gray-400);
            letter-spacing: 0.04em;
            margin-bottom: 0.4rem;
        }

        /* ── Answer feedback ──────────────────────────────────────────── */
        .answer-correct {
            background: var(--success-bg);
            border: 1px solid rgba(27,158,92,0.25);
            border-left: 4px solid var(--success);
            border-radius: var(--radius);
            padding: 0.85rem 1.2rem;
            color: var(--success);
            font-weight: 600;
            font-size: 0.875rem;
        }
        .answer-wrong {
            background: var(--error-bg);
            border: 1px solid rgba(204,51,51,0.20);
            border-left: 4px solid var(--error);
            border-radius: var(--radius);
            padding: 0.85rem 1.2rem;
            color: var(--error);
            font-weight: 600;
            font-size: 0.875rem;
        }
        .explanation-box {
            background: var(--gray-50);
            border: 1px solid var(--gray-100);
            border-left: 3px solid var(--gold-500);
            border-radius: var(--radius);
            padding: 1rem 1.25rem;
            margin-top: 0.75rem;
            font-size: 0.86rem;
            line-height: 1.68;
            color: var(--gray-600);
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .explanation-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: var(--gold-500);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-top: 0.75rem;
            margin-bottom: 0.15rem;
        }

        /* ── Section header ───────────────────────────────────────────── */
        .section-header {
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.35rem;
            font-weight: 600;
            color: var(--navy-800);
            letter-spacing: -0.01em;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--gray-100);
            margin-bottom: 1.25rem;
            position: relative;
        }
        .section-header::after {
            content: '';
            display: block;
            width: 36px;
            height: 2px;
            background: var(--gold-500);
            position: absolute;
            bottom: -1px;
            left: 0;
        }

        /* ── Badges ───────────────────────────────────────────────────── */
        .topic-badge {
            display: inline-block;
            background: var(--navy-100);
            color: var(--navy-800);
            border: 1px solid rgba(12,29,58,0.10);
            border-radius: var(--radius-sm);
            padding: 2px 8px;
            font-size: 0.70rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-right: 5px;
        }
        .difficulty-easy   { background: var(--success-bg);  color: var(--success); border-radius: var(--radius-sm); padding: 2px 8px; font-size: 0.70rem; font-weight: 600; border: 1px solid rgba(13,94,53,0.15); }
        .difficulty-medium { background: #FFF8E8; color: #7A5C00; border-radius: var(--radius-sm); padding: 2px 8px; font-size: 0.70rem; font-weight: 600; border: 1px solid rgba(122,92,0,0.15); }
        .difficulty-hard   { background: var(--error-bg);    color: var(--error);   border-radius: var(--radius-sm); padding: 2px 8px; font-size: 0.70rem; font-weight: 600; border: 1px solid rgba(139,28,28,0.15); }

        /* ── Flashcard ────────────────────────────────────────────────── */
        .flashcard-front {
            background: var(--navy-800);
            border-radius: var(--radius-lg);
            padding: 2.5rem 2rem;
            min-height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            box-shadow: var(--shadow-md);
            position: relative;
            overflow: hidden;
        }
        .flashcard-front::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--gold-500), var(--gold-300));
        }
        .flashcard-front .concept {
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.8rem;
            font-weight: 600;
            color: var(--gold-500);
            line-height: 1.2;
        }
        .flashcard-back {
            background: var(--white);
            border: 1px solid var(--gray-100);
            border-top: 3px solid var(--gold-500);
            border-radius: var(--radius-lg);
            padding: 1.75rem 2rem;
            box-shadow: var(--shadow-sm);
        }
        .formula-box {
            background: var(--gray-50);
            border: 1px solid var(--gray-100);
            color: var(--navy-800);
            font-family: 'IBM Plex Mono', monospace;
            border-radius: var(--radius);
            padding: 0.75rem 1rem;
            font-size: 0.9rem;
            margin-top: 0.75rem;
            letter-spacing: -0.01em;
        }

        /* ── Data tables (dataframe) ──────────────────────────────────── */
        .dataframe thead tr th {
            background-color: var(--navy-800) !important;
            color: var(--gold-500) !important;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }
        .dataframe tbody tr:nth-child(even) { background-color: var(--gray-25); }
        .dataframe tbody tr:hover { background-color: var(--gold-100) !important; }

        /* Markdown tables in question text */
        [data-testid="stMarkdownContainer"] table {
            border-collapse: collapse;
            width: auto;
            margin: 0.75rem 0 1rem 0;
            font-family: 'Inter', sans-serif;
            font-size: 0.84rem;
            border-radius: var(--radius);
            overflow: hidden;
            border: 1px solid var(--gray-200);
            box-shadow: var(--shadow-xs);
        }
        [data-testid="stMarkdownContainer"] table th {
            background-color: var(--navy-800) !important;
            color: var(--gold-500) !important;
            padding: 8px 16px;
            font-weight: 700;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        [data-testid="stMarkdownContainer"] table td {
            border-bottom: 1px solid var(--gray-100);
            padding: 7px 16px;
            background-color: var(--white);
            color: var(--gray-800);
        }
        [data-testid="stMarkdownContainer"] table tr:last-child td { border-bottom: none; }
        [data-testid="stMarkdownContainer"] table tr:nth-child(even) td { background-color: var(--gray-25); }

        /* ── Pass / Fail banners ──────────────────────────────────────── */
        .pass-banner {
            background: var(--success-bg);
            border: 1px solid rgba(27,158,92,0.25);
            border-top: 3px solid var(--success);
            color: var(--success);
            text-align: center;
            padding: 1.5rem 2rem;
            border-radius: var(--radius-lg);
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.8rem;
            font-weight: 700;
        }
        .fail-banner {
            background: var(--error-bg);
            border: 1px solid rgba(204,51,51,0.20);
            border-top: 3px solid var(--error);
            color: var(--error);
            text-align: center;
            padding: 1.5rem 2rem;
            border-radius: var(--radius-lg);
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.8rem;
            font-weight: 700;
        }

        /* ── Help button (? popover) ──────────────────────────────────── */
        .wib-help-wrap {
            display: flex;
            justify-content: flex-end;
            align-items: flex-start;
            padding-top: 1.5rem;
        }
        .wib-help-wrap button[kind="secondary"],
        .wib-help-wrap button {
            border-radius: 50% !important;
            width: 2rem !important;
            height: 2rem !important;
            min-height: 2rem !important;
            padding: 0 !important;
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            background: var(--navy-100) !important;
            color: var(--navy-600) !important;
            border: 1.5px solid rgba(12,29,58,0.18) !important;
            line-height: 1 !important;
            box-shadow: none !important;
            transition: background 0.15s, color 0.15s, border-color 0.15s !important;
        }
        .wib-help-wrap button:hover {
            background: var(--navy-700) !important;
            color: #fff !important;
            border-color: var(--navy-700) !important;
        }

        /* ── Responsive ───────────────────────────────────────────────── */
        @media (max-width: 768px) {
            .wib-hero .brand { font-size: 2.4rem; letter-spacing: 0.12em; text-indent: 0.12em; }
            .wib-hero .tagline { font-size: 0.70rem; }
            .metric-card .metric-value { font-size: 1.7rem; }
            .metric-card { padding: 0.85rem 0.7rem; }
            .wib-page-header .page-title { font-size: 1.65rem; }
            .wib-page-header .brand-fullname { font-size: 0.80rem; }

            /* Quiz / question options — full width stacked on mobile */
            .question-option {
                padding: 0.75rem 0.9rem;
                font-size: 0.9rem;
            }

            /* Flashcard front/back — tighter padding */
            .flashcard-front, .flashcard-back {
                padding: 1.4rem 1.1rem;
                min-height: 160px;
            }

            /* Pass/fail banner — fit on small screen */
            .pass-banner, .fail-banner {
                font-size: 1.2rem;
                padding: 1rem 1.2rem;
            }

            /* Topic badge wraps gracefully */
            .topic-badge {
                font-size: 0.68rem;
                padding: 0.22rem 0.55rem;
            }

            /* Study content — reduce side padding */
            .study-content {
                padding: 1rem 0.9rem;
            }
        }

        @media (max-width: 480px) {
            .wib-hero .brand { font-size: 2rem; }
            .metric-card .metric-value { font-size: 1.5rem; }
            .metric-card .metric-label { font-size: 0.65rem; }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
    # Mobile sidebar — URL polling + reload() + instant CSS hide.
    # Why location.replace(cur) failed: React calls history.pushState('/Quiz')
    # BEFORE our poll fires. The browser is already at /Quiz, so replace('/Quiz')
    # is treated as a same-URL navigation (soft reload or no-op in some browsers).
    # Fix: use location.reload() which always forces a true server round-trip
    # regardless of how the current URL was set.
    # Anti-flash: hide sidebar via CSS the instant we detect the URL change —
    # before the 50ms delay — so the user never sees the brief open state.
    _components.html(
        """
        <script>
        (function() {
            function isMobile() {
                try { return window.parent.innerWidth < 768; } catch(e) { return false; }
            }
            function setup() {
                try {
                    var par = window.parent;
                    if (par._wibInit) return;
                    par._wibInit = true;
                    var lastHref = par.location.href;
                    setInterval(function() {
                        try {
                            var cur = par.location.href;
                            if (cur === lastHref) return;
                            lastHref = cur;
                            if (!isMobile()) return;
                            // 1. Instant visual hide — eliminates the open-sidebar flash
                            try {
                                var sb = par.document.querySelector(
                                    'section[data-testid="stSidebar"]'
                                );
                                if (sb) {
                                    sb.style.setProperty('transform', 'translateX(-110%)', 'important');
                                    sb.style.setProperty('transition', 'none', 'important');
                                }
                            } catch(ignore) {}
                            // 2. Clear any Streamlit localStorage sidebar state
                            try {
                                var ls = par.localStorage;
                                var rm = [];
                                for (var i = 0; i < ls.length; i++) {
                                    var k = ls.key(i);
                                    if (k && /sidebar/i.test(k)) rm.push(k);
                                }
                                rm.forEach(function(k) { ls.removeItem(k); });
                            } catch(ignore) {}
                            // 3. reload() — forces a real server round-trip, unlike
                            //    replace(cur) which is a no-op when already at cur
                            setTimeout(function() { par.location.reload(); }, 50);
                        } catch(e) {}
                    }, 100);
                } catch(e) {}
            }
            setTimeout(setup, 200);
        })();
        </script>
        """,
        height=1,
    )


# ── Component helpers ─────────────────────────────────────────────────────────

# Original logo — kept verbatim, referenced as "logo initial" if rollback needed.
_SIDEBAR_BRAND_ORIGINAL = """
<div style="font-family:'Cormorant Garamond',Georgia,serif;font-size:1.9rem;font-weight:700;color:#C9A84C;letter-spacing:5px;line-height:1;">WIB</div>
<div style="font-size:0.63rem;color:rgba(255,255,255,0.38);letter-spacing:0.20em;text-transform:uppercase;margin-top:4px;font-weight:600;">CFA Level I</div>
"""

_SIDEBAR_BRAND = """
<div style="padding:4px 0 12px 0;">
  <div style="height:1px;width:30px;background:rgba(201,168,76,0.45);margin-bottom:13px;"></div>
  <div style="font-family:'EB Garamond','Cormorant Garamond',Georgia,serif;font-size:1.72rem;font-weight:500;color:#FFFFFF;letter-spacing:0.16em;text-indent:0.16em;line-height:1;">WIB</div>
  <div style="height:1px;background:linear-gradient(90deg,rgba(201,168,76,0.50) 0%,transparent 80%);margin:10px 0 8px 0;"></div>
  <div style="font-family:'Inter',sans-serif;font-size:0.52rem;color:rgba(201,168,76,0.62);letter-spacing:0.22em;text-indent:0.22em;text-transform:uppercase;font-weight:500;">CFA &middot; Level I</div>
</div>
"""


def render_sidebar_brand():
    """Inject the WIB brand mark inside st.sidebar context."""
    st.markdown(_SIDEBAR_BRAND, unsafe_allow_html=True)


def render_sidebar_user(username: str) -> None:
    """Display pseudo in sidebar — call inside st.sidebar context."""
    st.markdown(
        f'<div style="font-size:0.85rem;font-weight:600;color:rgba(255,255,255,0.90);'
        f'letter-spacing:0.02em;">{username}</div>',
        unsafe_allow_html=True,
    )


def render_hero(subtitle: str = "Who wants to be an Investment Banker?"):
    """Full hero banner — home page only."""
    st.markdown(
        f"""
        <div class="wib-hero">
            <div class="brand-rule"></div>
            <div class="brand">WIB</div>
            <div class="tagline" style="text-transform:none!important">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str = "", help_text: str = ""):
    """Refined page header for inner pages. Pass help_text to show a ? popover."""
    sub_html = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    header_html = f"""
        <div class="wib-page-header">
            <div class="brand-identity">
                <span class="brand-mark-word">WIB</span>
                <span class="brand-sep">&middot;</span>
                <span class="brand-fullname" style="text-transform:none!important">Who wants to be an Investment Banker?</span>
            </div>
            <div class="page-title">{title}</div>
            {sub_html}
        </div>
        """
    if help_text:
        col_h, col_btn = st.columns([20, 1])
        with col_h:
            st.markdown(header_html, unsafe_allow_html=True)
        with col_btn:
            st.markdown('<div class="wib-help-wrap">', unsafe_allow_html=True)
            with st.popover("?"):
                st.markdown(help_text)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(header_html, unsafe_allow_html=True)


def render_ticker():
    st.markdown(
        """
        <div class="ticker-wrapper">
          <div class="ticker-inner">
            <span class="ticker-item">CAC 40 &nbsp;<strong>5,234</strong>&nbsp;<span class="ticker-up">&#9650; 1.2%</span></span>
            <span class="ticker-item">S&amp;P 500 &nbsp;<strong>5,678</strong>&nbsp;<span class="ticker-up">&#9650; 0.8%</span></span>
            <span class="ticker-item">EUR/USD &nbsp;<strong>1.0823</strong>&nbsp;<span class="ticker-down">&#9660; 0.1%</span></span>
            <span class="ticker-item">Brent Crude &nbsp;<strong>$82.4</strong>&nbsp;<span class="ticker-down">&#9660; 0.3%</span></span>
            <span class="ticker-item">10Y UST &nbsp;<strong>4.35%</strong>&nbsp;<span class="ticker-up">&#9650; 2bp</span></span>
            <span class="ticker-item">Gold &nbsp;<strong>$2,318</strong>&nbsp;<span class="ticker-up">&#9650; 0.5%</span></span>
            <span class="ticker-item">USD/JPY &nbsp;<strong>154.2</strong>&nbsp;<span class="ticker-down">&#9660; 0.2%</span></span>
            <span class="ticker-item">DAX &nbsp;<strong>18,450</strong>&nbsp;<span class="ticker-up">&#9650; 0.6%</span></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(value: str, label: str) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """
