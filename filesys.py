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
    page_title="Task Logger Pro - Sidharth Shutter", 
    page_icon="🏢",
    layout="wide"
)

# Applied Google Sheet ID
SPREADSHEET_ID = "19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s"

# CSS Styling matching the HTML interface
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    .main-header {
        background-color: white;
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #E2E8F0;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    }
    .task-row-container {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Google Sheets Connection Management
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
            return get_empty_default_df(sheet_name)
            
        headers = [str(h).strip().lower() for h in rows[0]]
        data = rows[1:]
        df = pd.DataFrame(data, columns=headers)
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
        return df
    except Exception as e:
        st.error(f"⚠️ Google Sheets Connection Error on tab '{sheet_name}': {e}")
        return get_empty_default_df(sheet_name)

def get_empty_default_df(sheet_name):
    if sheet_name == "Installations":
        return pd.DataFrame(columns=[
            "installation_id", "city_prefix", "site_address", "team_details", 
            "order_created_date", "site_clearance_date", "target_ho_date", "status"
        ])
    elif sheet_name == "Order_Items":
        return pd.DataFrame(columns=["installation_id", "category", "sub_category", "dimensions", "quantity"])
    elif sheet_name == "Daily_Logs":
        return pd.DataFrame(columns=[
            "log_id", "installation_id", "day_number", "logged_timestamp", 
            "logged_date", "product_worked_on", "tasks_completed", 
            "next_day_planned_tasks", "submitted_by"
        ])
    return pd.DataFrame()

def append_to_sheet(sheet_name, row_data):
    try:
        sheet = get_worksheet(sheet_name)
        sheet.append_row(row_data)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Failed to append row to {sheet_name}: {e}")

def generate_log_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    return f"LOG-{year}-{''.join(random.choices(chars, k=5))}"

CATEGORIES = ['General', 'Work', 'Personal', 'Urgent', 'Meeting', 'Development', 'Design']

# Header Bar
st.markdown("""
    <div class="main-header">
        <div>
            <h2 style="margin:0; color:#0F172A;">📋 Task Logger Pro</h2>
            <p style="margin:0; font-size:13px; color:#64748B;">Quickly draft & log daily activities directly to Google Sheets</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Navigation Menu
menu = st.sidebar.radio("Navigation", ["Log Daily Tasks", "View Saved Logs & Master Data"])

if menu == "Log Daily Tasks":
    df_inst = read_sheet("Installations")
    df_logs = read_sheet("Daily_Logs")

    st.subheader("1. Select Installation Project")
    
    selected_id = None
    if df_inst.empty:
        st.warning("No installation project records found in Google Sheets.")
    else:
        options_list = [f"{row['installation_id']} | {row['site_address'][:30]}..." for _, row in df_inst.iterrows()]
        selected_option = st.selectbox("Choose Installation ID:", options_list)
        if selected_option:
            selected_id = selected_option.split(" | ")[0]

    if selected_id:
        inst_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]
        existing_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()
        day_label = f"Day {len(existing_logs) + 1}"

        st.info(f"**Project ID:** `{selected_id}` | **Day:** `{day_label}` | **Team:** `{inst_info['team_details']}`")

        col_tech, col_date = st.columns(2)
        with col_tech:
            submitted_by = st.text_input("Technician Name *", value=inst_info['team_details'].split('+')[0].strip())
        with col_date:
            log_date = st.date_input("Log Date", value=datetime.now())

        st.divider()

        # Initialize Dynamic Task Session State
        if "num_tasks" not in st.session_state:
            st.session_state.num_tasks = 5

        col_head1, col_head2 = st.columns([3, 1])
        with col_head1:
            st.subheader("2. Dynamic Task Logger")
        with col_head2:
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("➕ Add Row"):
                    st.session_state.num_tasks += 1
                    st.rerun()
            with c_btn2:
                if st.button("🔄 Reset 5"):
                    st.session_state.num_tasks = 5
                    st.rerun()

        # Render Task Input Rows
        task_entries = []
        
        # Grid Header
        hdr1, hdr2, hdr3 = st.columns([1, 6, 4])
        hdr1.caption("**DONE**")
        hdr2.caption("**TASK DESCRIPTION**")
        hdr3.caption("**CATEGORY / TAG**")

        for i in range(st.session_state.num_tasks):
            col_done, col_desc, col_cat = st.columns([1, 6, 4])
            
            with col_done:
                is_done = st.checkbox("", key=f"done_{i}")
            with col_desc:
                task_desc = st.text_input("", placeholder=f"Enter task description {i+1}...", key=f"desc_{i}", label_visibility="collapsed")
            with col_cat:
                category = st.selectbox("", CATEGORIES, key=f"cat_{i}", label_visibility="collapsed")

            if task_desc.strip():
                task_entries.append({
                    "done": is_done,
                    "desc": task_desc.strip(),
                    "category": category
                })

        st.divider()
        next_day_plan = st.text_area("Next Day Planned Tasks", placeholder="Describe tomorrow's plan...")

        if st.button("💾 Log Tasks to Google Sheet", type="primary", use_container_width=True):
            if not task_entries:
                st.error("Please enter at least one task description before logging.")
            elif not submitted_by.strip():
                st.error("Please specify the Technician Name.")
            else:
                # Format tasks into log structure
                formatted_tasks = []
                categories_used = set()
                
                for idx, t in enumerate(task_entries, 1):
                    status_icon = "✅ [DONE]" if t["done"] else "⏳ [PENDING]"
                    formatted_tasks.append(f"{idx}. {status_icon} {t['desc']} ({t['category']})")
                    categories_used.add(t['category'])

                combined_tasks_str = "\n".join(formatted_tasks)
                product_summary = ", ".join(list(categories_used))
                log_id = generate_log_id()
                auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                log_row = [
                    log_id, selected_id, day_label, auto_log_time, str(log_date), 
                    product_summary, combined_tasks_str, next_day_plan, submitted_by
                ]

                append_to_sheet("Daily_Logs", log_row)
                st.success(f"Successfully recorded {len(task_entries)} tasks under Log ID `{log_id}`!")

elif menu == "View Saved Logs & Master Data":
    st.header("📂 Saved Task Logs")
    df_logs = read_sheet("Daily_Logs")
    
    if df_logs.empty:
        st.info("No task logs recorded yet.")
    else:
        st.dataframe(df_logs, use_container_width=True)
