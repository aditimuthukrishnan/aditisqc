"""
Shared styling and theme configuration.
"""

import streamlit as st

# Color palette
COLORS = {
    'primary': '#1a1a2e',
    'secondary': '#16213e',
    'accent': '#0f3460',
    'highlight': '#e94560',
    'success': '#06d6a0',
    'warning': '#ffd166',
    'danger': '#ef476f',
    'muted': '#8d99ae',
    'bg': '#f8f9fa',
    'card': '#ffffff',
    'i30': '#ef476f',
    'i40': '#118ab2',
    'i50': '#06d6a0',
}

PARADIGM_COLORS = ['#ef476f', '#118ab2', '#06d6a0']
PARADIGM_NAMES = ['Industry 3.0', 'Industry 4.0', 'Industry 5.0']


def apply_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        h1, h2, h3 {
            color: #1a1a2e;
            font-weight: 600;
            letter-spacing: -0.02em;
        }

        .page-title {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.2rem;
            letter-spacing: -0.03em;
        }

        .page-subtitle {
            font-size: 0.95rem;
            color: #8d99ae;
            margin-bottom: 2rem;
            font-weight: 400;
        }

        .metric-row {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .card {
            background: #ffffff;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 1.2rem 1.5rem;
            margin-bottom: 1rem;
        }

        .card-label {
            font-size: 0.78rem;
            color: #8d99ae;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 500;
            margin-bottom: 0.3rem;
        }

        .card-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a2e;
            line-height: 1.1;
        }

        .card-delta {
            font-size: 0.82rem;
            margin-top: 0.3rem;
            font-weight: 500;
        }

        .delta-good { color: #06d6a0; }
        .delta-bad { color: #ef476f; }
        .delta-neutral { color: #8d99ae; }

        .suggestion-card {
            background: #f8f9fa;
            border-left: 3px solid #118ab2;
            border-radius: 0 8px 8px 0;
            padding: 1rem 1.2rem;
            margin-bottom: 0.8rem;
        }

        .suggestion-card.critical {
            border-left-color: #ef476f;
        }

        .suggestion-card.warning {
            border-left-color: #ffd166;
        }

        .suggestion-card.info {
            border-left-color: #118ab2;
        }

        .suggestion-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #1a1a2e;
            margin-bottom: 0.3rem;
        }

        .suggestion-body {
            font-size: 0.85rem;
            color: #495057;
            line-height: 1.5;
        }

        .section-divider {
            border: none;
            border-top: 1px solid #e9ecef;
            margin: 2rem 0;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 1rem 1.2rem;
        }

        div[data-testid="stMetric"] label {
            font-size: 0.78rem;
            color: #8d99ae;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1a1a2e;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            border-bottom: 1px solid #e9ecef;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 0;
            padding: 0.6rem 1.2rem;
            font-weight: 500;
            font-size: 0.88rem;
        }

        .stSidebar {
            background: #f8f9fa;
        }

        .stSidebar [data-testid="stSidebarContent"] {
            padding-top: 1.5rem;
        }
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, delta=None, delta_type="neutral"):
    delta_html = ""
    if delta:
        css_class = f"delta-{delta_type}"
        delta_html = f'<div class="card-delta {css_class}">{delta}</div>'

    st.markdown(f"""
    <div class="card">
        <div class="card-label">{label}</div>
        <div class="card-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def suggestion_card(title, body, level="info"):
    st.markdown(f"""
    <div class="suggestion-card {level}">
        <div class="suggestion-title">{title}</div>
        <div class="suggestion-body">{body}</div>
    </div>
    """, unsafe_allow_html=True)


def section_divider():
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
