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
    # 增加健壮性：检查文件是否存在且是否有内容
    if os.path.exists(TRACKING_FILE):
        try:
            t_df = pd.read_csv(TRACKING_FILE)
            if not t_df.empty and "Date" in t_df.columns:
                return t_df
        except:
            pass
    # 如果文件有问题，返回带正确列名的空表
    return pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

# --- 2. 初始化状态 ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = load_tracking()

# --- 3. 侧边栏：录入功能 ---
with st.sidebar:
    st.header("📝 录入请假")
    if st.session_state.df is not None:
        with st.form("leave_form"):
            names = sorted([n for n in st.session_state.df['Employee Name'].unique() if str(n) != 'nan'])
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            
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
                st.success(f"✅ {selected_name} 录入成功！")
    else:
        st.error("无法加载 Summary 数据，请检查仓库中的 CSV。")

# --- 4. 主页面 ---
tab1, tab2, tab3 = st.tabs(["📊 余额汇总 (Summary)", "📅 日历模式 (Calendar)", "📜 历史记录 (Tracking)"])

with tab1:
    if st.session_state.df is not None:
        st.dataframe(st.session_state.df, use_container_width=True)
        st.download_button("📥 下载最新 Summary CSV", st.session_state.df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

with tab2:
    st.header("📅 请假分布日历预览")
    track_df = st.session_state.tracking
    if not track_df.empty and "Date" in track_df.columns:
        track_df['Date'] = pd.to_datetime(track_df['Date'])
        # 提取月份进行筛选
        months = sorted(track_df['Date'].dt.strftime('%Y-%m').unique(), reverse=True)
        sel_month = st.selectbox("选择月份", months)
        
        month_data = track_df[track_df['Date'].dt.strftime('%Y-%m') == sel_month].sort_values("Date")
        
        if not month_data.empty:
            for d, group in month_data.groupby(month_data['Date'].dt.date):
                people_list = [f"{r['Name']} ({r['Type']} {r['Days']}天)" for _, r in group.iterrows()]
                st.write(f"🏷️ **{d.strftime('%m-%d %A')}** : {', '.join(people_list)}")
        else:
            st.write("该月暂无记录")
    else:
        st.info("暂无有效 Tracking 数据。请在侧边栏录入请假。")

with tab3:
    st.header("📜 完整 Tracking 记录")
    st.dataframe(st.session_state.tracking, use_container_width=True)
    st.download_button("📥 下载 Tracking CSV", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")
