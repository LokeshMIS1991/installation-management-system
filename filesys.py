import os
import re
import io
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import plotly.express as px

# ==========================================
# 0. OFFICIAL PRODUCT CATALOGUE DATA
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

# Sub-task mapping per primary task category
SUB_TASKS_MAPPING = {
    "Motorized Rolling Shutter Assembly": ["Guide Rail Installation", "Barrel Shaft Fitting", "Slat Interlocking", "Motor Mounting", "Limit Switch Setting"],
    "Electrical Wiring & Automation": ["Control Panel Cabling", "Sensor & Safety Edge Setup", "Remote/Push Button Wiring", "Power Testing & Grounding"],
    "Sliding Gate Fitting": ["Track Leveling & Anchoring", "Gate Leaf Alignment", "Rack & Pinion Fitting", "Motor Hookup"],
    "Structural Welding": ["Frame Bracket Fabrication", "Support Beam Welding", "Anchor Bolt Alignment"],
    "General Inspection & Maintenance": ["Lubrication & Spring Tensioning", "Operational Safety Check", "Final Handover Test"]
}

# ==========================================
# 1. PAGE CONFIG & GLOBAL THEME
# ==========================================
st.set_page_config(
    page_title="Sidharth Shutter & Automation - Portal", 
    layout="wide", 
    page_icon="⚙️"
)

COLOR_PRIMARY = "#10418A"    # Sidharth Deep Blue
COLOR_ACCENT = "#00A859"     # Vibrant Green
COLOR_BG_LIGHT = "#EBF3FA"   # Soft Blue Background Tint

# Apply High-Specificity Global CSS Inject
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
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        margin-bottom: 2px !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        gap: 4px !important;
    }}
    section[data-testid="stSidebar"] div.stButton > button {{
        background-color: {COLOR_ACCENT} !important;
        background: {COLOR_ACCENT} !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 10px 0px !important;
        font-size: 15px !important;
        border: none !important;
        width: 100% !important;
        margin-top: 10px !important;
        box-shadow: 0 4px 10px rgba(0, 168, 89, 0.35) !important;
    }}
    section[data-testid="stSidebar"] div.stButton > button * {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
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
        padding: 28px 24px;
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
        box-shadow: 0 4px 12px rgba(0, 168, 89, 0.3) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    div[data-testid="stFormSubmitButton"] > button * {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        white-space: nowrap !important;
    }}
    .login-caption {{
        color: #6C757D;
        text-align: center;
        font-size: 13px;
        margin-top: 10px;
        margin-bottom: 20px;
        font-weight: 500;
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
        for col_name, new_val in update_dict.items():
            if col_name in headers:
                col_num = headers.index(col_name) + 1
                sheet.update_cell(row_num, col_num, str(new_val))
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
        r'(Supervisor|Worker|Admin)'               # Role
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

# ==========================================
# 3. AUTHENTICATION (FORM LAYOUT)
# ==========================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "remembered_username" not in st.session_state:
    st.session_state.remembered_username = ""

if not st.session_state.authenticated_user:
    st.write("##")
    
    col_l, col_center, col_r = st.columns([1, 2, 1])
    with col_center:
        with st.form("login_form"):
            logo_path = "Company Logo.jpeg"
            if os.path.exists(logo_path):
                st.image(logo_path, use_container_width=True)
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
# 4. ACTIVE SESSION & REORDERED SIDEBAR NAVIGATION
# ==========================================
user = st.session_state.authenticated_user
user_name = user.get("name", "User")
user_role = user.get("role", "Worker")
user_base_location = user.get("base_location", "Jaipur")

logo_path = "Company Logo.jpeg"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 12px; background-color: {COLOR_PRIMARY}; color: white; border-radius: 8px; margin-bottom: 10px;">
            <h2 style="margin:0; font-size: 21px; color: white !important;">SIDHARTH</h2>
            <p style="margin:0; font-size: 11px; letter-spacing: 1.5px; color: {COLOR_ACCENT}; font-weight: bold;">SHUTTER & AUTOMATION</p>
        </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown(f"**Active User:** {user_name} (`{user_role}`)  \n**Base Station:** {user_base_location}")
st.sidebar.divider()

STATUS_OPTIONS = ["In Progress", "Completed", "On Hold", "Pending Inspection"]

# REORDERED NAVIGATION MENU BASED ON USER SPECIFICATION
if user_role == "Admin":
    menu_options = [
        "New Installation Order",
        "Log Daily Tasks",
        "View Logs & Update Status",
        "Active Tasks Dashboard",
        "Handover Date Dashboard",
        "Employee Analytics & Reports",
        "Team Head Dashboard",
        "Master Database",
        "Admin Analytics Dashboard",
        "User Management",
        "TA/DA Payroll & Travel Summary",
        "Advanced Field Logs Inspector"
    ]
elif user_role == "Supervisor":
    menu_options = [
        "New Installation Order",
        "Log Daily Tasks",
        "View Logs & Update Status",
        "Active Tasks Dashboard",
        "Handover Date Dashboard",
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
# 5. RESTRICTED WORK INPUT HELPER (WITH SUB-TASKS & ASSIGNED WORKER)
# ==========================================
def render_restricted_work_input(target_worker_name, is_crew_log=False):
    df_sites = read_sheet("Sites_Master")
    df_tasks = read_sheet("Task_Assignments")
    df_workers = read_sheet("Workers_Master")

    site_options = df_sites["installation_id"].tolist() if not df_sites.empty and "installation_id" in df_sites.columns else []
    if not site_options:
        st.warning("⚠️ No Installation Sites Created Yet — Create orders to log tasks.")
        return

    c_site, c_date = st.columns(2)
    with c_site:
        selected_site_id = st.selectbox(f"Select Site for {target_worker_name}", site_options, key=f"site_{target_worker_name}_{is_crew_log}")
    with c_date:
        log_date = st.date_input("Date of Work", value=datetime.now(), key=f"date_{target_worker_name}_{is_crew_log}")

    site_info = df_sites[df_sites["installation_id"] == selected_site_id].iloc[0]
    site_city = site_info.get("site_city", "Jaipur")

    target_base = user_base_location
    if is_crew_log:
        match = df_workers[df_workers["name"] == target_worker_name] if not df_workers.empty else pd.DataFrame()
        if not match.empty:
            target_base = match.iloc[0].get("base_location", "Jaipur")

    is_travel = str(target_base).strip().lower() != str(site_city).strip().lower()

    if is_travel:
        st.warning(f"✈️ **Travel Day Detected (TA/DA Triggered)**: Base ({target_base}) ≠ Site Location ({site_city})")
    else:
        st.info(f"🏠 **Local Site**: Base ({target_base}) matches Site Location ({site_city})")

    assigned_tasks = df_tasks[df_tasks["installation_id"] == selected_site_id]["task_name"].tolist() if not df_tasks.empty and "task_name" in df_tasks.columns else []
    if not assigned_tasks:
        assigned_tasks = list(SUB_TASKS_MAPPING.keys())

    # Task & Sub-Task Breakdown Section
    st.markdown("#### 🎯 Task & Sub-Task Breakdown")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        selected_task = st.selectbox("Primary Task", assigned_tasks, key=f"tsk_{target_worker_name}_{is_crew_log}")
    with col_t2:
        available_subtasks = SUB_TASKS_MAPPING.get(selected_task, ["General Sub-task"])
        selected_subtask = st.selectbox("Sub-Task Worked On", available_subtasks, key=f"sub_tsk_{target_worker_name}_{is_crew_log}")

    # Worker Assignment & Duration
    all_worker_names = df_workers["name"].tolist() if not df_workers.empty and "name" in df_workers.columns else [target_worker_name]
    default_w_idx = all_worker_names.index(target_worker_name) if target_worker_name in all_worker_names else 0

    col_w, col_pct, col_hrs, col_min = st.columns([2, 1.5, 1, 1])
    with col_w:
        assigned_worker = st.selectbox("Assigned Worker", all_worker_names, index=default_w_idx, key=f"assigned_w_{target_worker_name}_{is_crew_log}")
    with col_pct:
        progress_options = ["0%", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]
        progress_str = st.selectbox("Progress (%)", progress_options, index=5, key=f"pct_{target_worker_name}_{is_crew_log}")
        progress_pct = int(progress_str.replace("%", ""))
    with col_hrs:
        hours_spent = st.selectbox("Hours Taken", list(range(0, 17)), index=8, key=f"hrs_{target_worker_name}_{is_crew_log}")
    with col_min:
        minutes_spent = st.selectbox("Minutes", [0, 15, 30, 45], key=f"min_{target_worker_name}_{is_crew_log}")

    site_remarks = st.text_area("Site Remarks / Delays", placeholder="Note any motor issues, power availability, or structural delays...", key=f"rem_{target_worker_name}_{is_crew_log}")

    # Optional Site Photo Upload Field (Available to both Worker and Supervisor)[cite: 4]
    uploaded_photo = st.file_uploader(
        "📷 Upload Site Photo (Optional)", 
        type=["jpg", "jpeg", "png"], 
        key=f"photo_{target_worker_name}_{is_crew_log}",
        help="Capture or attach an image of the ongoing or completed installation task."
    )

    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Uploaded Site Photo Preview", width=250)

    if st.button(f"💾 Sync Daily Log to Data Base ({assigned_worker})", key=f"btn_{target_worker_name}_{is_crew_log}"):
        log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        photo_filename = uploaded_photo.name if uploaded_photo is not None else "No Photo"

        log_entry = {
            "log_id": log_id,
            "installation_id": selected_site_id,
            "logged_date": str(log_date),
            "worker_name": assigned_worker,
            "role": user_role if assigned_worker == user_name else "Worker",
            "task_name": selected_task,
            "sub_task_name": selected_subtask,
            "progress_percentage": progress_pct,
            "hours_spent": hours_spent,
            "minutes_spent": minutes_spent,
            "total_time_str": f"{hours_spent}h {minutes_spent}m",
            "base_location": target_base,
            "site_city": site_city,
            "is_travel_day": "Yes" if is_travel else "No",
            "site_remarks": site_remarks,
            "site_photo": photo_filename,
            "logged_by": user_name
        }
        append_to_sheet("Worker_Daily_Logs", log_entry)
        st.success(f"Successfully recorded log for **{assigned_worker}**!")
        st.rerun()

# ==========================================
# 6. MODULE IMPLEMENTATIONS (REORDERED TO MATCH MENU)
# ==========================================

# --- 1. NEW INSTALLATION ORDER ---
if menu == "New Installation Order":
    st.header("Create New Installation Order")
    
    if "team_members_count" not in st.session_state:
        st.session_state.team_members_count = 1
    if "products_count" not in st.session_state:
        st.session_state.products_count = 1

    visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"
    st.info(f"**Automated Visit ID:** {visit_id}")

    col_team, col_dates = st.columns(2)

    with col_team:
        st.markdown("### 👨‍💼 Team Structure")
        team_lead_name = st.text_input("Team Lead Name *", placeholder="e.g., Rajeer", key="inst_team_lead")
        
        team_helpers = []
        for i in range(st.session_state.team_members_count):
            helper = st.text_input("Team Members / Helpers", placeholder="e.g., Parvesh Kumar", key=f"inst_helper_{i}")
            if helper.strip():
                team_helpers.append(helper.strip())
        
        if st.button("➕ Add Team Member", key="btn_add_team_member"):
            st.session_state.team_members_count += 1
            st.rerun()

        city_name = st.text_input("City Name *", value="Mumbai", key="inst_city_name")
        site_address = st.text_area("Site Address *", placeholder="Full installation site address...", key="inst_site_address")

    with col_dates:
        st.markdown("### 📅 Order Dates")
        inst_date = st.date_input("Installation Date (Order Created Date)", value=datetime.now(), key="inst_order_date")
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
            product_type = st.selectbox(
                "Select The Product", 
                catalog_main_categories, 
                key=f"prod_type_{p_idx}"
            )
            dimensions = st.text_input("Dimensions (WxH)", placeholder="e.g., 5330X6000", key=f"prod_dim_{p_idx}")
        
        with col_p2:
            sub_cat_options = PRODUCT_CATALOG.get(product_type, ["Other"])
            sub_category = st.selectbox(
                "Select Sub-Category", 
                sub_cat_options, 
                key=f"prod_sub_{p_idx}"
            )
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
            st.error("Please fill in all mandatory fields (Team Lead Name, City Name, and Site Address).")
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
            st.success(f"Installation Order **{visit_id}** recorded successfully in the database!")
            st.session_state.team_members_count = 1
            st.session_state.products_count = 1

# --- 2. LOG DAILY TASKS ---
elif menu == "Log Daily Tasks":
    st.header(f"📝 Log Daily Tasks - {user_name}")
    render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

# --- 3. VIEW LOGS & UPDATE STATUS ---
elif menu == "View Logs & Update Status":
    st.header("🔍 View Daily Logs & Update Status")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty or "installation_id" not in df_sites.columns:
        st.info("⚠️ No Installation Sites Available")
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
            if st.button("Update Status"):
                update_sheet_row("Sites_Master", "installation_id", selected_inst, {"status": new_st})
                st.success(f"Status updated to **{new_st}** in Data Base!")
                st.rerun()

        st.divider()
        st.subheader("📜 Submitted Work Logs")
        p_logs = df_logs[df_logs["installation_id"] == selected_inst] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()

        if p_logs.empty:
            st.info("⚠️ No Logs Recorded for this Site Yet")
        else:
            for _, l in p_logs.iterrows():
                with st.expander(f"📅 Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Log ID: {l.get('log_id')}"):
                    st.write(f"**Primary Task:** {l.get('task_name')} | **Sub-Task:** {l.get('sub_task_name', 'N/A')}")
                    st.write(f"**Assigned Worker:** {l.get('worker_name')} | **Progress:** {l.get('progress_percentage')}%")
                    st.write(f"**Time Taken:** {l.get('hours_spent', 0)} hrs {l.get('minutes_spent', 0)} mins")
                    st.write(f"**Travel Day (TA/DA):** {l.get('is_travel_day')}")
                    st.write(f"**Photo Attached:** {l.get('site_photo', 'No Photo')}")
                    st.write(f"**Remarks:** {l.get('site_remarks', 'None')}")

# --- 4. ACTIVE TASKS DASHBOARD ---
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
            status_filter = st.selectbox("Filter by Task Status", ["All Statuses", "In Progress", "Pending", "Completed"])

        filtered_tasks = df_tasks.copy()
        if site_filter != "All Sites" and "installation_id" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["installation_id"] == site_filter]
        if status_filter != "All Statuses" and "status" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["status"] == status_filter]

        # Site Progress Tracker & Metrics
        st.write("##")
        if site_filter != "All Sites":
            site_task_subset = df_tasks[df_tasks["installation_id"] == site_filter] if "installation_id" in df_tasks.columns else pd.DataFrame()
            
            tot_site_tasks = len(site_task_subset)
            completed_tasks = len(site_task_subset[site_task_subset["status"] == "Completed"]) if "status" in site_task_subset.columns else 0
            in_prog_tasks = len(site_task_subset[site_task_subset["status"] == "In Progress"]) if "status" in site_task_subset.columns else 0
            pending_tasks = len(site_task_subset[site_task_subset["status"] == "Pending"]) if "status" in site_task_subset.columns else 0
            
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

            # CSV Export Generator
            metrics_df = pd.DataFrame([{
                "Site ID": site_filter,
                "Overall Completion (%)": f"{overall_pct}%",
                "Total Tasks": tot_site_tasks,
                "Completed Tasks": completed_tasks,
                "In Progress Tasks": in_prog_tasks,
                "Pending Tasks": pending_tasks
            }])

            csv_buffer = io.StringIO()
            metrics_df.to_csv(csv_buffer, index=False)
            csv_buffer.write("\n--- Detailed Task List ---\n")
            filtered_tasks.to_csv(csv_buffer, index=False)

            st.download_button(
                label=f"📥 Export {site_filter} Progress Report (CSV)",
                data=csv_buffer.getvalue(),
                file_name=f"{site_filter}_Progress_Report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        st.subheader(f"Task List ({len(filtered_tasks)} Records)")
        st.dataframe(filtered_tasks, use_container_width=True)

# --- 5. HANDOVER DATE DASHBOARD ---
elif menu == "Handover Date Dashboard":
    st.header("📅 Site Handover Date Dashboard")
    df_sites = read_sheet("Sites_Master")

    if df_sites.empty or "handover_date" not in df_sites.columns:
        st.info("⚠️ No Installation Sites Created Yet")
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

# --- 6. EMPLOYEE ANALYTICS & REPORTS ---
elif menu == "Employee Analytics & Reports":
    st.header("👤 Employee Deep Dive & Individual Analytics")
    st.caption("Select any worker to isolate their performance, daily progress graphs, and travel logs.")

    df_workers = read_sheet("Workers_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_workers.empty:
        st.warning("⚠️ Workers database is empty.")
    else:
        worker_names = df_workers["name"].tolist()
        default_index = worker_names.index("Parvesh Kumar") if "Parvesh Kumar" in worker_names else 0
        selected_emp = st.selectbox("🔍 Select Employee to Generate Report:", worker_names, index=default_index)

        emp_info = df_workers[df_workers["name"] == selected_emp].iloc[0]
        
        st.markdown(f"""
            <div class="card-box">
                <h3 style="margin:0;">{emp_info.get('name')} ({emp_info.get('worker_id')})</h3>
                <p style="margin:5px 0;"><b>Role:</b> {emp_info.get('role')} | <b>Base Location:</b> {emp_info.get('base_location')} | <b>ID Number:</b> [ID Redacted]</p>
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
                    task_list = ["All Tasks"] + emp_logs["task_name"].unique().tolist()
                    filter_task = st.selectbox("Filter by Task Type", task_list)

                filtered_emp_logs = emp_logs.copy()
                if filter_site != "All Sites":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs["installation_id"] == filter_site]
                if filter_travel == "Travel Days Only (Yes)":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs["is_travel_day"] == "Yes"]
                elif filter_travel == "Local Days Only (No)":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs["is_travel_day"] == "No"]
                if filter_task != "All Tasks":
                    filtered_emp_logs = filtered_emp_logs[filtered_emp_logs["task_name"] == filter_task]

                tot_hours = filtered_emp_logs["hours_spent"].sum() if "hours_spent" in filtered_emp_logs.columns else 0
                tot_travel_days = len(filtered_emp_logs[filtered_emp_logs["is_travel_day"] == "Yes"]) if "is_travel_day" in filtered_emp_logs.columns else 0
                tot_projects = filtered_emp_logs["installation_id"].nunique() if "installation_id" in filtered_emp_logs.columns else 0
                avg_progress = filtered_emp_logs["progress_percentage"].mean() if "progress_percentage" in filtered_emp_logs.columns and not filtered_emp_logs.empty else 0

                st.write("##")
                k1, k2, k3, k4 = st.columns(4)
                with k1:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_hours} hrs</div><div class="kpi-label">Total Logged Hours</div></div>', unsafe_allow_html=True)
                with k2:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_travel_days} Days</div><div class="kpi-label">Travel Days (TA/DA)</div></div>', unsafe_allow_html=True)
                with k3:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_projects}</div><div class="kpi-label">Unique Sites Worked</div></div>', unsafe_allow_html=True)
                with k4:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-number">{avg_progress:.1f}%</div><div class="kpi-label">Avg Task Progress</div></div>', unsafe_allow_html=True)

                st.divider()

                st.subheader("📊 Individual Performance Charts")
                g1, g2 = st.columns(2)

                with g1:
                    fig_hrs = px.bar(
                        filtered_emp_logs,
                        x="logged_date",
                        y="hours_spent",
                        color="installation_id",
                        title=f"Daily Hours Logged by {selected_emp}",
                        labels={"logged_date": "Date", "hours_spent": "Hours Worked", "installation_id": "Site ID"},
                        color_discrete_sequence=px.colors.qualitative.Set1
                    )
                    st.plotly_chart(fig_hrs, use_container_width=True)

                with g2:
                    fig_prog = px.line(
                        filtered_emp_logs,
                        x="logged_date",
                        y="progress_percentage",
                        color="task_name",
                        markers=True,
                        title=f"Task Progress Trajectory (%)",
                        labels={"logged_date": "Date", "progress_percentage": "Progress (%)", "task_name": "Task"}
                    )
                    st.plotly_chart(fig_prog, use_container_width=True)

                st.subheader(f"📋 Detailed Work Logs ({len(filtered_emp_logs)} Records)")
                disp_cols = [c for c in ["log_id", "logged_date", "installation_id", "task_name", "sub_task_name", "progress_percentage", "hours_spent", "minutes_spent", "is_travel_day", "site_remarks", "site_photo"] if c in filtered_emp_logs.columns]
                st.dataframe(filtered_emp_logs[disp_cols].sort_values(by="logged_date", ascending=False), use_container_width=True)

                csv_data = filtered_emp_logs.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Export {selected_emp}'s Report (CSV)",
                    data=csv_data,
                    file_name=f"{selected_emp.replace(' ', '_')}_Report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

# --- 7. TEAM HEAD DASHBOARD ---
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

# --- 8. MASTER DATABASE ---
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

# --- EXTRA ADMIN MODULES ---
elif menu == "My Work History":
    st.header(f"📜 Work Log History & Audit Trail - {user_name}")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty or "worker_name" not in df_logs.columns:
        st.info("⚠️ No Field Logs Recorded Yet")
    else:
        my_logs = df_logs[df_logs["worker_name"].astype(str).str.strip().str.lower() == user_name.strip().lower()]
        if my_logs.empty:
            st.info("⚠️ You have not submitted any daily work logs yet.")
        else:
            disp_cols = [c for c in ["log_id", "logged_date", "installation_id", "task_name", "sub_task_name", "progress_percentage", "hours_spent", "minutes_spent", "is_travel_day", "site_remarks", "site_photo"] if c in my_logs.columns]
            st.dataframe(my_logs[disp_cols].sort_values(by="logged_date", ascending=False), use_container_width=True)

elif menu == "My Profile & Settings":
    st.header("👤 Worker Profile & Security")
    st.markdown(f"**Name:** {user_name} | **Role:** {user_role} | **Base Station:** {user_base_location}")

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

elif menu == "User Management":
    st.header("👥 User & Access Management")
    st.dataframe(read_sheet("Workers_Master"), use_container_width=True)

elif menu == "TA/DA Payroll & Travel Summary":
    st.header("✈️ TA/DA Travel Allowance & Payroll Report")
    df_logs = read_sheet("Worker_Daily_Logs")
    if not df_logs.empty and "is_travel_day" in df_logs.columns:
        st.dataframe(df_logs[df_logs["is_travel_day"] == "Yes"], use_container_width=True)

elif menu == "Advanced Field Logs Inspector":
    st.header("🔍 Advanced Field Log Inspector & Exporter")
    df_logs = read_sheet("Worker_Daily_Logs")
    st.dataframe(df_logs, use_container_width=True)
