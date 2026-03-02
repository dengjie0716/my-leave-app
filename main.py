import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import calendar

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 核心加载逻辑 ---
def load_data():
    all_files = os.listdir(".")
    s_target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    t_target = next((f for f in all_files if "tracking" in f.lower() and f.endswith(".csv")), None)
    
    df, track = None, pd.DataFrame(columns=["Date", "Name", "Type", "Days"])
    
    if s_target:
        try:
            df_raw = pd.read_csv(s_target, header=None)
            header_idx = 0
            for i, row in df_raw.iterrows():
                if row.astype(str).str.contains("Employee", case=False).any():
                    header_idx = i; break
            df = pd.read_csv(s_target, skiprows=header_idx + 1, header=None)
            cols = ["Employee Name", "Employee#", "Vacation_Paid", "Vacation_Used", "Vacation_Remaining", "Sick_Paid", "Sick_Used", "Sick_Remaining", "Personal_Paid", "Personal_Used", "Personal_Remaining", "Jury_Used", "Maternity_Used", "Unpaid_Leave", "Placeholder", "Total_Days"]
            df.columns = [cols[i] if i < len(cols) else f"Extra_{i}" for i in range(len(df.columns))]
            df = df[df.iloc[:, 0].notna() & (~df.iloc[:, 0].astype(str).str.contains("Employee", case=False))]
            for c in df.columns[2:]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        except: pass
    if t_target:
        try:
            track = pd.read_csv(t_target)
            track['Date'] = pd.to_datetime(track['Date']).dt.strftime('%Y-%m-%d')
        except: pass
    return df, track

if 'df' not in st.session_state:
    st.session_state.df, st.session_state.tracking = load_data()

# --- 2. 顶部强提醒保存区域 ---
st.title("📊 假期管理系统 (全能看板)")

with st.expander("🚨 保存数据至 GitHub (操作完必点)", expanded=True):
    st.warning("由于系统限制，网页修改后不会自动保存。请下载以下文件并上传覆盖 GitHub 仓库：")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 1. 下载 Summary (余额)", st.session_state.df.to_csv(index=False).encode('utf-8-sig'), "summary.csv", "text/csv", use_container_width=True, type="primary")
    with c2:
        st.download_button("📥 2. 下载 Tracking (日历记录)", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv", "text/csv", use_container_width=True, type="primary")

st.divider()

# --- 3. 页面主体：单页纵向排版 ---
if st.session_state.df is not None:
    # 第一块：余额汇总
    st.header("1️⃣ 余额汇总 (Balance Overview)")
    allow_edit = st.checkbox("🔓 开启手动编辑模式")
    if allow_edit:
        edited = st.data_editor(st.session_state.df, use_container_width=True, key="main_editor")
        if st.button("💾 确认并保存修改"):
            st.session_state.df = edited; st.rerun()
    else:
        st.dataframe(st.session_state.df, use_container_width=True)

    st.divider()

    # 第二块：日历概览
    st.header("2️⃣ 月度日历视图 (Calendar Overview)")
    track = st.session_state.tracking
    if not track.empty:
        track['Date'] = pd.to_datetime(track['Date'])
        # 默认显示当前月份
        now = datetime.now()
        months = sorted(track['Date'].dt.strftime('%Y-%m').unique(), reverse=True)
        sel_m = st.selectbox("📅 切换月份查看", months if months else [now.strftime('%Y-%m')])
        y, m = map(int, sel_m.split('-'))
        cal = calendar.monthcalendar(y, m)
        
        # 绘制日历
        cols = st.columns(7)
        for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]): cols[i].markdown(f"**{d}**")
        m_data = track[track['Date'].dt.strftime('%Y-%m') == sel_m]
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    curr = f"{y}-{m:02d}-{day:02d}"
                    recs = m_data[m_data['Date'].dt.strftime('%Y-%m-%d') == curr]
                    box = f"**{day}**"
                    for _, r in recs.iterrows():
                        clr = "orange" if r['Type'] == "Maternity" else ("red" if r['Type'] == "Sick" else "blue")
                        box += f"\n\n:{clr}[{r['Name']}]"
                    cols[i].markdown(box)
            st.divider()
    else:
        st.info("目前没有请假记录，日历是空的。录入请假后会自动生成。")

    st.divider()

    # 第三块：详细记录
    st.header("3️⃣ 历史记录详情 (History)")
    st.dataframe(st.session_state.tracking, use_container_width=True)

    # --- 4. 侧边栏：录入 ---
    with st.sidebar:
        st.header("📝 录入请假")
        df = st.session_state.df
        with st.form("leave_form"):
            name = st.selectbox("选择员工", sorted(df.iloc[:, 0].unique()))
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            s_d, e_d = st.date_input("开始日期"), st.date_input("结束日期")
            m_days = st.number_input("手动天数", 0.0, 100.0, 1.0, 0.5)
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            if st.form_submit_button("🚀 提交"):
                idx = df.index[df.iloc[:, 0] == name][0]
                val = m_days if mode == "请假 (扣除)" else -m_days
                
                # 余额逻辑
                df.loc[idx, "Total_Days"] += val
                mapping = {"Sick":"Sick_Remaining","Personal":"Personal_Remaining","Jury":"Jury_Used","Maternity":"Maternity_Used","Unpaid":"Unpaid_Leave"}
                if tp == "Vacation":
                    p_rem, v_rem = "Personal_Remaining", "Vacation_Remaining"
                    p_used, v_used = "Personal_Used", "Vacation_Used"
                    curr_p = df.loc[idx, p_rem]
                    p_deduct = min(curr_p, val) if val > 0 else val
                    rest = val - p_deduct
                    df.loc[idx, p_rem] -= p_deduct; df.loc[idx, p_used] += p_deduct
                    df.loc[idx, v_rem] -= rest; df.loc[idx, v_used] += rest
                elif tp in mapping:
                    t_col = mapping[tp]
                    if "Remaining" in t_col:
                        df.loc[idx, t_col] -= val
                        u_col = t_col.replace("Remaining", "Used")
                        df.loc[idx, u_col] += val
                    else: df.loc[idx, t_col] += val
                
                if mode == "请假 (扣除)":
                    delta = (e_d - s_d).days + 1
                    new_rows = pd.DataFrame([((s_d + timedelta(days=i)).strftime("%Y-%m-%d"), name, tp, 1.0) for i in range(delta)], columns=["Date", "Name", "Type", "Days"])
                    st.session_state.tracking = pd.concat([st.session_state.tracking, new_rows], ignore_index=True)
                
                st.session_state.df = df
                st.rerun()
