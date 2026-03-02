import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import calendar

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 数据加载（强力对齐表头版） ---
def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: return None
    try:
        # 第一步：先读取所有数据，不设表头
        df_raw = pd.read_csv(target, header=None, low_memory=False)
        
        # 第二步：定位包含 "Employee" 的那一行作为数据的起点
        header_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains("Employee", case=False).any():
                header_idx = i
                break
        
        # 第三步：跳过原本乱糟糟的表头，直接读数据内容
        df = pd.read_csv(target, skiprows=header_idx + 1, header=None)
        
        # 第四步：【核心修复】定义你最精准的 16 列标准表头
        standard_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining", # 2,3,4
            "Sick_Paid", "Sick_Used", "Sick_Remaining",             # 5,6,7
            "Personal_Paid", "Personal_Used", "Personal_Remaining",  # 8,9,10
            "Jury_Used", "Maternity_Used", "Unpaid_Leave",          # 11,12,13
            "Placeholder", "Total_Days"                              # 14,15
        ]
        
        # 根据实际读到的列数进行强制重命名
        actual_len = len(df.columns)
        new_names = []
        for i in range(actual_len):
            if i < len(standard_cols):
                new_names.append(standard_cols[i])
            else:
                new_names.append(f"Extra_{i}")
        
        df.columns = new_names

        # 第五步：清理：删掉空行和无效行
        df = df[df.iloc[:, 0].notna()]
        df = df[df.iloc[:, 0].astype(str).str.contains("Employee", case=False) == False]
        
        # 第六步：强制数值化
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"加载失败，原因：{e}")
        return None

# --- 2. 初始化状态 ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

st.title("📊 假期管理系统 (标准表头回归版)")

if st.session_state.df is not None:
    df = st.session_state.df
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 月度日历视图", "📜 历史记录"])

    # --- Tab 1: 汇总 ---
    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary CSV", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    # --- Tab 2: 月视图 ---
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
                        day_records = month_data[month_data['Date'].dt.strftime('%Y-%m-%d') == curr_str]
                        box = f"**{day}**"
                        if not day_records.empty:
                            for _, r in day_records.iterrows():
                                # Maternity 显示橙色
                                color = "orange" if r['Type'] == "Maternity" else ("red" if r['Type'] == "Sick" else "blue")
                                box += f"\n\n:{color}[{r['Name']}]"
                        cols[i].markdown(box)
                st.divider()
        else: st.info("暂无记录。")

    # --- Tab 3: 历史记录 ---
    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)
        st.download_button("📥 下载 Tracking CSV", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")

    # --- 侧边栏：核心逻辑 ---
    with st.sidebar:
        st.header("📝 录入请假区间")
        with st.form("input_form"):
            names = sorted([str(n) for n in df.iloc[:, 0].unique() if str(n) != 'nan'])
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            start_d = st.date_input("开始日期", datetime.now())
            end_d = st.date_input("结束日期", datetime.now())
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            if st.form_submit_button("确认提交"):
                delta = (end_d - start_d).days + 1
                if delta <= 0:
                    st.error("日期范围错误")
                else:
                    idx = df.index[df.iloc[:, 0] == name][0]
                    val = delta if mode == "请假 (扣除)" else -delta
                    
                    # 关键逻辑：Vacation 扣 Personal，Maternity 独立
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
                        mapping = {
                            "Sick": "Sick_Remaining", "Personal": "Personal_Remaining",
                            "Jury": "Jury_Used", "Maternity": "Maternity_Used", "Unpaid": "Unpaid_Leave"
                        }
                        t_col = mapping[tp]
                        if "Remaining" in t_col:
                            df.loc[idx, t_col] -= val
                            u_col = t_col.replace("Remaining", "Used")
                            if u_col in df.columns: df.loc[idx, u_col] += val
                        else:
                            df.loc[idx, t_col] += val

                    if mode == "请假 (扣除)":
                        recs = [pd.DataFrame([[ (start_d+timedelta(days=i)).strftime("%Y-%m-%d"), name, tp, 1.0 ]], columns=["Date", "Name", "Type", "Days"]) for i in range(delta)]
                        st.session_state.tracking = pd.concat([st.session_state.tracking] + recs, ignore_index=True)
                    
                    st.session_state.df = df
                    st.rerun()
                
