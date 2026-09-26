import io
import pandas as pd


def generate_excel_download(df: pd.DataFrame, filename="report.xlsx") -> bytes:
    """Generates openpyxl Excel bytes buffer for downloading dataframes."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()
