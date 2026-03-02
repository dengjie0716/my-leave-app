import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import calendar

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 数据加载（增强稳定性版） ---
def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: return None
    try:
        # 寻找表头行
        df_raw = pd.read_csv(target, header=None, low_memory=False)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains("Employee", case=False).any():
                header_idx = i
                break
        
        # 读取数据
        df = pd.read_csv(target, header=header_idx)
        
        # --- 强制定义标准 16 列 ---
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",
            "Sick_Paid", "Sick_Used", "Sick_Remaining",
            "Personal_Paid", "Personal_Used", "Personal_Remaining",
            "Jury_Used", "Maternity_Used", "Unpaid_Leave", "Placeholder", "Total_Days"
        ]
        
        # 核心修复：根据实际列数强制更名，确保 'Employee Name' 永远在第一列
        actual_len = len(df.columns)
        new_names = []
        for i in range(actual_len):
            if i < len(clean_cols):
                new_names.append(clean_cols[i])
            else:
                new_names.append(f"Extra_{i}")
        df.columns = new_names

        # 清理行：去掉包含 "Employee" 的重复表头行和空行
