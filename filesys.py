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

# Email validation helper regex
EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

# Field Worker Designations
WORKER_DESIGNATIONS = ["Installer", "Helper", "Manager"]

# ==========================================
# 1. HELPER FUNCTIONS & WORK ID GENERATOR
# ==========================================
def validate_email(email_str: str) -> bool:
    """Validates structure of email address."""
    if not email_str:
        return False
    return bool(re.match(EMAIL_REGEX, email_str.strip()))


def generate_work_id(role: str, df_workers: pd.DataFrame) -> str:
    """Auto-generates dynamic Work IDs like ADM01, SPV001, W001, SP001."""
    role_prefix_map = {
        "Admin": "ADM",
        "Supervisor": "SPV",
        "Worker": "W",
        "Salesperson": "SP",
    }
    
    prefix = role_prefix_map.get(role, "EMP")
    
    if df_workers.empty or "worker_id" not in df_workers.columns:
        return f"{prefix}01" if prefix == "ADM" else f"{prefix}001"
    
    existing_ids = df_workers["worker_id"].dropna().astype(str).str.strip()
    role_ids = [uid for uid in existing_ids if uid.startswith(prefix)]
    
    if not role_ids:
        return f"{prefix}01" if prefix == "ADM" else f"{prefix}001"
    
    numbers = []
    for uid in role_ids:
        num_part = uid[len(prefix):]
        if num_part.isdigit():
            numbers.append(int(num_part))
            
    next_num = max(numbers) + 1 if numbers else 1
    padding = 2 if prefix == "ADM" else 3
    return f"{prefix}{next_num:0{padding}d}"

def format_worker_dropdown_options(df_workers: pd.DataFrame) -> list:
    """Formats worker options with designations for UI drop-downs."""
    if df_workers.empty or "name" not in df_workers.columns:
        return []
    
    options = []
    for _, row in df_workers.iterrows():
        name = str(row.get("name", "")).strip()
        role = str(row.get("role", "")).strip()
        desig = str(row.get("designation", "")).strip()
        
        if not name or role in ["Admin", "Salesperson"]:
            continue
            
        if role == "Worker" and desig:
            options.append(f"{name} ({desig})")
        else:
            options.append(name)
            
    return sorted(list(set(options)))


def render_view_logs_and_update_status():
    st.markdown("## 🔍 View Daily Logs & Update Status")

    df_sites = read_sheet("Sites_Master")
    if df_sites.empty:
        st.warning("No installation records found.")
        return

    df_sites.columns = [
        str(col).strip().lower().replace(" ", "_") for col in df_sites.columns
    ]

    site_map = {}
    site_data = {}

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

    selected_label = st.selectbox(
        "Select Installation ID",
        options=list(site_map.keys()),
        key="view_logs_site_select",
    )

    selected_id = site_map[selected_label]
    info = site_data[selected_id]

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
                f"📅 {header_prefix}Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Role/Designation: {l.get('worker_role', 'N/A')}"
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
        user_permission = {"type": "anyone", "role": "reader"}
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
        df = pd.DataFrame(data)
        
        # Redact government identity columns for privacy compliance
        if sheet_name == "Workers_Master" and "aadhaar_no" in df.columns:
            df["aadhaar_no"] = "[Redacted Identity]"
            
        return df
    except Exception as e:
        print(f"DEBUG SHEET ERROR [{sheet_name}]: {e}")
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


def delete_sheet_row(sheet_name: str, key_col: str, key_val: str) -> bool:
    """Deletes a row matching key_col == key_val from specified sheet."""
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        if df.empty or key_col not in df.columns:
            return False
        match_idx = df[df[key_col].astype(str).str.strip() == str(key_val).strip()].index
        if match_idx.empty:
            return False
        row_num = match_idx[0] + 2
        sheet.delete_rows(row_num)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error deleting row from '{sheet_name}': {e}")
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
        st.markdown('<div style="max-width: 420px; margin: 0 auto;">', unsafe_allow_html=True)
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
                "Username / Name / Work ID",
                value=st.session_state.remembered_username,
                placeholder="e.g. Parvesh Kumar or W001",
            )
            password_input = st.text_input("Password / PIN", type="password", placeholder="Enter password")

            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                show_pass = st.checkbox("Show Password")
            with col_chk2:
                remember_me = st.checkbox("Remember Me", value=bool(st.session_state.remembered_username))

            submit_button = st.form_submit_button("🔑 LOGIN TO DASHBOARD", use_container_width=True)

            if submit_button:
                if not username_input or not password_input:
                    st.error("Please fill in both Username and Password.")
                else:
                    df_workers = read_sheet("Workers_Master")
                    if not df_workers.empty:
                        user_row = df_workers[
                            (
                                (df_workers["name"].astype(str).str.strip().str.lower() == username_input.strip().lower())
                                | (df_workers["worker_id"].astype(str).str.strip().str.lower() == username_input.strip().lower())
                            )
                            & (df_workers["pin"].astype(str).str.strip() == str(password_input).strip())
                        ]
                        if not user_row.empty:
                            st.session_state.authenticated_user = user_row.iloc[0].to_dict()
                            st.session_state.remembered_username = username_input.strip() if remember_me else ""
                            st.success("Authentication Successful!")
                            st.rerun()
                        else:
                            st.error("Invalid Username or Password.")
                    else:
                        st.error("⚠️ Database Unreachable — Verify Google Sheets setup.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 5. ACTIVE SESSION & SIDEBAR
# ==========================================
user = st.session_state.authenticated_user
user_name = user.get("name", "User")
user_role = user.get("role", "Worker")
user_designation = user.get("designation", user_role)
user_id = user.get("worker_id", "N/A")
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
    f"**Active User:** {user_name} (`{user_id}`)  \n**Designation:** {user_designation}  \n**Role:** {user_role}  \n**Base Station:** {user_base_location}"
)
st.sidebar.divider()

if user_role == "Admin":
    menu_options = [
        "Admin Analytics Dashboard",
        "Sales Analytics Report",
        "Employee Analytics & Reports",
        "👥 Dynamic User & Access Management",
        "TA/DA Payroll & Travel Summary",
        "Advanced Field Logs Inspector",
        "Master Database",
    ]
elif user_role == "Salesperson":
    menu_options = [
        "My Sales Dashboard",
        "📝 Log Visit & Order Deal",
        "🔍 Track Site Progress",
        "My Profile & Settings",
    ]
elif user_role == "Supervisor":
    menu_options = [
        "🔔 New Installation Requests",
        "New Installation Order",
        "Log Daily Tasks",
        "💰 Log Site Daily Expenses",
        "View Logs & Update Status",
        "Handover Date Dashboard",
        "Active Tasks Dashboard",
        "Employee Analytics & Reports",
        "Team Head Dashboard",
        "Master Database",
    ]
else:  # Worker (Helper, Installer, Manager)
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
# 6. DYNAMIC WORK INPUT HELPER
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

    worker_options = format_worker_dropdown_options(df_workers)
    if not worker_options:
        worker_options = [target_worker_name]

    st.markdown("### 👥 Crew & Team Assignment")
    col_lead, col_helpers = st.columns(2)

    with col_lead:
        # Find default match
        default_lead_idx = 0
        for idx, w_opt in enumerate(worker_options):
            if target_worker_name in w_opt:
                default_lead_idx = idx
                break

        team_lead_selected = st.selectbox(
            "Team Lead Name *",
            options=worker_options,
            index=default_lead_idx,
            key=f"team_lead_{target_worker_name}_{is_crew_log}_v{v}",
        )

    with col_helpers:
        available_helpers = [w for w in worker_options if w != team_lead_selected]
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
        col_cat, col_desc, col_assigned, col_hrs, col_min = st.columns([2.5, 3, 2.5, 1.2, 1.2])

        with col_cat:
            cat = st.selectbox(f"Category #{i+1}", TASK_CATEGORIES, key=f"cat_{target_worker_name}_{is_crew_log}_{i}_v{v}")
        with col_desc:
            desc = st.text_input(f"Task #{i+1} Description", placeholder="e.g., Track Leveling", key=f"desc_{target_worker_name}_{is_crew_log}_{i}_v{v}")
        with col_assigned:
            assigned_worker = st.selectbox(f"Assigned To #{i+1}", options=active_crew, key=f"assigned_{target_worker_name}_{is_crew_log}_{i}_v{v}")
        with col_hrs:
            hrs = st.number_input("Hours", min_value=0, max_value=24, value=2, step=1, key=f"hrs_{target_worker_name}_{is_crew_log}_{i}_v{v}")
        with col_min:
            mins = st.selectbox("Minutes", [0, 15, 30, 45], key=f"min_{target_worker_name}_{is_crew_log}_{i}_v{v}")

        task_entries.append({
            "category": cat,
            "description": desc,
            "assigned_worker": assigned_worker,
            "hours": hrs,
            "minutes": mins,
        })

    if st.button("➕ ADD MORE TASK LINES", key=f"add_task_btn_{target_worker_name}_{is_crew_log}_v{v}"):
        st.session_state[task_count_key] += 1
        st.rerun()

    st.divider()

    st.markdown("### ⚠️ Site Remarks / Delays")
    col_delay_cat, col_delay_notes = st.columns([1, 2])

    with col_delay_cat:
        delay_reason = st.selectbox("Primary Delay Category", options=DELAY_REASONS, key=f"delay_reason_{target_worker_name}_{is_crew_log}_v{v}")

    with col_delay_notes:
        site_remarks = st.text_area("Specific Site Notes / Remarks", placeholder="Provide details...", key=f"rem_{target_worker_name}_{is_crew_log}_v{v}")

    st.markdown("### 📷 Site Photo Documentation")
    uploaded_photo = st.file_uploader("Upload Photo of Site", type=["jpg", "jpeg", "png"], key=f"photo_{target_worker_name}_{is_crew_log}_v{v}")

    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Uploaded Site Photo Preview", width=280)

    st.write("##")

    if st.button("💾 Sync Daily Log to Database", key=f"btn_sync_{target_worker_name}_{is_crew_log}_v{v}", use_container_width=True):
        valid_tasks = [t for t in task_entries if t["description"].strip()]
        
        if not valid_tasks:
            st.error("Please enter at least one task description before syncing.")
        else:
            photo_link = "No Photo"
            if uploaded_photo is not None:
                photo_name = f"{selected_site_id}_{target_worker_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                photo_link = upload_file_to_drive(uploaded_photo, photo_name)

            records_saved = 0

            for idx, t in enumerate(valid_tasks):
                clean_worker_name = t["assigned_worker"].split(" (")[0].strip()
                w_base = "Jaipur"
                w_desig = "Worker"
                
                if not df_workers.empty:
                    m = df_workers[df_workers["name"] == clean_worker_name]
                    if not m.empty:
                        w_base = m.iloc[0].get("base_location", "Jaipur")
                        w_desig = m.iloc[0].get("designation", "Worker")

                w_is_travel = str(w_base).strip().lower() != str(site_city).strip().lower()
                clean_lead_name = team_lead_selected.split(" (")[0].strip()

                log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx+1}"
                log_entry = {
                    "log_id": log_id,
                    "installation_id": selected_site_id,
                    "site_day": site_day_label,
                    "logged_date": str(log_date),
                    "worker_name": clean_worker_name,
                    "worker_role": w_desig,
                    "team_lead_name": clean_lead_name,
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

if menu == "💰 Log Site Daily Expenses":
    st.header("💰 Supervisor Daily Site Expense Logging")
    st.caption("Record daily operational costs for running sites.")

    df_sites = read_sheet("Sites_Master")

    if df_sites.empty:
        st.warning("No installation sites found.")
    else:
        active_sites = df_sites[~df_sites["status"].astype(str).str.strip().str.title().isin(["Handovered", "Handover", "Completed"])]

        if active_sites.empty:
            st.info("No active installation sites requiring daily expense logs.")
        else:
            site_options = {
                f"{row.get('installation_id')} — {row.get('client_name', 'N/A')} ({row.get('site_city', 'N/A')})": row.get('installation_id')
                for _, row in active_sites.iterrows()
            }

            with st.form("supervisor_expense_form"):
                selected_label = st.selectbox("Select Active Installation Site *", options=list(site_options.keys()))
                sel_site_id = site_options[selected_label]

                col1, col2 = st.columns(2)
                with col1:
                    exp_date = st.date_input("Expense Date", value=datetime.now())
                    travel_exp = st.number_input("Travel Expense (₹)", min_value=0.0, step=100.0)
                    stay_exp = st.number_input("Stay / Accommodation Expense (₹)", min_value=0.0, step=100.0)
                with col2:
                    food_exp = st.number_input("Food / Daily Allowance Expense (₹)", min_value=0.0, step=50.0)
                    misc_exp = st.number_input("Local Purchase / Misc Expense (₹)", min_value=0.0, step=100.0)

                exp_remarks = st.text_area("Expense Description / Notes", placeholder="Detail local purchase items or travel distance...")

                submit_expense = st.form_submit_button("💾 Record & Sync Daily Expense", use_container_width=True)

                if submit_expense:
                    total_amount = travel_exp + stay_exp + food_exp + misc_exp
                    if total_amount <= 0:
                        st.error("Please enter a non-zero expense amount.")
                    else:
                        exp_id = f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        exp_data = {
                            "expense_id": exp_id,
                            "installation_id": sel_site_id,
                            "logged_date": str(exp_date),
                            "supervisor_name": user_name,
                            "travel_expense": travel_exp,
                            "stay_expense": stay_exp,
                            "food_expense": food_exp,
                            "misc_expense": misc_exp,
                            "total_expense": total_amount,
                            "remarks": exp_remarks.strip(),
                        }
                        append_to_sheet("Expense_Logs", exp_data)
                        st.success(f"Daily expense of ₹{total_amount:,.2f} logged for site {sel_site_id}!")
                        st.rerun()
                        
            st.divider()
            st.subheader("📜 Recent Site Expense Logs")
            df_expenses = read_sheet("Expense_Logs")
            if not df_expenses.empty:
                st.dataframe(df_expenses.sort_values(by="logged_date", ascending=False), use_container_width=True)

# --- ADMIN: TA/DA PAYROLL & TRAVEL SUMMARY (REARRANGED: GRAPHS ON TOP, EXCEL BELOW) ---
elif menu == "TA/DA Payroll & Travel Summary":
    st.header("✈️ TA/DA Payroll & Field Travel Summary")
    st.caption("Calculate daily allowance, travel metrics, and worker site reimbursements.")

    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty:
        st.info("No field daily logs found for TA/DA calculations.")
    else:
        st.subheader("📊 TA/DA & Travel Visual Analytics")

        travel_logs = df_logs[df_logs["is_travel_day"].astype(str).str.title() == "Yes"] if "is_travel_day" in df_logs.columns else df_logs

        if travel_logs.empty:
            st.info("No outstation travel days logged yet.")
        else:
            summary = travel_logs.groupby("worker_name").agg(
                Travel_Days=("logged_date", "nunique"),
                Total_Hours=("hours_spent", "sum"),
                Sites_Covered=("installation_id", "nunique"),
            ).reset_index()

            # Dynamic TA/DA rate assumption: ₹500/travel day
            summary["Estimated_TADA_Allowance"] = summary["Travel_Days"] * 500

            # GRAPHS PLACED ON TOP
            c1, c2 = st.columns(2)
            with c1:
                fig_ta = px.bar(
                    summary,
                    x="worker_name",
                    y="Travel_Days",
                    title="Outstation Travel Days per Worker",
                    color="Travel_Days",
                )
                st.plotly_chart(fig_ta, use_container_width=True)
            with c2:
                fig_allowance = px.bar(
                    summary,
                    x="worker_name",
                    y="Estimated_TADA_Allowance",
                    title="Calculated TA/DA Allowance (₹)",
                    color="Estimated_TADA_Allowance",
                )
                st.plotly_chart(fig_allowance, use_container_width=True)

            st.divider()
            # EXCEL & TABLE BELOW GRAPHS
            st.subheader("📜 Detailed Individual Worker TA/DA Breakdown Table")
            st.dataframe(summary, use_container_width=True)

            excel_ta = generate_excel_download(summary, "TADA_Payroll_Summary.xlsx")
            st.download_button(
                "📥 Download TA/DA Payroll Summary Excel",
                data=excel_ta,
                file_name="TADA_Payroll_Summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# --- ADMIN: ADVANCED FIELD LOGS INSPECTOR (REARRANGED: CARDS ABOVE, EXCEL/TABLE BELOW) ---
elif menu == "Advanced Field Logs Inspector":
    st.header("🔍 Advanced Field Logs & Photo Inspector")
    st.caption("Audit complete field logs, examine attached site photos, and filter entries by date, worker, or site ID.")

    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty:
        st.warning("No worker field logs present in database.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            site_list = ["All Sites"] + sorted(df_logs["installation_id"].dropna().unique().tolist())
            selected_site = st.selectbox("Filter Site", site_list)
        with col_f2:
            worker_list = ["All Workers"] + sorted(df_logs["worker_name"].dropna().unique().tolist())
            selected_worker = st.selectbox("Filter Worker", worker_list)
        with col_f3:
            delay_list = ["All Categories"] + sorted(df_logs["delay_category"].dropna().unique().tolist()) if "delay_category" in df_logs.columns else ["All Categories"]
            selected_delay = st.selectbox("Filter Delay Category", delay_list)

        inspect_df = df_logs.copy()
        if selected_site != "All Sites":
            inspect_df = inspect_df[inspect_df["installation_id"] == selected_site]
        if selected_worker != "All Workers":
            inspect_df = inspect_df[inspect_df["worker_name"] == selected_worker]
        if selected_delay != "All Categories" and "delay_category" in inspect_df.columns:
            inspect_df = inspect_df[inspect_df["delay_category"] == selected_delay]

        # METRIC CARDS ABOVE
        st.write("##")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{len(inspect_df)}</div><div class="kpi-label">Total Field Logs</div></div>', unsafe_allow_html=True)
        with k2:
            s_cnt = inspect_df["installation_id"].nunique() if "installation_id" in inspect_df.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{s_cnt}</div><div class="kpi-label">Active Sites Covered</div></div>', unsafe_allow_html=True)
        with k3:
            w_cnt = inspect_df["worker_name"].nunique() if "worker_name" in inspect_df.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{w_cnt}</div><div class="kpi-label">Field Personnel</div></div>', unsafe_allow_html=True)
        with k4:
            p_cnt = len(inspect_df[inspect_df["site_photo"].astype(str).str.startswith("http")]) if "site_photo" in inspect_df.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{p_cnt}</div><div class="kpi-label">Photos Attached</div></div>', unsafe_allow_html=True)

        st.divider()
        # EXCEL TABLE BELOW
        st.subheader(f"📋 Inspection Records ({len(inspect_df)} entries found)")
        st.dataframe(inspect_df, use_container_width=True)

        excel_logs = generate_excel_download(inspect_df, "Field_Logs_Inspector.xlsx")
        st.download_button(
            "📥 Export Inspected Logs to Excel",
            data=excel_logs,
            file_name="Field_Logs_Inspector.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.divider()
        st.subheader("📷 Photo Audit Log")
        photo_logs = inspect_df[inspect_df["site_photo"].astype(str).str.startswith("http")] if "site_photo" in inspect_df.columns else pd.DataFrame()

        if photo_logs.empty:
            st.info("No site photos attached for selected filters.")
        else:
            cols = st.columns(3)
            for idx, (_, row) in enumerate(photo_logs.iterrows()):
                with cols[idx % 3]:
                    st.markdown(f"**Site:** `{row.get('installation_id')}` | **Worker:** {row.get('worker_name')}")
                    st.caption(f"Date: {row.get('logged_date')} | Task: {row.get('task_name')}")
                    st.markdown(f"[🔗 Open Google Drive Photo]({row.get('site_photo')})")

# --- SUPERVISOR / ADMIN: EMPLOYEE ANALYTICS & REPORTS (FIXED BLANK PAGE BUG) ---
elif menu == "Employee Analytics & Reports":
    st.header("👥 Employee Work Analytics & Performance Metrics")
    st.caption("Detailed productivity tracking, task distributions, and employee field logs.")

    df_logs = read_sheet("Worker_Daily_Logs")
    df_workers = read_sheet("Workers_Master")

    if df_logs.empty:
        st.info("No employee daily work logs found in the database.")
    else:
        # High-level Employee KPI Overview
        total_workers = df_logs["worker_name"].nunique() if "worker_name" in df_logs.columns else 0
        total_hours = df_logs["hours_spent"].sum() if "hours_spent" in df_logs.columns else 0
        total_days = df_logs["logged_date"].nunique() if "logged_date" in df_logs.columns else 0
        total_travel_days = len(df_logs[df_logs["is_travel_day"].astype(str).str.title() == "Yes"]) if "is_travel_day" in df_logs.columns else 0

        e1, e2, e3, e4 = st.columns(4)
        with e1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_workers}</div><div class="kpi-label">Active Field Workers</div></div>', unsafe_allow_html=True)
        with e2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_hours} hrs</div><div class="kpi-label">Total Field Work Hours</div></div>', unsafe_allow_html=True)
        with e3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_days}</div><div class="kpi-label">Unique Work Days</div></div>', unsafe_allow_html=True)
        with e4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_travel_days}</div><div class="kpi-label">Outstation Travel Days</div></div>', unsafe_allow_html=True)

        st.divider()

        # Graphs Overview
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("⏳ Total Work Hours per Employee")
            worker_hrs = df_logs.groupby("worker_name")["hours_spent"].sum().reset_index()
            fig_worker_hrs = px.bar(
                worker_hrs,
                x="worker_name",
                y="hours_spent",
                color="hours_spent",
                labels={"worker_name": "Worker Name", "hours_spent": "Total Hours"},
            )
            st.plotly_chart(fig_worker_hrs, use_container_width=True)

        with g2:
            st.subheader("🛠️ Category Time Allocation")
            cat_hrs = df_logs.groupby("task_category")["hours_spent"].sum().reset_index()
            fig_cat = px.pie(
                cat_hrs,
                names="task_category",
                values="hours_spent",
                hole=0.4,
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        st.divider()

        # Individual Worker Specific Drilldown
        st.subheader("👤 Individual Worker Analytics Filter")
        all_workers_list = sorted(df_logs["worker_name"].dropna().unique().tolist())
        selected_emp = st.selectbox("Select Worker for Specific Report", all_workers_list)

        emp_logs = df_logs[df_logs["worker_name"] == selected_emp]

        if not emp_logs.empty:
            st.write(f"### Report Summary for **{selected_emp}**")
            w_hrs = emp_logs["hours_spent"].sum()
            w_days = emp_logs["logged_date"].nunique()
            w_sites = emp_logs["installation_id"].nunique()

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{w_hrs} hrs</div><div class="kpi-label">Hours Contributed</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{w_days} Days</div><div class="kpi-label">Days Logged</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{w_sites} Sites</div><div class="kpi-label">Sites Assigned</div></div>', unsafe_allow_html=True)

            st.dataframe(emp_logs, use_container_width=True)

            excel_emp = generate_excel_download(emp_logs, f"{selected_emp}_Analytics.xlsx")
            st.download_button(
                f"📥 Download {selected_emp} Analytics Excel",
                data=excel_emp,
                file_name=f"{selected_emp}_Analytics.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# --- SUPERVISOR: NEW INSTALLATION REQUESTS ---
elif menu == "🔔 New Installation Requests":
    st.header("🔔 Pending Installation Requests & Sales Orders")
    st.caption("Review new installation orders raised by salespersons and assign team execution leads.")

    df_sites = read_sheet("Sites_Master")
    df_workers = read_sheet("Workers_Master")

    if df_sites.empty:
        st.info("No installation requests found.")
    else:
        unassigned_mask = (
            df_sites.get("team_lead", pd.Series()).astype(str).str.strip().replace(["", "nan", "None", "Unassigned"], "") == ""
        )
        pending_requests = df_sites[unassigned_mask].copy()

        if pending_requests.empty:
            st.success("✅ All installation orders have been processed and assigned to team leads!")
        else:
            st.warning(f"🚨 **{len(pending_requests)} New Installation Order(s) Awaiting Supervisor Action!**")

            worker_options = format_worker_dropdown_options(df_workers)

            for _, req in pending_requests.iterrows():
                site_id = req.get("installation_id", "N/A")
                c_name = req.get("client_name", "N/A")
                c_phone = req.get("client_phone", "N/A")
                sp_name = req.get("salesperson_name", "Salesperson")
                deal_amt = req.get("deal_amount", "N/A")

                with st.expander(f"🆕 Order ID: {site_id} — Client: {c_name} (Salesperson: {sp_name})", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Client Mobile:** {c_phone}")
                        st.write(f"**City:** {req.get('site_city', 'N/A')}")
                        st.write(f"**Address:** {req.get('site_address', 'N/A')}")
                        st.write(f"**Order Date:** {req.get('order_date', 'N/A')}")
                    with col2:
                        st.write(f"**Deal Value:** ₹{deal_amt}")
                        st.write(f"**Target Handover:** {req.get('handover_date', 'N/A')}")
                        st.write(f"**Products Summary:** {req.get('products_summary', 'None')}")

                    st.markdown("#### ⚡ Assign Execution Team & Activate Site")
                    with st.form(f"assign_team_form_{site_id}"):
                        a_lead = st.selectbox("Assign Team Lead *", options=worker_options, key=f"lead_{site_id}")
                        a_helpers = st.multiselect("Assign Helpers / Crew", options=[w for w in worker_options if w != a_lead], key=f"helpers_{site_id}")

                        submit_assignment = st.form_submit_button("✅ Accept Order & Assign Team", use_container_width=True)

                        if submit_assignment:
                            if not a_lead:
                                st.error("Please select a Team Lead.")
                            else:
                                clean_lead = a_lead.split(" (")[0].strip()
                                clean_helpers = [h.split(" (")[0].strip() for h in a_helpers]
                                updates = {
                                    "team_lead": clean_lead,
                                    "team_members": ", ".join(clean_helpers),
                                    "status": "In Progress",
                                }
                                update_sheet_row("Sites_Master", "installation_id", site_id, updates)
                                st.success(f"Installation **{site_id}** activated and assigned to **{clean_lead}**!")
                                st.rerun()

# --- SALESPERSON: MY SALES DASHBOARD ---
elif menu == "My Sales Dashboard":
    st.header(f"💼 Salesperson Project Portal — {user_name} ({user_id})")
    st.caption("Live monitoring of ongoing site installations, site statuses, and field team updates.")

    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty:
        st.info("No sites found in database.")
    else:
        if user_role == "Salesperson":
            sp_id_match = df_sites.get("salesperson_id", pd.Series()).astype(str).str.strip().str.lower() == str(user_id).strip().lower() if "salesperson_id" in df_sites.columns else pd.Series(False, index=df_sites.index)
            sp_name_match = df_sites.get("salesperson_name", pd.Series()).astype(str).str.strip().str.lower() == str(user_name).strip().lower() if "salesperson_name" in df_sites.columns else pd.Series(False, index=df_sites.index)
            my_sites = df_sites[sp_id_match | sp_name_match].copy()
        else:
            my_sites = df_sites.copy()

        if my_sites.empty:
            st.info("⚠️ You currently have no sites assigned to your Sales ID.")
        else:
            total_my_sites = len(my_sites)
            in_prog_my_sites = len(my_sites[my_sites["status"].astype(str).str.strip().str.title() == "In Progress"])
            hold_my_sites = len(my_sites[my_sites["status"].astype(str).str.strip().str.title() == "On Hold"])
            completed_my_sites = len(my_sites[my_sites["status"].astype(str).str.strip().str.title().isin(["Handovered", "Completed"])])

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_my_sites}</div><div class="kpi-label">Total Sites Acquired</div></div>', unsafe_allow_html=True)
            with s2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number" style="color:#00A859;">{in_prog_my_sites}</div><div class="kpi-label">In Progress</div></div>', unsafe_allow_html=True)
            with s3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number" style="color:#D32F2F;">{hold_my_sites}</div><div class="kpi-label">On Hold</div></div>', unsafe_allow_html=True)
            with s4:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{completed_my_sites}</div><div class="kpi-label">Completed Handovers</div></div>', unsafe_allow_html=True)

            st.divider()

            st.subheader("📋 My Acquired Sites & Progress Breakdown")
            for _, site in my_sites.iterrows():
                site_id = site.get("installation_id", "N/A")
                c_name = site.get("client_name", "N/A")
                st_val = str(site.get("status", "In Progress")).title()
                t_lead = site.get("team_lead", "Unassigned")
                deal_amt = site.get("deal_amount", "N/A")
                deal_amt_formatted = f"₹{float(deal_amt):,.2f}" if str(deal_amt).replace('.', '', 1).isdigit() else deal_amt
                
                site_logs = df_logs[df_logs["installation_id"] == site_id] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()
                workers_on_site = site_logs["worker_name"].unique().tolist() if not site_logs.empty and "worker_name" in site_logs.columns else []

                badge_color = "#00A859" if st_val in ["In Progress", "Handovered"] else "#D32F2F"

                with st.expander(f"📍 {site_id} — {c_name} [{st_val}]", expanded=True):
                    col_info, col_team = st.columns(2)
                    with col_info:
                        st.write(f"**Client Phone:** {site.get('client_phone', 'N/A')}")
                        st.write(f"**City:** {site.get('site_city', 'N/A')}")
                        st.write(f"**Order Date:** {site.get('order_date', 'N/A')}")
                        st.write(f"**Deal Amount:** {deal_amt_formatted}")
                        st.write(f"**Target Handover:** {site.get('handover_date', 'N/A')}")
                        st.write(f"**Current Status:** <span style='color:{badge_color}; font-weight:bold;'>{st_val}</span>", unsafe_allow_html=True)
                        if site.get("hold_reason"):
                            st.error(f"**Reason for Hold:** {site.get('hold_reason')}")
                    with col_team:
                        st.write(f"**Supervisor / Team Lead:** {t_lead}")
                        st.write(f"**Team Helpers:** {site.get('team_members', 'None')}")
                        st.write(f"**Active Field Workers Logged:** {', '.join(workers_on_site) if workers_on_site else 'No field logs yet'}")
                        st.write(f"**Total Days Worked On Site:** {site_logs['logged_date'].nunique() if not site_logs.empty else 0} Days")

# --- SALESPERSON: LOG VISIT & ORDER DEAL ---
elif menu == "📝 Log Visit & Order Deal":
    st.header(f"📝 Log Sales Field Visit & Order Deal — {user_name}")
    st.caption("Record site visits, update deal confirmation statuses, set agreed pricing, and create new order deals.")

    df_sites = read_sheet("Sites_Master")

    new_visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"

    st.info(f"🆔 **Automated Site / Order ID:** `{new_visit_id}`")

    with st.form("form_sales_visit_deal"):
        st.subheader("🏢 Client & Site Details")
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("Client / Business Name *", placeholder="e.g. Apex Warehousing")
            client_phone = st.text_input("Client Mobile Number *", max_chars=10, placeholder="e.g. 9876543210")
            client_email = st.text_input("Client Email Address", placeholder="e.g. client@company.com")
            visit_date = st.date_input("Visit Date", value=datetime.now())
        with c2:
            site_city = st.text_input("Site City *", value=user_base_location)
            site_address = st.text_area("Site Address *", placeholder="Complete site address details...")

        st.divider()
        st.subheader("🤝 Deal & Order Status Details")

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            order_confirmed = st.selectbox("Order Status *", ["Confirmed Order", "Under Negotiation / Lead", "Lost / Cancelled"])
        with col_d2:
            deal_amount = st.number_input("Agreed Deal Amount (₹) *", min_value=0.0, step=1000.0, format="%.2f")
        with col_d3:
            expected_handover = st.date_input("Expected Handover Date", value=datetime.now() + timedelta(days=20))

        st.markdown("### 📦 Product Requirements & Visit Notes")
        product_notes = st.text_area("Product Specifications / Deal Terms", placeholder="Mention shutter sizes, quantity, automation type, motor specs, etc.")
        visit_remarks = st.text_area("Sales Visit Remarks / Meeting Notes", placeholder="Detail discussion takeaways, pending approvals, or payment schedules...")

        submit_deal = st.form_submit_button("💾 Save Sales Visit & Sync Order Deal", use_container_width=True)

        if submit_deal:
            clean_phone = str(client_phone).strip()
            clean_email = str(client_email).strip()

            if not client_name.strip() or not clean_phone or not site_city.strip():
                st.error("Please fill in Client Name, Mobile Number, and Site City.")
            elif len(clean_phone) != 10 or not clean_phone.isdigit():
                st.error("Please enter a valid 10-digit mobile number.")
            elif clean_email and not validate_email(clean_email):
                st.error("Please enter a valid email address (e.g. name@domain.com).")
            else:
                order_status_mapped = "In Progress" if order_confirmed == "Confirmed Order" else ("On Hold" if order_confirmed == "Under Negotiation / Lead" else "Cancelled")
                
                order_payload = {
                    "installation_id": new_visit_id,
                    "client_name": client_name.strip(),
                    "client_phone": clean_phone,
                    "client_email": clean_email,
                    "salesperson_id": user_id,
                    "salesperson_name": user_name,
                    "team_lead": "",
                    "team_members": "",
                    "site_city": site_city.strip(),
                    "site_address": site_address.strip(),
                    "order_date": str(visit_date),
                    "handover_date": str(expected_handover),
                    "deal_status": order_confirmed,
                    "deal_amount": str(deal_amount),
                    "products_summary": product_notes.strip(),
                    "status": order_status_mapped,
                    "hold_reason": f"Sales Remarks: {visit_remarks.strip()}" if visit_remarks.strip() else "",
                }

                append_to_sheet("Sites_Master", order_payload)
                st.success(f"🎉 Deal for **{client_name}** recorded successfully under **{new_visit_id}**! Total Value: **₹{deal_amount:,.2f}**")
                st.rerun()

# --- SALESPERSON: TRACK SITE PROGRESS ---
elif menu == "🔍 Track Site Progress":
    st.header(f"🔍 Site Progress & Order Tracker — {user_name}")
    st.caption("Search site records by Site ID or Client Name to view live progress, worker logs, and timeline updates.")

    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty:
        st.warning("No installation records found in the database.")
    else:
        col_search1, col_search2 = st.columns([2, 1])
        with col_search1:
            search_query = st.text_input("🔍 Search by Site ID or Client Name:", placeholder="e.g. INST-2026 or Reliance").strip()
        with col_search2:
            status_filter = st.selectbox("Filter Status", ["All Statuses", "In Progress", "On Hold", "Handovered", "Completed"])

        filtered_df = df_sites.copy()

        if user_role == "Salesperson":
            sp_id_match = (
                filtered_df.get("salesperson_id", pd.Series())
                .astype(str)
                .str.strip()
                .str.lower()
                == str(user_id).strip().lower()
            ) if "salesperson_id" in filtered_df.columns else pd.Series(False, index=filtered_df.index)

            sp_name_match = (
                filtered_df.get("salesperson_name", pd.Series())
                .astype(str)
                .str.strip()
                .str.lower()
                == str(user_name).strip().lower()
            ) if "salesperson_name" in filtered_df.columns else pd.Series(False, index=filtered_df.index)

            filtered_df = filtered_df[sp_id_match | sp_name_match]

        if search_query:
            q = search_query.lower()
            filtered_df = filtered_df[
                filtered_df["installation_id"].astype(str).str.lower().str.contains(q)
                | filtered_df["client_name"].astype(str).str.lower().str.contains(q)
            ]

        if status_filter != "All Statuses":
            filtered_df = filtered_df[filtered_df["status"].astype(str).str.strip().str.title() == status_filter]

        st.write("##")

        if filtered_df.empty:
            st.info("No matching sites found for your search criteria or assigned user profile.")
        else:
            st.subheader(f"Found {len(filtered_df)} Matching Site(s)")
            for _, site in filtered_df.iterrows():
                site_id = site.get("installation_id", "N/A")
                c_name = site.get("client_name", "N/A")
                c_phone = site.get("client_phone", "N/A")
                status = str(site.get("status", "In Progress")).title()
                deal_amt = site.get("deal_amount", "N/A")
                deal_amt_formatted = f"₹{float(deal_amt):,.2f}" if str(deal_amt).replace('.', '', 1).isdigit() else deal_amt

                status_color = "#00A859" if status in ["In Progress", "Handovered"] else "#D32F2F"

                with st.expander(f"🏗️ {site_id} | {c_name} | Status: {status}", expanded=True):
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.markdown(f"**📞 Client Contact:** {c_phone}")
                        st.markdown(f"**📍 City:** {site.get('site_city', 'N/A')}")
                        st.markdown(f"**🏠 Address:** {site.get('site_address', 'N/A')}")
                    with col_m2:
                        st.markdown(f"**💰 Deal Value:** {deal_amt_formatted}")
                        st.markdown(f"**🤝 Deal Status:** {site.get('deal_status', 'N/A')}")
                        st.markdown(f"**📅 Order Date:** {site.get('order_date', 'N/A')}")
                    with col_m3:
                        st.markdown(f"**👨‍🔧 Supervisor / Team Lead:** {site.get('team_lead', 'Unassigned')}")
                        st.markdown(f"**🎯 Target Handover:** {site.get('handover_date', 'N/A')}")
                        st.markdown(f"**⚡ Current Status:** <span style='color:{status_color}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)

                    if site.get("hold_reason"):
                        st.warning(f"**Hold Remarks / Notes:** {site.get('hold_reason')}")

                    st.divider()
                    st.markdown("#### 📜 Live Field Logs for this Site")
                    site_logs = df_logs[df_logs["installation_id"] == site_id] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()

                    if site_logs.empty:
                        st.caption("No daily field logs submitted by workers yet.")
                    else:
                        disp_cols = [
                            c for c in [
                                "logged_date",
                                "site_day",
                                "worker_name",
                                "worker_role",
                                "task_category",
                                "task_name",
                                "hours_spent",
                                "site_remarks",
                            ] if c in site_logs.columns
                        ]
                        st.dataframe(site_logs[disp_cols].sort_values(by="logged_date", ascending=False), use_container_width=True)

# --- ADMIN: SALES ANALYTICS REPORT ---
elif menu == "Sales Analytics Report":
    st.header("📊 Salesperson Performance & Orders Analytics")
    st.caption("Track order volume, project statuses, and revenue acquisition per Salesperson across custom time windows.")

    df_sites = read_sheet("Sites_Master")
    df_workers = read_sheet("Workers_Master")

    if df_sites.empty:
        st.warning("No site records found in Sites_Master.")
    else:
        f1, f2 = st.columns([2, 2])
        with f1:
            time_filter = st.selectbox(
                "📅 Select Report Time Period:",
                [
                    "All Time",
                    "Last 15 Days",
                    "Last 1 Month (30 Days)",
                    "Last 3 Months (90 Days)",
                    "Last 6 Months (180 Days)",
                    "Last 9 Months (270 Days)",
                    "Quarterly (90 Days)",
                    "Last 1 Year (365 Days)",
                ],
            )

        filtered_sites = df_sites.copy()
        if "order_date" in filtered_sites.columns:
            filtered_sites["order_dt"] = pd.to_datetime(filtered_sites["order_date"], errors="coerce")
            today = datetime.now()

            days_map = {
                "Last 15 Days": 15,
                "Last 1 Month (30 Days)": 30,
                "Last 3 Months (90 Days)": 90,
                "Last 6 Months (180 Days)": 180,
                "Last 9 Months (270 Days)": 270,
                "Quarterly (90 Days)": 90,
                "Last 1 Year (365 Days)": 365,
            }

            if time_filter in days_map:
                cutoff_date = today - timedelta(days=days_map[time_filter])
                filtered_sites = filtered_sites[filtered_sites["order_dt"] >= cutoff_date]

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{len(filtered_sites)}</div><div class="kpi-label">Orders Acquired</div></div>', unsafe_allow_html=True)
        with k2:
            in_prog = len(filtered_sites[filtered_sites["status"].astype(str).str.strip().str.title() == "In Progress"]) if "status" in filtered_sites.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number" style="color:#00A859;">{in_prog}</div><div class="kpi-label">Sites In Progress</div></div>', unsafe_allow_html=True)
        with k3:
            on_hold = len(filtered_sites[filtered_sites["status"].astype(str).str.strip().str.title() == "On Hold"]) if "status" in filtered_sites.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number" style="color:#D32F2F;">{on_hold}</div><div class="kpi-label">Sites On Hold</div></div>', unsafe_allow_html=True)
        with k4:
            handovered = len(filtered_sites[filtered_sites["status"].astype(str).str.strip().str.title().isin(["Handovered", "Completed"])]) if "status" in filtered_sites.columns else 0
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{handovered}</div><div class="kpi-label">Completed Handovers</div></div>', unsafe_allow_html=True)

        st.divider()

        if "salesperson_name" in filtered_sites.columns or "salesperson_id" in filtered_sites.columns:
            sp_col = "salesperson_name" if "salesperson_name" in filtered_sites.columns else "salesperson_id"
            
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.subheader("📦 Total Orders Brought per Salesperson")
                fig_orders = px.bar(
                    filtered_sites,
                    x=sp_col,
                    color="status",
                    title=f"Orders & Status Breakdown ({time_filter})",
                    barmode="stack",
                )
                st.plotly_chart(fig_orders, use_container_width=True)

            with c_chart2:
                st.subheader("🎯 Site Status Share")
                fig_pie = px.pie(
                    filtered_sites,
                    names="status",
                    title=f"Site Execution Distribution ({time_filter})",
                    hole=0.4,
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("📜 Detailed Salesperson Order Records")
            disp_cols = [c for c in ["installation_id", "client_name", sp_col, "order_date", "deal_amount", "site_city", "status", "hold_reason"] if c in filtered_sites.columns]
            st.dataframe(filtered_sites[disp_cols], use_container_width=True)
        else:
            st.info("No salesperson assignment columns found in Sites_Master yet.")

# --- WORKER: MY WORK DASHBOARD ---
elif menu == "My Work Dashboard":
    st.header(f"⚡ Daily Workspace & Task Pipeline — {user_name} ({user_designation})")
    st.caption("Track your assigned site duties, update live task progress, and view performance metrics.")

    df_tasks = read_sheet("Task_Assignments")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    st.markdown("### 🏆 Performance & Metrics Scorecard")

    my_logs = pd.DataFrame()
    if not df_logs.empty and "worker_name" in df_logs.columns:
        my_logs = df_logs[df_logs["worker_name"].astype(str).str.strip().str.lower() == user_name.strip().lower()]

    days_worked = my_logs["logged_date"].nunique() if not my_logs.empty and "logged_date" in my_logs.columns else 0
    days_travelled = len(my_logs[my_logs["is_travel_day"] == "Yes"]) if not my_logs.empty and "is_travel_day" in my_logs.columns else 0
    total_hours = my_logs["hours_spent"].sum() if not my_logs.empty and "hours_spent" in my_logs.columns else 0

    avg_handover_days = "N/A"
    if not df_sites.empty and "installation_id" in df_sites.columns:
        my_site_ids = my_logs["installation_id"].unique() if not my_logs.empty else []
        my_sites = df_sites[df_sites["installation_id"].isin(my_site_ids)].copy()

        if not my_sites.empty and "order_date" in my_sites.columns and "handover_date" in my_sites.columns:
            my_sites["order_dt"] = pd.to_datetime(my_sites["order_date"], errors="coerce")
            my_sites["handover_dt"] = pd.to_datetime(my_sites["handover_date"], errors="coerce")
            my_sites["duration"] = (my_sites["handover_dt"] - my_sites["order_dt"]).dt.days
            valid_durations = my_sites["duration"].dropna()
            if not valid_durations.empty:
                avg_handover_days = f"{round(valid_durations.mean(), 1)} Days"

    perf_score = int((total_hours * 2) + (days_travelled * 15) + (days_worked * 10))

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{days_worked}</div><div class="kpi-label">Days Worked</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{days_travelled}</div><div class="kpi-label">Travel Days</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_hours} hrs</div><div class="kpi-label">Total Hours</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{avg_handover_days}</div><div class="kpi-label">Avg Handover Speed</div></div>', unsafe_allow_html=True)
    with k5:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number" style="color:#00A859;">{perf_score} pts</div><div class="kpi-label">Performance Score</div></div>', unsafe_allow_html=True)

# --- COMMON: LOG DAILY TASKS ---
elif menu == "Log Daily Tasks":
    render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

# --- WORKER: MY WORK HISTORY & PERFORMANCE ---
elif menu == "My Work History & Performance":
    st.header(f"📊 Detailed Performance Report — {user_name}")

    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty or "worker_name" not in df_logs.columns:
        st.info("⚠️ No Field Logs Recorded Yet")
    else:
        my_logs = df_logs[df_logs["worker_name"].astype(str).str.strip().str.lower() == user_name.strip().lower()]

        if my_logs.empty:
            st.info("⚠️ You have not submitted any daily work logs yet.")
        else:
            excel_bytes = generate_excel_download(my_logs, f"{user_name}_Performance_Report.xlsx")
            st.download_button(
                "📥 Download Performance Excel Report",
                data=excel_bytes,
                file_name=f"{user_name}_Performance_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
            st.dataframe(my_logs[disp_cols].sort_values(by="logged_date", ascending=False), use_container_width=True)

# --- WORKER/SALESPERSON: MY PROFILE & SETTINGS ---
elif menu == "My Profile & Settings":
    st.header("👤 Profile & Security Settings")

    col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
    with col_center:
        st.markdown(
            f"""
            <div class="card-box">
                <h3 style="margin:0;">{user_name}</h3>
                <p style="margin:5px 0;"><b>Designation:</b> {user_designation}</p>
                <p style="margin:5px 0;"><b>Access Role:</b> {user_role}</p>
                <p style="margin:5px 0;"><b>Work ID:</b> {user_id}</p>
                <p style="margin:5px 0;"><b>Phone:</b> {user.get('phone_no', 'N/A')}</p>
                <p style="margin:5px 0;"><b>Base Station:</b> {user_base_location}</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.subheader("🔑 Change Security PIN")
        with st.form("change_pin_form"):
            curr_pin = st.text_input("Current PIN", type="password")
            new_pin1 = st.text_input("New 4-Digit PIN", type="password", max_chars=4)
            new_pin2 = st.text_input("Confirm New PIN", type="password", max_chars=4)

            update_pin_btn = st.form_submit_button("Update Security PIN", use_container_width=True)

            if update_pin_btn:
                if str(curr_pin).strip() != str(user.get("pin", "")).strip():
                    st.error("Incorrect current PIN!")
                elif not new_pin1 or len(new_pin1) < 4:
                    st.error("New PIN must be at least 4 digits.")
                elif new_pin1 != new_pin2:
                    st.error("New PINs do not match!")
                else:
                    success = update_sheet_row("Workers_Master", "name", user_name, {"pin": new_pin1.strip()})
                    if success:
                        st.session_state.authenticated_user["pin"] = new_pin1.strip()
                        st.success("PIN updated successfully!")
                        st.rerun()

# --- SUPERVISOR: TEAM HEAD DASHBOARD ---
elif menu == "Team Head Dashboard":
    st.header("👥 Dual-Tab Team Head Dashboard")
    tab_personal, tab_crew = st.tabs(["👤 Personal Work Log", "👨‍🔧 Crew Task Logging"])

    with tab_personal:
        st.subheader(f"Personal Execution Log ({user_name})")
        render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

    with tab_crew:
        st.subheader("Manage Active Crew Logs")
        df_workers = read_sheet("Workers_Master")
        
        worker_options = format_worker_dropdown_options(df_workers)

        if not worker_options:
            st.info("⚠️ No Active Crew Members Found")
        else:
            selected_crew_str = st.selectbox("Select Worker to Log For", worker_options)
            selected_crew = selected_crew_str.split(" (")[0].strip()
            st.divider()
            render_restricted_work_input(target_worker_name=selected_crew, is_crew_log=True)

# --- SUPERVISOR: ACTIVE TASKS DASHBOARD ---
elif menu == "Active Tasks Dashboard":
    st.header("📋 Active Tasks Dashboard")
    st.caption("Track site installation progress, monitor individual task statuses, and export site reports.")

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
            status_filter = st.selectbox("Filter by Task Status", ["All Statuses", "In Progress", "Pending", "Completed"])

        filtered_tasks = df_tasks.copy()
        if site_filter != "All Sites" and "installation_id" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["installation_id"] == site_filter]
        if status_filter != "All Statuses" and "status" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["status"] == status_filter]

        st.write("##")
        st.subheader(f"Task List ({len(filtered_tasks)} Records)")
        st.dataframe(filtered_tasks, use_container_width=True)

# --- ADMIN: ANALYTICS DASHBOARD ---
elif menu == "Admin Analytics Dashboard":
    st.header("📊 Admin Operations & Dynamic Expense Analytics")

    df_logs = read_sheet("Worker_Daily_Logs")
    df_expenses = read_sheet("Expense_Logs")
    df_sites = read_sheet("Sites_Master")

    active_site_ids = []
    if not df_sites.empty and "installation_id" in df_sites.columns:
        df_sites_copy = df_sites.copy()
        df_sites_copy.columns = [str(col).strip().lower().replace(" ", "_") for col in df_sites_copy.columns]
        
        running_sites = df_sites_copy[
            ~df_sites_copy["status"].astype(str).str.strip().str.title().isin(["Handovered", "Handover", "Completed"])
        ]
        active_site_ids = running_sites["installation_id"].unique().tolist()

    if not df_logs.empty and active_site_ids:
        df_logs = df_logs[df_logs["installation_id"].isin(active_site_ids)]

    if df_logs.empty and df_expenses.empty:
        st.info("No active log or expense data available for running sites.")
    else:
        sites_visited = df_logs["installation_id"].nunique() if "installation_id" in df_logs.columns else 0
        days_worked = df_logs["logged_date"].nunique() if "logged_date" in df_logs.columns else 0
        days_travelled = len(df_logs[df_logs["is_travel_day"] == "Yes"]) if "is_travel_day" in df_logs.columns else 0

        active_expenses = df_expenses[df_expenses["installation_id"].isin(active_site_ids)] if not df_expenses.empty and "installation_id" in df_expenses.columns else pd.DataFrame()

        travel_exp = (
            pd.to_numeric(active_expenses["travel_expense"], errors="coerce").sum() 
            if not active_expenses.empty and "travel_expense" in active_expenses.columns 
            else 0
        )
        stay_exp = (
            pd.to_numeric(active_expenses["stay_expense"], errors="coerce").sum() 
            if not active_expenses.empty and "stay_expense" in active_expenses.columns 
            else 0
        )
        food_exp = (
            pd.to_numeric(active_expenses["food_expense"], errors="coerce").sum() 
            if not active_expenses.empty and "food_expense" in active_expenses.columns 
            else 0
        )
        misc_exp = (
            pd.to_numeric(active_expenses["misc_expense"], errors="coerce").sum() 
            if not active_expenses.empty and "misc_expense" in active_expenses.columns 
            else 0
        )
        total_site_expenses = travel_exp + stay_exp + food_exp + misc_exp

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{sites_visited}</div><div class="kpi-label">Active Sites Visited</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{days_worked}</div><div class="kpi-label">Days Worked</div></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">{days_travelled}</div><div class="kpi-label">Days Travelled</div></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">₹{total_site_expenses:,.0f}</div><div class="kpi-label">Running Sites Total Cost</div></div>', unsafe_allow_html=True)
        with k5:
            st.markdown(f'<div class="kpi-card"><div class="kpi-number">₹{travel_exp:,.0f}</div><div class="kpi-label">Travel Expenses</div></div>', unsafe_allow_html=True)

        st.divider()

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("⚠️ Problems & Delays Encountered")
            if "delay_category" in df_logs.columns:
                delay_df = df_logs[df_logs["delay_category"] != "No Delay"]
                if not delay_df.empty:
                    fig_delay = px.bar(
                        delay_df,
                        x="delay_category",
                        color="installation_id",
                        title="Site Problems by Category (Running Sites)",
                    )
                    st.plotly_chart(fig_delay, use_container_width=True)
                else:
                    st.success("No delays or problems reported across running sites!")

        with g2:
            st.subheader("💰 Dynamic Everyday Site Expenses Breakdown")
            if not active_expenses.empty and "installation_id" in active_expenses.columns:
                fig_exp = px.bar(
                    active_expenses,
                    x="installation_id",
                    y=["travel_expense", "stay_expense", "food_expense", "misc_expense"],
                    title="Active Site Expense Breakdown (Dynamic Daily Tracker)",
                    barmode="stack",
                )
                st.plotly_chart(fig_exp, use_container_width=True)
            else:
                st.info("No active site expenses recorded yet.")

# --- ADMIN: DYNAMIC USER & ACCESS MANAGEMENT (INCLUDES DELETE USER & UPDATE USER TABS) ---
elif menu == "👥 Dynamic User & Access Management":
    st.header("👥 Dynamic User & Access Management")
    df_workers = read_sheet("Workers_Master")

    if st.session_state.get("user_created_success"):
        new_user = st.session_state.get("created_user_name", "User")
        st.toast(f"👤 Account for {new_user} created successfully!", icon="✅")
        del st.session_state["user_created_success"]

    # Tab selection includes Update User and Delete User
    tabs_list = ["➕ Add Single User", "✏️ Update User", "❌ Delete User (Admin Only)", "⚡ Batch Process Raw String"]
    tab_add, tab_edit, tab_del, tab_batch = st.tabs(tabs_list)

    # 1. ADD USER TAB (WITH UNIQUE AADHAAR AND PHONE NUMBER)
    with tab_add:
        st.subheader("Add Employee / Salesperson / Supervisor")
        col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
        with col_center:
            selected_role = st.selectbox(
                "System Access Role *", 
                ["Worker", "Supervisor", "Salesperson", "Admin"], 
                key="add_user_role_select"
            )
            
            worker_designation = ""
            if selected_role == "Worker":
                worker_designation = st.selectbox(
                    "Field Designation *", 
                    WORKER_DESIGNATIONS, 
                    key="add_user_designation_select"
                )

            auto_generated_id = generate_work_id(selected_role, df_workers)

            with st.form("add_user_form"):
                st.info(f"**Auto-Generated Work ID:** `{auto_generated_id}`")
                
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("Full Name *")
                    new_phone = st.text_input("Phone Number *", max_chars=10, placeholder="10-digit mobile number")
                    if selected_role != "Worker":
                        new_email = st.text_input("Email Address *", placeholder="e.g. user@company.com")
                    else:
                        new_email = ""
                with c2:
                    new_aadhaar = st.text_input("Aadhaar Number *", max_chars=12, placeholder="12-digit number")
                    new_pin = st.text_input("4-Digit PIN / Password *", type="password")
                    new_base = st.text_input("Base Station / City", value="Jaipur")

                submit_new_user = st.form_submit_button("Create User & Sync to Database", use_container_width=True)
                if submit_new_user:
                    clean_aadhaar = str(new_aadhaar).strip()
                    clean_phone = str(new_phone).strip()

                    # Validate Aadhaar Duplication
                    existing_aadhaars = []
                    if not df_workers.empty and "aadhaar_no" in df_workers.columns:
                        existing_aadhaars = df_workers["aadhaar_no"].astype(str).str.strip().tolist()

                    if not new_name or not new_pin or not clean_phone:
                        st.error("Please fill in Full Name, Phone Number, and PIN.")
                    elif len(clean_phone) != 10 or not clean_phone.isdigit():
                        st.error("Please enter a valid 10-digit phone number.")
                    elif selected_role != "Worker" and (not new_email or not validate_email(new_email)):
                        st.error("Please enter a valid email address.")
                    elif not clean_aadhaar or len(clean_aadhaar) != 12 or not clean_aadhaar.isdigit():
                        st.error("Aadhaar number must contain exactly 12 numeric digits.")
                    elif clean_aadhaar in existing_aadhaars:
                        st.error("⚠️ Duplicate Aadhaar Number detected! An employee with this Aadhaar already exists.")
                    else:
                        user_dict = {
                            "worker_id": auto_generated_id,
                            "name": new_name.strip(),
                            "phone_no": clean_phone,
                            "email": new_email.strip() if selected_role != "Worker" else "",
                            "aadhaar_no": clean_aadhaar,
                            "pin": str(new_pin).strip(),
                            "role": selected_role,
                            "designation": worker_designation if selected_role == "Worker" else selected_role,
                            "base_location": new_base.strip(),
                        }
                        append_to_sheet("Workers_Master", user_dict)
                        st.session_state["user_created_success"] = True
                        st.session_state["created_user_name"] = new_name
                        st.rerun()

    # 2. UPDATE USER TAB
    with tab_edit:
        st.subheader("✏️ Update User Profile & Access")
        if df_workers.empty or "name" not in df_workers.columns:
            st.info("No user profiles available to update.")
        else:
            selected_edit_user = st.selectbox("Select User Profile to Edit", sorted(df_workers["name"].unique().tolist()))
            user_data = df_workers[df_workers["name"] == selected_edit_user].iloc[0]

            col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
            with col_center:
                with st.form("edit_user_form"):
                    e_role = st.selectbox(
                        "Update System Access Role",
                        ["Worker", "Supervisor", "Salesperson", "Admin"],
                        index=["Worker", "Supervisor", "Salesperson", "Admin"].index(user_data.get("role", "Worker")),
                    )
                    
                    e_desig = user_data.get("designation", "")
                    desig_idx = WORKER_DESIGNATIONS.index(e_desig) if e_desig in WORKER_DESIGNATIONS else 0
                    
                    e_designation = st.selectbox(
                        "Update Field Designation",
                        WORKER_DESIGNATIONS,
                        index=desig_idx
                    ) if e_role == "Worker" else e_role

                    e_phone = st.text_input("Update Phone Number", value=str(user_data.get("phone_no", "")))

                    if e_role != "Worker":
                        e_email = st.text_input("Update Email", value=str(user_data.get("email", "")))
                    else:
                        e_email = ""

                    e_pin = st.text_input("Update PIN", value=str(user_data.get("pin", "")))
                    e_base = st.text_input("Update Base Location", value=str(user_data.get("base_location", "Jaipur")))

                    submit_edit = st.form_submit_button("Update Profile in Database", use_container_width=True)
                    if submit_edit:
                        if e_role != "Worker" and e_email and not validate_email(e_email):
                            st.error("Please enter a valid email address.")
                        else:
                            updates = {
                                "role": e_role,
                                "designation": e_designation,
                                "phone_no": e_phone.strip(),
                                "email": e_email.strip() if e_role != "Worker" else "",
                                "pin": e_pin,
                                "base_location": e_base,
                            }
                            update_sheet_row("Workers_Master", "name", selected_edit_user, updates)
                            st.success(f"Updated **{selected_edit_user}** successfully!")
                            st.rerun()

    # 3. DELETE USER TAB (ADMIN ONLY)
    with tab_del:
        st.subheader("❌ Delete User Account")
        if user_role != "Admin":
            st.error("🔒 Security Restriction: Only Admin accounts can delete user profiles.")
        elif df_workers.empty or "name" not in df_workers.columns:
            st.info("No users available to delete.")
        else:
            # Filter out logged-in admin from self-deletion
            deletable_users = df_workers[df_workers["name"] != user_name]
            
            if deletable_users.empty:
                st.info("No other user profiles available to delete.")
            else:
                user_to_delete = st.selectbox("Select User Profile to Permanently Delete", deletable_users["name"].tolist(), key="del_user_select")
                del_target_info = deletable_users[deletable_users["name"] == user_to_delete].iloc[0]
                
                st.warning(f"⚠️ Are you sure you want to delete **{user_to_delete}** (`{del_target_info.get('worker_id', 'N/A')}`)? This action cannot be undone.")
                
                col_del_btn1, col_del_btn2 = st.columns([1, 2])
                with col_del_btn1:
                    if st.button("🗑️ Confirm & Delete User", key="btn_confirm_delete_user"):
                        success = delete_sheet_row("Workers_Master", "name", user_to_delete)
                        if success:
                            st.success(f"User **{user_to_delete}** deleted successfully from database.")
                            st.rerun()
                        else:
                            st.error("Failed to delete user. Please retry.")

    # 4. BATCH IMPORT TAB
    with tab_batch:
        st.subheader("⚡ Batch Import Employees")
        raw_text_input = st.text_area("Paste Continuous Data String Here:")
        if st.button("🔍 Parse and Import Data"):
            if raw_text_input:
                pattern = re.compile(
                    r"([A-Z]{1,3}\d{2,3})([A-Za-z\s]+?)(\d{12})(\d{4})(Supervisor|Worker|Admin|Salesperson)([A-Za-z]+)"
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
                            "designation": "Installer" if m[4] == "Worker" else m[4],
                            "base_location": m[5],
                        },
                    )
                st.success("All extracted users synced!")
                st.rerun()

# --- SUPERVISOR: NEW ORDER ---
elif menu == "New Installation Order":
    st.header("Create New Installation Order")
    df_workers = read_sheet("Workers_Master")
    df_sites = read_sheet("Sites_Master")
    
    worker_options = format_worker_dropdown_options(df_workers)
    salesperson_options = []

    if not df_workers.empty and "name" in df_workers.columns:
        sp_df = df_workers[df_workers["role"].astype(str).str.strip().str.title() == "Salesperson"]
        if not sp_df.empty:
            salesperson_options = (sp_df["worker_id"].astype(str) + " - " + sp_df["name"].astype(str)).tolist()

    if "products_count" not in st.session_state:
        st.session_state.products_count = 1

    st.markdown("### 🔗 Order Creation & Linkage")
    existing_sp_orders = {}
    if not df_sites.empty and "installation_id" in df_sites.columns:
        unassigned_df = df_sites[
            df_sites.get("team_lead", pd.Series()).astype(str).str.strip().replace(["", "nan", "None"], "") == ""
        ]
        for _, r in unassigned_df.iterrows():
            s_id = str(r.get("installation_id")).strip()
            c_n = str(r.get("client_name")).strip()
            existing_sp_orders[f"{s_id} — {c_n}"] = s_id

    link_type = st.radio(
        "Order Source:",
        options=["Create Custom Site ID (Direct Supervisor Order)", "Select Existing Salesperson Order ID"],
        horizontal=True
    )

    if link_type == "Select Existing Salesperson Order ID" and existing_sp_orders:
        selected_sp_label = st.selectbox("Select Pending Sales Order *", options=list(existing_sp_orders.keys()))
        visit_id = existing_sp_orders[selected_sp_label]
        st.info(f"📌 **Linking to Existing Salesperson Order ID:** `{visit_id}`")
    else:
        visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"
        st.info(f"🆔 **Automated Site / Order ID:** `{visit_id}`")

    col_client, col_team, col_dates = st.columns(3)

    with col_client:
        st.markdown("### 🏢 Client Info")
        client_name = st.text_input("Client / Company Name *", placeholder="e.g. Reliance Logistics")
        client_phone = st.text_input("Client Mobile No. *", placeholder="e.g. 9876543210", max_chars=10)
        client_email = st.text_input("Client Email Address", placeholder="e.g. client@company.com")
        
        selected_sp = st.selectbox("💼 Link Salesperson", options=["Unassigned"] + salesperson_options)
        sp_id = selected_sp.split(" - ")[0] if selected_sp != "Unassigned" else ""
        sp_name = selected_sp.split(" - ")[1] if selected_sp != "Unassigned" else "Unassigned"

    with col_team:
        st.markdown("### 👨‍💼 Team & Site Structure")
        team_lead_name = st.selectbox("Team Lead Name *", options=worker_options, key="inst_team_lead")
        team_helpers = st.multiselect("Team Members / Helpers", options=[w for w in worker_options if w != team_lead_name], key="inst_helpers")
        city_name = st.text_input("City Name *", value="Mumbai", key="inst_city_name")
        site_address = st.text_area("Site Address *", placeholder="Full installation site address...", key="inst_site_address")

    with col_dates:
        st.markdown("### 📅 Order Dates")
        inst_date = st.date_input("Installation Date", value=datetime.now(), key="inst_order_date")
        site_clearance_date = st.date_input("Site Clearance Date", value=datetime.now(), key="inst_clearance_date")
        target_handover_date = st.date_input("Target Handover Date", value=datetime.now() + timedelta(days=15), key="inst_handover_date")

    st.divider()

    st.markdown("### 📦 Order Products Details")
    products_data = []
    catalog_main_categories = list(PRODUCT_CATALOG.keys())

    for p_idx in range(st.session_state.products_count):
        st.markdown(f"#### Product #{p_idx + 1}")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            product_type = st.selectbox("Select Product", catalog_main_categories, key=f"prod_type_{p_idx}")
            dimensions = st.text_input("Dimensions (WxH)", placeholder="e.g., 5330X6000", key=f"prod_dim_{p_idx}")
        with col_p2:
            sub_cat_options = PRODUCT_CATALOG.get(product_type, ["Other"])
            sub_category = st.selectbox("Select Sub-Category", sub_cat_options, key=f"prod_sub_{p_idx}")
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"prod_qty_{p_idx}")

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
    if st.button("💾 Submit Installation Order", use_container_width=True, key="btn_submit_inst_order"):
        clean_phone = str(client_phone).strip()
        clean_email = str(client_email).strip()

        if not client_name or not clean_phone or not team_lead_name or not city_name or not site_address:
            st.error("Please fill in all mandatory fields.")
        elif len(clean_phone) != 10 or not clean_phone.isdigit():
            st.error("Please enter a valid 10-digit mobile number.")
        elif clean_email and not validate_email(clean_email):
            st.error("Please enter a valid email address.")
        else:
            clean_lead = team_lead_name.split(" (")[0].strip()
            clean_helpers = [h.split(" (")[0].strip() for h in team_helpers]

            order_data = {
                "installation_id": visit_id,
                "client_name": client_name.strip(),
                "client_phone": clean_phone,
                "client_email": clean_email,
                "salesperson_id": sp_id,
                "salesperson_name": sp_name,
                "team_lead": clean_lead,
                "team_members": ", ".join(clean_helpers),
                "site_city": city_name,
                "site_address": site_address,
                "order_date": str(inst_date),
                "site_clearance_date": str(site_clearance_date),
                "handover_date": str(target_handover_date),
                "products_summary": str(products_data),
                "status": "In Progress",
            }
            if link_type == "Select Existing Salesperson Order ID" and existing_sp_orders:
                update_sheet_row("Sites_Master", "installation_id", visit_id, order_data)
            else:
                append_to_sheet("Sites_Master", order_data)

            st.success(f"Installation Order **{visit_id}** for **{client_name}** linked to **{sp_name}** successfully!")
            st.session_state.products_count = 1

# --- SUPERVISOR: VIEW LOGS & UPDATE ---
elif menu == "View Logs & Update Status":
    render_view_logs_and_update_status()

# --- OTHER SECTIONS & MASTER DATABASE ---
elif menu == "Master Database":
    st.header("🗄️ Live Google Sheets Database")
    m_tab1, m_tab2, m_tab3, m_tab4, m_tab5 = st.tabs([
        "Workers Master",
        "Sites Master",
        "Task Assignments",
        "Worker Daily Logs",
        "Expense Logs",
    ])

    with m_tab1:
        st.dataframe(read_sheet("Workers_Master"), use_container_width=True)
    with m_tab2:
        st.dataframe(read_sheet("Sites_Master"), use_container_width=True)
    with m_tab3:
        st.dataframe(read_sheet("Task_Assignments"), use_container_width=True)
    with m_tab4:
        st.dataframe(read_sheet("Worker_Daily_Logs"), use_container_width=True)
    with m_tab5:
        st.dataframe(read_sheet("Expense_Logs"), use_container_width=True)
