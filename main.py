import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import calendar

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 数据加载 ---
def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: return None
    try:
        df_raw = pd.read_csv(target, header=None, low_memory=False)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains("Employee", case=False).any():
                header_idx = i
                break
        
        df = pd.read_csv(target, skiprows=header_idx + 1, header=None)
        
        standard_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",
            "Sick_Paid", "Sick_Used", "Sick_Remaining",
            "Personal_Paid", "Personal_Used", "Personal_Remaining",
            "Jury_Used", "Maternity_Used", "Unpaid_Leave", 
            "Placeholder", "Total_Days"
        ]
        
        actual_len = len(df.columns)
        new_names = [standard_cols[i] if i < len(standard_cols) else f"Extra_{i}" for i in range(actual_len)]
        df.columns = new_names
        df = df[df.iloc[:, 0].notna() & (df.iloc[:, 0].astype(str).str.contains("Employee", case=False) == False)]
        
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

st.title("📊 假期管理系统")

if st.session_state.df is not None:
    df = st.session_state.df
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 月度日历视图", "📜 历史记录"])

    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载 Summary CSV", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    with tab2:
        track = st.session_state.tracking
        if not track.empty:
            track['Date'] = pd.to_datetime(track['Date'])
            all_months = sorted(track['Date'].dt.strftime('%Y-%m').unique(), reverse=True)
            sel_month_str = st.selectbox("选择月份", all_months)
            sel_date = datetime.strptime(sel_month_str, '%Y-%m')
            cal = calendar.monthcalendar(sel_date.year, sel_date.month)
            
            cols = st.columns(7)
            for i, d_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                cols[i].markdown(f"**{d_name}**")

            month_data = track[track['Date'].dt.strftime('%Y-%m') == sel_month_str]
            for week in cal:
                cols = st.columns(7)
                for i, day in enumerate(week):
                    if day != 0:
                        curr_str = f"{sel_date.year}-{sel_date.month:02d}-{day:02d}"
                        day_recs = month_data[month_data['Date'].dt.strftime('%Y-%m-%d') == curr_str]
                        box = f"**{day}**"
                        if not day_recs.empty:
                            for _, r in day_recs.iterrows():
                                color = "orange" if r['Type'] == "Maternity" else ("red" if r['Type'] == "Sick" else "blue")
                                box += f"\n\n:{color}[{r['Name']}]"
                        cols[i].markdown(box)
                st.divider()
        else: st.info("暂无记录。")

    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)

    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("input_form"):
            names = sorted([str(n) for n in df.iloc[:, 0].unique()])
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            start_d = st.date_input("开始日期", datetime.now())
            end_d = st.date_input("结束日期", datetime.now())
            manual_days = st.number_input("手动输入总天数", 0.0, 100.0, 1.0, 0.5)
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            if st.form_submit_button("确认提交"):
                idx = df.index[df.iloc[:, 0] == name][0]
                val = manual_days if mode == "请假 (扣除)" else -manual_days
                
                if tp == "Vacation":
                    p_rem, p_used = "Personal_Remaining", "Personal_Used"
                    v_rem, v_used = "Vacation_Remaining", "Vacation_Used"
                    curr_p = df.loc[idx, p_rem]
                    p_deduct = min(curr_p, val) if val > 0 else val
                    rest = val - p_deduct
                    df.loc[idx, p_rem] -= p_deduct
                    df.loc[idx, p_used] += p_deduct
                    df.loc[idx, v_rem] -= rest
                    df.loc[idx, v_used] += rest
                else:
                    mapping = {"Sick":"Sick_Remaining","Personal":"Personal_Remaining","Jury":"Jury_Used","Maternity":"Maternity_Used","Unpaid":"Unpaid_Leave"}
                    t_col = mapping[tp]
                    if "Remaining" in t_col:
                        df.loc[idx, t_col] -= val
                        u_col = t_col.replace("Remaining", "Used")
                        if u_col in df.columns: df.loc[idx, u_col] += val
                    else:
                        df.loc[idx, t_col] += val

                if mode == "请假 (扣除)":
                    calendar_delta = (end_d - start_d).days + 1
                    recs = [pd.DataFrame([[ (start_d+timedelta(days=i)).strftime("%Y-%m-%d"), name, tp, 1.0]], columns=["Date", "Name", "Type", "Days"]) for i in range(calendar_delta)]
                    st.session_state.tracking = pd.concat([st.session_state.tracking] + recs, ignore_index=True)
                st.session_state.df = df
                st.rerun()

        # --- 🚨 隐藏的管理工具 ---
        st.write("---")
        with st.expander("🛠️ 管理工具 (重置/维护)"):
            st.warning("此区域包含敏感操作")
            confirm_reset = st.checkbox("我确定要清空所有已用数据")
            if confirm_reset:
                if st.button("🗑️ 确认清空所有数据", type="primary"):
                    df["Vacation_Used"] = 0.0
                    df["Vacation_Remaining"] = df["Vacation_Paid"]
                    df["Sick_Used"] = 0.0
                    df["Sick_Remaining"] = df["Sick_Paid"]
                    df["Personal_Used"] = 0.0
                    df["Personal_Remaining"] = df["Personal_Paid"]
                    df["Jury_Used"] = 0.0
                    df["Maternity_Used"] = 0.0
                    df["Unpaid_Leave"] = 0.0
                    
                    st.session_state.df = df
                    st.session_state.tracking = pd.DataFrame(columns=["Date", "Name", "Type", "Days"])
                    st.success("数据已在内存中重置！请下载 CSV 并更新仓库。")
                    st.rerun()
