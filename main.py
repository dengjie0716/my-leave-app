import streamlit as st
import pandas as pd
import os
from datetime import datetime
import calendar

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 数据加载与处理 ---
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

st.title("📊 假期管理系统")

if st.session_state.df is not None:
    df = st.session_state.df
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 月度日历视图", "📜 历史记录"])

    # --- Tab 1: 汇总 ---
    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    # --- Tab 2: Outlook 风格日历 ---
    with tab2:
        st.header("📅 请假月历概览")
        track = st.session_state.tracking
        if not track.empty:
            track['Date'] = pd.to_datetime(track['Date'])
            # 月份选择
            all_months = sorted(track['Date'].dt.strftime('%Y-%m').unique(), reverse=True)
            sel_month_str = st.selectbox("选择要查看的月份", all_months)
            
            sel_date = datetime.strptime(sel_month_str, '%Y-%m')
            year, month = sel_date.year, sel_date.month
            
            # 生成该月的日历矩阵
            cal = calendar.monthcalendar(year, month)
            month_name = calendar.month_name[month]
            
            st.write(f"### {month_name} {year}")
            
            # 这里的 HTML/CSS 模拟 Outlook 格子
            cols = st.columns(7)
            days_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for i, day_name in enumerate(days_abbr):
                cols[i].markdown(f"**{day_name}**")

            month_data = track[track['Date'].dt.strftime('%Y-%m') == sel_month_str]

            for week in cal:
                cols = st.columns(7)
                for i, day in enumerate(week):
                    if day == 0:
                        cols[i].write("") # 空白格
                    else:
                        # 查找当天是否有假
                        current_date_str = f"{year}-{month:02d}-{day:02d}"
                        day_records = month_data[month_data['Date'].dt.strftime('%Y-%m-%d') == current_date_str]
                        
                        box_content = f"**{day}**"
                        if not day_records.empty:
                            for _, r in day_records.iterrows():
                                # 为不同假种涂色（Markdown 模拟）
                                color = "red" if r['Type'] == "Sick" else "blue"
                                box_content += f"\n\n:{color}[{r['Name']}]"
                        
                        cols[i].markdown(box_content)
                st.divider()
        else:
            st.info("暂无 Tracking 记录，日历无法显示。请在侧边栏录入。")

    # --- Tab 3: 历史 ---
    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)
        st.download_button("📥 下载 Tracking", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")

    # --- 侧边栏逻辑 (保持不变但天数上限设为100) ---
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("input_form"):
            name_col = df.columns[0]
            names = sorted([str(n) for n in df[name_col].unique() if str(n) != 'nan'])
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("申请假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            days = st.number_input("天数", 0.5, 100.0, 1.0, 0.5)
            ldate = st.date_input("日期", datetime.now())
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            def get_col(keywords):
                for col in df.columns:
                    if all(k.lower() in col.lower() for k in keywords): return col
                return None

            if st.form_submit_button("确认提交"):
                idx = df.index[df[name_col] == name][0]
                val = days if mode == "请假 (扣除)" else -days
                
                # Vacation 优先扣 Personal
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
                        df.loc[idx, t_col] += (val if "Used" in t_col or "Unpaid" in t_col else -val)
                        if "Remaining" in t_col:
                            u_col = t_col.replace("Remaining", "Used").replace("remaining", "used")
                            if u_col in df.columns: df.loc[idx, u_col] += val

                if mode == "请假 (扣除)":
                    new_row = pd.DataFrame([[ldate.strftime("%Y-%m-%d"), name, tp, days]], columns=["Date", "Name", "Type", "Days"])
                    st.session_state.tracking = pd.concat([st.session_state.tracking, new_row], ignore_index=True)
                st.session_state.df = df
                st.rerun()
