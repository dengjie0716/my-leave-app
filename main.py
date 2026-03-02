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
        df = pd.read_csv(target, header=header_idx)
        df = df[df.iloc[:, 0].astype(str).str.contains("Employee", case=False) == False]
        df = df[df.iloc[:, 0].notna()]
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

st.title("📊 假期管理系统 (区间请假版)")

if st.session_state.df is not None:
    df = st.session_state.df
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 月度日历视图", "📜 历史记录"])

    # --- Tab 1: 汇总 ---
    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    # --- Tab 2: 月视图 ---
    with tab2:
        st.header("📅 请假月历概览")
        track = st.session_state.tracking
        if not track.empty:
            track['Date'] = pd.to_datetime(track['Date'])
            all_months = sorted(track['Date'].dt.strftime('%Y-%m').unique(), reverse=True)
            sel_month_str = st.selectbox("选择月份", all_months)
            
            sel_date = datetime.strptime(sel_month_str, '%Y-%m')
            year, month = sel_date.year, sel_date.month
            cal = calendar.monthcalendar(year, month)
            
            # 日历表头
            cols = st.columns(7)
            days_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for i, d_name in enumerate(days_abbr):
                cols[i].markdown(f"**{d_name}**")

            month_data = track[track['Date'].dt.strftime('%Y-%m') == sel_month_str]

            for week in cal:
                cols = st.columns(7)
                for i, day in enumerate(week):
                    if day == 0:
                        cols[i].write("")
                    else:
                        curr_str = f"{year}-{month:02d}-{day:02d}"
                        day_records = month_data[month_data['Date'].dt.strftime('%Y-%m-%d') == curr_str]
                        
                        box = f"**{day}**"
                        if not day_records.empty:
                            # 去重显示，防止同一天多条记录挤爆格子
                            for _, r in day_records.iterrows():
                                color = "red" if r['Type'] == "Sick" else "blue"
                                box += f"\n\n:{color}[{r['Name']}]"
                        cols[i].markdown(box)
                st.divider()
        else:
            st.info("暂无请假记录。")

    # --- Tab 3: 历史 ---
    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)
        st.download_button("📥 下载 Tracking", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")

    # --- 侧边栏：区间录入 ---
    with st.sidebar:
        st.header("📝 录入请假区间")
        with st.form("input_form"):
            name_col = df.columns[0]
            names = sorted([str(n) for n in df[name_col].unique() if str(n) != 'nan'])
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            
            # 关键改动：选择开始和结束日期
            start_d = st.date_input("开始日期", datetime.now())
            end_d = st.date_input("结束日期", datetime.now())
            
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            def get_col(keywords):
                for col in df.columns:
                    if all(k.lower() in col.lower() for k in keywords): return col
                return None

            if st.form_submit_button("确认提交"):
                # 1. 计算天数
                delta = (end_d - start_d).days + 1
                if delta <= 0:
                    st.error("结束日期不能早于开始日期")
                else:
                    idx = df.index[df[name_col] == name][0]
                    val = delta if mode == "请假 (扣除)" else -delta
                    
                    # 2. 余额扣减逻辑
                    p_rem = get_col(["Personal", "Remaining"])
                    if tp == "Vacation" and p_rem:
                        p_curr = df.loc[idx, p_rem]
                        p_deduct = min(p_curr, val) if val > 0 else val
                        rest = val - p_deduct
                        df.loc[idx, p_rem] -= p_deduct
                        p_used = get_col(["Personal", "Used"])
                        if p_used: df.loc[idx, p_used] += p_deduct
                        v_rem, v_used = get_col(["Vacation", "Remaining"]), get_col(["Vacation", "Used"])
                        if v_rem: df.loc[idx, v_rem] -= rest
                        if v_used: df.loc[idx, v_used] += rest
                    else:
                        target_kw = {"Sick":["Sick","Rem"],"Personal":["Personal","Rem"],"Jury":["Jury","Used"],"Maternity":["Maternity","Used"],"Unpaid":["Unpaid"]}
                        t_col = get_col(target_kw[tp])
                        if t_col:
                            if "Remaining" in t_col:
                                df.loc[idx, t_col] -= val
                                u_col = t_col.replace("Remaining", "Used").replace("remaining", "used")
                                if u_col in df.columns: df.loc[idx, u_col] += val
                            else:
                                df.loc[idx, t_col] += val

                    # 3. Tracking 逻辑：将区间拆分为每一天，方便日历显示
                    if mode == "请假 (扣除)":
                        new_rows = []
                        for i in range(delta):
                            current_day = start_d + timedelta(days=i)
                            new_rows.append([current_day.strftime("%Y-%m-%d"), name, tp, 1.0])
                        new_df = pd.DataFrame(new_rows, columns=["Date", "Name", "Type", "Days"])
                        st.session_state.tracking = pd.concat([st.session_state.tracking, new_df], ignore_index=True)
                    
                    st.session_state.df = df
                    st.success(f"已登记 {name} 从 {start_d} 到 {end_d} 共 {delta} 天假期")
                    st.rerun()
