# app.py

import io
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Import static options from config.py
from config import (
    DELAY_REASONS,
    HOLD_REASONS,
    PRODUCT_CATALOG,
    STATUS_OPTIONS,
    TASK_CATEGORIES,
)

# ==========================================
# 0. CONFIGURATION & CONSTANTS
# ==========================================
DRIVE_FOLDER_ID = "0ADjIFMwZGB62Uk9PVA"

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "Company Logo.jpeg"


# ==========================================
# 1. HELPER FUNCTIONS & VIEW LOGS MODULE
# ==========================================
def render_view_logs_and_update_status():
    st.markdown("## 🔍 View Daily Logs & Update Status")

    # 1. Fetch data from Google Sheets
    df_sites = read_sheet("Sites_Master")
    if df_sites.empty:
        st.warning("No installation records found.")
        return

    # 2. Standardize column headers
    df_sites.columns = [
        str(col).strip().lower().replace(" ", "_") for col in df_sites.columns
    ]

    site_map = {}
    site_data = {}

    # 3. Process each site record and filter out Handovered / Completed sites
    for _, s in df_sites.iterrows():
        site_id = str(s.get("installation_id", "")).strip()
        status = str(s.get("status") or "In Progress").strip().title()

        if not site_id or status in ["Handovered", "Handover", "Completed"]:
            continue

        c_name = str(
            s.get("client_name")
            or s.get("client")
            or s.get("company_name")
            or "N/A"
        ).strip()
        c_phone = str(
            s.get("client_phone")
            or s.get("mobile_no")
            or s.get("phone")
            or "N/A"
        ).strip()
        city = str(s.get("site_city") or s.get("city") or "N/A").strip()
        lead = str(s.get("team_lead") or s.get("lead") or "N/A").strip()

        display_label = f"{site_id} — {c_name}" if c_name != "N/A" else site_id

        site_map[display_label] = site_id
        site_data[site_id] = {
            "client_name": c_name,
            "client_phone": c_phone,
            "city": city,
            "team_lead": lead,
            "status": status,
        }

    if not site_map:
        st.info("No active installation sites found (all sites completed or handovered).")
        return

    # 4. Dropdown for Site Selection
    selected_label = st.selectbox(
        "Select Installation ID",
        options=list(site_map.keys()),
        key="view_logs_site_select",
    )

    selected_id = site_map[selected_label]
    info = site_data[selected_id]

    # 5. Display Installation Details
    st.markdown(
        f"""
        <div style="background-color: #f0f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #1E3A8A; margin-top: 15px; margin-bottom: 20px;">
            <h2 style="color: #1E3A8A; margin-top: 0; margin-bottom: 10px;">{selected_id}</h2>
            <p style="margin: 5px 0;"><strong>Client Name:</strong> {info['client_name']} | <strong>Client Mobile:</strong> {info['client_phone']}</p>
            <p style="margin: 5px 0;"><strong>City:</strong> {info['city']} | <strong>Team Lead:</strong> {info['team_lead']}</p>
            <p style="margin: 5px 0;"><strong>Current Status:</strong> {info['status']}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # 6. Dynamic Status Update Controls with Mandatory On-Hold Handling
    col_st, col_btn = st.columns([2, 1])
    with col_st:
        curr_st = info["status"]
        st_idx = (
            STATUS_OPTIONS.index(curr_st) if curr_st in STATUS_OPTIONS else 0
        )
        new_st = st.selectbox(
            "Update Status",
            STATUS_OPTIONS,
            index=st_idx,
            key="update_status_selectbox",
        )

    hold_reason_val = ""
    hold_remark_val = ""

    if new_st == "On Hold":
        st.warning("⚠️ Site is being placed On Hold. A reason is mandatory.")
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            hold_reason_val = st.selectbox(
                "Mandatory Reason for Hold *",
                HOLD_REASONS,
                key="hold_reason_select",
            )
        with c_r2:
            if hold_reason_val == "Other":
                hold_remark_val = st.text_input(
                    "Specific Hold Remarks (Mandatory for 'Other') *",
                    key="hold_remark_input",
                )

    with col_btn:
        st.write(" ")
        st.write(" ")
        if st.button("Update Status", key="btn_update_site_status"):
            if new_st == "On Hold":
                if hold_reason_val == "Other" and not hold_remark_val.strip():
                    st.error("Please enter specific remarks when selecting 'Other'.")
                    st.stop()
                
                final_hold_note = (
                    f"On Hold Reason: {hold_reason_val} - {hold_remark_val}"
                    if hold_reason_val == "Other"
                    else f"On Hold Reason: {hold_reason_val}"
                )
                update_sheet_row(
                    "Sites_Master",
                    "installation_id",
                    selected_id,
                    {"status": new_st, "hold_reason": final_hold_note},
                )
            else:
                update_sheet_row(
                    "Sites_Master",
                    "installation_id",
                    selected_id,
                    {"status": new_st},
                )

            st.success(f"Status updated to **{new_st}**!")
            st.rerun()

    # 7. Submitted Field Logs
    st.divider()
    st.subheader("📜 Submitted Work Logs")
    df_logs = read_sheet("Worker_Daily_Logs")
    p_logs = (
        df_logs[df_logs["installation_id"] == selected_id]
        if not df_logs.empty and "installation_id" in df_logs.columns
        else pd.DataFrame()
    )

    if not p_logs.empty:
        for _, l in p_logs.iterrows():
            day_lbl = l.get("site_day", "")
            header_prefix = f"[{day_lbl}] " if day_lbl else ""
            with st.expander(
                f"📅 {header_prefix}Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Role: {l.get('worker_role', 'N/A')}"
            ):
                st.write(f"**Task Category:** {l.get('task_category')}")
                st.write(f"**Task Description:** {l.get('task_name')}")
                st.write(
                    f"**Time Spent:** {l.get('hours_spent')} hrs {l.get('minutes_spent')} mins"
                )
                st.write(f"**Travel Day (TA/DA):** {l.get('is_travel_day')}")
                st.write(f"**Photo Attached:** {l.get('site_photo', 'No Photo')}")
                st.write(
                    f"**Remarks / Cause of Delay:** {l.get('site_remarks', 'None')}"
                )
    else:
        st.info("No submitted field logs found for this installation ID.")


# ==========================================
# 2. PAGE CONFIG & RESPONSIVE GLOBAL THEME
# ==========================================
st.set_page_config(
    page_title="Sidharth Shutter & Automation - Portal",
    layout="wide",
    page_icon="⚙️",
    initial_sidebar_state="auto",
)

COLOR_PRIMARY = "#10418A"
COLOR_ACCENT = "#00A859"
COLOR_BG_LIGHT = "#EBF3FA"

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

# ==========================================
# 3. GOOGLE SHEETS & DRIVE ENGINE
# ==========================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_credentials():
    """Reads GCP credentials from Streamlit secrets and auto-corrects literal '\\n' in private key."""
    creds_dict = dict(st.secrets["gcp_service_account"])

    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)


@st.cache_resource
def get_gspread_client():
    creds = get_credentials()
    return gspread.authorize(creds)


@st.cache_resource
def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


DRIVE_FOLDER_ID = st.secrets.get("drive_folder_id", "0ADjIFMwZGB62Uk9PVA")


def upload_file_to_drive(uploaded_file, file_name):
    """Uploads a file to Google Drive and makes it accessible via link."""
    try:
        service = get_drive_service()

        file_metadata = {
            "name": file_name,
            "parents": [DRIVE_FOLDER_ID],
        }

        media = MediaIoBaseUpload(
            io.BytesIO(uploaded_file.getvalue()),
            mimetype=uploaded_file.type,
            resumable=True,
        )

        file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )

        file_id = file.get("id")

        user_permission = {
            "type": "anyone",
            "role": "reader",
        }
        service.permissions().create(
            fileId=file_id,
            body=user_permission,
            fields="id",
            supportsAllDrives=True,
        ).execute()

        return file.get("webViewLink", "")

    except Exception as e:
        st.error(f"Error uploading image to Google Drive: {e}")
        return "Upload Failed"


def get_workbook():
    client = get_gspread_client()
    sheet_url = st.secrets.get(
        "spreadsheet_url",
        "https://docs.google.com/spreadsheets/d/19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s/edit",
    )
    return client.open_by_url(sheet_url)


@st.cache_data(ttl=60)
def read_sheet(sheet_name: str) -> pd.DataFrame:
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error reading tab '{sheet_name}': {e}")
        return pd.DataFrame()


def append_to_sheet(sheet_name: str, row_data_dict: dict):
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        headers = sheet.row_values(1)
        if not headers:
            headers = list(row_data_dict.keys())
            sheet.append_row(headers)
        row_values = [str(row_data_dict.get(h, "")) for h in headers]
        sheet.append_row(row_values)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error writing to tab '{sheet_name}': {e}")


def update_sheet_row(
    sheet_name: str, key_col: str, key_val: str, update_dict: dict
) -> bool:
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        if df.empty or key_col not in df.columns:
            return False
        match_idx = df[df[key_col].astype(str) == str(key_val)].index
        if match_idx.empty:
            return False
        row_num = match_idx[0] + 2
        headers = sheet.row_values(1)
        for col_name, new_val in update_dict.items():
            if col_name in headers:
                col_num = headers.index(col_name) + 1
                sheet.update_cell(row_num, col_num, str(new_val))
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error updating tab '{sheet_name}': {e}")
        return False


def generate_excel_download(df, filename="report.xlsx"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()


# ==========================================
# 4. AUTHENTICATION
# ==========================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "remembered_username" not in st.session_state:
    st.session_state.remembered_username = ""

if not st.session_state.authenticated_user:
    st.write("##")
    col_l, col_center, col_r = st.columns([1, 1.2, 1])
    with col_center:
        st.markdown(
            '<div style="max-width: 420px; margin: 0 auto;">',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), use_container_width=True)
            else:
                st.markdown(
                    f"""
                    <div style="text-align: center;">
                        <h1 style="color: {COLOR_PRIMARY}; margin: 0; font-size: 26px;">SIDHARTH</h1>
                        <p style="color: {COLOR_ACCENT}; font-weight: bold; margin: 0; font-size: 12px; letter-spacing: 2px;">SHUTTER & AUTOMATION</p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

            st.caption("Enterprise Operations & Field Portal")

            username_input = st.text_input(
                "Username / Name",
                value=st.session_state.remembered_username,
                placeholder="e.g. Parvesh Kumar or Vishak",
            )
            password_input = st.text_input(
                "Password / PIN", type="password", placeholder="Enter password"
            )

            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                show_pass = st.checkbox("Show Password")
            with col_chk2:
                remember_me = st.checkbox(
                    "Remember Me",
                    value=bool(st.session_state.remembered_username),
                )

            submit_button = st.form_submit_button(
                "🔑 LOGIN TO DASHBOARD", use_container_width=True
            )

            if submit_button:
                if not username_input or not password_input:
                    st.error("Please fill in both Username and Password.")
                else:
                    df_workers = read_sheet("Workers_Master")
                    if not df_workers.empty:
                        user_row = df_workers[
                            (
                                df_workers["name"]
                                .astype(str)
                                .str.strip()
                                .str.lower()
                                == username_input.strip().lower()
                            )
                            & (
                                df_workers["pin"].astype(str)
                                == str(password_input).strip()
                            )
                        ]
                        if not user_row.empty:
                            st.session_state.authenticated_user = user_row.iloc[
                                0
                            ].to_dict()
                            st.session_state.remembered_username = (
                                username_input.strip() if remember_me else ""
                            )
                            st.success("Authentication Successful!")
                            st.rerun()
                        else:
                            st.error("Invalid Username or Password.")
                    else:
                        st.error(
                            "⚠️ Database Unreachable — Verify Google Sheets setup."
                        )
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 5. ACTIVE SESSION & SIDEBAR
# ==========================================
user = st.session_state.authenticated_user
user_name = user.get("name", "User")
user_role = user.get("role", "Worker")
user_base_location = user.get("base_location", "Jaipur")

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), use_container_width=True)
else:
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; padding: 12px; background-color: {COLOR_PRIMARY}; color: white; border-radius: 8px; margin-bottom: 10px;">
            <h2 style="margin:0; font-size: 21px; color: white !important;">SIDHARTH</h2>
            <p style="margin:0; font-size: 11px; letter-spacing: 1.5px; color: {COLOR_ACCENT}; font-weight: bold;">SHUTTER & AUTOMATION</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    f"**Active User:** {user_name} (`{user_role}`)  \n**Base Station:**"
    f" {user_base_location}"
)
st.sidebar.divider()

if user_role == "Admin":
    menu_options = [
        "Admin Analytics Dashboard",
        "Employee Analytics & Reports",
        "User Management",
        "TA/DA Payroll & Travel Summary",
        "Advanced Field Logs Inspector",
        "Master Database",
    ]
elif user_role == "Supervisor":
    menu_options = [
        "New Installation Order",
        "Log Daily Tasks",
        "View Logs & Update Status",
        "Handover Date Dashboard",
        "Active Tasks Dashboard",
        "Employee Analytics & Reports",
        "Team Head Dashboard",
        "Master Database",
    ]
else:  # Worker
    menu_options = [
        "My Work Dashboard",
        "Log Daily Tasks",
        "My Work History & Performance",
        "My Profile & Settings",
    ]

menu = st.sidebar.radio("Navigation Menu", menu_options)

st.sidebar.divider()

if st.sidebar.button("🚪 LOG OUT", use_container_width=True):
    st.session_state.authenticated_user = None
    st.rerun()


# ==========================================
# 6. DYNAMIC WORK INPUT HELPER WITH SUCCESS MODAL
# ==========================================
@st.dialog("🎉 Daily Log Submitted Successfully!")
def show_upload_success_modal(site_id, day_label, records_count):
    st.write("### Great Job! 🚀")
    st.markdown(
        f"""
        Your **{records_count} task(s)** and photos for **{site_id} ({day_label})** have been uploaded and saved directly to the database.
        
        * All entries have been synchronized.
        * The entry form has been cleared for your next log.
        """
    )
    if st.button("Close & Continue", use_container_width=True, key="btn_close_success_dialog"):
        st.session_state["show_success_modal"] = False
        st.rerun()


def render_restricted_work_input(target_worker_name, is_crew_log=False):
    if st.session_state.get("show_success_modal"):
        m_info = st.session_state.get("modal_info", {})
        show_upload_success_modal(
            m_info.get("site_id", ""),
            m_info.get("day_label", ""),
            m_info.get("count", 1)
        )

    form_version_key = f"form_version_{target_worker_name}_{is_crew_log}"
    if form_version_key not in st.session_state:
        st.session_state[form_version_key] = 0
    v = st.session_state[form_version_key]

    df_sites = read_sheet("Sites_Master")
    df_workers = read_sheet("Workers_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    valid_site_map = {}
    site_info_dict = {}

    if not df_sites.empty and "installation_id" in df_sites.columns:
        today_date = datetime.now().date()

        for _, s in df_sites.iterrows():
            site_id = str(s.get("installation_id", "")).strip()
            status = str(s.get("status", "")).strip().lower()
            c_name = str(s.get("client_name", "N/A")).strip() or "N/A"
            c_phone = str(s.get("client_phone", "N/A")).strip() or "N/A"
            handover_str = str(s.get("handover_date", "")).strip()

            if status in ["handovered", "handover", "completed"]:
                continue

            if handover_str:
                try:
                    h_date = pd.to_datetime(handover_str).date()
                    if today_date > h_date:
                        continue
                except Exception:
                    pass

            display_label = f"{site_id} — {c_name}"
            valid_site_map[display_label] = site_id
            site_info_dict[site_id] = {
                "client_name": c_name,
                "client_phone": c_phone,
                "city": s.get("site_city", "Jaipur"),
                "address": s.get("site_address", "N/A"),
            }

    if not valid_site_map:
        st.warning("⚠️ No Active Installation Sites Available.")
        return

    header_placeholder = st.empty()

    c_site, c_date = st.columns(2)
    with c_site:
        selected_display_label = st.selectbox(
            "Current Logging for :",
            list(valid_site_map.keys()),
            key=f"site_{target_worker_name}_{is_crew_log}_v{v}",
        )
        selected_site_id = valid_site_map[selected_display_label]

    with c_date:
        log_date = st.date_input(
            "Date of Work",
            value=datetime.now(),
            key=f"date_{target_worker_name}_{is_crew_log}_v{v}",
        )

    site_days_count = 1
    if not df_logs.empty and "installation_id" in df_logs.columns and "logged_date" in df_logs.columns:
        site_logs = df_logs[df_logs["installation_id"] == selected_site_id]
        logged_dates = sorted(site_logs["logged_date"].astype(str).unique())

        cur_date_str = str(log_date)
        if cur_date_str in logged_dates:
            site_days_count = logged_dates.index(cur_date_str) + 1
        else:
            site_days_count = len(logged_dates) + 1

    site_day_label = f"Day {site_days_count}"

    header_placeholder.markdown(f"## 📝 Log Daily Tasks - {selected_site_id} ({site_day_label})")

    site_meta = site_info_dict[selected_site_id]
    st.markdown(
        f"""
        <div class="client-card">
            <span style="font-size:15px; font-weight:700; color:{COLOR_PRIMARY};">🏢 Client Name: {site_meta['client_name']}</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span style="font-size:15px; font-weight:700; color:{COLOR_ACCENT};">📞 Contact Mobile: <a href="tel:{site_meta['client_phone']}" style="color:{COLOR_ACCENT}; text-decoration:none;">{site_meta['client_phone']}</a></span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span style="font-size:15px; font-weight:700; color:{COLOR_PRIMARY};">📅 Current Timeline: <strong>{site_day_label}</strong></span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    site_city = site_meta["city"]

    if not df_workers.empty and "name" in df_workers.columns:
        if "role" in df_workers.columns:
            filtered_workers = df_workers[
                ~df_workers["role"]
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(["supervisor", "admin"])
            ]
            worker_options = sorted(
                filtered_workers["name"].astype(str).str.strip().unique().tolist()
            )
        else:
            worker_options = sorted(
                df_workers["name"].astype(str).str.strip().unique().tolist()
            )
    else:
        worker_options = [target_worker_name]

    st.markdown("### 👥 Crew & Team Assignment")
    col_lead, col_helpers = st.columns(2)

    with col_lead:
        default_lead_idx = (
            worker_options.index(target_worker_name)
            if target_worker_name in worker_options
            else 0
        )
        team_lead_selected = st.selectbox(
            "Team Lead Name *",
            options=worker_options,
            index=default_lead_idx,
            key=f"team_lead_{target_worker_name}_{is_crew_log}_v{v}",
        )

    with col_helpers:
        available_helpers = [
            w for w in worker_options if w != team_lead_selected
        ]
        team_helpers_selected = st.multiselect(
            "Team Members / Helpers",
            options=available_helpers,
            key=f"helpers_{target_worker_name}_{is_crew_log}_v{v}",
        )

    active_crew = [team_lead_selected] + team_helpers_selected

    st.write("##")
    st.markdown("### 🛠️ Tasks Completed Today")

    task_count_key = f"task_lines_count_{target_worker_name}_{is_crew_log}_v{v}"
    if task_count_key not in st.session_state:
        st.session_state[task_count_key] = 1

    task_entries = []

    for i in range(st.session_state[task_count_key]):
        st.caption(f"**Task Line #{i+1}**")
        col_cat, col_desc, col_assigned, col_hrs, col_min = st.columns(
            [2.5, 3, 2.5, 1.2, 1.2]
        )

        with col_cat:
            cat = st.selectbox(
                f"Category #{i+1}",
                TASK_CATEGORIES,
                key=f"cat_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_desc:
            desc = st.text_input(
                f"Task #{i+1} Description",
                placeholder="e.g., Track Leveling",
                key=f"desc_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_assigned:
            assigned_worker = st.selectbox(
                f"Assigned To #{i+1}",
                options=active_crew,
                key=f"assigned_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_hrs:
            hrs = st.number_input(
                "Hours",
                min_value=0,
                max_value=24,
                value=2,
                step=1,
                key=f"hrs_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_min:
            mins = st.selectbox(
                "Minutes",
                [0, 15, 30, 45],
                key=f"min_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )

        task_entries.append(
            {
                "category": cat,
                "description": desc,
                "assigned_worker": assigned_worker,
                "hours": hrs,
                "minutes": mins,
            }
        )

    if st.button(
        "➕ ADD MORE TASK LINES",
        key=f"add_task_btn_{target_worker_name}_{is_crew_log}_v{v}",
    ):
        st.session_state[task_count_key] += 1
        st.rerun()

    st.divider()

    st.markdown("### ⚠️ Site Remarks / Delays")
    col_delay_cat, col_delay_notes = st.columns([1, 2])

    with col_delay_cat:
        delay_reason = st.selectbox(
            "Primary Delay Category",
            options=DELAY_REASONS,
            key=f"delay_reason_{target_worker_name}_{is_crew_log}_v{v}",
        )

    with col_delay_notes:
        site_remarks = st.text_area(
            "Specific Site Notes / Remarks",
            placeholder="Provide details...",
            key=f"rem_{target_worker_name}_{is_crew_log}_v{v}",
        )

    st.markdown("### 📷 Site Photo Documentation")
    uploaded_photo = st.file_uploader(
        "Upload Photo of Site",
        type=["jpg", "jpeg", "png"],
        key=f"photo_{target_worker_name}_{is_crew_log}_v{v}",
    )

    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Uploaded Site Photo Preview", width=280)

    st.write("##")

    if st.button(
        "💾 Sync Daily Log to Database",
        key=f"btn_sync_{target_worker_name}_{is_crew_log}_v{v}",
        use_container_width=True,
    ):
        valid_tasks = [t for t in task_entries if t["description"].strip()]
        
        if not valid_tasks:
            st.error("Please enter at least one task description before syncing.")
            return

        photo_link = "No Photo"
        if uploaded_photo is not None:
            photo_name = f"{selected_site_id}_{target_worker_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_link = upload_file_to_drive(uploaded_photo, photo_name)

        records_saved = 0

        for idx, t in enumerate(valid_tasks):
            worker = t["assigned_worker"]
            w_base = "Jaipur"
            if not df_workers.empty:
                m = df_workers[df_workers["name"] == worker]
                if not m.empty:
                    w_base = m.iloc[0].get("base_location", "Jaipur")

            w_is_travel = (
                str(w_base).strip().lower() != str(site_city).strip().lower()
            )

            log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx+1}"
            log_entry = {
                "log_id": log_id,
                "installation_id": selected_site_id,
                "site_day": site_day_label,
                "logged_date": str(log_date),
                "worker_name": worker,
                "worker_role": (
                    "Team Lead" if worker == team_lead_selected else "Helper"
                ),
                "team_lead_name": team_lead_selected,
                "task_category": t["category"],
                "task_name": t["description"],
                "hours_spent": t["hours"],
                "minutes_spent": t["minutes"],
                "base_location": w_base,
                "site_city": site_city,
                "is_travel_day": "Yes" if w_is_travel else "No",
                "delay_category": delay_reason,
                "site_remarks": site_remarks,
                "site_photo": photo_link,
                "logged_by": target_worker_name,
            }
            append_to_sheet("Worker_Daily_Logs", log_entry)
            records_saved += 1

        if records_saved > 0:
            st.session_state["show_success_modal"] = True
            st.session_state["modal_info"] = {
                "site_id": selected_site_id,
                "day_label": site_day_label,
                "count": records_saved,
            }
            st.session_state[form_version_key] += 1
            st.rerun()


# ==========================================
# 7. ROUTING & MODULE IMPLEMENTATION
# ==========================================

# --- WORKER: MY WORK DASHBOARD ---
if menu == "My Work Dashboard":
    st.header(f"⚡ Daily Workspace & Task Pipeline — {user_name}")
    st.caption(
        "Track your assigned site duties, update live task progress, and view"
        " performance metrics."
    )

    df_tasks = read_sheet("Task_Assignments")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    st.markdown("### 🏆 Performance & Metrics Scorecard")

    my_logs = pd.DataFrame()
    if not df_logs.empty and "worker_name" in df_logs.columns:
        my_logs = df_logs[
            df_logs["worker_name"].astype(str).str.strip().str.lower()
            == user_name.strip().lower()
        ]

    days_worked = (
        my_logs["logged_date"].nunique()
        if not my_logs.empty and "logged_date" in my_logs.columns
        else 0
    )
    days_travelled = (
        len(my_logs[my_logs["is_travel_day"] == "Yes"])
        if not my_logs.empty and "is_travel_day" in my_logs.columns
        else 0
    )
    total_hours = (
        my_logs["hours_spent"].sum()
        if not my_logs.empty and "hours_spent" in my_logs.columns
        else 0
    )

    avg_handover_days = "N/A"
    if not df_sites.empty and "installation_id" in df_sites.columns:
        my_site_ids = (
            my_logs["installation_id"].unique() if not my_logs.empty else []
        )
        my_sites = df_sites[
            df_sites["installation_id"].isin(my_site_ids)
        ].copy()

        if (
            not my_sites.empty
            and "order_date" in my_sites.columns
            and "handover_date" in my_sites.columns
        ):
            my_sites["order_dt"] = pd.to_datetime(
                my_sites["order_date"], errors="coerce"
            )
            my_sites["handover_dt"] = pd.to_datetime(
                my_sites["handover_date"], errors="coerce"
            )
            my_sites["duration"] = (
                my_sites["handover_dt"] - my_sites["order_dt"]
            ).dt.days
            valid_durations = my_sites["duration"].dropna()
            if not valid_durations.empty:
                avg_handover_days = f"{round(valid_durations.mean(), 1)} Days"

    perf_score = int(
        (total_hours * 2) + (days_travelled * 15) + (days_worked * 10)
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            '<div class="kpi-card"><div'
            f' class="kpi-number">{days_worked}</div><div'
            ' class="kpi-label">Days Worked</div></div>',
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            '<div class="kpi-card"><div'
            f' class="kpi-number">{days_travelled}</div><div'
            ' class="kpi-label">Travel Days</div></div>',
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            '<div class="kpi-card"><div'
            f' class="kpi-number">{total_hours} hrs</div><div'
            ' class="kpi-label">Total Hours</div></div>',
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            '<div class="kpi-card"><div'
            f' class="kpi-number">{avg_handover_days}</div><div'
            ' class="kpi-label">Avg Handover Speed</div></div>',
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            '<div class="kpi-card"><div class="kpi-number" style="color:'
            f' #00A859;">{perf_score} pts</div><div'
            ' class="kpi-label">Performance Score</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    st.markdown("### 📋 Assigned Work Pipeline")

    my_tasks = pd.DataFrame()
    if not df_tasks.empty and "assigned_worker" in df_tasks.columns:
        my_tasks = df_tasks[
            df_tasks["assigned_worker"].astype(str).str.strip().str.lower()
            == user_name.strip().lower()
        ]

    if my_tasks.empty:
        st.info("ℹ️ No direct task assignments found in `Task_Assignments`.")
    else:
        pending_tasks = my_tasks[
            my_tasks["status"]
            .astype(str)
            .str.lower()
            .isin(["pending", "in progress"])
        ]
        completed_tasks = my_tasks[
            my_tasks["status"].astype(str).str.lower() == "completed"
        ]

        t_tab1, t_tab2 = st.tabs([
            f"⏳ Active & Pending Tasks ({len(pending_tasks)})",
            f"✅ Completed Tasks ({len(completed_tasks)})",
        ])

        with t_tab1:
            if pending_tasks.empty:
                st.success("🎉 You are all caught up!")
            else:
                for idx, t_row in pending_tasks.iterrows():
                    t_id = t_row.get("task_id", f"TSK-{idx}")
                    site_id = t_row.get("installation_id", "N/A")
                    t_name = t_row.get("task_name", "Unassigned Task")
                    t_status = t_row.get("status", "Pending")

                    site_detail = "N/A"
                    if not df_sites.empty and "installation_id" in df_sites.columns:
                        match = df_sites[df_sites["installation_id"] == site_id]
                        if not match.empty:
                            site_detail = (
                                f"{match.iloc[0].get('site_city', '')} -"
                                f" {match.iloc[0].get('site_address', '')}"
                            )

                    with st.expander(
                        f"📍 Site: {site_id} | Task: {t_name} [{t_status}]",
                        expanded=True,
                    ):
                        st.write(f"**Location / Address:** {site_detail}")
                        st.write(
                            "**Category:**"
                            f" {t_row.get('task_category', 'General')}"
                        )
                        st.write(
                            "**Target Completion:**"
                            f" {t_row.get('target_date', 'Asap')}"
                        )

                        c_act1, c_act2 = st.columns([2, 1])
                        with c_act1:
                            new_status = st.selectbox(
                                "Update Status:",
                                ["Pending", "In Progress", "Completed"],
                                index=(
                                    [
                                        "Pending",
                                        "In Progress",
                                        "Completed",
                                    ].index(t_status)
                                    if t_status
                                    in ["Pending", "In Progress", "Completed"]
                                    else 0
                                ),
                                key=f"status_select_{t_id}",
                            )
                        with c_act2:
                            st.write(" ")
                            st.write(" ")
                            if st.button("Update Task Status", key=f"btn_upd_{t_id}"):
                                update_sheet_row(
                                    "Task_Assignments",
                                    "task_id",
                                    t_id,
                                    {"status": new_status},
                                )
                                st.success(
                                    f"Task status updated to {new_status}!"
                                )
                                st.rerun()

        with t_tab2:
            if completed_tasks.empty:
                st.info("No completed tasks recorded yet.")
            else:
                disp_cols = [
                    c
                    for c in [
                        "task_id",
                        "installation_id",
                        "task_category",
                        "task_name",
                        "status",
                        "completed_date",
                    ]
                    if c in completed_tasks.columns
                ]
                st.dataframe(
                    completed_tasks[disp_cols], use_container_width=True
                )

# --- COMMON: LOG DAILY TASKS ---
elif menu == "Log Daily Tasks":
    render_restricted_work_input(
        target_worker_name=user_name, is_crew_log=False
    )

# --- WORKER: MY WORK HISTORY & PERFORMANCE ---
elif menu == "My Work History & Performance":
    st.header(f"📊 Detailed Performance Report — {user_name}")

    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty or "worker_name" not in df_logs.columns:
        st.info("⚠️ No Field Logs Recorded Yet")
    else:
        my_logs = df_logs[
            df_logs["worker_name"].astype(str).str.strip().str.lower()
            == user_name.strip().lower()
        ]

        if my_logs.empty:
            st.info("⚠️ You have not submitted any daily work logs yet.")
        else:
            excel_bytes = generate_excel_download(
                my_logs, f"{user_name}_Performance_Report.xlsx"
            )
            st.download_button(
                "📥 Download Performance Excel Report",
                data=excel_bytes,
                file_name=f"{user_name}_Performance_Report.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )

            st.write("##")
            st.subheader("📈 Execution Breakdown")
            c_g1, c_g2 = st.columns(2)

            with c_g1:
                fig_hrs = px.bar(
                    my_logs,
                    x="logged_date",
                    y="hours_spent",
                    color="installation_id",
                    title="Daily Hours Logged per Site",
                )
                st.plotly_chart(fig_hrs, use_container_width=True)

            with c_g2:
                if "task_category" in my_logs.columns:
                    fig_pie = px.pie(
                        my_logs,
                        names="task_category",
                        values="hours_spent",
                        title="Time Distribution by Task Category",
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            st.divider()
            st.subheader(f"📜 Submitted Work Logs ({len(my_logs)} Entries)")
            disp_cols = [
                c
                for c in [
                    "log_id",
                    "site_day",
                    "logged_date",
                    "installation_id",
                    "worker_role",
                    "team_lead_name",
                    "task_category",
                    "task_name",
                    "hours_spent",
                    "minutes_spent",
                    "is_travel_day",
                    "site_remarks",
                ]
                if c in my_logs.columns
            ]
            st.dataframe(
                my_logs[disp_cols].sort_values(
                    by="logged_date", ascending=False
                ),
                use_container_width=True,
            )

# --- WORKER DASHBOARD SECTION ---
elif menu == "My Work Dashboard":
    st.header(f"⚡ My Personal Summary — {user_name}")
    
    df_logs = read_sheet("Worker_Daily_Logs")
    df_expenses = read_sheet("Expense_Logs")
    
    my_logs = df_logs[df_logs["worker_name"].str.strip().str.lower() == user_name.strip().lower()] if not df_logs.empty else pd.DataFrame()
    my_expenses = df_expenses[df_expenses["worker_name"].str.strip().str.lower() == user_name.strip().lower()] if not df_expenses.empty else pd.DataFrame()

    if my_logs.empty:
        st.info("No work history found.")
    else:
        # Personal KPI Cards
        w1, w2, w3, w4, w5, w6 = st.columns(6)
        w1.metric("Sites Visited", my_logs["installation_id"].nunique())
        w2.metric("Days Worked", my_logs["logged_date"].nunique())
        w3.metric("Travel Days", len(my_logs[my_logs["is_travel_day"] == "Yes"]))
        w4.metric("Travel Expenses", f"₹{my_expenses['travel_expense'].sum():,.0f}" if "travel_expense" in my_expenses.columns else "₹0")
        w5.metric("Stay Expenses", f"₹{my_expenses['stay_expense'].sum():,.0f}" if "stay_expense" in my_expenses.columns else "₹0")
        w6.metric("Leaves/Absences", len(my_logs[my_logs["attendance_status"] == "Leave"]) if "attendance_status" in my_logs.columns else "0")

        # Visual Chart of Personal Logged Problems
        st.write("##")
        fig_my_problems = px.pie(
            my_logs, 
            names="delay_category", 
            title="Overview of Issues Faced on Sites",
            hole=0.4
        )
        st.plotly_chart(fig_my_problems, use_container_width=True)
        
# --- WORKER: MY PROFILE & SETTINGS ---
elif menu == "My Profile & Settings":
    st.header("👤 Worker Profile & Security")

    col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
    with col_center:
        st.markdown(
            f"""
            <div class="card-box">
                <h3 style="margin:0;">{user_name}</h3>
                <p style="margin:5px 0;"><b>Role:</b> {user_role}</p>
                <p style="margin:5px 0;"><b>Worker ID:</b> {user.get('worker_id', 'N/A')}</p>
                <p style="margin:5px 0;"><b>Base Station:</b> {user_base_location}</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.subheader("🔑 Change Security PIN")
        with st.form("change_pin_form"):
            curr_pin = st.text_input("Current PIN", type="password")
            new_pin1 = st.text_input(
                "New 4-Digit PIN", type="password", max_chars=4
            )
            new_pin2 = st.text_input(
                "Confirm New PIN", type="password", max_chars=4
            )

            update_pin_btn = st.form_submit_button(
                "Update Security PIN", use_container_width=True
            )

            if update_pin_btn:
                if str(curr_pin).strip() != str(user.get("pin", "")).strip():
                    st.error("Incorrect current PIN!")
                elif not new_pin1 or len(new_pin1) < 4:
                    st.error("New PIN must be at least 4 digits.")
                elif new_pin1 != new_pin2:
                    st.error("New PINs do not match!")
                else:
                    success = update_sheet_row(
                        "Workers_Master",
                        "name",
                        user_name,
                        {"pin": new_pin1.strip()},
                    )
                    if success:
                        st.session_state.authenticated_user["pin"] = (
                            new_pin1.strip()
                        )
                        st.success("PIN updated successfully!")
                        st.rerun()

# --- SUPERVISOR: TEAM HEAD DASHBOARD ---
elif menu == "Team Head Dashboard":
    st.header("👥 Dual-Tab Team Head Dashboard")
    tab_personal, tab_crew = st.tabs(
        ["👤 Personal Work Log", "👨‍🔧 Crew Task Logging"]
    )

    with tab_personal:
        st.subheader(f"Personal Execution Log ({user_name})")
        render_restricted_work_input(
            target_worker_name=user_name, is_crew_log=False
        )

    with tab_crew:
        st.subheader("Manage Active Crew Logs")
        df_workers = read_sheet("Workers_Master")
        crew_members = (
            df_workers[df_workers["role"] == "Worker"]["name"].tolist()
            if not df_workers.empty and "role" in df_workers.columns
            else []
        )

        if not crew_members:
            st.info("⚠️ No Active Crew Members Found")
        else:
            selected_crew = st.selectbox("Select Worker to Log For", crew_members)
            st.divider()
            render_restricted_work_input(
                target_worker_name=selected_crew, is_crew_log=True
            )

# --- SUPERVISOR: ACTIVE TASKS DASHBOARD ---
elif menu == "Active Tasks Dashboard":
    st.header("📋 Active Tasks Dashboard")
    st.caption(
        "Track site installation progress, monitor individual task statuses,"
        " and export site reports."
    )

    df_tasks = read_sheet("Task_Assignments")
    df_sites = read_sheet("Sites_Master")

    if df_tasks.empty:
        st.info("⚠️ No Active Tasks Found")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            site_options = ["All Sites"] + (
                df_sites["installation_id"].tolist()
                if not df_sites.empty and "installation_id" in df_sites.columns
                else []
            )
            site_filter = st.selectbox("Filter by Site", site_options)
        with col_f2:
            status_filter = st.selectbox(
                "Filter by Task Status",
                ["All Statuses", "In Progress", "Pending", "Completed"],
            )

        filtered_tasks = df_tasks.copy()
        if (
            site_filter != "All Sites"
            and "installation_id" in filtered_tasks.columns
        ):
            filtered_tasks = filtered_tasks[
                filtered_tasks["installation_id"] == site_filter
            ]
        if (
            status_filter != "All Statuses"
            and "status" in filtered_tasks.columns
        ):
            filtered_tasks = filtered_tasks[
                filtered_tasks["status"] == status_filter
            ]

        st.write("##")
        if site_filter != "All Sites":
            site_task_subset = (
                df_tasks[df_tasks["installation_id"] == site_filter]
                if "installation_id" in df_tasks.columns
                else pd.DataFrame()
            )

            tot_site_tasks = len(site_task_subset)
            completed_tasks = (
                len(site_task_subset[site_task_subset["status"] == "Completed"])
                if "status" in site_task_subset.columns
                else 0
            )
            in_prog_tasks = (
                len(
                    site_task_subset[
                        site_task_subset["status"] == "In Progress"
                    ]
                )
                if "status" in site_task_subset.columns
                else 0
            )

            overall_pct = (
                int((completed_tasks / tot_site_tasks) * 100)
                if tot_site_tasks > 0
                else 0
            )

            st.subheader(f"📊 Site Progress Tracker — {site_filter}")
            st.progress(overall_pct / 100)

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(
                    '<div class="kpi-card"><div'
                    f' class="kpi-number">{overall_pct}%</div><div'
                    ' class="kpi-label">Overall Completion</div></div>',
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    '<div class="kpi-card"><div'
                    f' class="kpi-number">{tot_site_tasks}</div><div'
                    ' class="kpi-label">Total Site Tasks</div></div>',
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    '<div class="kpi-card"><div'
                    f' class="kpi-number">{in_prog_tasks}</div><div'
                    ' class="kpi-label">In Progress</div></div>',
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    '<div class="kpi-card"><div'
                    f' class="kpi-number">{completed_tasks}</div><div'
                    ' class="kpi-label">Completed</div></div>',
                    unsafe_allow_html=True,
                )

            st.divider()

        st.subheader(f"Task List ({len(filtered_tasks)} Records)")
        st.dataframe(filtered_tasks, use_container_width=True)

# --- PAGE: EMPLOYEE ANALYTICS & REPORTS ---
elif menu == "Employee Analytics & Reports":
    st.header("👤 Employee Deep Dive & Individual Analytics")
    st.caption(
        "Select any worker to isolate their performance, daily progress"
        " graphs, and travel logs."
    )

    df_workers = read_sheet("Workers_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_workers.empty:
        st.warning("⚠️ Workers database is empty.")
    else:
        worker_names = sorted(
            df_workers["name"].astype(str).str.strip().unique().tolist()
        )
        default_index = (
            worker_names.index("Parvesh Kumar")
            if "Parvesh Kumar" in worker_names
            else 0
        )
        selected_emp = st.selectbox(
            "🔍 Select Employee to Generate Report:",
            worker_names,
            index=default_index,
        )

        emp_info = df_workers[df_workers["name"] == selected_emp].iloc[0]

        st.markdown(
            f"""
            <div class="card-box">
                <h3 style="margin:0;">{emp_info.get('name')} ({emp_info.get('worker_id')})</h3>
                <p style="margin:5px 0;"><b>Role:</b> {emp_info.get('role')} | <b>Base Location:</b> {emp_info.get('base_location')}</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        if df_logs.empty or "worker_name" not in df_logs.columns:
            st.info(f"No task logs recorded yet for {selected_emp}.")
        else:
            emp_logs = df_logs[
                df_logs["worker_name"].astype(str).str.strip().str.lower()
                == selected_emp.strip().lower()
            ].copy()

            if emp_logs.empty:
                st.warning(f"⚠️ No field logs recorded for **{selected_emp}**.")
            else:
                st.subheader("⚙️ Filter Report")
                col_f1, col_f2, col_f3 = st.columns(3)

                with col_f1:
                    site_list = [
                        "All Sites"
                    ] + emp_logs["installation_id"].unique().tolist()
                    filter_site = st.selectbox(
                        "Filter by Installation Site", site_list
                    )
                with col_f2:
                    travel_opt = [
                        "All Days",
                        "Travel Days Only (Yes)",
                        "Local Days Only (No)",
                    ]
                    filter_travel = st.selectbox(
                        "Filter by Travel Status", travel_opt
                    )
                with col_f3:
                    cat_col = (
                        "task_category"
                        if "task_category" in emp_logs.columns
                        else "task_name"
                    )
                    task_list = [
                        "All Categories"
                    ] + emp_logs[cat_col].unique().tolist()
                    filter_task = st.selectbox("Filter by Category", task_list)

                filtered_emp_logs = emp_logs.copy()
                if filter_site != "All Sites":
                    filtered_emp_logs = filtered_emp_logs[
                        filtered_emp_logs["installation_id"] == filter_site
                    ]
                if filter_travel == "Travel Days Only (Yes)":
                    filtered_emp_logs = filtered_emp_logs[
                        filtered_emp_logs["is_travel_day"] == "Yes"
                    ]
                elif filter_travel == "Local Days Only (No)":
                    filtered_emp_logs = filtered_emp_logs[
                        filtered_emp_logs["is_travel_day"] == "No"
                    ]
                if filter_task != "All Categories":
                    filtered_emp_logs = filtered_emp_logs[
                        filtered_emp_logs[cat_col] == filter_task
                    ]

                tot_hours = (
                    filtered_emp_logs["hours_spent"].sum()
                    if "hours_spent" in filtered_emp_logs.columns
                    else 0
                )
                tot_travel_days = (
                    len(
                        filtered_emp_logs[
                            filtered_emp_logs["is_travel_day"] == "Yes"
                        ]
                    )
                    if "is_travel_day" in filtered_emp_logs.columns
                    else 0
                )
                tot_projects = (
                    filtered_emp_logs["installation_id"].nunique()
                    if "installation_id" in filtered_emp_logs.columns
                    else 0
                )

                st.write("##")
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.markdown(
                        '<div class="kpi-card"><div'
                        f' class="kpi-number">{tot_hours} hrs</div><div'
                        ' class="kpi-label">Total Logged Hours</div></div>',
                        unsafe_allow_html=True,
                    )
                with k2:
                    st.markdown(
                        '<div class="kpi-card"><div'
                        f' class="kpi-number">{tot_travel_days} Days</div><div'
                        ' class="kpi-label">Travel Days (TA/DA)</div></div>',
                        unsafe_allow_html=True,
                    )
                with k3:
                    st.markdown(
                        '<div class="kpi-card"><div'
                        f' class="kpi-number">{tot_projects}</div><div'
                        ' class="kpi-label">Unique Sites Worked</div></div>',
                        unsafe_allow_html=True,
                    )

                st.divider()

                st.subheader("📊 Individual Work Breakdown")
                g1, g2 = st.columns(2)

                with g1:
                    fig_hrs = px.bar(
                        filtered_emp_logs,
                        x="logged_date",
                        y="hours_spent",
                        color="installation_id",
                        title=f"Daily Hours Logged by {selected_emp}",
                    )
                    st.plotly_chart(fig_hrs, use_container_width=True)

                with g2:
                    if "task_category" in filtered_emp_logs.columns:
                        fig_cat = px.pie(
                            filtered_emp_logs,
                            names="task_category",
                            values="hours_spent",
                            title="Time Spent per Category",
                        )
                        st.plotly_chart(fig_cat, use_container_width=True)

                st.subheader(
                    f"📋 Detailed Work Logs ({len(filtered_emp_logs)} Records)"
                )
                disp_cols = [
                    c
                    for c in [
                        "log_id",
                        "site_day",
                        "logged_date",
                        "installation_id",
                        "worker_role",
                        "team_lead_name",
                        "task_category",
                        "task_name",
                        "hours_spent",
                        "minutes_spent",
                        "is_travel_day",
                        "site_remarks",
                        "site_photo",
                    ]
                    if c in filtered_emp_logs.columns
                ]
                st.dataframe(
                    filtered_emp_logs[disp_cols].sort_values(
                        by="logged_date", ascending=False
                    ),
                    use_container_width=True,
                )

# --- ADMIN: ANALYTICS DASHBOARD ---
elif menu == "Admin Analytics Dashboard":
    st.header("📊 Admin Operations & Expense Analytics")

    df_logs = read_sheet("Worker_Daily_Logs")
    df_sites = read_sheet("Sites_Master")
    
    # Safe read for Expense_Logs to prevent dashboard crashes
    try:
        df_expenses = read_sheet("Expense_Logs")
    except Exception as e:
        df_expenses = pd.DataFrame()
        st.warning("⚠️ Could not load 'Expense_Logs' tab. Displaying operational data only.")

    # 1. Filter Active ("Running") Sites
    active_site_ids = []
    if not df_sites.empty and "installation_id" in df_sites.columns:
        df_sites_copy = df_sites.copy()
        df_sites_copy.columns = [str(col).strip().lower().replace(" ", "_") for col in df_sites_copy.columns]
        
        # Exclude completed/handovered sites
        running_sites = df_sites_copy[
            ~df_sites_copy["status"].astype(str).str.strip().str.title().isin(["Handovered", "Handover", "Completed"])
        ]
        active_site_ids = running_sites["installation_id"].unique().tolist()

    # Filter logs for active sites
    if not df_logs.empty and active_site_ids:
        df_logs = df_logs[df_logs["installation_id"].isin(active_site_ids)]

    if df_logs.empty:
        st.info("No log data available for running sites.")
    else:
        # 2. Dynamic KPI Calculations
        sites_visited = df_logs["installation_id"].nunique() if "installation_id" in df_logs.columns else 0
        days_worked = df_logs["logged_date"].nunique() if "logged_date" in df_logs.columns else 0
        days_travelled = len(df_logs[df_logs["is_travel_day"] == "Yes"]) if "is_travel_day" in df_logs.columns else 0

        # Safe aggregation for expense metrics
        travel_exp = (
            df_expenses["travel_expense"].sum() 
            if not df_expenses.empty and "travel_expense" in df_expenses.columns 
            else 0
        )
        stay_exp = (
            df_expenses["stay_expense"].sum() 
            if not df_expenses.empty and "stay_expense" in df_expenses.columns 
            else 0
        )
        leave_days = (
            len(df_logs[df_logs["attendance_status"] == "Leave"]) 
            if "attendance_status" in df_logs.columns 
            else 0
        )

        # 3. Render KPI Cards
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{sites_visited}</div><div class="kpi-label">Active Sites Visited</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{days_worked}</div><div class="kpi-label">Days Worked</div></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{days_travelled}</div><div class="kpi-label">Days Travelled</div></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">₹{travel_exp:,.0f}</div><div class="kpi-label">Travel Expense</div></div>', unsafe_allow_html=True)
        with k5:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">₹{stay_exp:,.0f}</div><div class="kpi-label">Stay Expense</div></div>', unsafe_allow_html=True)
        with k6:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number" style="color:#D32F2F;">{leave_days}</div><div class="kpi-label">On-Site Leaves</div></div>', unsafe_allow_html=True)

        st.divider()

        # 4. Analytics Visualizations
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("⚠️ Problems & Delays Reported")
            if "delay_category" in df_logs.columns:
                delay_df = df_logs[df_logs["delay_category"] != "No Delay"]
                if not delay_df.empty:
                    fig_delay = px.bar(
                        delay_df,
                        x="delay_category",
                        color="installation_id",
                        title="Site Issues by Category",
                        labels={"delay_category": "Issue Type", "count": "Occurrences"}
                    )
                    st.plotly_chart(fig_delay, use_container_width=True)
                else:
                    st.success("No active issues reported!")

        with g2:
            st.subheader("💰 Expenses by Worker")
            if not df_expenses.empty and "worker_name" in df_expenses.columns:
                fig_exp = px.bar(
                    df_expenses,
                    x="worker_name",
                    y=["travel_expense", "stay_expense"],
                    title="Travel vs Stay Expenses",
                    barmode="stack",
                    labels={"value": "Amount (₹)", "worker_name": "Worker"}
                )
                st.plotly_chart(fig_exp, use_container_width=True)
            else:
                st.info("Expense log sheet is empty or unavailable.")
                
# --- ADMIN: USER MANAGEMENT ---
elif menu == "User Management":
    st.header("👥 User & Access Management")
    df_workers = read_sheet("Workers_Master")

    if st.session_state.get("user_created_success"):
        new_user = st.session_state.get("created_user_name", "User")
        st.toast(f"👤 Account for {new_user} created successfully!", icon="✅")
        del st.session_state["user_created_success"]
        if "created_user_name" in st.session_state:
            del st.session_state["created_user_name"]

    tab_add, tab_batch, tab_edit = st.tabs([
        "➕ Add Single User",
        "⚡ Batch Process Raw String",
        "✏️ Edit Existing User & Role",
    ])

    with tab_add:
        st.subheader("Add Worker / Supervisor to System")
        col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
        with col_center:
            with st.form("add_user_form"):
                c1, c2 = st.columns(2)
                with c1:
                    new_w_id = st.text_input(
                        "Worker ID", value=f"W{len(df_workers)+1:03d}"
                    )
                    new_name = st.text_input("Full Name")
                    new_id_num = st.text_input(
                        "12-Digit Government ID",
                        max_chars=12,
                        placeholder="e.g. 123456789012",
                    )
                with c2:
                    new_pin = st.text_input(
                        "4-Digit PIN / Password", type="password"
                    )
                    new_role = st.selectbox(
                        "System Role", ["Worker", "Supervisor", "Admin"]
                    )
                    new_base = st.text_input(
                        "Base Station / City", value="Jaipur"
                    )

                submit_new_user = st.form_submit_button(
                    "Create User & Sync to Data Base", use_container_width=True
                )
                if submit_new_user:
                    clean_id = str(new_id_num).strip()
                    if not new_name or not new_pin or not clean_id:
                        st.error("Please fill in Full Name, ID Number, and PIN.")
                    elif len(clean_id) != 12 or not clean_id.isdigit():
                        st.error("Invalid ID Number! Must be 12 digits.")
                    else:
                        user_dict = {
                            "worker_id": new_w_id,
                            "name": new_name,
                            "aadhaar_no": clean_id,
                            "pin": str(new_pin),
                            "role": new_role,
                            "base_location": new_base,
                        }
                        append_to_sheet("Workers_Master", user_dict)
                        st.session_state["user_created_success"] = True
                        st.session_state["created_user_name"] = new_name
                        st.rerun()

    with tab_batch:
        st.subheader("⚡ Batch Import Workers")
        raw_text_input = st.text_area("Paste Continuous Data String Here:")
        if st.button("🔍 Parse and Import Worker Data"):
            if raw_text_input:
                pattern = re.compile(
                    r"(W\d{3})([A-Za-z\s]+?)(\d{12})(\d{4})(Supervisor|Worker|Admin)([A-Za-z]+)"
                )
                matches = pattern.findall(raw_text_input)
                for m in matches:
                    append_to_sheet(
                        "Workers_Master",
                        {
                            "worker_id": m[0],
                            "name": m[1].strip(),
                            "aadhaar_no": m[2],
                            "pin": m[3],
                            "role": m[4],
                            "base_location": m[5],
                        },
                    )
                st.success("All extracted workers synced!")
                st.rerun()

    with tab_edit:
        st.subheader("Update User Profile")
        if not df_workers.empty and "name" in df_workers.columns:
            selected_edit_user = st.selectbox(
                "Select User to Edit", sorted(df_workers["name"].tolist())
            )
            user_data = df_workers[
                df_workers["name"] == selected_edit_user
            ].iloc[0]

            col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
            with col_center:
                with st.form("edit_user_form"):
                    e_role = st.selectbox(
                        "Update Role",
                        ["Worker", "Supervisor", "Admin"],
                        index=["Worker", "Supervisor", "Admin"].index(
                            user_data.get("role", "Worker")
                        ),
                    )
                    e_pin = st.text_input(
                        "Update PIN", value=str(user_data.get("pin", ""))
                    )
                    e_base = st.text_input(
                        "Update Base Location",
                        value=str(user_data.get("base_location", "Jaipur")),
                    )

                    submit_edit = st.form_submit_button(
                        "Update Profile in Data Base", use_container_width=True
                    )
                    if submit_edit:
                        updates = {
                            "role": e_role,
                            "pin": e_pin,
                            "base_location": e_base,
                        }
                        update_sheet_row(
                            "Workers_Master", "name", selected_edit_user, updates
                        )
                        st.success(f"Updated **{selected_edit_user}** successfully!")
                        st.rerun()

# --- ADMIN: TA/DA PAYROLL ---
elif menu == "TA/DA Payroll & Travel Summary":
    st.header("✈️ TA/DA Travel Allowance & Payroll Report")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty or "is_travel_day" not in df_logs.columns:
        st.info("⚠️ No Travel Days Claimed Yet")
    else:
        travel_logs = df_logs[df_logs["is_travel_day"] == "Yes"]
        if travel_logs.empty:
            st.warning("⚠️ No Travel Days Claimed Yet")
        else:
            summary_df = (
                travel_logs.groupby(["worker_name", "base_location"])
                .agg(
                    total_travel_days=("is_travel_day", "count"),
                    total_hours_worked=("hours_spent", "sum"),
                )
                .reset_index()
            )

            ta_rate = st.number_input(
                "Daily TA/DA Allowance Rate (₹)", value=500, step=50
            )
            summary_df["Estimated Allowance (₹)"] = (
                summary_df["total_travel_days"] * ta_rate
            )

            excel_bytes = generate_excel_download(
                summary_df, "TADA_Payroll_Report.xlsx"
            )
            st.download_button(
                "📥 Download Payroll Excel Report",
                data=excel_bytes,
                file_name="TADA_Payroll_Report.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )

            st.write("##")
            st.dataframe(summary_df, use_container_width=True)

# --- ADMIN: ADVANCED FIELD LOGS INSPECTOR ---
elif menu == "Advanced Field Logs Inspector":
    st.header("🔍 Advanced Field Log Inspector & Exporter")
    df_logs = read_sheet("Worker_Daily_Logs")

    if not df_logs.empty:
        excel_bytes = generate_excel_download(df_logs, "All_Field_Logs.xlsx")
        st.download_button(
            "📥 Download All Logs (Excel)",
            data=excel_bytes,
            file_name="All_Field_Logs.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        st.write("##")
        st.dataframe(df_logs, use_container_width=True)

# --- SUPERVISOR: HANDOVER DASHBOARD ---
elif menu == "Handover Date Dashboard":
    st.header("📅 Site Handover Date Dashboard")
    df_sites = read_sheet("Sites_Master")

    if not df_sites.empty and "handover_date" in df_sites.columns:
        df_sites["handover_date_dt"] = pd.to_datetime(
            df_sites["handover_date"], errors="coerce"
        )
        df_sites["days_remaining"] = (
            df_sites["handover_date_dt"] - datetime.now()
        ).dt.days

        for _, site in df_sites.iterrows():
            days = site.get("days_remaining", 0)
            badge_color = (
                COLOR_ACCENT
                if days > 15
                else ("#E6A100" if days >= 0 else "#D32F2F")
            )

            st.markdown(
                f"""
                <div class="card-box">
                    <h3 style="margin:0;">{site.get('site_name', 'N/A')} ({site.get('installation_id', 'N/A')})</h3>
                    <p style="margin:5px 0;"><b>Client:</b> {site.get('client_name', 'N/A')} | <b>Contact:</b> {site.get('client_phone', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>City:</b> {site.get('site_city', 'N/A')} | <b>Team Lead:</b> {site.get('team_lead', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Target Handover:</b> {site.get('handover_date', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Status:</b> <span style="color:{badge_color}; font-weight:bold;">{site.get('status', 'In Progress')} ({days} Days Remaining)</span></p>
                </div>
            """,
                unsafe_allow_html=True,
            )

# --- SUPERVISOR: NEW ORDER ---
elif menu == "New Installation Order":
    st.header("Create New Installation Order")
    df_workers = read_sheet("Workers_Master")
    worker_options = (
        sorted(df_workers["name"].tolist())
        if not df_workers.empty and "name" in df_workers.columns
        else [user_name]
    )

    if "products_count" not in st.session_state:
        st.session_state.products_count = 1

    visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"
    st.info(f"**Automated Visit ID:** {visit_id}")

    col_client, col_team, col_dates = st.columns(3)

    with col_client:
        st.markdown("### 🏢 Client Info")
        client_name = st.text_input(
            "Client / Company Name *", placeholder="e.g. Reliance Logistics"
        )
        client_phone = st.text_input(
            "Client Mobile No. *", placeholder="e.g. 9876543210", max_chars=10
        )

    with col_team:
        st.markdown("### 👨‍💼 Team & Site Structure")
        team_lead_name = st.selectbox(
            "Team Lead Name *", options=worker_options, key="inst_team_lead"
        )
        team_helpers = st.multiselect(
            "Team Members / Helpers",
            options=[w for w in worker_options if w != team_lead_name],
            key="inst_helpers",
        )
        city_name = st.text_input(
            "City Name *", value="Mumbai", key="inst_city_name"
        )
        site_address = st.text_area(
            "Site Address *",
            placeholder="Full installation site address...",
            key="inst_site_address",
        )

    with col_dates:
        st.markdown("### 📅 Order Dates")
        inst_date = st.date_input(
            "Installation Date", value=datetime.now(), key="inst_order_date"
        )
        site_clearance_date = st.date_input(
            "Site Clearance Date",
            value=datetime.now(),
            key="inst_clearance_date",
        )
        target_handover_date = st.date_input(
            "Target Handover Date",
            value=datetime.now() + timedelta(days=15),
            key="inst_handover_date",
        )

    st.divider()

    st.markdown("### 📦 Order Products Details")
    products_data = []
    catalog_main_categories = list(PRODUCT_CATALOG.keys())

    for p_idx in range(st.session_state.products_count):
        st.markdown(f"#### Product #{p_idx + 1}")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            product_type = st.selectbox(
                "Select Product", catalog_main_categories, key=f"prod_type_{p_idx}"
            )
            dimensions = st.text_input(
                "Dimensions (WxH)",
                placeholder="e.g., 5330X6000",
                key=f"prod_dim_{p_idx}",
            )
        with col_p2:
            sub_cat_options = PRODUCT_CATALOG.get(product_type, ["Other"])
            sub_category = st.selectbox(
                "Select Sub-Category", sub_cat_options, key=f"prod_sub_{p_idx}"
            )
            quantity = st.number_input(
                "Quantity", min_value=1, value=1, step=1, key=f"prod_qty_{p_idx}"
            )

        products_data.append({
            "product_type": product_type,
            "sub_category": sub_category,
            "dimensions": dimensions,
            "quantity": quantity,
        })

    if st.button("➕ Add Another Product", key="btn_add_product"):
        st.session_state.products_count += 1
        st.rerun()

    st.write("##")
    if st.button(
        "💾 Submit Installation Order",
        use_container_width=True,
        key="btn_submit_inst_order",
    ):
        clean_phone = str(client_phone).strip()
        if (
            not client_name
            or not clean_phone
            or not team_lead_name
            or not city_name
            or not site_address
        ):
            st.error(
                "Please fill in all mandatory fields including Client Name and"
                " Contact Number."
            )
        elif len(clean_phone) != 10 or not clean_phone.isdigit():
            st.error(
                "Please enter a valid 10-digit mobile number for the client."
            )
        else:
            order_data = {
                "installation_id": visit_id,
                "client_name": client_name.strip(),
                "client_phone": clean_phone,
                "team_lead": team_lead_name,
                "team_members": ", ".join(team_helpers),
                "site_city": city_name,
                "site_address": site_address,
                "order_date": str(inst_date),
                "site_clearance_date": str(site_clearance_date),
                "handover_date": str(target_handover_date),
                "products_summary": str(products_data),
                "status": "In Progress",
            }
            append_to_sheet("Sites_Master", order_data)
            st.success(
                f"Installation Order **{visit_id}** for **{client_name}**"
                " recorded successfully!"
            )
            st.session_state.products_count = 1

# --- SUPERVISOR: VIEW LOGS & UPDATE ---
elif menu == "View Logs & Update Status":
    render_view_logs_and_update_status()

# --- SUPERVISOR: SITE DASHBOARD ---
elif menu == "Team Head Dashboard":
    st.header("🏢 Site Performance & Supervisor Dashboard")
    st.caption("Live operational metrics and reported site updates for running projects.")

    df_logs = read_sheet("Worker_Daily_Logs")
    df_sites = read_sheet("Sites_Master")

    if df_sites.empty:
        st.warning("No site data found in database.")
    else:
        # Standardize site columns
        df_sites.columns = [str(c).strip().lower().replace(" ", "_") for c in df_sites.columns]
        
        # Filter for active/running sites
        active_sites_df = df_sites[
            ~df_sites["status"].astype(str).str.strip().str.title().isin(["Handovered", "Handover", "Completed"])
        ]
        
        site_options = ["All Active Sites"] + active_sites_df["installation_id"].tolist()
        selected_site = st.selectbox("🎯 Select Active Installation Site", site_options)

        sub_logs = df_logs.copy() if not df_logs.empty else pd.DataFrame()

        if selected_site != "All Active Sites" and not sub_logs.empty:
            sub_logs = sub_logs[sub_logs["installation_id"] == selected_site]

        # Top Metric Cards
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            site_count = len(active_sites_df) if selected_site == "All Active Sites" else 1
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{site_count}</div><div class="kpi-label">Active Sites</div></div>', unsafe_allow_html=True)
        with s2:
            days_count = sub_logs["logged_date"].nunique() if not sub_logs.empty and "logged_date" in sub_logs.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{days_count}</div><div class="kpi-label">Days Worked</div></div>', unsafe_allow_html=True)
        with s3:
            travel_count = len(sub_logs[sub_logs["is_travel_day"] == "Yes"]) if not sub_logs.empty and "is_travel_day" in sub_logs.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{travel_count}</div><div class="kpi-label">Travel Days Logged</div></div>', unsafe_allow_html=True)
        with s4:
            total_hrs = sub_logs["hours_spent"].sum() if not sub_logs.empty and "hours_spent" in sub_logs.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_hrs} hrs</div><div class="kpi-label">Total Field Hours</div></div>', unsafe_allow_html=True)

        st.divider()

        # Operational Remarks and Delays Log
        st.subheader("🚨 Field Remarks & Delay Logs")
        if not sub_logs.empty and "site_remarks" in sub_logs.columns:
            remarks_df = sub_logs[
                sub_logs["site_remarks"].astype(str).str.strip().str.lower().ne("none") & 
                sub_logs["site_remarks"].astype(str).str.strip().ne("")
            ]
            if not remarks_df.empty:
                disp_cols = [c for c in ["logged_date", "installation_id", "worker_name", "delay_category", "site_remarks", "site_photo"] if c in remarks_df.columns]
                st.dataframe(remarks_df[disp_cols].sort_values(by="logged_date", ascending=False), use_container_width=True)
            else:
                st.info("No delays or site issues reported.")
        else:
            st.info("No field logs found for the selected view.")
    
# --- MASTER DATABASE ---
elif menu == "Master Database":
    st.header("🗄️ Live Google Sheets Database")
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs([
        "Workers Master",
        "Sites Master",
        "Task Assignments",
        "Worker Daily Logs",
    ])

    with m_tab1:
        st.dataframe(read_sheet("Workers_Master"), use_container_width=True)
    with m_tab2:
        st.dataframe(read_sheet("Sites_Master"), use_container_width=True)
    with m_tab3:
        st.dataframe(read_sheet("Task_Assignments"), use_container_width=True)
    with m_tab4:
        st.dataframe(read_sheet("Worker_Daily_Logs"), use_container_width=True)
