import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="假期管理与日历系统", layout="wide")

# 文件定义
SUMMARY_FILE = "summary.csv"
TRACKING_FILE = "tracking.csv"

# --- 1. 数据加载函数 ---
def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: return None
    try:
        preview = pd.read_csv(target, header=None, nrows=10)
        header_idx = 0
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 你的精准列定义
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",
            "Sick_Paid", "Sick_Used", "Sick_Remaining",
            "Personal_Paid", "Personal_Used", "Personal_Remaining",
            "Jury_Used", "Maternity_Used", "Unpaid_Leave", "Placeholder", "Total_Days"
        ]
        df = pd.read_csv(target, header=header_idx)
        df.columns = clean_cols[:len(df.columns)]
        df = df[df["Employee Name"].astype(str) != "Employee Name"]
        df = df[df["Employee Name"].notna()]
        return df
    except: return None

def load_tracking():
    if os.path.exists(TRACKING_FILE):
        return pd.read_csv(TRACKING_FILE)
    return pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

# --- 2. 初始化状态 ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = load_tracking()

# --- 3. 侧边栏：录入功能 ---
with st.sidebar:
    st.header("📝 录入请假")
    with st.form("leave_form"):
        names = sorted([n for n in st.session_state.df['Employee Name'].unique()])
        selected_name = st.selectbox("选择员工", names)
        tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
        
        # 新增：日期选择
        leave_date = st.date_input("请假日期", datetime.now())
        days = st.number_input("天数", 0.5, 30.0, 1.0, 0.5)
        
        mode = st.radio("操作类型", ["员工请假 (扣除)", "录入修正 (补回)"])
        submit = st.form_submit_button("确认提交")

        if submit:
            df = st.session_state.df
            idx = df.index[df['Employee Name'] == selected_name][0]
            calc_days = days if mode == "员工请假 (扣除)" else -days
            
            # --- 余额抵扣逻辑 ---
            if tp == "Vacation":
                p_rem, p_used = "Personal_Remaining", "Personal_Used"
                curr_p = pd.to_numeric(df.loc[idx, p_rem], errors='coerce') or 0
                p_deduct = min(curr_p, calc_days) if calc_days > 0 else calc_days
                rem_to_calc = calc_days - p_deduct
                df.loc[idx, p_rem] = curr_p - p_deduct
                df.loc[idx, p_used] = (pd.to_numeric(df.loc[idx, p_used], errors='coerce') or 0) + p_deduct
                v_rem, v_used = "Vacation_Remaining", "Vacation_Used"
                df.loc[idx, v_rem] = (pd.to_numeric(df.loc[idx, v_rem], errors='coerce') or 0) - rem_to_calc
                df.loc[idx, v_used] = (pd.to_numeric(df.loc[idx, v_used], errors='coerce') or 0) + rem_to_calc
            else:
                target_map = {"Sick":"Sick_Remaining","Personal":"Personal_Remaining","Jury":"Jury_Used","Maternity":"Maternity_Used","Unpaid":"Unpaid_Leave"}
                t_col = target_map[tp]
                curr_val = pd.to_numeric(df.loc[idx, t_col], errors='coerce') or 0
                if "Remaining" in t_col:
                    df.loc[idx, t_col] = curr_val - calc_days
                    u_col = t_col.replace("Remaining", "Used")
                    df.loc[idx, u_col] = (pd.to_numeric(df.loc[idx, u_col], errors='coerce') or 0) + calc_days
                else:
                    df.loc[idx, t_col] = curr_val + calc_days

            # --- Tracking 记录逻辑 ---
            if mode == "员工请假 (扣除)":
                new_record = pd.DataFrame([[leave_date.strftime("%Y-%m-%d"), selected_name, tp, days]], columns=["Date", "Name", "Type", "Days"])
                st.session_state.tracking = pd.concat([st.session_state.tracking, new_record], ignore_index=True)
            
            st.session_state.df = df
            st.success("✅ 录入成功并已加入 Tracking")

# --- 4. 主页面：多模式切换 ---
tab1, tab2, tab3 = st.tabs(["📊 余额汇总 (Summary)", "📅 日历模式 (Calendar)", "📜 历史记录 (Tracking)"])

with tab1:
    st.dataframe(st.session_state.df, use_container_width=True)
    st.download_button("📥 下载最新 Summary CSV", st.session_state.df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

with tab2:
    st.header("📅 请假分布日历")
    track_df = st.session_state.tracking
    if not track_df.empty:
        # 简单的日历列表视图，按月份筛选
        track_df['Date'] = pd.to_datetime(track_df['Date'])
        month = st.selectbox("选择月份", sorted(track_df['Date'].dt.strftime('%Y-%m').unique(), reverse=True))
        month_data = track_df[track_df['Date'].dt.strftime('%Y-%m') == month]
        
        # 这里的展示方式：使用内置的 chart 或 table 来模拟
        st.write(f"### {month} 请假概览")
        for d in sorted(month_data['Date'].unique()):
            day_str = pd.to_datetime(d).strftime('%m-%d (%a)')
            day_records = month_data[month_data['Date'] == d]
            people = ", ".join([f"{r['Name']} ({r['Type']})" for _, r in day_records.iterrows()])
            st.write(f"**{day_str}**: {people}")
    else:
        st.info("暂无 Tracking 数据，请开始录入。")

with tab3:
    st.header("📜 完整 Tracking 记录")
    st.dataframe(st.session_state.tracking, use_container_width=True)
    st.download_button("📥 下载 Tracking CSV", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")
