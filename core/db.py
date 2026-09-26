import io
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_credentials():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)


@st.cache_resource
def get_gspread_client():
    creds = get_credentials()
    return gspread.authorize(creds)


@st.cache_resource
def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def upload_file_to_drive(uploaded_file, file_name):
    try:
        drive_folder_id = st.secrets.get("drive_folder_id", "0ADjIFMwZGB62Uk9PVA")
        service = get_drive_service()
        file_metadata = {
            "name": file_name,
            "parents": [drive_folder_id],
        }
        media = MediaIoBaseUpload(
            io.BytesIO(uploaded_file.getvalue()),
            mimetype=uploaded_file.type,
            resumable=True,
        )
        file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )
        file_id = file.get("id")
        user_permission = {"type": "anyone", "role": "reader"}
        service.permissions().create(
            fileId=file_id,
            body=user_permission,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        return file.get("webViewLink", "")
    except Exception as e:
        st.error(f"Error uploading image to Google Drive: {e}")
        return "Upload Failed"


def get_workbook():
    client = get_gspread_client()
    sheet_url = st.secrets.get(
        "spreadsheet_url",
        "https://docs.google.com/spreadsheets/d/19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s/edit",
    )
    return client.open_by_url(sheet_url)


@st.cache_data(ttl=60)
def read_sheet(sheet_name: str) -> pd.DataFrame:
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Redact government identity columns for privacy compliance
        if sheet_name == "Workers_Master" and "aadhaar_no" in df.columns:
            df["aadhaar_no"] = "[Redacted Identity]"

        return df
    except Exception as e:
        print(f"DEBUG SHEET ERROR [{sheet_name}]: {e}")
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
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error writing to tab '{sheet_name}': {e}")


def update_sheet_row(
    sheet_name: str, key_col: str, key_val: str, update_dict: dict
) -> bool:
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
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error updating tab '{sheet_name}': {e}")
        return False
