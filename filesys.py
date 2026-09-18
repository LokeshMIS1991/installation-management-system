import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import random
import string
import os

# Page Configuration
st.set_page_config(
    page_title="Sidharth Shutter & Automation", 
    page_icon="🏢",
    layout="wide"
)

# Render High-Quality Logo in Navigation Bar (Sidebar)
LOGO_PATH = "Company Logo.jpeg"  # Ensure the image file is in the working directory

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.markdown("### 🏢 Sidharth Shutter")

st.sidebar.markdown("---")

# Custom CSS Theme based on Logo Palette
st.markdown("""
    <style>
    /* Global Page Styling */
    .stApp {
        background-color: #FAFCFE;
    }

    /* Custom Header Styling */
    h1, h2, h3 {
        color: #0F4C81 !important;
        font-weight: 700 !important;
    }

    /* Primary Buttons Styling (Logo Green Accent) */
    div.stButton > button:first-child {
        background-color: #00A651 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    div.stButton > button:first-child:hover {
        background-color: #008741 !important;
        box-shadow: 0 4px 10px rgba(0, 166, 81, 0.3) !important;
    }

    /* Form Submit & Primary Action Buttons (Deep Blue) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #0F4C81 0%, #1A6BBA 100%) !important;
        color: white !important;
        border: none !important;
    }
    
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0A375E 0%, #0F4C81 100%) !important;
        box-shadow: 0 4px 10px rgba(15, 76, 129, 0.3) !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #F0F5FA !important;
        border-right: 2px solid #0F4C81 !important;
    }

    /* Sidebar Logo Padding Cleanup */
    section[data-testid="stSidebar"] [data-testid="stImage"] {
        padding-top: 10px;
        padding-bottom: 10px;
    }

    /* Sidebar Radio Highlights */
    div[role="radiogroup"] label[data-baseweb="radio"] div:first-child {
        background-color: #0F4C81 !important;
    }

    /* Input Field Focus Borders */
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus, .stTextArea>div>div>textarea:focus {
        border-color: #00A651 !important;
        box-shadow: 0 0 0 1px #00A651 !important;
    }

    /* Tab Headers Styling */
    button[data-baseweb="tab"] {
        color: #0F4C81 !important;
        font-weight: 600 !important;
    }

    button[aria-selected="true"] {
        color: #00A651 !important;
        border-bottom-color: #00A651 !important;
    }
    </style>
""", unsafe_allow_html=True)
