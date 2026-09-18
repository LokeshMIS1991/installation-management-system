import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import string

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Task Logger Pro",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

SPREADSHEET_ID = "19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s"
CATEGORIES = ['General', 'Work', 'Personal', 'Urgent', 'Meeting', 'Development', 'Design']

# Custom CSS to mimic the HTML Task Logger Interface closely
st.markdown("""
    <style>
    /* Background and Layout Styles */
    .main {
        background-color: #F8FAFC;
    }
    .stAppHeader {
        display: none;
    }
    
    /* Custom Card Styling */
    .task-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    }
    
    /* Table Header styling */
    .table-header {
        font-size: 11px;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    
    /* Inputs Styling */
    div[data-baseweb="input"] {
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] {
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Google Sheets Authentication & Helper Functions
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
    return client.open_by_key(SPREADSHEET_ID).worksheet(worksheet_name)

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
        st.error(f"Error reading '{sheet_name}': {e}")
        return pd.DataFrame()

def append_to_sheet(sheet_name, row_data):
    sheet = get_worksheet(sheet_name)
    sheet.append_row(row_data)

def generate_log_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    return f"LOG-{year}-{''.join(random.choices(chars, k=5))}"

# ---------------------------------------------------------
# 3. Dynamic Session State Management
# ---------------------------------------------------------
if "tasks_list" not in st.session_state:
    st.session_state.tasks_list = [
        {"done": False, "text": "", "category": "General"} for _ in range(5)
    ]

# Helper handlers to alter task state dynamically
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
# 4. Header Bar
# ---------------------------------------------------------
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("📋 Task Logger")
    st.caption("Quickly draft & log daily activities")

with header_col2:
    current_date = datetime.now().strftime("%a, %b %d, %Y")
    st.info(f"📅 **{current_date}**")

# ---------------------------------------------------------
# 5. Installation Project Selection
# ---------------------------------------------------------
st.subheader("1. Select Installation Project")
df_inst = read_sheet("Installations")
df_logs = read_sheet("Daily_Logs")

selected_id = None
if df_inst.empty:
    st.warning("⚠️ No records found in the 'Installations' sheet. Please verify access rights.")
else:
    # Build readable options list dropdown
    options = []
    for _, row in df_inst.iterrows():
        inst_id = row.get("installation_id", "N/A")
        address = row.get("site_address", "No Address")
        options.append(f"{inst_id} | {address[:35]}")
    
    selected_option = st.selectbox("Choose Installation ID", options)
    if selected_option:
        selected_id = selected_option.split(" | ")[0]

if selected_id:
    # Calculate automatic day label based on history
    existing_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()
    day_number_str = f"Day {len(existing_logs) + 1}"

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        st.metric(label="Selected Project", value=selected_id)
    with col_meta2:
        st.metric(label="Log Sequence", value=day_number_str)
    with col_meta3:
        submitted_by = st.text_input("Technician Name", value="Field Tech", key="tech_name_input")

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. Task Entry Interface (Matching HTML Form Layout)
    # ---------------------------------------------------------
    st.subheader("2. Task Entry")

    # Top Control Buttons
    ctrl_col1, ctrl_col2 = st.columns([1, 1])
    with ctrl_col1:
        st.button("🗑️ Clear All", on_click=clear_all_tasks)
    with ctrl_col2:
        st.button("🔄 Reset to 5", on_click=reset_tasks_to_5)

    st.markdown("<br>", unsafe_allow_html=True)

    # Column Headers
    if len(st.session_state.tasks_list) > 0:
        h1, h2, h3, h4 = st.columns([1, 6, 3, 1])
        h1.markdown("<p class='table-header'>DONE</p>", unsafe_allow_html=True)
        h2.markdown("<p class='table-header'>TASK DESCRIPTION</p>", unsafe_allow_html=True)
        h3.markdown("<p class='table-header'>CATEGORY / TAG</p>", unsafe_allow_html=True)
        h4.markdown("<p class='table-header'>ACTION</p>", unsafe_allow_html=True)

    # Render Task Rows
    for idx, task in enumerate(st.session_state.tasks_list):
        c_done, c_text, c_cat, c_del = st.columns([1, 6, 3, 1])
        
        with c_done:
            task["done"] = st.checkbox("", value=task["done"], key=f"chk_{idx}")
        
        with c_text:
            task["text"] = st.text_input(
                "", 
                value=task["text"], 
                placeholder="Enter task description...", 
                key=f"txt_{idx}",
                label_visibility="collapsed"
            )
            
        with c_cat:
            cat_index = CATEGORIES.index(task["category"]) if task["category"] in CATEGORIES else 0
            task["category"] = st.selectbox(
                "", 
                CATEGORIES, 
                index=cat_index, 
                key=f"cat_{idx}",
                label_visibility="collapsed"
            )
            
        with c_del:
            if st.button("❌", key=f"del_{idx}"):
                remove_task_row(idx)
                st.rerun()

    # Dynamic Row Action
    st.button("➕ Add Another Task", on_click=add_task_row, type="secondary")

    st.markdown("---")
    
    # Plans for Next Day
    next_day_plan = st.text_area("Next Day Planned Tasks", placeholder="Briefly state what needs to be done tomorrow...")

    # Log Tasks Button
    if st.button("💾 Log Tasks", type="primary", use_container_width=True):
        # Validate task descriptions
        valid_tasks = [t for t in st.session_state.tasks_list if t["text"].strip()]

        if not valid_tasks:
            st.error("Please enter at least one task description before logging.")
        elif not submitted_by.strip():
            st.error("Please provide the Technician Name.")
        else:
            # Format combined logged tasks text
            formatted_entries = []
            categories_set = set()

            for i, t in enumerate(valid_tasks, 1):
                status = "[DONE]" if t["done"] else "[PENDING]"
                formatted_entries.append(f"{i}. {status} {t['text'].strip()} ({t['category']})")
                categories_set.add(t["category"])

            tasks_text_summary = "\n".join(formatted_entries)
            categories_summary = ", ".join(list(categories_set))
            
            log_id = generate_log_id()
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_date_str = datetime.now().strftime("%Y-%m-%d")

            # Match exact Google Sheet row structure
            new_log_row = [
                log_id,
                selected_id,
                day_number_str,
                timestamp_str,
                log_date_str,
                categories_summary,
                tasks_text_summary,
                next_day_plan,
                submitted_by
            ]

            try:
                append_to_sheet("Daily_Logs", new_log_row)
                st.success(f"Log **{log_id}** saved successfully with {len(valid_tasks)} task entries!")
                reset_tasks_to_5()
            except Exception as e:
                st.error(f"Failed to submit task log: {e}")

# ---------------------------------------------------------
# 7. Saved Logs History Section
# ---------------------------------------------------------
st.markdown("---")
st.subheader("🕒 Saved Task Logs History")

if not df_logs.empty and selected_id:
    filtered_logs = df_logs[df_logs["installation_id"] == selected_id]
    if not filtered_logs.empty:
        for _, log in filtered_logs.iterrows():
            with st.expander(f"📄 Log {log.get('log_id', 'N/A')} - {log.get('logged_timestamp', '')}"):
                st.write(f"**Submitted By:** {log.get('submitted_by', 'N/A')}")
                st.write(f"**Categories Covered:** {log.get('product_worked_on', 'N/A')}")
                st.text(f"Tasks:\n{log.get('tasks_completed', '')}")
                if log.get('next_day_planned_tasks'):
                    st.info(f"**Next Day Plan:** {log['next_day_planned_tasks']}")
    else:
        st.caption("No task logs recorded for this installation project yet.")
else:
    st.caption("Select an Installation ID above to inspect history.")
