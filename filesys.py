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
    page_title="Task Logger Pro - Sidharth Shutter & Automation",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

SPREADSHEET_ID = "19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s"
SPREADSHEET_NAME = "Installation_Schedules"

CATEGORIES = ['General', 'Work', 'Personal', 'Urgent', 'Meeting', 'Development', 'Design']
STATUS_OPTIONS = ['Pending', 'In Progress', 'Completed', 'On Hold']

# Custom Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', sans-serif;
    }
    .task-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 1rem;
        padding: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
        margin-bottom: 1.5rem;
    }
    .table-header {
        font-size: 0.75rem;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    div[data-baseweb="input"] { border-radius: 0.5rem !important; }
    div[data-baseweb="select"] { border-radius: 0.5rem !important; }
    .badge-primary {
        background-color: #EEF2FF;
        color: #4F46E5;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
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
        st.error(f"Error reading worksheet '{sheet_name}': {e}")
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
# 3. Dynamic Task State Management
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
# 4. App Navigation & Header
# ---------------------------------------------------------
st.sidebar.title("🏢 Navigation")
page = st.sidebar.radio(
    "Select Module:",
    ["Page 1: Installation Management", "Page 2: Daily Task Logger"]
)

head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("📋 Task Logger")
    st.caption("Quickly draft & log daily activities • Sidharth Shutter & Automation")

with head_col2:
    st.info(f"📅 **{datetime.now().strftime('%a, %b %d, %Y')}**")

st.markdown("---")

# ---------------------------------------------------------
# PAGE 1: INSTALLATION MANAGEMENT
# ---------------------------------------------------------
if page == "Page 1: Installation Management":
    st.header("🏢 Page 1: Installation Management")
    
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
    
    df_inst = read_sheet("Installations")
    df_logs = read_sheet("Daily_Logs")
    df_items = read_sheet("Order_Items")

    selected_id = None

    # Project Selection
    with st.container():
        st.subheader("Select Active Installation")
        if df_inst.empty:
            st.warning("⚠️ No installation records loaded. Create one on Page 1 first.")
        else:
            options = ["-- Select Installation ID --"]
            for _, row in df_inst.iterrows():
                inst_id = row.get("installation_id", "N/A")
                address = row.get("site_address", "No Address")
                city = row.get("city_prefix", "")
                options.append(f"{inst_id} | {city} - {address[:35]}")
            
            selected_option = st.selectbox("Choose Active Project:", options)
            if selected_option and selected_option != "-- Select Installation ID --":
                selected_id = selected_option.split(" | ")[0]

    # ---------------------------------------------------------
    # Active Installation Display Banner
    # ---------------------------------------------------------
    if selected_id:
        team_name = "N/A"
        if not df_inst.empty and "installation_id" in df_inst.columns:
            match_row = df_inst[df_inst["installation_id"] == selected_id]
            if not match_row.empty and "team_details" in match_row.columns:
                team_name = match_row.iloc[0]["team_details"] or "N/A"

        if not df_logs.empty and "installation_id" in df_logs.columns:
            existing_logs = df_logs[df_logs["installation_id"] == selected_id]
            day_count = len(existing_logs) + 1
        else:
            existing_logs = pd.DataFrame()
            day_count = 1

        day_number_str = f"Day {day_count}"

        st.markdown(
            f"""
            <div style="
                background-color: #EFF6FF; 
                border-left: 5px solid #10B981; 
                padding: 14px 20px; 
                border-radius: 8px; 
                margin: 15px 0px 25px 0px;">
                <span style="font-weight: 700; color: #1E3A8A; font-size: 16px;">Active Installation ID: </span>
                <span style="font-weight: 800; color: #10B981; font-size: 17px; margin-right: 15px;">{selected_id}</span>
                <span style="color: #2563EB; font-weight: 600; font-size: 14px;">(Auto-Calculated: {day_number_str} | Team: {team_name})</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        if not df_items.empty and "installation_id" in df_items.columns:
            site_items = df_items[df_items["installation_id"] == selected_id]
        else:
            site_items = pd.DataFrame()

        if not site_items.empty:
            with st.expander("📦 View Site Items / Equipment List", expanded=False):
                st.dataframe(site_items, use_container_width=True)

        # Task Entry Form Container
        st.markdown('<div class="task-card">', unsafe_allow_html=True)
        
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1])
        with ctrl_col1:
            st.markdown("### Task Entry")
            st.caption("Fill in details, mark completed items, and log them.")
            submitted_by = st.text_input("Technician / Logger Name:", value="Field Engineer", key="tech_name")
            
        with ctrl_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("🗑️ Clear All", on_click=clear_all_tasks, use_container_width=True)
        with ctrl_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("🔄 Reset to 5", on_click=reset_tasks_to_5, use_container_width=True)

        st.markdown("---")

        if len(st.session_state.tasks_list) > 0:
            h1, h2, h3, h4 = st.columns([1, 6, 3, 1])
            h1.markdown("<p class='table-header'>DONE</p>", unsafe_allow_html=True)
            h2.markdown("<p class='table-header'>TASK DESCRIPTION</p>", unsafe_allow_html=True)
            h3.markdown("<p class='table-header'>CATEGORY / TAG</p>", unsafe_allow_html=True)
            h4.markdown("<p class='table-header'>ACTION</p>", unsafe_allow_html=True)

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

        st.markdown("<br>", unsafe_allow_html=True)

        bot_col1, bot_col2, bot_col3 = st.columns([2, 1, 2])
        with bot_col1:
            st.button("➕ Add Another Task", on_click=add_task_row)
        with bot_col2:
            st.markdown(f"**Total:** `{len(st.session_state.tasks_list)}` tasks")
        with bot_col3:
            submit_btn = st.button("💾 Log Tasks", type="primary", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        next_day_plan = st.text_area("Next Day Planned Tasks", placeholder="State tasks planned for tomorrow...")

        if submit_btn:
            valid_tasks = [t for t in st.session_state.tasks_list if t["text"].strip()]

            if not valid_tasks:
                st.error("Please enter at least one task description before logging.")
            elif not submitted_by.strip():
                st.error("Please specify the Technician Name.")
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

        # Saved Task Logs History
        st.markdown("---")
        st.markdown("### 🕒 Saved Task Logs")

        if not df_logs.empty and selected_id and "installation_id" in df_logs.columns:
            filtered_logs = df_logs[df_logs["installation_id"] == selected_id]
            if not filtered_logs.empty:
                st.markdown(f"<span class='badge-primary'>{len(filtered_logs)} Logged Groups</span><br><br>", unsafe_allow_html=True)
                for _, log in filtered_logs.iterrows():
                    with st.expander(f"📄 Log {log.get('log_id', 'N/A')} - {log.get('logged_timestamp', '')}"):
                        st.write(f"**Submitted By:** {log.get('submitted_by', 'N/A')}")
                        st.write(f"**Categories:** {log.get('product_worked_on', 'N/A')}")
                        st.text(f"Tasks:\n{log.get('tasks_completed', '')}")
                        if log.get('next_day_planned_tasks'):
                            st.info(f"**Planned Next Steps:** {log['next_day_planned_tasks']}")
            else:
                st.caption("No daily logs recorded for this project yet.")
    else:
        st.markdown(
            """
            <div style="
                background-color: #FEF2F2; 
                border-left: 5px solid #EF4444; 
                padding: 14px 20px; 
                border-radius: 8px; 
                margin: 15px 0px 25px 0px;">
                <span style="font-weight: 700; color: #991B1B; font-size: 15px;">No ID is selected.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
