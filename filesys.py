import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import string

# ----------------------------------- ----------------------
# 1. Configuration & Page Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sidharth Shutter - Installation Management",
    page_icon="🏗️",
    layout="wide"
)

# Spreadsheet Configuration
SPREADSHEET_ID = "19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s"
SPREADSHEET_NAME = "Installation_Schedules"

CATEGORIES = ['General', 'Work', 'Personal', 'Urgent', 'Meeting', 'Development', 'Design']

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
# 2. Resilient Google Sheets Authentication
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
        # Dual-fallback approach: Try Sheet ID first, fallback to Sheet Name
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
# 4. Main App Interface
# ---------------------------------------------------------
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("🏭 Sidharth Shutter & Automation")
    st.caption("Installation Management System & Daily Task Logger")

with header_col2:
    st.info(f"📅 **{datetime.now().strftime('%a, %b %d, %Y')}**")

st.markdown("---")

# ---------------------------------------------------------
# 5. Project Selection & Data Binding
# ---------------------------------------------------------
st.subheader("1. Select Installation Record")

df_inst = read_sheet("Installations")
df_logs = read_sheet("Daily_Logs")

selected_id = None

if df_inst.empty:
    st.warning("⚠️ No records loaded from the 'Installations' sheet. Verify sheet sharing settings with your service account.")
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
    # Filter logs to calculate exact log sequence
    existing_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()
    day_number_str = f"Day {len(existing_logs) + 1}"

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="Active Project ID", value=selected_id)
    with col_m2:
        st.metric(label="Log Sequence", value=day_number_str)
    with col_m3:
        submitted_by = st.text_input("Technician / Manager Name", value="Field Engineer", key="tech_input")

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. Task Entry Form
    # ---------------------------------------------------------
    st.subheader("2. Task Logger Entry")

    # Form Control Action Buttons
    ctrl1, ctrl2 = st.columns([1, 1])
    with ctrl1:
        st.button("🗑️ Clear All Rows", on_click=clear_all_tasks)
    with ctrl2:
        st.button("🔄 Reset Slots (5)", on_click=reset_tasks_to_5)

    st.markdown("<br>", unsafe_allow_html=True)

    # Dynamic Header Row
    if len(st.session_state.tasks_list) > 0:
        h1, h2, h3, h4 = st.columns([1, 6, 3, 1])
        h1.markdown("<p class='table-header'>DONE</p>", unsafe_allow_html=True)
        h2.markdown("<p class='table-header'>TASK DESCRIPTION</p>", unsafe_allow_html=True)
        h3.markdown("<p class='table-header'>CATEGORY / TAG</p>", unsafe_allow_html=True)
        h4.markdown("<p class='table-header'>ACTION</p>", unsafe_allow_html=True)

    # Render Task Input Rows
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

    st.button("➕ Add Task Row", on_click=add_task_row, type="secondary")

    st.markdown("---")
    next_day_plan = st.text_area("Next Day Planned Tasks", placeholder="State tasks planned for tomorrow...")

    # Submission Action
    if st.button("💾 Submit & Save Task Log", type="primary", use_container_width=True):
        valid_tasks = [t for t in st.session_state.tasks_list if t["text"].strip()]

        if not valid_tasks:
            st.error("Please fill in at least one task description before saving.")
        elif not submitted_by.strip():
            st.error("Please enter the Technician / Manager Name.")
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
                st.success(f"Log **{log_id}** recorded to Google Sheet successfully!")
                reset_tasks_to_5()
            except Exception as e:
                st.error(f"Failed to record daily log: {e}")

# ---------------------------------------------------------
# 7. Recorded History Section
# ---------------------------------------------------------
st.markdown("---")
st.subheader("🕒 Daily Log Activity")

if not df_logs.empty and selected_id:
    filtered_logs = df_logs[df_logs["installation_id"] == selected_id]
    if not filtered_logs.empty:
        for _, log in filtered_logs.iterrows():
            with st.expander(f"📄 Log {log.get('log_id', 'N/A')} - {log.get('logged_timestamp', '')}"):
                st.write(f"**Technician:** {log.get('submitted_by', 'N/A')}")
                st.write(f"**Categories:** {log.get('product_worked_on', 'N/A')}")
                st.text(f"Tasks:\n{log.get('tasks_completed', '')}")
                if log.get('next_day_planned_tasks'):
                    st.info(f"**Planned Next Steps:** {log['next_day_planned_tasks']}")
    else:
        st.caption("No daily logs recorded for this project yet.")
