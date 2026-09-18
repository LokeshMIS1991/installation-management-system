import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import string

# ---------------------------------------------------------
# 1. Configuration & Global Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sidharth Shutter & Automation",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

SPREADSHEET_ID = "19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s"
SPREADSHEET_NAME = "Installation_Schedules"

CATEGORIES = ['General', 'Work', 'Personal', 'Urgent', 'Meeting', 'Development', 'Design']
STATUS_OPTIONS = ['Pending', 'In Progress', 'Completed', 'On Hold']

# Custom CSS Styling
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    .table-header {
        font-size: 11px;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    div[data-baseweb="input"] { border-radius: 8px !important; }
    div[data-baseweb="select"] { border-radius: 8px !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Resilient Google Sheets Connection
# ---------------------------------------------------------
@st.cache_resource(ttl=300)
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
    # Opens sheet via exact Key to prevent SpreadsheetNotFound exception
    try:
        return client.open_by_key(SPREADSHEET_ID).worksheet(worksheet_name)
    except Exception:
        return client.open(SPREADSHEET_NAME).worksheet(worksheet_name)

def read_sheet(sheet_name):
    try:
        sheet = get_worksheet(sheet_name)
        rows = sheet.get_all_values()
        if not rows or len(rows) < 2:
            return pd.DataFrame()
        
        headers = [str(h).strip().lower() for h in rows[0]]
        data = rows[1:]
        df = pd.DataFrame(data, columns=headers)
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading '{sheet_name}': {e}")
        return pd.DataFrame()

def append_to_sheet(sheet_name, row_data):
    sheet = get_worksheet(sheet_name)
    sheet.append_row(row_data)

def generate_log_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    return f"LOG-{year}-{''.join(random.choices(chars, k=5))}"

def generate_inst_id(prefix):
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    clean_prefix = prefix.strip().upper() if prefix.strip() else "INST"
    return f"{clean_prefix}-{year}-{''.join(random.choices(chars, k=5))}"

# ---------------------------------------------------------
# 3. Dynamic Session State Initialization
# ---------------------------------------------------------
if "tasks_list" not in st.session_state:
    st.session_state.tasks_list = [
        {"done": False, "text": "", "category": "General"} for _ in range(5)
    ]

def add_task_row():
    st.session_state.tasks_list.append({"done": False, "text": "", "category": "General"})

def reset_tasks_to_5():
    st.session_state.tasks_list = [
        {"done": False, "text": "", "category": "General"} for _ in range(5)
    ]

def clear_all_tasks():
    st.session_state.tasks_list = []

def remove_task_row(index):
    if 0 <= index < len(st.session_state.tasks_list):
        st.session_state.tasks_list.pop(index)

# ---------------------------------------------------------
# 4. Navigation & Header UI
# ---------------------------------------------------------
st.sidebar.title("🏢 Navigation")
page = st.sidebar.radio(
    "Select Module:",
    ["Page 1: Installation Management", "Page 2: Daily Task Logger"]
)

header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("🏭 Sidharth Shutter & Automation")
    st.caption("Installation Management System")

with header_col2:
    st.info(f"📅 **{datetime.now().strftime('%a, %b %d, %Y')}**")

st.markdown("---")

# ---------------------------------------------------------
# PAGE 1: INSTALLATION MANAGEMENT
# ---------------------------------------------------------
if page == "Page 1: Installation Management":
    st.header("📋 Page 1: Installation Management")
    
    tab1, tab2 = st.tabs(["➕ Add New Installation", "🔍 View Existing Installations"])
    
    with tab1:
        st.subheader("Create Installation Record")
        with st.form("add_installation_form"):
            col1, col2 = st.columns(2)
            with col1:
                city_prefix = st.text_input("City Prefix (e.g. MUM, DEL, BGP)", value="MUM")
                site_address = st.text_area("Site Address", placeholder="Enter full address...")
                team_details = st.text_input("Team Details / Assigned Techs")
            with col2:
                order_created = st.date_input("Order Created Date", datetime.now())
                site_clearance_date = st.date_input("Site Clearance Date", datetime.now())
                target_ho_date = st.date_input("Target Handover Date", datetime.now())
                status = st.selectbox("Status", STATUS_OPTIONS)
            
            submit_inst = st.form_submit_button("💾 Save Installation Record", type="primary")
            
            if submit_inst:
                if not site_address.strip():
                    st.error("Site Address is required.")
                else:
                    new_inst_id = generate_inst_id(city_prefix)
                    inst_row = [
                        new_inst_id,
                        city_prefix,
                        site_address,
                        team_details,
                        str(order_created),
                        str(site_clearance_date),
                        str(target_ho_date),
                        status
                    ]
                    try:
                        append_to_sheet("Installations", inst_row)
                        st.success(f"Installation **{new_inst_id}** saved to sheet successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to record installation: {e}")

    with tab2:
        st.subheader("All Installation Records")
        df_inst = read_sheet("Installations")
        if df_inst.empty:
            st.info("No installation records found.")
        else:
            st.dataframe(df_inst, use_container_width=True)

# ---------------------------------------------------------
# PAGE 2: DAILY TASK LOGGER
# ---------------------------------------------------------
elif page == "Page 2: Daily Task Logger":
    st.header("📋 Page 2: Daily Task Logger")
    
    df_inst = read_sheet("Installations")
    df_logs = read_sheet("Daily_Logs")

    selected_id = None

    if df_inst.empty:
        st.warning("⚠️ No installation records found in the 'Installations' sheet. Add an installation on Page 1 first.")
    else:
        options = []
        for _, row in df_inst.iterrows():
            inst_id = row.get("installation_id", "N/A")
            address = row.get("site_address", "No Address")
            city = row.get("city_prefix", "")
            options.append(f"{inst_id} | {city} - {address[:35]}")
        
        selected_option = st.selectbox("Choose Active Installation ID:", options)
        if selected_option:
            selected_id = selected_option.split(" | ")[0]

    if selected_id:
        existing_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()
        day_number_str = f"Day {len(existing_logs) + 1}"

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric(label="Selected Project", value=selected_id)
        with col_m2:
            st.metric(label="Log Sequence", value=day_number_str)
        with col_m3:
            submitted_by = st.text_input("Technician / Manager Name", value="Field Tech", key="tech_input")

        st.markdown("---")
        st.subheader("Task Entry Form")

        # Controls
        ctrl1, ctrl2 = st.columns([1, 1])
        with ctrl1:
            st.button("🗑️ Clear All", on_click=clear_all_tasks)
        with ctrl2:
            st.button("🔄 Reset to 5 Slots", on_click=reset_tasks_to_5)

        st.markdown("<br>", unsafe_allow_html=True)

        # Dynamic Headers
        if len(st.session_state.tasks_list) > 0:
            h1, h2, h3, h4 = st.columns([1, 6, 3, 1])
            h1.markdown("<p class='table-header'>DONE</p>", unsafe_allow_html=True)
            h2.markdown("<p class='table-header'>TASK DESCRIPTION</p>", unsafe_allow_html=True)
            h3.markdown("<p class='table-header'>CATEGORY / TAG</p>", unsafe_allow_html=True)
            h4.markdown("<p class='table-header'>ACTION</p>", unsafe_allow_html=True)

        # Dynamic Input Rows
        for idx, task in enumerate(st.session_state.tasks_list):
            c_done, c_text, c_cat, c_del = st.columns([1, 6, 3, 1])
            
            with c_done:
                task["done"] = st.checkbox("", value=task["done"], key=f"chk_{idx}")
            
            with c_text:
                task["text"] = st.text_input("", value=task["text"], placeholder="Enter task description...", key=f"txt_{idx}", label_visibility="collapsed")
                
            with c_cat:
                cat_index = CATEGORIES.index(task["category"]) if task["category"] in CATEGORIES else 0
                task["category"] = st.selectbox("", CATEGORIES, index=cat_index, key=f"cat_{idx}", label_visibility="collapsed")
                
            with c_del:
                if st.button("❌", key=f"del_{idx}"):
                    remove_task_row(idx)
                    st.rerun()

        st.button("➕ Add Task Row", on_click=add_task_row)

        st.markdown("---")
        next_day_plan = st.text_area("Next Day Planned Tasks", placeholder="State tasks planned for tomorrow...")

        if st.button("💾 Submit & Log Tasks", type="primary", use_container_width=True):
            valid_tasks = [t for t in st.session_state.tasks_list if t["text"].strip()]

            if not valid_tasks:
                st.error("Please enter at least one task description before saving.")
            elif not submitted_by.strip():
                st.error("Please provide the Technician Name.")
            else:
                formatted_entries = []
                categories_set = set()

                for i, t in enumerate(valid_tasks, 1):
                    status = "[DONE]" if t["done"] else "[PENDING]"
                    formatted_entries.append(f"{i}. {status} {t['text'].strip()} ({t['category']})")
                    categories_set.add(t["category"])

                tasks_summary = "\n".join(formatted_entries)
                categories_summary = ", ".join(list(categories_set))
                log_id = generate_log_id()

                new_log_row = [
                    log_id,
                    selected_id,
                    day_number_str,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d"),
                    categories_summary,
                    tasks_summary,
                    next_day_plan,
                    submitted_by
                ]

                try:
                    append_to_sheet("Daily_Logs", new_log_row)
                    st.success(f"Log **{log_id}** saved to Google Sheets successfully!")
                    reset_tasks_to_5()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save log: {e}")

        # Activity Log History
        st.markdown("---")
        st.subheader("🕒 Log History for Selected Installation")
        if not df_logs.empty and selected_id:
            filtered_logs = df_logs[df_logs["installation_id"] == selected_id]
            if not filtered_logs.empty:
                for _, log in filtered_logs.iterrows():
                    with st.expander(f"📄 Log {log.get('log_id', 'N/A')} - {log.get('logged_timestamp', '')}"):
                        st.write(f"**Submitted By:** {log.get('submitted_by', 'N/A')}")
                        st.write(f"**Categories:** {log.get('product_worked_on', 'N/A')}")
                        st.text(f"Tasks:\n{log.get('tasks_completed', '')}")
                        if log.get('next_day_planned_tasks'):
                            st.info(f"**Planned Next Steps:** {log['next_day_planned_tasks']}")
            else:
                st.caption("No daily logs recorded for this project yet.")
