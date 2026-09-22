import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ==========================================
# 1. PAGE CONFIG & GLOBAL THEME
# ==========================================
st.set_page_config(
    page_title="Sidharth Shutter & Automation - Portal", 
    layout="wide", 
    page_icon="⚙️"
)

# Color Palette derived from Sidharth Shutter & Automation Logo
COLOR_PRIMARY = "#10418A"    # Sidharth Deep Blue
COLOR_ACCENT = "#00A859"     # Vibrant Green Dot
COLOR_BG_LIGHT = "#EBF3FA"   # Soft Blue Background Tint

# Apply Global CSS Inject
st.markdown(f"""
    <style>
    /* App background */
    .stApp {{
        background-color: #F4F7FC;
    }}
    
    /* Headers */
    h1, h2, h3 {{ 
        color: {COLOR_PRIMARY} !important; 
        font-weight: 700 !important; 
    }}
    
    /* Standard Buttons */
    .stButton>button {{ 
        background-color: {COLOR_PRIMARY} !important; 
        color: white !important; 
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }}
    .stButton>button:hover {{ 
        background-color: {COLOR_ACCENT} !important; 
        color: white !important; 
        box-shadow: 0 4px 10px rgba(0, 168, 89, 0.3) !important;
    }}
    
    /* Card Boxes & Dashboard Containers */
    .card-box {{ 
        background-color: {COLOR_BG_LIGHT}; 
        border-left: 6px solid {COLOR_PRIMARY}; 
        padding: 18px; 
        border-radius: 8px; 
        margin-bottom: 15px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: #EBF1F8;
    }}

    /* ==========================================
       LOGIN CARD STYLING (MATCHING CUSTOM UI)
       ========================================== */
    div[data-testid="stForm"] {{
        background-color: #FFFFFF;
        border: 2px solid {COLOR_PRIMARY};
        border-radius: 16px;
        padding: 35px 30px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
        max-width: 480px;
        margin: 0 auto;
    }}

    .login-title {{
        color: {COLOR_PRIMARY};
        font-weight: 800;
        text-align: center;
        font-size: 28px;
        margin-bottom: 0px;
        letter-spacing: 1px;
    }}
    .login-subtitle {{
        color: {COLOR_ACCENT};
        font-weight: 700;
        text-align: center;
        font-size: 13px;
        letter-spacing: 2px;
        margin-bottom: 6px;
    }}
    .login-caption {{
        color: #6C757D;
        text-align: center;
        font-size: 13px;
        margin-bottom: 25px;
    }}

    div[data-testid="stForm"] .stTextInput label {{
        color: {COLOR_PRIMARY} !important;
        font-weight: 700 !important;
    }}
    div[data-testid="stForm"] .stTextInput input {{
        border-radius: 8px !important;
        border: 1px solid {COLOR_PRIMARY} !important;
        padding: 10px 14px !important;
    }}

    div[data-testid="stForm"] .stButton>button {{
        background-color: {COLOR_ACCENT} !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 12px 0px !important;
        font-size: 16px !important;
        border: none !important;
        width: 100% !important;
        margin-top: 15px !important;
        box-shadow: 0 4px 12px rgba(0, 168, 89, 0.3) !important;
    }}
    div[data-testid="stForm"] .stButton>button:hover {{
        background-color: #008747 !important;
        box-shadow: 0 6px 15px rgba(0, 168, 89, 0.4) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GOOGLE SHEETS LIVE CONNECTION ENGINE
# ==========================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    """Authenticate with Google Sheets API using Streamlit secrets."""
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(credentials)

def get_workbook():
    client = get_gspread_client()
    sheet_url = st.secrets.get("spreadsheet_url", "https://docs.google.com/spreadsheets/d/19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s/edit")
    return client.open_by_url(sheet_url)

def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Reads a tab from the live Google Sheet and returns a DataFrame."""
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error reading tab '{sheet_name}': {e}")
        return pd.DataFrame()

def append_to_sheet(sheet_name: str, row_data_dict: dict):
    """Appends a row into the specified tab in Google Sheets."""
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        headers = sheet.row_values(1)
        
        if not headers:
            headers = list(row_data_dict.keys())
            sheet.append_row(headers)
            
        row_values = [str(row_data_dict.get(h, "")) for h in headers]
        sheet.append_row(row_values)
    except Exception as e:
        st.error(f"Error writing to tab '{sheet_name}': {e}")

def update_sheet_row(sheet_name: str, key_col: str, key_val: str, update_dict: dict) -> bool:
    """Updates specific cell values in a matching row in Google Sheets."""
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        
        if df.empty or key_col not in df.columns:
            return False
            
        match_idx = df[df[key_col].astype(str) == str(key_val)].index
        if match_idx.empty:
            return False
            
        row_num = match_idx[0] + 2  # 1-indexed + header row
        headers = sheet.row_values(1)

        for col_name, new_val in update_dict.items():
            if col_name in headers:
                col_num = headers.index(col_name) + 1
                sheet.update_cell(row_num, col_num, str(new_val))
        return True
    except Exception as e:
        st.error(f"Error updating tab '{sheet_name}': {e}")
        return False

# ==========================================
# 3. AUTHENTICATION (CENTERED CARD LOGIN)
# ==========================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if not st.session_state.authenticated_user:
    st.write("##")
    st.write("##")
    
    with st.form("login_form"):
        st.markdown('<div class="login-title">SIDHARTH</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">SHUTTER & AUTOMATION</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-caption">Enterprise Operations & Field Portal</div>', unsafe_allow_html=True)

        username_input = st.text_input("Username / Name", placeholder="e.g. Admin User or Vishak")
        password_input = st.text_input("Password / PIN", type="password", placeholder="Enter password")

        submit_button = st.form_submit_button("🔑 Login to Dashboard", use_container_width=True)

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
                        st.success("Authentication Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")
                else:
                    st.error("Unable to load user database. Verify Google Sheets setup.")
    st.stop()

# ==========================================
# 4. ACTIVE SESSION & SIDEBAR NAVIGATION
# ==========================================
user = st.session_state.authenticated_user
user_name = user.get("name", "User")
user_role = user.get("role", "Worker")
user_base_location = user.get("base_location", "Jaipur")

# Render Sidebar Branding
st.sidebar.markdown(f"""
    <div style="text-align: center; padding: 12px; background-color: {COLOR_PRIMARY}; color: white; border-radius: 8px; margin-bottom: 15px;">
        <h2 style="margin:0; font-size: 21px; color: white !important;">SIDHARTH</h2>
        <p style="margin:0; font-size: 11px; letter-spacing: 1.5px; color: {COLOR_ACCENT}; font-weight: bold;">SHUTTER & AUTOMATION</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"**Active User:** {user_name} (`{user_role}`)  \n**Base Location:** {user_base_location}")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.divider()

# Navigation Mapping based on Google Sheets User Role
STATUS_OPTIONS = ["In Progress", "Completed", "On Hold", "Pending Inspection"]

if user_role in ["Admin", "Supervisor"]:
    menu_options = [
        "Active Tasks Dashboard", 
        "Handover Date Dashboard", 
        "New Installation Order", 
        "Log Daily Tasks", 
        "Team Head Dashboard", 
        "View Logs & Update Status", 
        "Master Database"
    ]
else:
    menu_options = ["Log Daily Tasks"]

menu = st.sidebar.radio("Navigation Menu", menu_options)

# ==========================================
# 5. RESTRICTED LOGGING FORM HELPER
# ==========================================
def render_restricted_work_input(target_worker_name, is_crew_log=False):
    df_sites = read_sheet("Sites_Master")
    df_tasks = read_sheet("Task_Assignments")

    site_options = df_sites["installation_id"].tolist() if not df_sites.empty and "installation_id" in df_sites.columns else []
    if not site_options:
        st.warning("No installation sites found in Google Sheets 'Sites_Master'.")
        return

    c_site, c_date = st.columns(2)
    with c_site:
        selected_site_id = st.selectbox(f"Select Site for {target_worker_name}", site_options, key=f"site_{target_worker_name}_{is_crew_log}")
    with c_date:
        log_date = st.date_input("Date of Work", value=datetime.now(), key=f"date_{target_worker_name}_{is_crew_log}")

    site_info = df_sites[df_sites["installation_id"] == selected_site_id].iloc[0]
    site_city = site_info.get("site_city", "Jaipur")

    # Dynamic TA/DA Travel Calculation
    target_base = user_base_location
    if is_crew_log:
        df_w = read_sheet("Workers_Master")
        match = df_w[df_w["name"] == target_worker_name]
        if not match.empty:
            target_base = match.iloc[0].get("base_location", "Jaipur")

    is_travel = str(target_base).strip().lower() != str(site_city).strip().lower()

    if is_travel:
        st.warning(f"✈️ **Travel Day Detected (TA/DA Triggered)**: Base (`{target_base}`) ≠ Site Location (`{site_city}`)")
    else:
        st.info(f"🏠 **Local Site**: Base (`{target_base}`) matches Site Location (`{site_city}`)")

    assigned_tasks = df_tasks[df_tasks["installation_id"] == selected_site_id]["task_name"].tolist() if not df_tasks.empty and "task_name" in df_tasks.columns else []
    if not assigned_tasks:
        assigned_tasks = ["Motorized Rolling Shutter Assembly", "Electrical Wiring & Automation", "Sliding Gate Fitting", "Structural Welding"]

    c_tsk, c_pct, c_hrs, c_min = st.columns([3, 2, 1, 1])
    with c_tsk:
        selected_task = st.selectbox("Task Worked On", assigned_tasks, key=f"tsk_{target_worker_name}_{is_crew_log}")
    with c_pct:
        progress_pct = st.selectbox("Progress (%)", [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], index=5, key=f"pct_{target_worker_name}_{is_crew_log}")
    with c_hrs:
        hours_spent = st.number_input("Hours", min_value=0, max_value=24, value=8, key=f"hrs_{target_worker_name}_{is_crew_log}")
    with c_min:
        minutes_spent = st.selectbox("Minutes", [0, 15, 30, 45], key=f"min_{target_worker_name}_{is_crew_log}")

    site_remarks = st.text_area("Site Remarks / Delays", placeholder="Note any motor issues, power availability, or structural delays...", key=f"rem_{target_worker_name}_{is_crew_log}")

    if st.button(f"💾 Sync Daily Log to Google Sheets ({target_worker_name})", type="primary", key=f"btn_{target_worker_name}_{is_crew_log}"):
        log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        log_entry = {
            "log_id": log_id,
            "installation_id": selected_site_id,
            "logged_date": str(log_date),
            "worker_name": target_worker_name,
            "role": user_role if target_worker_name == user_name else "Worker",
            "task_name": selected_task,
            "progress_percentage": progress_pct,
            "hours_spent": hours_spent,
            "minutes_spent": minutes_spent,
            "base_location": target_base,
            "site_city": site_city,
            "is_travel_day": "Yes" if is_travel else "No",
            "site_remarks": site_remarks,
            "logged_by": user_name
        }
        append_to_sheet("Worker_Daily_Logs", log_entry)
        st.success(f"Successfully recorded log for **{target_worker_name}**!")
        st.rerun()

# ==========================================
# 6. MODULE IMPLEMENTATIONS
# ==========================================

# --- ACTIVE TASKS DASHBOARD ---
if menu == "Active Tasks Dashboard":
    st.header("📋 Active Tasks Dashboard")
    df_tasks = read_sheet("Task_Assignments")
    df_sites = read_sheet("Sites_Master")

    if df_tasks.empty:
        st.info("No active tasks found in Google Sheets.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            site_options = ["All Sites"] + (df_sites["installation_id"].tolist() if not df_sites.empty and "installation_id" in df_sites.columns else [])
            site_filter = st.selectbox("Filter by Site", site_options)
        with col_f2:
            status_filter = st.selectbox("Filter by Task Status", ["All Statuses", "In Progress", "Pending", "Completed"])

        filtered_tasks = df_tasks.copy()
        if site_filter != "All Sites" and "installation_id" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["installation_id"] == site_filter]
        if status_filter != "All Statuses" and "status" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["status"] == status_filter]

        st.dataframe(filtered_tasks, use_container_width=True)

# --- HANDOVER DATE DASHBOARD ---
elif menu == "Handover Date Dashboard":
    st.header("📅 Site Handover Date Dashboard")
    df_sites = read_sheet("Sites_Master")

    if df_sites.empty or "handover_date" not in df_sites.columns:
        st.info("No site handover records found in Google Sheets.")
    else:
        df_sites["handover_date_dt"] = pd.to_datetime(df_sites["handover_date"], errors="coerce")
        df_sites["days_remaining"] = (df_sites["handover_date_dt"] - datetime.now()).dt.days

        st.subheader("Upcoming Project Handovers")
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

# --- NEW INSTALLATION ORDER ---
elif menu == "New Installation Order":
    st.header("🆕 Create New Installation Order")
    with st.form("new_order_form"):
        c1, c2 = st.columns(2)
        with c1:
            inst_id = st.text_input("Installation ID", value=f"INST-2026-{datetime.now().strftime('%M%S')}")
            site_name = st.text_input("Site / Project Name")
            site_city = st.text_input("Site City")
        with c2:
            team_lead = st.text_input("Assigned Team Lead", value=user_name)
            order_date = st.date_input("Order Date", value=datetime.now())
            handover_date = st.date_input("Target Handover Date", value=datetime.now() + timedelta(days=30))

        submit = st.form_submit_button("Create Installation Order", type="primary")
        if submit:
            if not site_name or not site_city:
                st.error("Please fill in site name and city.")
            else:
                new_site = {
                    "installation_id": inst_id,
                    "site_name": site_name,
                    "site_city": site_city,
                    "team_lead": team_lead,
                    "status": "In Progress",
                    "order_date": str(order_date),
                    "handover_date": str(handover_date)
                }
                append_to_sheet("Sites_Master", new_site)
                st.success(f"Installation Order **{inst_id}** recorded in Google Sheets!")

# --- LOG DAILY TASKS ---
elif menu == "Log Daily Tasks":
    st.header(f"📝 Log Daily Tasks - {user_name}")
    render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

# --- TEAM HEAD DASHBOARD ---
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
            st.info("No workers registered in Google Sheets Workers_Master.")
        else:
            selected_crew = st.selectbox("Select Worker to Log For", crew_members)
            st.divider()
            render_restricted_work_input(target_worker_name=selected_crew, is_crew_log=True)

# --- VIEW LOGS & UPDATE STATUS ---
elif menu == "View Logs & Update Status":
    st.header("🔍 View Daily Logs & Update Status")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty or "installation_id" not in df_sites.columns:
        st.info("No sites available in Google Sheets.")
    else:
        site_list = df_sites["installation_id"].tolist()
        selected_inst = st.selectbox("Select Installation ID", site_list)

        site_row = df_sites[df_sites["installation_id"] == selected_inst].iloc[0]
        
        st.markdown(f"""
            <div class="card-box">
                <h3 style="margin:0;">{site_row.get('site_name', 'N/A')} ({site_row.get('installation_id', 'N/A')})</h3>
                <p style="margin:5px 0;"><b>City:</b> {site_row.get('site_city', 'N/A')} | <b>Team Lead:</b> {site_row.get('team_lead', 'N/A')}</p>
                <p style="margin:5px 0;"><b>Current Status:</b> <b>{site_row.get('status', 'In Progress')}</b></p>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("⚙️ Update Project Status")
        col_st, col_btn = st.columns([2, 1])
        with col_st:
            curr_st = site_row.get("status", "In Progress")
            st_idx = STATUS_OPTIONS.index(curr_st) if curr_st in STATUS_OPTIONS else 0
            new_st = st.selectbox("New Status", STATUS_OPTIONS, index=st_idx)
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("Update Status", type="primary"):
                update_sheet_row("Sites_Master", "installation_id", selected_inst, {"status": new_st})
                st.success(f"Status updated to **{new_st}** in Google Sheets!")
                st.rerun()

        st.divider()
        st.subheader("📜 Submitted Work Logs")
        p_logs = df_logs[df_logs["installation_id"] == selected_inst] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()

        if p_logs.empty:
            st.info("No logs recorded for this site yet.")
        else:
            for _, l in p_logs.iterrows():
                with st.expander(f"📅 Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Log ID: {l.get('log_id')}"):
                    st.write(f"**Task:** {l.get('task_name')} ({l.get('progress_percentage')}% Progress)")
                    st.write(f"**Time Spent:** {l.get('hours_spent')} hrs {l.get('minutes_spent')} mins")
                    st.write(f"**Travel Day (TA/DA):** {l.get('is_travel_day')}")
                    st.write(f"**Remarks:** {l.get('site_remarks', 'None')}")

# --- MASTER DATABASE ---
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
