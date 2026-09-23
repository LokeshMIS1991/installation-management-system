import os
import re
import io
from pathlib import Path
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import plotly.express as px

# ==========================================
# 0. CROSS-PLATFORM PATH MANAGEMENT
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "Company Logo.jpeg"

# ==========================================
# 1. OFFICIAL PRODUCT CATALOGUE & CATEGORIES
# ==========================================
PRODUCT_CATALOG = {
    "Rolling Shutters": ["Motorized Rolling Shutter", "Gear Rolling Shutter", "Manual Rolling Shutter"],
    "Dock Leveler": ["Hydraulic Doclevller", "Hydraulic Dock Edge", "Manual Dock Edge"],
    "Gates": ["Sliding Gate", "Telescopic Gate", "L-Folding Gate", "Swing Gate", "Retractable Gate"],
    "Doors": ["High Speed Door", "Fire Door", "HMPS Door", "GPD Door", "Overhead Sectional Door"],
    "Boom Barrier": ["Automatic Traffic Barrier", "Heavy-Duty Traffic Barrier"],
    "Dock Shelter": ["Retractable Dock Shelter", "Inflatable Dock Shelter"],
    "Dock Bumper": ["Heavy Rubber Bumper", "Moulded Bumper"],
    "Other": ["Other"]
}

TASK_CATEGORIES = [
    "Civil & Mounting Work",
    "Track Leveling",
    "Wiring & Electrical",
    "Commissioning & Testing",
    "Site Survey",
    "Travel / Transit",
    "Other"
]

DELAY_REASONS = [
    "No Delay",
    "Power Supply Issue",
    "Civil Work Delay",
    "Client Hold",
    "Material Missing",
    "Weather Delay",
    "Other"
]

STATUS_OPTIONS = ["In Progress", "Completed", "On Hold", "Pending Inspection", "Handovered"]

# ==========================================
# 2. PAGE CONFIG & RESPONSIVE GLOBAL THEME
# ==========================================
st.set_page_config(
    page_title="Sidharth Shutter & Automation - Portal", 
    layout="wide", 
    page_icon="⚙️",
    initial_sidebar_state="expanded"
)

COLOR_PRIMARY = "#10418A"    # Sidharth Deep Blue
COLOR_ACCENT = "#00A859"     # Vibrant Green
COLOR_BG_LIGHT = "#EBF3FA"   # Soft Blue Background Tint

st.markdown(f"""
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
    section[data-testid="stSidebar"] hr {{
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
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
    .login-caption {{
        color: #6C757D;
        text-align: center;
        font-size: 13px;
        margin-top: 10px;
        margin-bottom: 20px;
        font-weight: 500;
    }}
    img {{
        max-width: 100%;
        height: auto;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GOOGLE SHEETS LIVE CONNECTION ENGINE
# ==========================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(credentials)

def get_workbook():
    client = get_gspread_client()
    sheet_url = st.secrets.get("spreadsheet_url", "https://docs.google.com/spreadsheets/d/19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s/edit")
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
        
        # Add timestamp if missing
        if "created_at" in headers and "created_at" not in row_data_dict:
            row_data_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row_values = [str(row_data_dict.get(h, "")) for h in headers]
        sheet.append_row(row_values)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error writing to tab '{sheet_name}': {e}")

def update_sheet_row(sheet_name: str, key_col: str, key_val: str, update_dict: dict) -> bool:
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
        
        # Add timestamp if missing
        if "updated_at" in headers:
            update_dict["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for col_name, new_val in update_dict.items():
            if col_name in headers:
                col_num = headers.index(col_name) + 1
                sheet.update_cell(row_num, col_num, str(new_val))
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error updating tab '{sheet_name}': {e}")
        return False

def parse_raw_worker_string(raw_str):
    pattern = re.compile(
        r'(W\d{3})'                                 # Worker ID
        r'([A-Za-z\s]+?)'                           # Name
        r'(\d{12})'                                 # National ID
        r'(\d{4})'                                  # PIN
        r'(Supervisor|Worker|Admin)'                # Role
        r'([A-Za-z]+)'                              # Base Location
    )
    parsed_workers = []
    matches = pattern.findall(raw_str)
    for m in matches:
        parsed_workers.append({
            "worker_id": m[0],
            "name": m[1].strip(),
            "aadhaar_no": m[2],
            "pin": m[3],
            "role": m[4],
            "base_location": m[5]
        })
    return parsed_workers

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# ==========================================
# 4. AUTHENTICATION
# ==========================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "remembered_username" not in st.session_state:
    st.session_state.remembered_username = ""

if not st.session_state.authenticated_user:
    st.write("##")
    col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
    with col_center:
        with st.form("login_form"):
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), use_container_width=True)
            else:
                st.markdown(f"""
                    <div style="text-align: center;">
                        <h1 style="color: {COLOR_PRIMARY}; margin: 0; font-size: 32px;">SIDHARTH</h1>
                        <p style="color: {COLOR_ACCENT}; font-weight: bold; margin: 0; font-size: 14px; letter-spacing: 2px;">SHUTTER & AUTOMATION</p>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="login-caption">Enterprise Operations & Field Portal</div>', unsafe_allow_html=True)

            username_input = st.text_input("Username / Name", value=st.session_state.remembered_username, placeholder="e.g. Parvesh Kumar or Vishak")
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
                            (df_workers["name"].astype(str).str.strip().str.lower() == username_input.strip().lower()) & 
                            (df_workers["pin"].astype(str) == str(password_input).strip())
                        ]
                        if not user_row.empty:
                            st.session_state.authenticated_user = user_row.iloc[0].to_dict()
                            if remember_me:
                                st.session_state.remembered_username = username_input.strip()
                            else:
                                st.session_state.remembered_username = ""
                            st.success("Authentication Successful!")
                            st.rerun()
                        else:
                            st.error("Invalid Username or Password.")
                    else:
                        st.error("⚠️ Database Unreachable — Verify Google Sheets setup.")
    st.stop()

# ==========================================
# 5. ACTIVE SESSION & SIDEBAR NAVIGATION
# ==========================================
user = st.session_state.authenticated_user
user_name = user.get("name", "User")
user_role = user.get("role", "Worker")
user_base_location = user.get("base_location", "Jaipur")

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), use_container_width=True)
else:
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 12px; background-color: {COLOR_PRIMARY}; color: white; border-radius: 8px; margin-bottom: 10px;">
            <h2 style="margin:0; font-size: 21px; color: white !important;">SIDHARTH</h2>
            <p style="margin:0; font-size: 11px; letter-spacing: 1.5px; color: {COLOR_ACCENT}; font-weight: bold;">SHUTTER & AUTOMATION</p>
        </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown(f"**Active User:** {user_name} (`{user_role}`)  \n**Base Station:** {user_base_location}")
st.sidebar.divider()

if user_role == "Admin":
    menu_options = [
        "Admin Analytics Dashboard",
        "Employee Analytics & Reports",
        "User Management", 
        "TA/DA Payroll & Travel Summary", 
        "Advanced Field Logs Inspector", 
        "Master Database"
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
        "Master Database"
    ]
else:
    menu_options = [
        "Log Daily Tasks", 
        "My Work History", 
        "My Profile & Settings"
    ]

menu = st.sidebar.radio("Navigation Menu", menu_options)
st.sidebar.divider()

if st.sidebar.button("🚪 LOG OUT", use_container_width=True):
    st.session_state.authenticated_user = None
    st.rerun()

# ==========================================
# 6. DYNAMIC MULTI-TASK WORK INPUT HELPER
# ==========================================
def render_restricted_work_input(target_worker_name, is_crew_log=False):
    df_sites = read_sheet("Sites_Master")
    df_workers = read_sheet("Workers_Master")

    if not df_sites.empty and "installation_id" in df_sites.columns:
        if "status" in df_sites.columns:
            active_sites = df_sites[
                ~df_sites["status"].astype(str).str.strip().str.lower().isin(["handovered", "handover", "completed"])
            ]
            site_options = active_sites["installation_id"].tolist()
        else:
            site_options = df_sites["installation_id"].tolist()
    else:
        site_options = []

    if not df_workers.empty and "name" in df_workers.columns:
        if "role" in df_workers.columns:
            filtered_workers = df_workers[
                ~df_workers["role"].astype(str).str.strip().str.lower().isin(["supervisor", "admin"])
            ]
            worker_options = sorted(filtered_workers["name"].astype(str).str.strip().unique().tolist())
        else:
            worker_options = sorted(df_workers["name"].astype(str).str.strip().unique().tolist())
    else:
        worker_options = [target_worker_name]

    if not site_options:
        st.warning("⚠️ No Active Installation Sites Available — All sites are either handovered or not yet created.")
        return

    header_placeholder = st.empty()

    c_site, c_date = st.columns(2)
    with c_site:
        selected_site_id = st.selectbox(
            "Current Logging for :", 
            site_options, 
            key=f"site_{target_worker_name}_{is_crew_log}"
        )
    with c_date:
        log_date = st.date_input("Date of Work", value=datetime.now(), key=f"date_{target_worker_name}_{is_crew_log}")

    header_placeholder.markdown(f"## 📝 Log Daily Tasks - {selected_site_id}")

    site_info = df_sites[df_sites["installation_id"] == selected_site_id].iloc[0]
    site_city = site_info.get("site_city", "Jaipur")

    st.markdown("### 👥 Crew & Team Assignment")
    col_lead, col_helpers = st.columns(2)

    with col_lead:
        default_lead_idx = worker_options.index(target_worker_name) if target_worker_name in worker_options else 0
        team_lead_selected = st.selectbox(
            "Team Lead Name *",
            options=worker_options,
            index=default_lead_idx,
            key=f"team_lead_{target_worker_name}_{is_crew_log}"
        )

    with col_helpers:
        available_helpers = [w for w in worker_options if w != team_lead_selected]
        team_helpers_selected = st.multiselect(
            "Team Members / Helpers",
            options=available_helpers,
            key=f"helpers_{target_worker_name}_{is_crew_log}"
        )

    active_crew = [team_lead_selected] + team_helpers_selected

    st.write("##")
    st.markdown("### 🛠️ Tasks Completed Today")

    task_count_key = f"task_lines_count_{target_worker_name}_{is_crew_log}"
    if task_count_key not in st.session_state:
        st.session_state[task_count_key] = 1

    task_entries = []

    for i in range(st.session_state[task_count_key]):
        st.caption(f"**Task Line #{i+1}**")
        col_cat, col_desc, col_assigned, col_hrs, col_min = st.columns([2.5, 3, 2.5, 1.2, 1.2])

        with col_cat:
            cat = st.selectbox(f"Category #{i+1}", TASK_CATEGORIES, key=f"cat_{target_worker_name}_{is_crew_log}_{i}")
        with col_desc:
            desc = st.text_input(f"Task #{i+1} Description", placeholder="e.g., Track Leveling", key=f"desc_{target_worker_name}_{is_crew_log}_{i}")
        with col_assigned:
            assigned_worker = st.selectbox(f"Assigned To #{i+1}", options=active_crew, key=f"assigned_{target_worker_name}_{is_crew_log}_{i}")
        with col_hrs:
            hrs = st.number_input(f"Hours", min_value=0, max_value=24, value=2, step=1, key=f"hrs_{target_worker_name}_{is_crew_log}_{i}")
        with col_min:
            mins = st.selectbox(f"Minutes", [0, 15, 30, 45], key=f"min_{target_worker_name}_{is_crew_log}_{i}")

        task_entries.append({
            "category": cat,
            "description": desc,
            "assigned_worker": assigned_worker,
            "hours": hrs,
            "minutes": mins
        })

    if st.button("➕ ADD MORE TASK LINES", key=f"add_task_btn_{target_worker_name}_{is_crew_log}"):
        st.session_state[task_count_key] += 1
        st.rerun()

    st.divider()

    st.markdown("### ⚠️ Site Remarks / Delays")
    col_delay_cat, col_delay_notes = st.columns([1, 2])
    
    with col_delay_cat:
        delay_reason = st.selectbox("Primary Delay Category", options=DELAY_REASONS, key=f"delay_reason_{target_worker_name}_{is_crew_log}")
        
    with col_delay_notes:
        site_remarks = st.text_area("Specific Site Notes / Remarks", placeholder="Provide additional details regarding the delay or site notes...", key=f"rem_{target_worker_name}_{is_crew_log}")

    st.markdown("### 📷 Site Photo Documentation")
    uploaded_photo = st.file_uploader("Upload Photo of Site / Issues / Completed Task", type=["jpg", "jpeg", "png"], key=f"photo_{target_worker_name}_{is_crew_log}")

    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Uploaded Site Photo Preview", width=280)

    st.write("##")

    if st.button("💾 Sync Daily Log to Database", key=f"btn_sync_{target_worker_name}_{is_crew_log}", use_container_width=True):
        photo_filename = uploaded_photo.name if uploaded_photo is not None else "No Photo"
        records_saved = 0

        for idx, t in enumerate(task_entries):
            if not t["description"].strip():
                continue

            worker = t["assigned_worker"]
            w_base = "Jaipur"
            if not df_workers.empty:
                m = df_workers[df_workers["name"] == worker]
                if not m.empty:
                    w_base = m.iloc[0].get("base_location", "Jaipur")

            w_is_travel = str(w_base).strip().lower() != str(site_city).strip().lower()

            log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx+1}"
            log_entry = {
                "log_id": log_id,
                "installation_id": selected_site_id,
                "logged_date": str(log_date),
                "worker_name": worker,
                "worker_role": "Team Lead" if worker == team_lead_selected else "Helper",
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
                "site_photo": photo_filename,
                "logged_by": target_worker_name
            }
            append_to_sheet("Worker_Daily_Logs", log_entry)
            records_saved += 1

        if records_saved > 0:
            st.success(f"Successfully recorded {records_saved} task log(s) for crew members!")
            st.session_state[task_count_key] = 1
            st.rerun()
        else:
            st.error("Please fill in at least one Task Description before submitting.")

# ==========================================
# 7. ROUTING & MODULE IMPLEMENTATION
# ==========================================

if menu == "Log Daily Tasks":
    render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

elif menu == "Team Head Dashboard":
    st.header("👥 Dual-Tab Team Head Dashboard")
    tab_personal, tab_crew = st.tabs(["👤 Personal Work Log", "👨‍🔧 Crew Task Logging"])

    with tab_personal:
        st.subheader(f"Personal Execution Log ({user_name})")
        render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

    with tab_crew:
        st.subheader("Manage Active Crew Logs")
        df_workers = read_sheet("Workers_Master")
        crew_members = df_workers[df_workers["role"] == "Worker"]["name"].tolist() if not df_workers.empty and "role" in df_workers.columns else []

        if not crew_members:
            st.info("⚠️ No Active Crew Members Found")
        else:
            selected_crew = st.selectbox("Select Worker to Log For", crew_members)
            st.divider()
            render_restricted_work_input(target_worker_name=selected_crew, is_crew_log=True)

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
            site_options = ["All Sites"] + (df_sites["installation_id"].tolist() if not df_sites.empty and "installation_id" in df_sites.columns else [])
            site_filter = st.selectbox("Filter by Site", site_options)
        with col_f2:
            status_filter = st.selectbox("Filter by Task Status", ["All Statuses"] + STATUS_OPTIONS)

        filtered_tasks = df_tasks.copy()
        if site_filter != "All Sites" and "installation_id" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["installation_id"] == site_filter]
        if status_filter != "All Statuses" and "status" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["status"] == status_filter]

        st.write("##")
        if site_filter != "All Sites":
            site_task_subset = df_tasks[df_tasks["installation_id"] == site_filter] if "installation_id" in df_tasks.columns else pd.DataFrame()
            
            tot_site_tasks = len(site_task_subset)
            completed_tasks = len(site_task_subset[site_task_subset["status"] == "Completed"]) if "status" in site_task_subset.columns else 0
            in_prog_tasks = len(site_task_subset[site_task_subset["status"] == "In Progress"]) if "status" in site_task_subset.columns else 0
            
            overall_pct = int((completed_tasks / tot_site_tasks) * 100) if tot_site_tasks > 0 else 0

            st.subheader(f"📊 Site Progress Tracker — {site_filter}")
            st.progress(overall_pct / 100)

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{overall_pct}%</div><div class="kpi-label">Overall Completion</div></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_site_tasks}</div><div class="kpi-label">Total Site Tasks</div></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{in_prog_tasks}</div><div class="kpi-label">In Progress</div></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{completed_tasks}</div><div class="kpi-label">Completed</div></div>', unsafe_allow_html=True)

            st.divider()

        st.subheader(f"Task List ({len(filtered_tasks)} Records)")
        st.dataframe(filtered_tasks, use_container_width=True)

elif menu == "Employee Analytics & Reports":
    st.header("👤 Employee Deep Dive & Individual Analytics")
    st.caption("Select any worker to isolate their performance, daily progress graphs, and travel logs.")

    df_workers = read_sheet("Workers_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_workers.empty:
        st.warning("⚠️ Workers database is empty.")
    else:
        worker_names = sorted(df_workers["name"].astype(str).str.strip().unique().tolist())
        default_index = worker_names.index("Parvesh Kumar") if "Parvesh Kumar" in worker_names else 0
        selected_emp = st.selectbox("🔍 Select Employee to Generate Report:", worker_names, index=default_index)

        emp_info = df_workers[df_workers["name"] == selected_emp].iloc[0]
        
        st.markdown(f"""
            <div class="card-box">
                <h3 style="margin:0;">{emp_info.get('name')} ({emp_info.get('worker_id')})</h3>
                <p style="margin:5px 0;"><b>Role:</b> {emp_info.get('role')} | <b>Base Location:</b> {emp_info.get('base_location')}</p>
            </div>
        """, unsafe_allow_html=True)

        if df_logs.empty or "worker_name" not in df_logs.columns:
            st.info(f"No task logs recorded yet for {selected_emp}.")
        else:
            emp_logs = df_logs[df_logs["worker_name"].astype(str).str.strip().str.lower() == selected_emp.strip().lower()].copy()

            if emp_logs.empty:
                st.warning(f"⚠️ No field logs recorded in the system for **{selected_emp}** yet.")
            else:
                st.subheader("⚙️ Filter Report")
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    site_list = ["All Sites"] + emp_logs["installation_id"].unique().tolist()
                    filter_site = st.selectbox("Filter by Installation Site", site_list)
                with col_f2:
                    travel_opt = ["All Days", "Travel Days Only (Yes)", "Local Days Only (No)"]
                    filter_travel = st.selectbox("Filter by Travel Status", travel_opt)
                with col_f3:
                    cat_col = "task_category" if "task_category" in emp_logs.columns else "task_name"
                    task_list = ["All Categories"] + emp_logs[cat_col].unique().tolist()
                    filter_task = st.selectbox("Filter by Category", task_list)

                filtered_emp_logs = emp_logs.copy()
                if filter_site != "All Sites":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs["installation_id"] == filter_site]
                if filter_travel == "Travel Days Only (Yes)":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs["is_travel_day"] == "Yes"]
                elif filter_travel == "Local Days Only (No)":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs["is_travel_day"] == "No"]
                if filter_task != "All Categories":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs[cat_col] == filter_task]

                tot_hours = filtered_emp_logs["hours_spent"].sum() if "hours_spent" in filtered_emp_logs.columns else 0
                tot_travel_days = len(filtered_emp_logs[filtered_emp_logs["is_travel_day"] == "Yes"]) if "is_travel_day" in filtered_emp_logs.columns else 0
                tot_projects = filtered_emp_logs["installation_id"].nunique() if "installation_id" in filtered_emp_logs.columns else 0

                st.write("##")
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_hours} hrs</div><div class="kpi-label">Total Logged Hours</div></div>', unsafe_allow_html=True)
                with k2:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_travel_days} Days</div><div class="kpi-label">Travel Days (TA/DA)</div></div>', unsafe_allow_html=True)
                with k3:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_projects}</div><div class="kpi-label">Unique Sites Worked</div></div>', unsafe_allow_html=True)

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
                        labels={"logged_date": "Date", "hours_spent": "Hours Worked", "installation_id": "Site ID"}
                    )
                    st.plotly_chart(fig_hrs, use_container_width=True)

                with g2:
                    if "task_category" in filtered_emp_logs.columns:
                        fig_cat = px.pie(
                            filtered_emp_logs,
                            names="task_category",
                            values="hours_spent",
                            title=f"Time Spent per Category"
                        )
                        st.plotly_chart(fig_cat, use_container_width=True)

                st.subheader(f"📋 Detailed Work Logs ({len(filtered_emp_logs)} Records)")
                disp_cols = [c for c in ["log_id", "logged_date", "installation_id", "worker_role", "team_lead_name", "task_category", "task_name", "hours_spent", "minutes_spent", "is_travel_day", "site_remarks", "site_photo"] if c in filtered_emp_logs.columns]
                st.dataframe(filtered_emp_logs[disp_cols].sort_values(by="logged_date", ascending=False), use_container_width=True)

                st.download_button(
                    label="📥 Export Employee Log as CSV",
                    data=convert_df_to_csv(filtered_emp_logs),
                    file_name=f"{selected_emp}_work_logs.csv",
                    mime="text/csv"
                )

elif menu == "My Work History":
    st.header(f"📜 Work Log History & Audit Trail - {user_name}")
    st.caption("Complete transparency of all logged daily tasks, progress increments, and travel allowances.")
    
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty or "worker_name" not in df_logs.columns:
        st.info("⚠️ No Field Logs Recorded Yet")
    else:
        my_logs = df_logs[df_logs["worker_name"].astype(str).str.strip().str.lower() == user_name.strip().lower()]
        
        if my_logs.empty:
            st.info("⚠️ You have not submitted any daily work logs yet.")
        else:
            tot_my_hrs = my_logs["hours_spent"].sum() if "hours_spent" in my_logs.columns else 0
            tot_my_trv = len(my_logs[my_logs["is_travel_day"] == "Yes"]) if "is_travel_day" in my_logs.columns else 0
            tot_sites = my_logs["installation_id"].nunique() if "installation_id" in my_logs.columns else 0

            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_my_hrs} hrs</div><div class="kpi-label">Total Hours Logged</div></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_my_trv} Days</div><div class="kpi-label">Travel Days (TA/DA Claimed)</div></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_sites}</div><div class="kpi-label">Sites Worked On</div></div>', unsafe_allow_html=True)

            st.write("##")
            search_query = st.text_input("🔍 Search Logs by Site ID, Category, Task Name, or Date", "")
            
            filtered_logs = my_logs.copy()
            if search_query:
                mask = filtered_logs.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
                filtered_logs = filtered_logs[mask]

            st.subheader(f"Submitted Log Entries ({len(filtered_logs)} Records)")
            disp_cols = [c for c in ["log_id", "logged_date", "installation_id", "worker_role", "team_lead_name", "task_category", "task_name", "hours_spent", "minutes_spent", "is_travel_day", "site_remarks", "site_photo"] if c in filtered_logs.columns]
            st.dataframe(filtered_logs[disp_cols].sort_values(by="logged_date", ascending=False), use_container_width=True)

elif menu == "My Profile & Settings":
    st.header("👤 Worker Profile & Security")
    
    col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
    with col_center:
        st.markdown(f"""
            <div class="card-box">
                <h3 style="margin:0;">{user_name}</h3>
                <p style="margin:5px 0;"><b>Role:</b> {user_role}</p>
                <p style="margin:5px 0;"><b>Worker ID:</b> {user.get('worker_id', 'N/A')}</p>
                <p style="margin:5px 0;"><b>Base Station:</b> {user_base_location}</p>
            </div>
        """, unsafe_allow_html=True)

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

elif menu == "Admin Analytics Dashboard":
    st.header("📊 Admin Operations Dashboard")
    df_logs = read_sheet("Worker_Daily_Logs")
    df_workers = read_sheet("Workers_Master")
    df_sites = read_sheet("Sites_Master")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{len(df_workers)}</div><div class="kpi-label">Active Team Members</div></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{len(df_sites)}</div><div class="kpi-label">Total Installation Sites</div></div>', unsafe_allow_html=True)
    with kpi3:
        tot_hrs = df_logs["hours_spent"].sum() if not df_logs.empty and "hours_spent" in df_logs.columns else 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_hrs} hrs</div><div class="kpi-label">Total Field Hours Logged</div></div>', unsafe_allow_html=True)
    with kpi4:
        trv_days = len(df_logs[df_logs["is_travel_day"] == "Yes"]) if not df_logs.empty and "is_travel_day" in df_logs.columns else 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{trv_days} Days</div><div class="kpi-label">TA/DA Travel Days Claims</div></div>', unsafe_allow_html=True)

    st.write("##")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Field Hours per Worker")
        if not df_logs.empty and "worker_name" in df_logs.columns and df_logs["hours_spent"].sum() > 0:
            hrs_df = df_logs.groupby("worker_name")["hours_spent"].sum().reset_index()
            fig_hrs_bar = px.bar(hrs_df, x="worker_name", y="hours_spent", color="hours_spent", title="Field Hours by Worker")
            st.plotly_chart(fig_hrs_bar, use_container_width=True)
        else:
            st.info("⚠️ No Field Hours Logged Yet")

    with col_chart2:
        st.subheader("Site Status Distribution")
        if not df_sites.empty and "status" in df_sites.columns:
            st_counts = df_sites["status"].value_counts().reset_index()
            st_counts.columns = ["Status", "Count"]
            fig_status_pie = px.pie(st_counts, names="Status", values="Count", title="Site Status Distribution", hole=0.4)
            st.plotly_chart(fig_status_pie, use_container_width=True)
        else:
            st.info("⚠️ No Installation Sites Created Yet")

elif menu == "User Management":
    st.header("👥 User & Access Management")
    df_workers = read_sheet("Workers_Master")

    tab_add, tab_batch, tab_edit = st.tabs(["➕ Add Single User", "⚡ Batch Process Raw String", "✏️ Edit Existing User & Role"])

    with tab_add:
        st.subheader("Add Worker / Supervisor to System")
        col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
        with col_center:
            with st.form("add_user_form"):
                c1, c2 = st.columns(2)
                with c1:
                    new_w_id = st.text_input("Worker ID", value=f"W{len(df_workers)+1:03d}")
                    new_name = st.text_input("Full Name")
                    new_id_num = st.text_input("12-Digit Government ID", max_chars=12, placeholder="e.g. 123456789012")
                with c2:
                    new_pin = st.text_input("4-Digit PIN / Password", type="password")
                    new_role = st.selectbox("System Role", ["Worker", "Supervisor", "Admin"])
                    new_base = st.text_input("Base Station / City", value="Jaipur")

                submit_new_user = st.form_submit_button("Create User & Sync to Data Base", use_container_width=True)
                if submit_new_user:
                    clean_id = str(new_id_num).strip()
                    if not new_name or not new_pin or not clean_id:
                        st.error("Please fill in Full Name, ID Number, and PIN.")
                    elif len(clean_id) != 12 or not clean_id.isdigit():
                        st.error("Invalid ID Number! Must be exactly 12 numeric digits.")
                    else:
                        user_dict = {
                            "worker_id": new_w_id,
                            "name": new_name,
                            "aadhaar_no": clean_id,
                            "pin": str(new_pin),
                            "role": new_role,
                            "base_location": new_base
                        }
                        append_to_sheet("Workers_Master", user_dict)
                        st.success(f"User **{new_name}** successfully registered and synced!")
                        st.rerun()

    with tab_batch:
        st.subheader("⚡ Batch Import Workers from Continuous String")
        raw_text_input = st.text_area("Paste Continuous Data String Here:", placeholder="W002Vishak1234567890121234SupervisorJaipur...")
        if st.button("🔍 Parse and Import Worker Data"):
            if raw_text_input:
                parsed_list = parse_raw_worker_string(raw_text_input)
                if parsed_list:
                    for w in parsed_list:
                        append_to_sheet("Workers_Master", w)
                    st.success("All extracted workers synced to Google Sheets!")
                    st.rerun()

    with tab_edit:
        st.subheader("Update User Profile, Role & PIN")
        if not df_workers.empty and "name" in df_workers.columns:
            selected_edit_user = st.selectbox("Select User to Edit", sorted(df_workers["name"].tolist()))
            user_data = df_workers[df_workers["name"] == selected_edit_user].iloc[0]

            col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
            with col_center:
                with st.form("edit_user_form"):
                    e_role = st.selectbox("Update Role", ["Worker", "Supervisor", "Admin"], index=["Worker", "Supervisor", "Admin"].index(user_data.get("role", "Worker")))
                    e_pin = st.text_input("Update PIN", value=str(user_data.get("pin", "")))
                    e_base = st.text_input("Update Base Location", value=str(user_data.get("base_location", "Jaipur")))

                    submit_edit = st.form_submit_button("Update Profile in Data Base", use_container_width=True)
                    if submit_edit:
                        updates = {"role": e_role, "pin": e_pin, "base_location": e_base}
                        update_sheet_row("Workers_Master", "name", selected_edit_user, updates)
                        st.success(f"Updated **{selected_edit_user}** successfully!")
                        st.rerun()

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
            summary_df = travel_logs.groupby(["worker_name", "base_location"]).agg(
                total_travel_days=("is_travel_day", "count"),
                total_hours_worked=("hours_spent", "sum")
            ).reset_index()

            ta_rate = st.number_input("Daily TA/DA Allowance Rate (₹)", value=500, step=50)
            summary_df["Estimated Allowance (₹)"] = summary_df["total_travel_days"] * ta_rate
            st.dataframe(summary_df, use_container_width=True)

            st.download_button(
                label="📥 Export TA/DA Summary as CSV",
                data=convert_df_to_csv(summary_df),
                file_name="tada_summary_report.csv",
                mime="text/csv"
            )

elif menu == "Advanced Field Logs Inspector":
    st.header("🔍 Advanced Field Log Inspector & Exporter")
    df_logs = read_sheet("Worker_Daily_Logs")

    if not df_logs.empty:
        st.dataframe(df_logs, use_container_width=True)
        st.download_button(
            label="📥 Export All Logs as CSV",
            data=convert_df_to_csv(df_logs),
            file_name="all_field_logs.csv",
            mime="text/csv"
        )

elif menu == "Handover Date Dashboard":
    st.header("📅 Site Handover Date Dashboard")
    df_sites = read_sheet("Sites_Master")

    if not df_sites.empty and "handover_date" in df_sites.columns:
        df_sites["handover_date_dt"] = pd.to_datetime(df_sites["handover_date"], errors="coerce")
        df_sites["days_remaining"] = (df_sites["handover_date_dt"] - datetime.now()).dt.days

        for _, site in df_sites.iterrows():
            days = site.get("days_remaining", 0)
            badge_color = COLOR_ACCENT if days > 15 else ("#E6A100" if days >= 0 else "#D32F2F")
            
            st.markdown(f"""
                <div class="card-box">
                    <h3 style="margin:0;">{site.get('site_name', 'N/A')} ({site.get('installation_id', 'N/A')})</h3>
                    <p style="margin:5px 0;"><b>City:</b> {site.get('site_city', 'N/A')} | <b>Team Lead:</b> {site.get('team_lead', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Target Handover:</b> {site.get('handover_date', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Status:</b> <span style="color:{badge_color}; font-weight:bold;">{site.get('status', 'In Progress')} ({days} Days Remaining)</span></p>
                </div>
            """, unsafe_allow_html=True)

elif menu == "New Installation Order":
    st.header("Create New Installation Order")
    df_workers = read_sheet("Workers_Master")
    worker_options = sorted(df_workers["name"].tolist()) if not df_workers.empty and "name" in df_workers.columns else [user_name]

    if "team_members_count" not in st.session_state:
        st.session_state.team_members_count = 1
    if "products_count" not in st.session_state:
        st.session_state.products_count = 1

    visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"
    st.info(f"**Automated Visit ID:** {visit_id}")

    col_team, col_dates = st.columns(2)

    with col_team:
        st.markdown("### 👨‍💼 Team Structure")
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
            "quantity": quantity
        })

    if st.button("➕ Add Another Product", key="btn_add_product"):
        st.session_state.products_count += 1
        st.rerun()

    st.write("##")
    if st.button("💾 Submit Installation Order", use_container_width=True, key="btn_submit_inst_order"):
        if not team_lead_name or not city_name or not site_address:
            st.error("Please fill in mandatory fields.")
        else:
            order_data = {
                "installation_id": visit_id,
                "team_lead": team_lead_name,
                "team_members": ", ".join(team_helpers),
                "site_city": city_name,
                "site_address": site_address,
                "order_date": str(inst_date),
                "site_clearance_date": str(site_clearance_date),
                "handover_date": str(target_handover_date),
                "products_summary": str(products_data),
                "status": "In Progress"
            }
            append_to_sheet("Sites_Master", order_data)
            st.success(f"Installation Order **{visit_id}** recorded successfully!")
            st.session_state.products_count = 1

elif menu == "View Logs & Update Status":
    st.header("🔍 View Daily Logs & Update Status")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if not df_sites.empty and "installation_id" in df_sites.columns:
        site_list = df_sites["installation_id"].tolist()
        selected_inst = st.selectbox("Select Installation ID", site_list)

        site_row = df_sites[df_sites["installation_id"] == selected_inst].iloc[0]
        
        st.markdown(f"""
            <div class="card-box">
                <h3 style="margin:0;">{site_row.get('installation_id', 'N/A')}</h3>
                <p style="margin:5px 0;"><b>City:</b> {site_row.get('site_city', 'N/A')} | <b>Team Lead:</b> {site_row.get('team_lead', 'N/A')}</p>
                <p style="margin:5px 0;"><b>Current Status:</b> <b>{site_row.get('status', 'In Progress')}</b></p>
            </div>
        """, unsafe_allow_html=True)

        col_st, col_btn = st.columns([2, 1])
        with col_st:
            curr_st = site_row.get("status", "In Progress")
            st_idx = STATUS_OPTIONS.index(curr_st) if curr_st in STATUS_OPTIONS else 0
            new_st = st.selectbox("New Status", STATUS_OPTIONS, index=st_idx)
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("Update Status"):
                update_sheet_row("Sites_Master", "installation_id", selected_inst, {"status": new_st})
                st.success(f"Status updated to **{new_st}** in Database!")
                st.rerun()

        st.divider()
        st.subheader("📜 Submitted Work Logs")
        p_logs = df_logs[df_logs["installation_id"] == selected_inst] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()

        if not p_logs.empty:
            for _, l in p_logs.iterrows():
                with st.expander(f"📅 Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Role: {l.get('worker_role', 'N/A')}"):
                    st.write(f"**Task Category:** {l.get('task_category')}")
                    st.write(f"**Task Description:** {l.get('task_name')}")
                    st.write(f"**Time Spent:** {l.get('hours_spent')} hrs {l.get('minutes_spent')} mins")
                    st.write(f"**Travel Day (TA/DA):** {l.get('is_travel_day')}")
                    st.write(f"**Photo Attached:** {l.get('site_photo', 'No Photo')}")
                    st.write(f"**Remarks / Cause of Delay:** {l.get('site_remarks', 'None')}")

elif menu == "Master Database":
    st.header("🗄️ Live Google Sheets Database")
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["Workers Master", "Sites Master", "Task Assignments", "Worker Daily Logs"])

    with m_tab1:
        st.dataframe(read_sheet("Workers_Master"), use_container_width=True)
    with m_tab2:
        st.dataframe(read_sheet("Sites_Master"), use_container_width=True)
    with m_tab3:
        st.dataframe(read_sheet("Task_Assignments"), use_container_width=True)
    with m_tab4:
        st.dataframe(read_sheet("Worker_Daily_Logs"), use_container_width=True)
