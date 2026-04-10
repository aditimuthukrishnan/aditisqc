"""
Shared styling and theme configuration.
"""

import streamlit as st

PARADIGM_COLORS = ['#ef476f', '#118ab2', '#06d6a0']
PARADIGM_NAMES = ['Industry 3.0', 'Industry 4.0', 'Industry 5.0']


def apply_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1100px;
        }

        h1, h2, h3, h4, h5 {
            color: #1a1a2e !important;
            font-weight: 600;
            letter-spacing: -0.01em;
        }

        .page-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1a1a2e !important;
            margin-bottom: 0.1rem;
            letter-spacing: -0.02em;
        }

        .page-subtitle {
            font-size: 0.9rem;
            color: #6c757d !important;
            margin-bottom: 1.8rem;
            font-weight: 400;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 0.9rem 1rem;
        }

        div[data-testid="stMetric"] label {
            font-size: 0.72rem !important;
            color: #6c757d !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 700;
            color: #1a1a2e !important;
        }

        .suggestion-card {
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-left: 3px solid #118ab2;
            border-radius: 0 6px 6px 0;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.7rem;
        }

        .suggestion-card.critical {
            border-left-color: #ef476f;
            background: #fff5f5;
        }

        .suggestion-card.warning {
            border-left-color: #ffd166;
            background: #fffdf5;
        }

        .suggestion-card.info {
            border-left-color: #118ab2;
            background: #f5faff;
        }

        .suggestion-title {
            font-weight: 600;
            font-size: 0.88rem;
            color: #1a1a2e !important;
            margin-bottom: 0.25rem;
        }

        .suggestion-body {
            font-size: 0.82rem;
            color: #495057 !important;
            line-height: 1.55;
        }

        .section-divider {
            border: none;
            border-top: 1px solid #e9ecef;
            margin: 1.5rem 0;
        }

        section[data-testid="stSidebar"] {
            background: #f8f9fa !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            border-bottom: 1px solid #dee2e6;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 0;
            padding: 0.5rem 1rem;
            font-weight: 500;
            font-size: 0.85rem;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
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