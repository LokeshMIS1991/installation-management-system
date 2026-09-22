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

# Sub-task mapping per task category
SUB_TASKS_MAPPING = {
    "Assembly / Mechanical": ["Guide Rail Installation", "Barrel Shaft Fitting", "Slat Interlocking", "Motor Mounting", "Limit Switch Setting"],
    "Electrical Wiring & Automation": ["Control Panel Cabling", "Sensor & Safety Edge Setup", "Remote/Push Button Wiring", "Power Testing & Grounding"],
    "Fitting & Alignment": ["Track Leveling & Anchoring", "Gate Leaf Alignment", "Rack & Pinion Fitting", "Motor Hookup"],
    "Structural & Welding": ["Frame Bracket Fabrication", "Support Beam Welding", "Anchor Bolt Alignment"],
    "General": ["Reach", "Open", "Clean Site", "Start", "Out", "Check", "Operational Safety Check", "Final Handover Test"]
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

            username_input = st.text_input("Username / Name", value=st.session_state.remembered_username, placeholder="e.g. Rajbeer or Ramji")
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
# 4. ACTIVE SESSION & NAVIGATION
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

if user_role in ["Admin", "Supervisor"]:
    menu_options = [
        "Supervisor Daily Task Logger",
        "New Installation Order",
        "View Logs & Update Status",
        "Active Tasks Dashboard",
        "Handover Date Dashboard",
        "Employee Analytics & Reports",
        "Master Database"
    ]
else:
    menu_options = [
        "Supervisor Daily Task Logger", 
        "My Work History", 
        "My Profile & Settings"
    ]

menu = st.sidebar.radio("Navigation Menu", menu_options)

st.sidebar.divider()

if st.sidebar.button("🚪 LOG OUT", use_container_width=True):
    st.session_state.authenticated_user = None
    st.rerun()

# ==========================================
# 5. SUPERVISOR DAILY TASK LOGGER ENGINE
# ==========================================
def render_supervisor_logger():
    st.header("📝 Supervisor Daily Execution Logger")

    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    # DYNAMIC FILTER: Show active "In Progress" sites only[cite: 4]
    if not df_sites.empty and "installation_id" in df_sites.columns:
        if "status" in df_sites.columns:
            active_sites_df = df_sites[df_sites["status"].astype(str).str.strip().str.lower() == "in progress"]
        else:
            active_sites_df = df_sites
        site_options = active_sites_df["installation_id"].tolist()
    else:
        site_options = []

    if not site_options:
        st.warning("⚠️ No Active 'In Progress' Installation Sites found. Create a site order first.")
        return

    col1, col2 = st.columns(2)
    with col1:
        selected_site_id = st.selectbox("Select Active Installation ID", site_options)
    with col2:
        log_date = st.date_input("Logged Date", value=datetime.now())

    # Auto-calculate Day Number for the selected site[cite: 4]
    site_logs = df_logs[df_logs["installation_id"] == selected_site_id] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()
    next_day_num = f"Day {len(site_logs) + 1}"

    st.info(f"📌 Logging Entry for **{selected_site_id}** | **Sequence:** {next_day_num}")

    col_prod, col_pln = st.columns(2)
    with col_prod:
        product_worked_on = st.text_input("Product Worked On (with size)", placeholder="e.g., Motorized Rolling Shutter (5330x6000)")
    with col_pln:
        next_day_planned = st.text_input("Next Day Planned Tasks", value="None planned")

    st.markdown("### 🛠️ Tasks Completed Today")

    if "task_input_count" not in st.session_state:
        st.session_state.task_input_count = 4

    tasks_list = []
    for i in range(st.session_state.task_input_count):
        c_cat, c_desc = st.columns([1, 2])
        with c_cat:
            cat = st.selectbox(f"Category #{i+1}", list(SUB_TASKS_MAPPING.keys()), key=f"cat_{i}")
        with c_desc:
            desc = st.text_input(f"Task #{i+1} Description", placeholder="e.g., Track Leveling or 2 shutters installed", key=f"desc_{i}")
        if desc.strip():
            tasks_list.append(f"{i+1}. [✓] [{cat}] {desc.strip()}")

    if st.button("➕ Add More Task Lines"):
        st.session_state.task_input_count += 1
        st.rerun()

    formatted_tasks_str = "\n".join(tasks_list) if tasks_list else "1. General inspection completed"

    # Optional photo attachment[cite: 4]
    uploaded_photo = st.file_uploader("📷 Upload Site Photo (Optional)", type=["jpg", "jpeg", "png"], key="supervisor_photo_upload")
    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Uploaded Site Photo Preview", width=250)

    st.markdown("**Formatted Log Output Preview:**")
    st.code(formatted_tasks_str)

    if st.button("💾 SUBMIT DAILY WORK LOG", use_container_width=True):
        generated_log_id = f"LOG-2026-{os.urandom(2).hex().upper()}"
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_payload = {
            "log_id": generated_log_id,
            "installation_id": selected_site_id,
            "day_number": next_day_num,
            "logged_timestamp": timestamp_str,
            "logged_date": str(log_date),
            "product_worked_on": product_worked_on if product_worked_on else "General Product",
            "tasks_completed": formatted_tasks_str,
            "next_day_planned_tasks": next_day_planned,
            "submitted_by": user_name
        }

        append_to_sheet("Worker_Daily_Logs", log_payload)
        st.success(f"Log **{generated_log_id}** saved successfully!")
        st.session_state.task_input_count = 4
        st.rerun()

# ==========================================
# 6. APPLICATION MODULES
# ==========================================

if menu == "Supervisor Daily Task Logger":
    render_supervisor_logger()

# --- NEW INSTALLATION ORDER ---
elif menu == "New Installation Order":
    st.header(" Create New Installation Order")
    
    if "team_members_count" not in st.session_state:
        st.session_state.team_members_count = 1
    if "products_count" not in st.session_state:
        st.session_state.products_count = 1

    visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"
    st.info(f"**Automated Installation ID:** {visit_id}")

    col_team, col_dates = st.columns(2)

    with col_team:
        st.markdown("### 👨‍💼 Team Structure")
        team_lead_name = st.text_input("Team Lead Name *", placeholder="e.g., Rajbeer or Ramji", key="inst_team_lead")
        
        team_helpers = []
        for i in range(st.session_state.team_members_count):
            helper = st.text_input(f"Team Member / Helper #{i+1}", placeholder="e.g., Parvesh Kumar", key=f"inst_helper_{i}")
            if helper.strip():
                team_helpers.append(helper.strip())
        
        if st.button("➕ Add Team Member", key="btn_add_team_member"):
            st.session_state.team_members_count += 1
            st.rerun()

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
            product_type = st.selectbox("Select The Product", catalog_main_categories, key=f"prod_type_{p_idx}")
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
            st.success(f"Installation Order **{visit_id}** recorded successfully!")
            st.session_state.team_members_count = 1
            st.session_state.products_count = 1

# --- VIEW LOGS & UPDATE STATUS ---
elif menu == "View Logs & Update Status":
    st.header("🔍 Site Log Inspector & Handover Status")
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
                <h3 style="margin:0;">Site ID: {site_row.get('installation_id', 'N/A')}</h3>
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
                st.success(f"Status updated to **{new_st}**. (If set to Completed, site hides from logger dropdowns)")
                st.rerun()

        st.divider()
        st.subheader("📜 Submitted Daily Work Logs")
        p_logs = df_logs[df_logs["installation_id"] == selected_inst] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()

        if p_logs.empty:
            st.info("⚠️ No Logs Recorded for this Site Yet")
        else:
            st.dataframe(p_logs, use_container_width=True)

# --- ACTIVE TASKS DASHBOARD ---
elif menu == "Active Tasks Dashboard":
    st.header("📋 Active Tasks & Site Dashboard")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    kpi1, kpi2, kpi3 = st.columns(3)
    
    total_sites = len(df_sites) if not df_sites.empty else 0
    active_sites = len(df_sites[df_sites["status"] == "In Progress"]) if not df_sites.empty and "status" in df_sites.columns else 0
    total_logs = len(df_logs) if not df_logs.empty else 0

    with kpi1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_sites}</div><div class="kpi-label">TOTAL SITES</div></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{active_sites}</div><div class="kpi-label">ACTIVE (IN PROGRESS)</div></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{total_logs}</div><div class="kpi-label">LOGS SUBMITTED</div></div>', unsafe_allow_html=True)

    st.write("##")
    st.subheader("Recent Daily Log Submissions")
    if not df_logs.empty:
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No logs submitted yet.")

# --- HANDOVER DATE DASHBOARD ---
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
                    <h3 style="margin:0;">Site ID: {site.get('installation_id', 'N/A')}</h3>
                    <p style="margin:5px 0;"><b>City:</b> {site.get('site_city', 'N/A')} | <b>Team Lead:</b> {site.get('team_lead', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Target Handover:</b> {site.get('handover_date', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Status:</b> <span style="color:{badge_color}; font-weight:bold;">{site.get('status', 'In Progress')} ({days} Days Remaining)</span></p>
                </div>
            """, unsafe_allow_html=True)

# --- EMPLOYEE ANALYTICS & REPORTS ---
elif menu == "Employee Analytics & Reports":
    st.header("👤 Employee Daily Logs & Performance Analytics")
    df_logs = read_sheet("Worker_Daily_Logs")
    
    if not df_logs.empty and "submitted_by" in df_logs.columns:
        supervisors = df_logs["submitted_by"].unique().tolist()
        selected_sup = st.selectbox("Select Supervisor/Worker", supervisors)
        
        emp_logs = df_logs[df_logs["submitted_by"] == selected_sup]
        
        st.subheader(f"Log Details for {selected_sup}")
        st.dataframe(emp_logs, use_container_width=True)
        
        if "logged_date" in emp_logs.columns:
            logs_by_date = emp_logs.groupby("logged_date").size().reset_index(name="logs_count")
            fig = px.bar(logs_by_date, x="logged_date", y="logs_count", title=f"Daily Activity Count for {selected_sup}", color_discrete_sequence=[COLOR_PRIMARY])
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activity data available for analytics.")

# --- MASTER DATABASE ---
elif menu == "Master Database":
    st.header("🗄️ Live Google Sheets Database")
    m_tab1, m_tab2, m_tab3 = st.tabs(["Workers Master", "Sites Master", "Worker Daily Logs"])

    with m_tab1:
        st.dataframe(read_sheet("Workers_Master"), use_container_width=True)
    with m_tab2:
        st.dataframe(read_sheet("Sites_Master"), use_container_width=True)
    with m_tab3:
        st.dataframe(read_sheet("Worker_Daily_Logs"), use_container_width=True)

# --- MY WORK HISTORY (WORKER VIEW) ---
elif menu == "My Work History":
    st.header(f"📜 Work Log History - {user_name}")
    df_logs = read_sheet("Worker_Daily_Logs")
    if not df_logs.empty and "submitted_by" in df_logs.columns:
        my_logs = df_logs[df_logs["submitted_by"].astype(str).str.strip().str.lower() == user_name.strip().lower()]
        st.dataframe(my_logs, use_container_width=True)
    else:
        st.info("No log history found.")

# --- MY PROFILE & SETTINGS ---
elif menu == "My Profile & Settings":
    st.header("👤 Worker Profile & Security")
    st.markdown(f"""
        <div class="card-box">
            <p style="margin:5px 0;"><b>Name:</b> {user_name}</p>
            <p style="margin:5px 0;"><b>Role:</b> {user_role}</p>
            <p style="margin:5px 0;"><b>Base Station:</b> {user_base_location}</p>
        </div>
    """, unsafe_allow_html=True)
