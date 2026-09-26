import streamlit as st

COLOR_PRIMARY = "#10418A"
COLOR_ACCENT = "#00A859"
COLOR_BG_LIGHT = "#EBF3FA"


def apply_custom_styles():
    """Applies global CSS themes and styling across all Streamlit views."""
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: #F4F7FC;
        }}
        h1, h2, h3 {{ 
            color: {COLOR_PRIMARY} !important; 
            font-weight: 700 !important; 
        }}
        .stButton>button {{ 
            background-color: {COLOR_ACCENT} !important; 
            background: {COLOR_ACCENT} !important; 
            color: #FFFFFF !important; 
            border-radius: 8px !important;
            border: none !important;
            font-weight: 700 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 12px rgba(0, 168, 89, 0.3) !important;
        }}
        .stButton>button * {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }}
        .stButton>button:hover {{ 
            background-color: #008747 !important; 
            background: #008747 !important; 
            color: #FFFFFF !important; 
            box-shadow: 0 6px 15px rgba(0, 168, 89, 0.45) !important;
        }}
        .card-box {{ 
            background-color: {COLOR_BG_LIGHT}; 
            border-left: 6px solid {COLOR_PRIMARY}; 
            padding: 18px; 
            border-radius: 8px; 
            margin-bottom: 15px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .client-card {{
            background-color: #FFFFFF;
            border-left: 5px solid {COLOR_ACCENT};
            padding: 12px 18px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }}
        .kpi-card {{
            background-color: #FFFFFF;
            border: 2px solid {COLOR_PRIMARY};
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 10px;
        }}
        .kpi-number {{
            font-size: 28px;
            font-weight: bold;
            color: {COLOR_PRIMARY};
        }}
        .kpi-label {{
            font-size: 13px;
            color: #6C757D;
            font-weight: 600;
        }}
        section[data-testid="stSidebar"] {{
            background-color: #EBF1F8;
        }}
        section[data-testid="stSidebar"] .block-container {{
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
        }}
        div[data-testid="stForm"] div[data-baseweb="input"],
        div[data-testid="stForm"] div[data-baseweb="select"] > div {{
            border: 2px solid {COLOR_PRIMARY} !important;
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
        }}
        div[data-testid="stForm"] label {{
            color: {COLOR_PRIMARY} !important;
            font-weight: 700 !important;
        }}
        div[data-testid="stForm"] {{
            background-color: #FFFFFF;
            border: 2px solid {COLOR_PRIMARY};
            border-radius: 16px;
            padding: 24px 18px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
        }}
        div[data-testid="stFormSubmitButton"] > button {{
            background-color: {COLOR_ACCENT} !important;
            background: {COLOR_ACCENT} !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            padding: 12px 20px !important;
            font-size: 15px !important;
            border: none !important;
            width: 100% !important;
            min-height: 48px !important;
            margin-top: 15px !important;
        }}
        </style>
    """,
        unsafe_allow_html=True,
    )
