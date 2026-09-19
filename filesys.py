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

SPREADSHEET_NAME = "Installation_Schedules"
LOGO_PATH = "Company Logo.jpeg"

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.markdown("### 🏢 Sidharth Shutter")

st.sidebar.markdown("---")

# Custom CSS Theme
st.markdown("""
    <style>
    .stApp {
        background-color: #FAFCFE;
    }
    h1, h2, h3 {
        color: #0F4C81 !important;
        font-weight: 700 !important;
    }
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
    button[kind="primary"] {
        background: linear-gradient(135deg, #0F4C81 0%, #1A6BBA 100%) !important;
        color: white !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0A375E 0%, #0F4C81 100%) !important;
        box-shadow: 0 4px 10px rgba(15, 76, 129, 0.3) !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #F0F5FA !important;
        border-right: 2px solid #0F4C81 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stImage"] {
        padding-top: 10px;
        padding-bottom: 10px;
    }
    div[role="radiogroup"] label[data-baseweb="radio"] div:first-child {
        background-color: #0F4C81 !important;
    }
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus, .stTextArea>div>div>textarea:focus {
        border-color: #00A651 !important;
        box-shadow: 0 0 0 1px #00A651 !important;
    }
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

TASK_CATEGORIES = [
    "General", 
    "Assembly / Mechanical", 
    "Wiring / Electrical", 
    "Testing & Commissioning", 
    "Civil / Prep"
]

@st.cache_resource
def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    
    return gspread.authorize(creds)

def get_default_headers(worksheet_name):
    if worksheet_name == "Installations":
        return [
            "installation_id", "city_prefix", "site_address", "team_details", 
            "order_created_date", "site_clearance_date", "target_ho_date", "status"
        ]
    elif worksheet_name == "Order_Items":
        return [
            "installation_id", "category", "sub_category", "dimensions", "quantity"
        ]
    elif worksheet_name == "Daily_Logs":
        return [
            "log_id", "installation_id", "day_number", "logged_timestamp", 
            "logged_date", "product_worked_on", "tasks_completed", 
            "next_day_planned_tasks", "site_remarks", "submitted_by"
        ]
    return []

def get_worksheet(worksheet_name):
    client = get_gspread_client()
    spreadsheet = client.open(SPREADSHEET_NAME)
    
    try:
        return spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        headers = get_default_headers(worksheet_name)
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="100", cols=str(len(headers) or 10))
        if headers:
            worksheet.append_row(headers)
        return worksheet

def append_to_sheet(sheet_name, row_data):
    try:
        sheet = get_worksheet(sheet_name)
        sheet.append_row(row_data)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Failed to append row to {sheet_name}: {e}")

def read_sheet(sheet_name):
    try:
        sheet = get_worksheet(sheet_name)
        rows = sheet.get_all_values()
        
        if not rows or len(rows) < 2:
            return get_empty_default_df(sheet_name)
            
        headers = [str(h).strip().lower() for h in rows[0]]
        data = rows[1:]
        
        df = pd.DataFrame(data, columns=headers)
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
        return df
    except Exception:
        return get_empty_default_df(sheet_name)

def get_empty_default_df(sheet_name):
    headers = get_default_headers(sheet_name)
    return pd.DataFrame(columns=headers)

def update_sheet_row(sheet_name, key_column_name, key_value, updated_row_dict):
    try:
        sheet = get_worksheet(sheet_name)
        rows = sheet.get_all_values()
        if not rows:
            return False
            
        headers = [str(h).strip().lower() for h in rows[0]]
        key_column_name_lower = str(key_column_name).strip().lower()
        
        if key_column_name_lower not in headers:
            return False
            
        key_col_idx = headers.index(key_column_name_lower)
        
        for row_idx, row in enumerate(rows[1:], start=2):
            if len(row) > key_col_idx and str(row[key_col_idx]).strip() == str(key_value).strip():
                for col_name, val in updated_row_dict.items():
                    col_name_lower = str(col_name).strip().lower()
                    if col_name_lower in headers:
                        target_col_idx = headers.index(col_name_lower) + 1
                        sheet.update_cell(row_idx, target_col_idx, str(val))
                st.cache_data.clear()
                return True
    except Exception as e:
        st.error(f"Update failed: {e}")
    return False

def generate_project_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    unique_suffix = ''.join(random.choices(chars, k=5))
    return f"INST-{year}-{unique_suffix}"

def generate_log_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    unique_suffix = ''.join(random.choices(chars, k=5))
    return f"LOG-{year}-{unique_suffix}"

def format_tasks_to_string(tasks_list):
    """Formats structured task item list into printable multiline string."""
    formatted_lines = []
    for idx, t in enumerate(tasks_list, start=1):
        desc = t.get("description", "").strip()
        if desc:
            status_symbol = "✓" if t.get("done", True) else " "
            cat = t.get("category", "General")
            formatted_lines.append(f"{idx}. [{status_symbol}] [{cat}] {desc}")
    return "\n".join(formatted_lines)

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

STATUS_OPTIONS = ["In Progress", "On Hold", "Pending", "Completed", "Cancelled"]

st.markdown("""
    <div style="border-left: 6px solid #00A651; padding: 12px 18px; background-color: #F0F5FA; border-radius: 4px; margin-bottom: 25px;">
        <h1 style="margin:0; padding:0; font-size: 28px; color: #0F4C81;">🏢 Sidharth Shutter & Automation</h1>
        <p style="margin:2px 0 0 0; color: #1A6BBA; font-weight: 600; font-size: 14px;">Installation Management System</p>
    </div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("Navigation", [
    "Active Tasks Dashboard",
    "Handover Date Dashboard",
    "New Installation Order", 
    "Log Daily Tasks",
    "View Logs & Update Status", 
    "Master Database"
])

def render_task_grid(session_key):
    if session_key not in st.session_state:
        st.session_state[session_key] = [
            {"done": True, "description": "", "category": "General"},
            {"done": True, "description": "", "category": "General"},
            {"done": True, "description": "", "category": "General"},
            {"done": True, "description": "", "category": "General"}
        ]

    tasks = st.session_state[session_key]

    c_head1, c_head2, c_head3, c_head4 = st.columns([0.6, 3.5, 2.2, 0.8])
    with c_head1:
        st.markdown("**DONE**")
    with c_head2:
        st.markdown("**TASK DESCRIPTION**")
    with c_head3:
        st.markdown("**CATEGORY / TAG**")
    with c_head4:
        st.markdown("**ACTION**")

    indices_to_remove = []

    for idx, item in enumerate(tasks):
        col1, col2, col3, col4 = st.columns([0.6, 3.5, 2.2, 0.8])
        
        with col1:
            item["done"] = st.checkbox("", value=item.get("done", True), key=f"{session_key}_done_{idx}")
        with col2:
            item["description"] = st.text_input("", value=item.get("description", ""), placeholder="Enter task description...", key=f"{session_key}_desc_{idx}", label_visibility="collapsed")
        with col3:
            curr_cat = item.get("category", "General")
            cat_idx = TASK_CATEGORIES.index(curr_cat) if curr_cat in TASK_CATEGORIES else 0
            item["category"] = st.selectbox("", TASK_CATEGORIES, index=cat_idx, key=f"{session_key}_cat_{idx}", label_visibility="collapsed")
        with col4:
            if st.button("🗑️", key=f"{session_key}_del_{idx}"):
                indices_to_remove.append(idx)

    if indices_to_remove:
        for i in sorted(indices_to_remove, reverse=True):
            st.session_state[session_key].pop(i)
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_add, col_metric = st.columns([3, 2])
    with col_add:
        if st.button("➕ Add Another Task", key=f"{session_key}_add_btn"):
            st.session_state[session_key].append({"done": True, "description": "", "category": "General"})
            st.rerun()
    with col_metric:
        st.markdown(f"<div style='text-align: right; padding-top: 8px; color: #64748B; font-weight: 600;'>Total: <b>{len(tasks)}</b> tasks</div>", unsafe_allow_html=True)

def render_worker_inputs():
    if "workers_list" not in st.session_state or not st.session_state.workers_list:
        st.session_state.workers_list = ["", ""]

    st.markdown("### 👷 Site Workers / Team Members On-Site")
    
    for i in range(0, len(st.session_state.workers_list), 2):
        col_w1, col_w2 = st.columns(2)
        
        with col_w1:
            val1 = st.session_state.workers_list[i]
            st.session_state.workers_list[i] = st.text_input(
                f"Worker #{i+1} Name", 
                value=val1, 
                key=f"worker_field_{i}",
                placeholder=f"e.g., Worker {i+1} Name"
            )
            
        if i + 1 < len(st.session_state.workers_list):
            with col_w2:
                val2 = st.session_state.workers_list[i+1]
                st.session_state.workers_list[i+1] = st.text_input(
                    f"Worker #{i+2} Name", 
                    value=val2, 
                    key=f"worker_field_{i+1}",
                    placeholder=f"e.g., Worker {i+2} Name"
                )

    c_add, c_remove = st.columns([2, 2])
    with c_add:
        if st.button("➕ Add Another Worker"):
            st.session_state.workers_list.append("")
            st.rerun()
    with c_remove:
        if len(st.session_state.workers_list) > 1:
            if st.button("➖ Remove Last Worker Field"):
                st.session_state.workers_list.pop()
                st.rerun()

    valid_workers = [w.strip() for w in st.session_state.workers_list if w.strip()]
    st.caption(f"Currently logging **{len(valid_workers)}** worker(s) present today.")
    return ", ".join(valid_workers)

# ------------------------------------------
# 1. ACTIVE TASKS DASHBOARD
# ------------------------------------------
if menu == "Active Tasks Dashboard":
    st.header("📊 Active Installation Progress Dashboard")

    df_logs = read_sheet("Daily_Logs")
    df_inst = read_sheet("Installations")

    if df_inst.empty:
        st.info("No installation projects found.")
    else:
        df_inst.columns = df_inst.columns.str.strip().str.lower()
        if not df_logs.empty:
            df_logs.columns = df_logs.columns.str.strip().str.lower()

        active_inst = df_inst[df_inst.get("status", "In Progress").astype(str).str.lower() != "completed"].copy()

        if active_inst.empty:
            st.success("🎉 All installation tasks are complete! No pending or 'In Progress' work.")
        else:
            inst_col_logs = next((c for c in df_logs.columns if "installation" in c or "inst" in c), "installation_id") if not df_logs.empty else "installation_id"

            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Active Sites In Progress", len(active_inst))
            col_m2.metric("Total Active Logs Recorded", len(df_logs) if not df_logs.empty else 0)

            st.divider()
            st.subheader("🚧 Ongoing Projects & Task Completion Status")

            for _, project in active_inst.iterrows():
                inst_id = str(project.get("installation_id") or "N/A")
                raw_addr = project.get("site_address")
                site_addr = str(raw_addr) if pd.notna(raw_addr) and str(raw_addr).strip() != "" else "N/A"
                team = str(project.get("team_details") or "Unassigned")
                p_status = str(project.get("status") or "In Progress")

                p_logs = pd.DataFrame()
                if not df_logs.empty and inst_col_logs in df_logs.columns:
                    p_logs = df_logs[df_logs[inst_col_logs].astype(str).str.strip() == inst_id.strip()]

                total_logs = len(p_logs)
                completed_task_count = 0
                latest_tasks_text = "No tasks recorded yet."
                
                if not p_logs.empty:
                    all_tasks_combined = " ".join(p_logs.get("tasks_completed", p_logs.get("completed_tasks", "")).dropna().astype(str))
                    completed_task_count = sum(1 for line in all_tasks_combined.split('\n') if line.strip())
                    latest_log = p_logs.iloc[-1]
                    latest_tasks_text = str(latest_log.get("tasks_completed", latest_log.get("completed_tasks", "N/A")) or "N/A")

                estimated_total_steps = 10 
                calc_progress = min(int((completed_task_count / estimated_total_steps) * 100), 95) if completed_task_count > 0 else 5

                with st.container():
                    st.markdown(f"""
                        <div style="background-color: #F8F9FA; border: 1px solid #E0E0E0; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                            <h4 style="margin: 0; color: #0F4C81;">📍 {inst_id} — <span style="font-size: 14px; color: #555;">{site_addr[:40]}...</span></h4>
                            <p style="margin: 5px 0 0 0; font-size: 13px;"><b>Team Assigned:</b> {team} | <b>Days Worked:</b> {total_logs} Day(s) | <b>Status:</b> <span style="color: #D97706; font-weight: bold;">{p_status}</span></p>
                        </div>
                    """, unsafe_allow_html=True)

                    st.write(f"**Completion Progress:** {calc_progress}%")
                    st.progress(calc_progress / 100)

                    with st.expander(f"🔍 View Recent Task Updates for {inst_id}"):
                        st.markdown("**Latest Work Logged:**")
                        st.text(latest_tasks_text)
                    
                    st.divider()

# ------------------------------------------
# 2. HANDOVER DATE DASHBOARD
# ------------------------------------------
elif menu == "Handover Date Dashboard":
    st.header("📅 Handover Schedule Dashboard")

    df_inst = read_sheet("Installations")

    if df_inst.empty:
        st.info("No installation records found.")
    else:
        df_inst.columns = df_inst.columns.str.strip().str.lower()
        handover_col = next((c for c in df_inst.columns if "target_ho_date" in c or "handover" in c or "completion_date" in c), None)

        if not handover_col:
            st.error("No handover date column found in the Installations sheet.")
        else:
            df_inst["parsed_handover"] = pd.to_datetime(df_inst[handover_col], errors="coerce")
            
            show_completed = st.checkbox("Include Completed Handovers", value=False)
            filtered_df = df_inst.copy()
            if not show_completed and "status" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["status"].astype(str).str.lower() != "completed"]

            today = pd.to_datetime(datetime.now().date())

            overdue_df = filtered_df[filtered_df["parsed_handover"] < today]
            today_df = filtered_df[filtered_df["parsed_handover"] == today]
            upcoming_df = filtered_df[(filtered_df["parsed_handover"] > today) & (filtered_df["parsed_handover"] <= today + pd.Timedelta(days=7))]
            future_df = filtered_df[filtered_df["parsed_handover"] > today + pd.Timedelta(days=7)]
            unscheduled_df = filtered_df[filtered_df["parsed_handover"].isna()]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("🚨 Overdue", len(overdue_df))
            m2.metric("📌 Handover Today", len(today_df))
            m3.metric("⏳ Next 7 Days", len(upcoming_df))
            m4.metric("📅 Future / Unscheduled", len(future_df) + len(unscheduled_df))

            st.divider()
            st.subheader("📈 Handover Distribution Over Time")
            chart_data = filtered_df.dropna(subset=["parsed_handover"])
            if not chart_data.empty:
                handover_counts = chart_data["parsed_handover"].dt.date.value_counts().sort_index()
                st.bar_chart(handover_counts)
            else:
                st.info("No valid handover dates available to chart.")

            st.divider()

            tab_overdue, tab_today, tab_upcoming, tab_all = st.tabs([
                f"🚨 Overdue ({len(overdue_df)})", 
                f"📌 Today ({len(today_df)})", 
                f"⏳ Next 7 Days ({len(upcoming_df)})", 
                f"📋 All Tracked ({len(filtered_df)})"
            ])

            def render_project_list(dataframe, alert_color="#D97706"):
                if dataframe.empty:
                    st.write("No projects in this category.")
                else:
                    for _, row in dataframe.iterrows():
                        inst_id = str(row.get("installation_id") or "N/A")
                        raw_site = row.get("site_address")
                        site = str(raw_site) if pd.notna(raw_site) and str(raw_site).strip() != "" else "N/A"
                        team = str(row.get("team_details") or "Unassigned")
                        h_date = str(row.get(handover_col) or "Not Set")
                        status = str(row.get("status") or "In Progress")

                        st.markdown(f"""
                            <div style="background-color: #F8F9FA; border-left: 5px solid {alert_color}; padding: 12px 18px; border-radius: 6px; margin-bottom: 12px;">
                                <h4 style="margin: 0; color: #0F4C81;">📍 {inst_id} — <span style="font-size: 14px; color: #444;">{site[:40]}...</span></h4>
                                <p style="margin: 4px 0 0 0; font-size: 13px;">
                                    <b>Target Handover Date:</b> <span style="color: {alert_color}; font-weight: bold;">{h_date}</span> | 
                                    <b>Team:</b> {team} | 
                                    <b>Status:</b> {status}
                                </p>
                            </div>
                        """, unsafe_allow_html=True)

            with tab_overdue:
                render_project_list(overdue_df, alert_color="#DC2626")
            with tab_today:
                render_project_list(today_df, alert_color="#00A651")
            with tab_upcoming:
                render_project_list(upcoming_df, alert_color="#2563EB")
            with tab_all:
                render_project_list(filtered_df, alert_color="#6B7280")

# ------------------------------------------
# 3. NEW INSTALLATION ORDER
# ------------------------------------------
elif menu == "New Installation Order":
    st.header("Create New Installation Order")

    if "temp_inst_id" not in st.session_state:
        st.session_state.temp_inst_id = generate_project_id()

    # Dynamic multi-product list initialisation
    if "order_products" not in st.session_state:
        st.session_state.order_products = [
            {"category": "Rolling Shutters", "sub_category": "Motorized Rolling Shutter", "custom_name": "", "dimensions": "", "quantity": 1}
        ]

    # Dynamic Team Members List Initialisation
    if "team_members" not in st.session_state:
        st.session_state.team_members = [""]

    # Show persistent success notification after creation
    if "last_created_order" in st.session_state:
        st.success(st.session_state.last_created_order)
        del st.session_state.last_created_order

    st.markdown(f"""
        <div style="background-color: #EBF3FE; border: 1px solid #1A6BBA; padding: 14px 20px; border-radius: 8px; margin-bottom: 20px;">
            <span style="color: #0F4C81; font-weight: 700; font-size: 15px;">Automated Visit ID:</span>
            <span style="color: #00A651; font-weight: 700; font-size: 16px; margin-left: 8px; font-family: monospace;">{st.session_state.temp_inst_id}</span>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👨‍💼 Team Structure")
        team_lead = st.text_input("Team Lead Name *", placeholder="e.g., Rajeer")
        
        st.markdown("**Team Members / Helpers**")
        member_to_remove = []
        
        for idx, member in enumerate(st.session_state.team_members):
            c_mem, c_del = st.columns([3.5, 0.8])
            with c_mem:
                st.session_state.team_members[idx] = st.text_input(
                    f"Team Member #{idx + 1}", 
                    value=member, 
                    placeholder=f"e.g., Helper {idx + 1}", 
                    key=f"team_member_field_{idx}",
                    label_visibility="collapsed"
                )
            with c_del:
                if len(st.session_state.team_members) > 1:
                    if st.button("🗑️", key=f"del_team_mem_{idx}"):
                        member_to_remove.append(idx)
        
        if member_to_remove:
            for i in sorted(member_to_remove, reverse=True):
                st.session_state.team_members.pop(i)
            st.rerun()

        if st.button("➕ Add Team Member"):
            st.session_state.team_members.append("")
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        city_name = st.text_input("City Name *", "Mumbai").strip()
        site_address = st.text_area("Site Address *", placeholder="Full installation site address...")

    with col2:
        st.markdown("### 📅 Order Dates")
        min_past_date = datetime.now() - timedelta(days=7)
        order_created_date = st.date_input("Installation Date (Order Created Date)", value=datetime.now(), min_value=min_past_date, format="YYYY-MM-DD")
        site_clearance = st.date_input("Site Clearance Date", value=datetime.now(), min_value=min_past_date, format="YYYY-MM-DD")
        target_ho_date = st.date_input("Target Handover Date", value=datetime.now() + timedelta(days=15), min_value=min_past_date, format="YYYY-MM-DD")

    st.divider()
    st.subheader("📦 Order Products Details")

    prod_to_remove = []

    for idx, prod in enumerate(st.session_state.order_products):
        with st.container():
            st.markdown(f"#### Product #{idx + 1}")
            
            c_cat, c_sub = st.columns(2)
            cats = list(PRODUCT_CATALOG.keys())
            curr_cat_idx = cats.index(prod["category"]) if prod["category"] in cats else 0
            
            with c_cat:
                selected_cat = st.selectbox("Select The Product", cats, index=curr_cat_idx, key=f"prod_cat_{idx}")
                prod["category"] = selected_cat

            sub_options = PRODUCT_CATALOG.get(selected_cat, ["Other"])
            curr_sub_idx = sub_options.index(prod["sub_category"]) if prod["sub_category"] in sub_options else 0

            with c_sub:
                selected_sub = st.selectbox("Select Sub-Category", sub_options, index=curr_sub_idx, key=f"prod_sub_{idx}")
                prod["sub_category"] = selected_sub

            if selected_cat == "Other" or selected_sub == "Other":
                prod["custom_name"] = st.text_input("Enter Custom Product Name", value=prod.get("custom_name", ""), placeholder="Specify item name...", key=f"prod_custom_{idx}")

            c_dim, c_qty, c_del = st.columns([2.3, 2.3, 0.4])
            
            with c_dim:
                prod["dimensions"] = st.text_input("Dimensions (WxH)", value=prod.get("dimensions", ""), placeholder="e.g., 5330X6000", key=f"prod_dim_{idx}")
                
            with c_qty:
                prod["quantity"] = st.number_input("Quantity", min_value=1, value=int(prod.get("quantity", 1)), step=1, key=f"prod_qty_{idx}")
                
            with c_del:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if len(st.session_state.order_products) > 1:
                    if st.button("🗑️", key=f"del_prod_{idx}"):
                        prod_to_remove.append(idx)

            st.markdown("---")

    if prod_to_remove:
        for i in sorted(prod_to_remove, reverse=True):
            st.session_state.order_products.pop(i)
        st.rerun()

    c_add_p, _ = st.columns([2, 3])
    with c_add_p:
        if st.button("➕ Add Another Product"):
            st.session_state.order_products.append(
                {"category": "Rolling Shutters", "sub_category": "Motorized Rolling Shutter", "custom_name": "", "dimensions": "", "quantity": 1}
            )
            st.rerun()

    st.divider()
    st.subheader("📦 Order Products Details")

    prod_to_remove = []

    for idx, prod in enumerate(st.session_state.order_products):
        with st.container():
            st.markdown(f"#### Product #{idx + 1}")
            
            # Row 1: Product Category & Sub-Category (50% / 50% split)
            c_cat, c_sub = st.columns(2)
            
            cats = list(PRODUCT_CATALOG.keys())
            curr_cat_idx = cats.index(prod["category"]) if prod["category"] in cats else 0
            
            with c_cat:
                selected_cat = st.selectbox(
                    "Select The Product", 
                    cats, 
                    index=curr_cat_idx, 
                    key=f"prod_cat_{idx}"
                )
                prod["category"] = selected_cat

            sub_options = PRODUCT_CATALOG.get(selected_cat, ["Other"])
            curr_sub_idx = sub_options.index(prod["sub_category"]) if prod["sub_category"] in sub_options else 0

            with c_sub:
                selected_sub = st.selectbox(
                    "Select Sub-Category", 
                    sub_options, 
                    index=curr_sub_idx, 
                    key=f"prod_sub_{idx}"
                )
                prod["sub_category"] = selected_sub

            # Optional Custom Name field if 'Other' is selected
            if selected_cat == "Other" or selected_sub == "Other":
                prod["custom_name"] = st.text_input(
                    "Enter Custom Product Name", 
                    value=prod.get("custom_name", ""), 
                    placeholder="Specify item name...", 
                    key=f"prod_custom_{idx}"
                )

            # Row 2: Dimensions (Col 1), Quantity (Col 2 - Shifted right under Sub-Category), Delete Action (Col 3)
            c_dim, c_qty, c_del = st.columns([2.3, 2.3, 0.4])
            
            with c_dim:
                prod["dimensions"] = st.text_input(
                    "Dimensions (WxH)", 
                    value=prod.get("dimensions", ""), 
                    placeholder="e.g., 5330X6000", 
                    key=f"prod_dim_{idx}"
                )
                
            with c_qty:
                prod["quantity"] = st.number_input(
                    "Quantity", 
                    min_value=1, 
                    value=int(prod.get("quantity", 1)), 
                    step=1, 
                    key=f"prod_qty_{idx}"
                )
                
            with c_del:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if len(st.session_state.order_products) > 1:
                    if st.button("🗑️", key=f"del_prod_{idx}"):
                        prod_to_remove.append(idx)

            st.markdown("---")

    if prod_to_remove:
        for i in sorted(prod_to_remove, reverse=True):
            st.session_state.order_products.pop(i)
        st.rerun()

    c_add_p, _ = st.columns([2, 3])
    with c_add_p:
        if st.button("➕ Add Another Product"):
            st.session_state.order_products.append(
                {"category": "Rolling Shutters", "sub_category": "Motorized Rolling Shutter", "custom_name": "", "dimensions": "", "quantity": 1}
            )
            st.rerun()
# ------------------------------------------
# 4. LOG DAILY TASKS
# ------------------------------------------
elif menu == "Log Daily Tasks":
    st.header("📋 Log Daily Tasks")

    df_inst = read_sheet("Installations")
    df_logs = read_sheet("Daily_Logs")

    if not df_inst.empty:
        df_inst.columns = df_inst.columns.str.strip().str.lower()
    if not df_logs.empty:
        df_logs.columns = df_logs.columns.str.strip().str.lower()

    all_ids = df_inst["installation_id"].tolist() if not df_inst.empty and "installation_id" in df_inst.columns else []
    id_options = ["-- Select Installation ID --"] + [
        f"{row['installation_id']} | {row['site_address'][:25]}... [{row.get('status', 'In Progress')}]" 
        for _, row in df_inst.iterrows()
    ] if not df_inst.empty and "installation_id" in df_inst.columns else ["No existing IDs found"]

    if "selected_inst_id" not in st.session_state:
        st.session_state.selected_inst_id = ""
    if "pk_input_val" not in st.session_state:
        st.session_state.pk_input_val = ""
    if "pk_select_val" not in st.session_state:
        st.session_state.pk_select_val = "-- Select Installation ID --"

    def sync_from_input():
        input_text = st.session_state.pk_input_val.strip()
        if input_text in all_ids:
            st.session_state.selected_inst_id = input_text
            matching_label = next((opt for opt in id_options if opt.startswith(f"{input_text} |")), "-- Select Installation ID --")
            st.session_state.pk_select_val = matching_label
        else:
            matched = [i for i in all_ids if input_text.lower() in str(i).lower()]
            if matched:
                st.session_state.selected_inst_id = matched[0]
                matching_label = next((opt for opt in id_options if opt.startswith(f"{matched[0]} |")), "-- Select Installation ID --")
                st.session_state.pk_select_val = matching_label
            else:
                st.session_state.selected_inst_id = input_text

    def sync_from_select():
        selected = st.session_state.pk_select_val
        if selected and selected not in ["-- Select Installation ID --", "No existing IDs found"]:
            extracted_id = selected.split(" | ")[0]
            st.session_state.selected_inst_id = extracted_id
            st.session_state.pk_input_val = extracted_id
        else:
            st.session_state.selected_inst_id = ""
            st.session_state.pk_input_val = ""

    st.subheader("Select the Data")
    search_tab1, search_tab2 = st.tabs(["🔎 Search by Installation Id", "📅 Search by Date"])

    with search_tab1:
        col_pk_input, col_pk_select = st.columns(2)
        with col_pk_input:
            st.text_input("Enter Installation ID directly:", placeholder="e.g., INST-2026-G4HVI", key="pk_input_val", on_change=sync_from_input)
        with col_pk_select:
            st.selectbox("Installation Id", options=id_options, key="pk_select_val", on_change=sync_from_select)

    with search_tab2:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            filter_date = st.date_input("Filter Orders by Created Date:", value=datetime.now(), key="log_date_filter", format="YYYY-MM-DD")
        with col_d2:
            if not df_inst.empty and "order_created_date" in df_inst.columns:
                filtered_df = df_inst[df_inst["order_created_date"].astype(str) == str(filter_date)]
                if not filtered_df.empty:
                    date_options = ["-- Select Installation ID --"] + [
                        f"{row['installation_id']} | {row['site_address'][:20]}... | Status: [{row.get('status', 'In Progress')}]" 
                        for _, row in filtered_df.iterrows()
                    ]
                    def sync_from_date_select():
                        sel = st.session_state.log_date_select
                        if sel != "-- Select Installation ID --":
                            ext_id = sel.split(" | ")[0]
                            st.session_state.selected_inst_id = ext_id
                            st.session_state.pk_input_val = ext_id
                            matching_label = next((opt for opt in id_options if opt.startswith(f"{ext_id} |")), "-- Select Installation ID --")
                            st.session_state.pk_select_val = matching_label

                    st.selectbox("Select Project matching date:", date_options, key="log_date_select", on_change=sync_from_date_select)
                else:
                    st.info(f"No installation orders found created on {filter_date}.")
            else:
                st.info("No installation records available to filter by date.")

    st.divider()

    selected_id = st.session_state.selected_inst_id

    if selected_id and not df_inst.empty and selected_id in df_inst["installation_id"].values:
        inst_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]

        inst_col_logs = next((c for c in df_logs.columns if "installation" in c or "inst" in c), "installation_id") if not df_logs.empty else "installation_id"
        existing_logs = pd.DataFrame()
        if not df_logs.empty and inst_col_logs in df_logs.columns:
            df_logs[inst_col_logs] = df_logs[inst_col_logs].astype(str).str.strip()
            existing_logs = df_logs[df_logs[inst_col_logs] == selected_id.strip()]

        day_number_int = len(existing_logs) + 1
        day_label = f"Day {day_number_int}"

        df_items = read_sheet("Order_Items")
        if not df_items.empty:
            df_items.columns = df_items.columns.str.strip().str.lower()

        site_items = df_items[df_items["installation_id"] == selected_id] if not df_items.empty and "installation_id" in df_items.columns else pd.DataFrame()
        product_options = [f"{row.get('sub_category', row.get('category', 'Product'))} ({row.get('dimensions', '')})" for _, row in site_items.iterrows()] if not site_items.empty else []
        product_options.append("General Site Work / Preparation")

        st.markdown(f"""
            <div style="background-color: #EBF3FE; border-left: 5px solid #00A651; padding: 14px 20px; border-radius: 6px; margin-bottom: 20px;">
                <span style="color: #0F4C81; font-weight: 700; font-size: 15px;">Active Installation ID:</span>
                <span style="color: #00A651; font-weight: 700; font-size: 16px; margin-left: 8px; font-family: monospace;">{selected_id}</span>
                <span style="color: #1A6BBA; font-weight: 600; font-size: 14px; margin-left: 15px;">(Auto-Calculated: <b>{day_label}</b> | Assigned Team: {inst_info.get('team_details', 'N/A')})</span>
            </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p1:
            log_date = st.date_input("Log Date", value=datetime.now(), min_value=datetime.now() - timedelta(days=14), format="YYYY-MM-DD")
        with col_p2:
            product_worked_on = st.selectbox("Product Worked On *", product_options)
        with col_p3:
            curr_status = inst_info.get('status', 'In Progress')
            status_index = STATUS_OPTIONS.index(curr_status) if curr_status in STATUS_OPTIONS else 0
            work_status = st.selectbox("Work Progress Status *", STATUS_OPTIONS, index=status_index)

        auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        st.divider()

        submitted_by = render_worker_inputs()

        st.divider()

        st.markdown(f"### Work Progress & Tasks Executed ({day_label})")
        render_task_grid("log_tasks_grid")

        st.divider()
        st.markdown("### ⚠️ Site Remarks & Delay Reasons (Optional)")
        site_remarks = st.text_area("Site Remarks / Delay Reasons", placeholder="Record material shortages, client delays, electrical issues, or site hold details...")

        st.divider()

        if st.button("💾 Log Tasks", use_container_width=True, type="primary"):
            grid_items = st.session_state.get("log_tasks_grid", [])
            valid_items = [t for t in grid_items if t.get("description", "").strip()]

            if not valid_items:
                st.error("Please enter at least one task description.")
            elif not submitted_by.strip():
                st.error("Please enter at least one worker's name.")
            else:
                combined_tasks = format_tasks_to_string(valid_items)
                log_id = generate_log_id()
                
                log_row = [
                    log_id, selected_id, day_label, auto_log_time, str(log_date), 
                    product_worked_on, combined_tasks, "None planned", site_remarks, submitted_by
                ]
                append_to_sheet("Daily_Logs", log_row)
                update_sheet_row("Installations", "installation_id", selected_id, {"status": work_status})
                
                st.success(f"Successfully recorded **{day_label}** log with workers (**{submitted_by}**) & updated status to **{work_status}** for Installation ID **`{selected_id}`**!")
                
                st.session_state["log_tasks_grid"] = [
                    {"done": True, "description": "", "category": "General"},
                    {"done": True, "description": "", "category": "General"},
                    {"done": True, "description": "", "category": "General"},
                    {"done": True, "description": "", "category": "General"}
                ]
                st.session_state["workers_list"] = ["", ""]
                st.rerun()
    else:
        st.markdown("""
            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 14px 20px; border-radius: 6px; margin-bottom: 20px;">
                <span style="color: #991B1B; font-weight: 700; font-size: 15px;">No Installation ID selected. Please select or enter a valid ID above.</span>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# 5. VIEW LOGS & UPDATE STATUS
# ------------------------------------------
elif menu == "View Logs & Update Status":
    st.header("🔍 View Logs & Update Installation Status")

    df_inst = read_sheet("Installations")
    
    if df_inst.empty:
        st.warning("No Installation IDs recorded.")
    else:
        inst_map = {f"{row['installation_id']} | {row['site_address'][:25]}...": row['installation_id'] for _, row in df_inst.iterrows()}
        selected_label = st.selectbox("Select Installation Project ID:", list(inst_map.keys()))
        selected_id = inst_map[selected_label]

        site_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]
        
        st.success(f"### Target Installation Project ID: `{site_info['installation_id']}`")
        st.write(f"**Site Address:** {site_info['site_address']} | **Team Details:** {site_info['team_details']}")
        
        st.divider()

        st.subheader("📌 Update Overall Status")
        col_status, col_btn = st.columns([2, 1])
        
        current_status = site_info['status'] if site_info['status'] in STATUS_OPTIONS else "In Progress"
        
        with col_status:
            new_status = st.selectbox("Change Overall Status:", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))
            
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("Update Status", type="primary"):
                updated_inst = update_sheet_row("Installations", "installation_id", selected_id, {"status": new_status})
                if updated_inst:
                    st.success(f"Status for Installation Project `{selected_id}` updated to **{new_status}**!")
                    st.rerun()
                else:
                    st.error("Could not update status in Google Sheets.")

        st.divider()
        st.subheader("📦 Order Specifications")
        
        df_items = read_sheet("Order_Items")
        site_items = df_items[df_items["installation_id"] == selected_id] if not df_items.empty else pd.DataFrame()
        if not site_items.empty:
            st.table(site_items[["category", "sub_category", "dimensions", "quantity"]])
        else:
            st.info("No order items recorded for this installation ID.")

        st.divider()
        st.subheader("📅 Activity Timeline")
        
        df_logs = read_sheet("Daily_Logs")
        site_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()

        if site_logs.empty:
            st.info("No activity logs recorded for this Installation ID yet.")
        else:
            for _, row in site_logs.iterrows():
                with st.expander(f"📅 **{row.get('day_number', 'Day Log')} - Date: {row['logged_date']}**", expanded=True):
                    st.markdown(f"""
                    * **Visit Log ID:** `{row.get('log_id', 'N/A')}`
                    * **Timestamp:** `{str(row.get('logged_timestamp', '')).split(' ')[-1]}`
                    * **Product Worked On:** {row.get('product_worked_on', 'N/A')}
                    * **Workers On Site:** {row.get('submitted_by', 'N/A')}
                    * **Site Remarks:** {row.get('site_remarks', 'None')}
                    
                    **Completed Tasks:**
                    ```
                    {row.get('tasks_completed', '')}
                    ```
                    """)

# ------------------------------------------
# 6. MASTER DATABASE
# ------------------------------------------
elif menu == "Master Database":
    st.header("Master Database View (Google Sheets)")
    
    st.subheader("1. All Installations")
    st.dataframe(read_sheet("Installations"), use_container_width=True)
    
    st.subheader("2. All Order Items")
    st.dataframe(read_sheet("Order_Items"), use_container_width=True)
    
    st.subheader("3. All Log Entries")
    st.dataframe(read_sheet("Daily_Logs"), use_container_width=True)
