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

# Main Google Sheets Workbook Name
SPREADSHEET_NAME = "Installation_Schedules"

# Render High-Quality Logo in Navigation Bar (Sidebar)
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

# Google Sheets Client
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

def get_worksheet(worksheet_name):
    client = get_gspread_client()
    return client.open(SPREADSHEET_NAME).worksheet(worksheet_name)

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
    if sheet_name == "Installations":
        return pd.DataFrame(columns=[
            "installation_id", "city_prefix", "site_address", "team_details", 
            "order_created_date", "site_clearance_date", "target_ho_date", "status"
        ])
    elif sheet_name == "Order_Items":
        return pd.DataFrame(columns=[
            "installation_id", "category", "sub_category", "dimensions", "quantity"
        ])
    elif sheet_name == "Daily_Logs":
        return pd.DataFrame(columns=[
            "log_id", "installation_id", "day_number", "logged_timestamp", 
            "logged_date", "product_worked_on", "tasks_completed", 
            "next_day_planned_tasks", "site_remarks", "submitted_by"
        ])
    return pd.DataFrame()

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

def delete_sheet_row(sheet_name, key_column_name, key_value):
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
                sheet.delete_rows(row_idx)
                st.cache_data.clear()
                return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
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
    "New Installation Order", 
    "Log Daily Tasks",
    "Edit Task Log (By Primary Key)",
    "View Logs & Update Status", 
    "Master Database"
])

if "task_count" not in st.session_state:
    st.session_state.task_count = 5

if "next_task_count" not in st.session_state:
    st.session_state.next_task_count = 5

# 1. NEW INSTALLATION ORDER
if menu == "New Installation Order":
    st.header("Create New Installation Order")

    if "temp_inst_id" not in st.session_state:
        st.session_state.temp_inst_id = generate_project_id()

    st.markdown(f"""
        <div style="background-color: #EBF3FE; border: 1px solid #1A6BBA; padding: 14px 20px; border-radius: 8px; margin-bottom: 20px;">
            <span style="color: #0F4C81; font-weight: 700; font-size: 15px;">Automated Visit ID:</span>
            <span style="color: #00A651; font-weight: 700; font-size: 16px; margin-left: 8px; font-family: monospace;">{st.session_state.temp_inst_id}</span>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        team_details = st.text_input("Team's Details *", placeholder="e.g., Rajeer + 2 Helpers")
        city_name = st.text_input("City Name *", "Mumbai").strip()
        site_address = st.text_area("Site Address *", placeholder="Full installation site address...")

    with col2:
        min_past_date = datetime.now() - timedelta(days=7)
        order_created_date = st.date_input("Installation Date (Order Created Date)", value=datetime.now(), min_value=min_past_date, format="YYYY-MM-DD")
        site_clearance = st.date_input("Site Clearance Date", value=datetime.now(), min_value=min_past_date, format="YYYY-MM-DD")
        target_ho_date = st.date_input("Target Handover Date", value=datetime.now() + timedelta(days=15), min_value=min_past_date, format="YYYY-MM-DD")

    st.divider()

    col_cat, col_sub = st.columns(2)
    with col_cat:
        selected_category = st.selectbox("Select The Product", list(PRODUCT_CATALOG.keys()))
    with col_sub:
        selected_sub_category = st.selectbox("Select Sub-Category", PRODUCT_CATALOG[selected_category])

    final_product_name = selected_sub_category
    if selected_category == "Other" or selected_sub_category == "Other":
        custom_name = st.text_input("Enter Custom Product Name", placeholder="Specify item name...")
        if custom_name.strip():
            final_product_name = custom_name.strip()

    col_dim, col_qty = st.columns(2)
    with col_dim:
        dimensions = st.text_input("Dimensions (WxH)", placeholder="e.g., 5330X6000")
    with col_qty:
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

    st.divider()

    if st.button("Save Installation Order", use_container_width=True, type="primary"):
        if not team_details.strip():
            st.error("Please enter Team's Details.")
        elif not site_address.strip():
            st.error("Please enter a valid Site Address.")
        else:
            df_inst = read_sheet("Installations")
            existing_ids = df_inst["installation_id"].tolist() if not df_inst.empty else []
            
            inst_id = st.session_state.temp_inst_id
            while inst_id in existing_ids:
                inst_id = generate_project_id()

            city_prefix = city_name[:3].upper() if city_name else "GEN"

            inst_row = [
                inst_id, city_prefix, site_address, team_details, 
                str(order_created_date), str(site_clearance), str(target_ho_date), "In Progress"
            ]
            append_to_sheet("Installations", inst_row)
            
            item_row = [inst_id, selected_category, final_product_name, dimensions, int(quantity)]
            append_to_sheet("Order_Items", item_row)
            
            st.success(f"Saved to Google Sheets! Generated Installation ID: **`{inst_id}`**")
            st.session_state.temp_inst_id = generate_project_id()

# 2. LOG DAILY TASKS
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
            matched = [i for i in all_ids if input_text.lower() in i.lower()]
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
            st.text_input(
                "Enter Installation ID directly:", 
                placeholder="e.g., INST-2026-G4HVI", 
                key="pk_input_val",
                on_change=sync_from_input
            )
        
        with col_pk_select:
            st.selectbox(
                "Installation Id", 
                options=id_options, 
                key="pk_select_val",
                on_change=sync_from_select
            )

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
                <span style="color: #1A6BBA; font-weight: 600; font-size: 14px; margin-left: 15px;">(Auto-Calculated: <b>{day_label}</b> | Team: {inst_info.get('team_details', 'N/A')})</span>
            </div>
        """, unsafe_allow_html=True)

        if not existing_logs.empty:
            last_log = existing_logs.iloc[-1]
            prev_planned = last_log.get('next_day_planned_tasks', last_log.get('next_day_plann', ''))
            if prev_planned and str(prev_planned).strip():
                with st.expander(f"📌 Tasks Planned Yesterday ({last_log.get('day_number', 'Previous Log')})", expanded=True):
                    st.info(prev_planned)

        col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 1, 1])
        with col_p1:
            log_date = st.date_input("Log Date", value=datetime.now(), min_value=datetime.now() - timedelta(days=14), format="YYYY-MM-DD")
        with col_p2:
            product_worked_on = st.selectbox("Product Worked On *", product_options)
        with col_p3:
            default_tech = inst_info['team_details'].split('+')[0].strip() if '+' in str(inst_info.get('team_details', '')) else str(inst_info.get('team_details', ''))
            submitted_by = st.text_input("Technician Name *", value=default_tech)
        with col_p4:
            curr_status = inst_info.get('status', 'In Progress')
            status_index = STATUS_OPTIONS.index(curr_status) if curr_status in STATUS_OPTIONS else 0
            work_status = st.selectbox("Work Progress Status *", STATUS_OPTIONS, index=status_index, key="work_progress_status")

        auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        st.divider()

        st.markdown("### 📝 Today's Completed Tasks")
        completed_tasks = []
        for i in range(st.session_state.task_count):
            task_input = st.text_input(f"Completed Task {i + 1}", key=f"today_task_{i}", placeholder="Describe work completed today...").strip()
            if task_input:
                completed_tasks.append(f"{i + 1}. {task_input}")

        col_tc1, col_tc2, _ = st.columns([1, 1, 3])
        with col_tc1:
            if st.button("➕ Add Task"):
                st.session_state.task_count += 1
                st.rerun()
        with col_tc2:
            if st.session_state.task_count > 1 and st.button("➖ Remove Task"):
                st.session_state.task_count -= 1
                st.rerun()

        st.divider()

        st.markdown("### 🔮 Planned Tasks for Next Day")
        next_tasks = []
        for j in range(st.session_state.next_task_count):
            next_input = st.text_input(f"Next Day Task {j + 1}", key=f"next_task_{j}", placeholder="Describe task planned for tomorrow...").strip()
            if next_input:
                next_tasks.append(f"{j + 1}. {next_input}")

        col_nt1, col_nt2, _ = st.columns([1, 1, 3])
        with col_nt1:
            if st.button("➕ Add Next Task"):
                st.session_state.next_task_count += 1
                st.rerun()
        with col_nt2:
            if st.session_state.next_task_count > 1 and st.button("➖ Remove Next Task"):
                st.session_state.next_task_count -= 1
                st.rerun()

        st.divider()
        st.markdown("### ⚠️ Site Remarks & Delay Issues (Optional)")
        site_remarks = st.text_area("Site Remarks / Delay Reasons", placeholder="Record material shortages, client delays, electrical issues, or site hold details...")

        st.divider()

        if st.button("Submit Daily Task Log", use_container_width=True, type="primary"):
            if not completed_tasks:
                st.error("Please fill in at least one completed task description.")
            elif not submitted_by.strip():
                st.error("Please specify the Technician Name.")
            else:
                combined_completed = "\n".join(completed_tasks)
                combined_next = "\n".join(next_tasks) if next_tasks else "None planned"
                log_id = generate_log_id()
                
                log_row = [
                    log_id, selected_id, day_label, auto_log_time, str(log_date), 
                    product_worked_on, combined_completed, combined_next, site_remarks, submitted_by
                ]
                append_to_sheet("Daily_Logs", log_row)

                update_sheet_row("Installations", "installation_id", selected_id, {"status": work_status})
                
                st.success(f"Successfully recorded **{day_label}** log & updated status to **{work_status}** for Installation ID **`{selected_id}`**!")
                st.session_state.task_count = 5
                st.session_state.next_task_count = 5
    else:
        st.markdown("""
            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 14px 20px; border-radius: 6px; margin-bottom: 20px;">
                <span style="color: #991B1B; font-weight: 700; font-size: 15px;">No Installation ID selected. Please select or enter a valid ID above.</span>
            </div>
        """, unsafe_allow_html=True)

# 3. EDIT TASK LOG
elif menu == "Edit Task Log (By Primary Key)":
    st.header("✏️ Edit Task Log")

    df_logs = read_sheet("Daily_Logs")
    df_inst = read_sheet("Installations")

    if not df_logs.empty:
        df_logs.columns = df_logs.columns.str.strip().str.lower()
    if not df_inst.empty:
        df_inst.columns = df_inst.columns.str.strip().str.lower()

    inst_col_logs = next((c for c in df_logs.columns if "installation" in c or "inst" in c), "installation_id") if not df_logs.empty else "installation_id"
    all_inst_ids = df_inst["installation_id"].tolist() if not df_inst.empty and "installation_id" in df_inst.columns else []

    inst_options = ["-- Select Installation ID --"] + [
        f"{str(row.get('installation_id', ''))} | {str(row.get('site_address', ''))[:25]}... [{str(row.get('status', 'In Progress'))}]" 
        for _, row in df_inst.iterrows()
    ] if not df_inst.empty and "installation_id" in df_inst.columns else ["No existing IDs found"]

    if "edit_inst_id" not in st.session_state:
        st.session_state.edit_inst_id = ""
    if "edit_input_val" not in st.session_state:
        st.session_state.edit_input_val = ""
    if "edit_select_val" not in st.session_state:
        st.session_state.edit_select_val = "-- Select Installation ID --"

    def sync_edit_input():
        input_text = st.session_state.edit_input_val.strip()
        if input_text in all_inst_ids:
            st.session_state.edit_inst_id = input_text
            match = next((opt for opt in inst_options if opt.startswith(f"{input_text} |")), "-- Select Installation ID --")
            st.session_state.edit_select_val = match
        else:
            matched = [i for i in all_inst_ids if input_text.lower() in str(i).lower()]
            if matched:
                st.session_state.edit_inst_id = matched[0]
                match = next((opt for opt in inst_options if opt.startswith(f"{matched[0]} |")), "-- Select Installation ID --")
                st.session_state.edit_select_val = match
            else:
                st.session_state.edit_inst_id = input_text

    def sync_edit_select():
        selected = st.session_state.edit_select_val
        if selected and selected not in ["-- Select Installation ID --", "No existing IDs found"]:
            extracted_id = selected.split(" | ")[0]
            st.session_state.edit_inst_id = extracted_id
            st.session_state.edit_input_val = extracted_id
        else:
            st.session_state.edit_inst_id = ""
            st.session_state.edit_input_val = ""

    st.subheader("Select the Data")
    edit_tab1, edit_tab2 = st.tabs(["🔎 Search by Installation Id", "📅 Search by Date"])

    with edit_tab1:
        col_e_in, col_e_sel = st.columns(2)
        with col_e_in:
            st.text_input(
                "Enter Installation ID directly:",
                placeholder="e.g., INST-2026-UKVXU",
                key="edit_input_val",
                on_change=sync_edit_input
            )
        with col_e_sel:
            st.selectbox(
                "Installation Id",
                options=inst_options,
                key="edit_select_val",
                on_change=sync_edit_select
            )

    with edit_tab2:
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            filter_edit_date = st.date_input("Filter Orders by Created Date:", value=datetime.now(), key="edit_date_filter", format="YYYY-MM-DD")
        with col_ed2:
            if not df_inst.empty and "order_created_date" in df_inst.columns:
                filtered_df = df_inst[df_inst["order_created_date"].astype(str) == str(filter_edit_date)]
                if not filtered_df.empty:
                    date_options = ["-- Select Installation ID --"] + [
                        f"{str(row.get('installation_id', ''))} | {str(row.get('site_address', ''))[:20]}... | Status: [{str(row.get('status', 'In Progress'))}]" 
                        for _, row in filtered_df.iterrows()
                    ]
                    def sync_edit_date_select():
                        sel = st.session_state.edit_date_select
                        if sel != "-- Select Installation ID --":
                            ext_id = sel.split(" | ")[0]
                            st.session_state.edit_inst_id = ext_id
                            st.session_state.edit_input_val = ext_id
                            match = next((opt for opt in inst_options if opt.startswith(f"{ext_id} |")), "-- Select Installation ID --")
                            st.session_state.edit_select_val = match

                    st.selectbox("Select Project matching date:", date_options, key="edit_date_select", on_change=sync_edit_date_select)
                else:
                    st.info(f"No installation orders found created on {filter_edit_date}.")
            else:
                st.info("No installation records available to filter by date.")

    st.divider()

    selected_id = st.session_state.edit_inst_id

    if selected_id and not df_inst.empty and selected_id in df_inst["installation_id"].astype(str).values:
        inst_info = df_inst[df_inst["installation_id"].astype(str) == selected_id].iloc[0]

        existing_logs = pd.DataFrame()
        if not df_logs.empty and inst_col_logs in df_logs.columns:
            df_logs[inst_col_logs] = df_logs[inst_col_logs].astype(str).str.strip()
            existing_logs = df_logs[df_logs[inst_col_logs] == selected_id.strip()].reset_index(drop=True)

        if existing_logs.empty:
            st.warning(f"No task logs found recorded yet for Installation ID: `{selected_id}`.")
        else:
            log_day_choices = []
            for idx, row in existing_logs.iterrows():
                calc_day = str(row.get("day_number", f"Day {idx + 1}") or f"Day {idx + 1}")
                log_date_str = str(row.get("logged_date", row.get("log_date", "N/A")) or "N/A")
                log_id_str = str(row.get("log_id", "") or "")
                log_day_choices.append(f"{calc_day} | Date: {log_date_str} ({log_id_str})")

            selected_day_label = st.selectbox("Select Log Entry to Update:", log_day_choices)
            selected_idx = log_day_choices.index(selected_day_label)
            selected_log_row = existing_logs.iloc[selected_idx]

            active_day_name = str(selected_log_row.get("day_number", f"Day {selected_idx + 1}") or f"Day {selected_idx + 1}")
            current_log_id = str(selected_log_row.get("log_id", "") or "")
            team_details_safe = str(inst_info.get('team_details', 'N/A') or 'N/A')

            # Safe Markdown formatting without NoneType conversion errors
            st.markdown(f"""
                <div style="background-color: #EBF3FE; border-left: 5px solid #00A651; padding: 14px 20px; border-radius: 6px; margin-bottom: 20px;">
                    <span style="color: #0F4C81; font-weight: 700; font-size: 15px;">Active Installation ID:</span>
                    <span style="color: #00A651; font-weight: 700; font-size: 16px; margin-left: 8px; font-family: monospace;">{selected_id}</span>
                    <span style="color: #1A6BBA; font-weight: 600; font-size: 14px; margin-left: 15px;">(Editing: <b>{active_day_name}</b> | Team: {team_details_safe})</span>
                </div>
            """, unsafe_html=True)

            with st.expander("📋 View All Previously Recorded Work Summaries for this Site", expanded=True):
                for idx, log in existing_logs.iterrows():
                    log_day = str(log.get('day_number', f"Day {idx + 1}") or f"Day {idx + 1}")
                    log_time = str(log.get('logged_date', log.get('log_date', 'N/A')) or 'N/A')
                    tech = str(log.get('submitted_by', 'N/A') or 'N/A')
                    tasks = str(log.get('tasks_completed', log.get('completed_tasks', 'No tasks logged.')) or 'No tasks logged.')
                    
                    st.markdown(f"**{log_day}** — *{log_time}* (By: **{tech}**)")
                    st.text(tasks)
                    st.markdown("---")

            with st.form(key="edit_task_log_form"):
                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                
                with col_p1:
                    try:
                        raw_date = str(selected_log_row.get("logged_date", selected_log_row.get("log_date", "")))
                        parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
                    except ValueError:
                        parsed_date = datetime.now()
                    new_log_date = st.date_input("Log Date", value=parsed_date, format="YYYY-MM-DD")

                with col_p2:
                    raw_product = str(selected_log_row.get("product_worked_on", "") or "")
                    new_product = st.text_input("Product Worked On", value=raw_product, placeholder="e.g. Rolling Shutter")

                with col_p3:
                    new_tech = st.text_input("Technician Name", value=str(selected_log_row.get("submitted_by", "") or ""))

                with col_p4:
                    curr_status = str(inst_info.get('status', 'In Progress') or 'In Progress')
                    status_idx = STATUS_OPTIONS.index(curr_status) if curr_status in STATUS_OPTIONS else 0
                    new_status = st.selectbox("Work Progress Status *", STATUS_OPTIONS, index=status_idx)

                st.divider()

                existing_tasks_text = str(selected_log_row.get("tasks_completed", selected_log_row.get("completed_tasks", "")) or "")
                
                new_completed = st.text_area(
                    f"Work Progress & Tasks Executed ({active_day_name})", 
                    value=existing_tasks_text, 
                    height=200,
                    help="Modify or append tasks directly to this log entry."
                )

                new_site_remarks = st.text_area(
                    "Site Remarks / Delay Reasons (Optional)", 
                    value=str(selected_log_row.get("site_remarks", "") or ""), 
                    height=90
                )

                submit_edit = st.form_submit_button(f"💾 Save Updated {active_day_name} Log", type="primary", use_container_width=True)

                if submit_edit:
                    cleaned_tasks = new_completed.strip()
                    if not cleaned_tasks:
                        st.error("Tasks completed cannot be empty.")
                    else:
                        # Check if the existing record in database already contains identical data
                        curr_db_task = str(selected_log_row.get("tasks_completed", selected_log_row.get("completed_tasks", "")) or "").strip()
                        curr_db_prod = str(selected_log_row.get("product_worked_on", "") or "").strip()
                        curr_db_tech = str(selected_log_row.get("submitted_by", "") or "").strip()
                        curr_db_date = str(selected_log_row.get("logged_date", selected_log_row.get("log_date", "")) or "").strip()

                        if (cleaned_tasks == curr_db_task and 
                            new_product.strip() == curr_db_prod and 
                            new_tech.strip() == curr_db_tech and 
                            str(new_log_date).strip() == curr_db_date):
                            st.warning("⚠️ Same entry already done. No changes were made.")
                        else:
                            updated_fields = {
                                "logged_date": str(new_log_date),
                                "product_worked_on": new_product,
                                "tasks_completed": cleaned_tasks,
                                "site_remarks": new_site_remarks,
                                "submitted_by": new_tech,
                                "day_number": active_day_name
                            }
                            
                            target_key = "log_id" if current_log_id else inst_col_logs
                            target_val = current_log_id if current_log_id else selected_id

                            update_sheet_row("Daily_Logs", target_key, target_val, updated_fields)
                            update_sheet_row("Installations", "installation_id", selected_id, {"status": new_status})

                            st.success(f"Successfully updated log for **{active_day_name}** under Installation ID **`{selected_id}`**!")
                            st.rerun()

            st.divider()
            with st.expander(f"🗑️ Danger Zone: Delete {active_day_name} Log Entry"):
                st.warning(f"Deleting this entry will permanently remove the {active_day_name} log from Google Sheets.")
                if st.button(f"Confirm Delete {active_day_name}", key="delete_log_btn"):
                    if current_log_id:
                        deleted = delete_sheet_row("Daily_Logs", "log_id", current_log_id)
                    else:
                        deleted = delete_sheet_row("Daily_Logs", inst_col_logs, selected_id)
                        
                    if deleted:
                        st.success(f"{active_day_name} log entry deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete log entry.")

    elif selected_id:
        st.error(f"Installation ID `{selected_id}` not found in master records.")

# 4. VIEW LOGS & UPDATE STATUS
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
                    * **Technician:** {row.get('submitted_by', 'N/A')}
                    * **Site Remarks:** {row.get('site_remarks', 'None')}
                    
                    **Completed Tasks:**
                    ```
                    {row.get('tasks_completed', '')}
                    ```
                    
                    **Planned Tasks for Next Day:**
                    ```
                    {row.get('next_day_planned_tasks', 'None recorded')}
                    ```
                    """)

# 5. MASTER DATABASE
elif menu == "Master Database":
    st.header("Master Database View (Google Sheets)")
    
    st.subheader("1. All Installations")
    st.dataframe(read_sheet("Installations"), use_container_width=True)
    
    st.subheader("2. All Order Items")
    st.dataframe(read_sheet("Order_Items"), use_container_width=True)
    
    st.subheader("3. All Log Entries")
    st.dataframe(read_sheet("Daily_Logs"), use_container_width=True)
