import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import calendar

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 数据加载（找回标准表头） ---
def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: return None
    try:
        # 寻找表头行
        df_raw = pd.read_csv(target, header=None, low_memory=False)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 读取数据
        df = pd.read_csv(target, header=header_idx)
        
        # --- 强行盖回之前的标准 16 列名 ---
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining", # 2,3,4
            "Sick_Paid", "Sick_Used", "Sick_Remaining",             # 5,6,7
            "Personal_Paid", "Personal_Used", "Personal_Remaining",  # 8,9,10
            "Jury_Used",                                           # 11
            "Maternity_Used",                                      # 12
            "Unpaid_Leave",                                        # 13
            "Placeholder",                                         # 14 (幽灵列)
            "Total_Days"                                           # 15
        ]
        
        # 动态对齐：如果文件列数多于模板，补齐 Extra；如果少于，则截取
        if len(df.columns) >= len(clean_cols):
            df.columns = clean_cols + list(df.columns[len(clean_cols):])
        else:
            df.columns = clean_cols[:len(df.columns)]

        # 清理行
        df = df[df["Employee Name"].astype(str).str.contains("Employee") == False]
        df = df[df["Employee Name"].notna()]
        
        # 强制数值化
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

st.title("📊 假期管理系统 (标准表头回归版)")

if st.session_state.df is not None:
    df = st.session_state.df
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 月度日历视图", "📜 历史记录"])

    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary CSV", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

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
                                color = "orange" if r['Type'] == "Maternity" else ("red" if r['Type'] == "Sick" else "blue")
                                box += f"\n\n:{color}[{r['Name']}]"
                        cols[i].markdown(box)
                st.divider()
        else: st.info("暂无记录。")

    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)
        st.download_button("📥 下载 Tracking CSV", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")

    with st.sidebar:
        st.header("📝 录入请假区间")
        with st.form("input_form"):
            names = sorted([str(n) for n in df["Employee Name"].unique()])
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
                    idx = df.index[df["Employee Name"] == name][0]
                    val = delta if mode == "请假 (扣除)" else -delta
                    
                    # --- 精准逻辑：Vacation 扣 Personal，其他独立 ---
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
                        # 映射到正确的列名
                        mapping = {
                            "Sick": "Sick_Remaining",
                            "Personal": "Personal_Remaining",
                            "Jury": "Jury_Used",
                            "Maternity": "Maternity_Used",
                            "Unpaid": "Unpaid_Leave"
                        }
                        t_col = mapping[tp]
                        if "Remaining" in t_col:
                            df.loc[idx, t_col] -= val
                            u_col = t_col.replace("Remaining", "Used")
                            df.loc[idx, u_col] += val
                        else:
                            df.loc[idx, t_col] += val

                    if mode == "请假 (扣除)":
                        recs = [pd.DataFrame([[ (start_d+timedelta(days=i)).strftime("%Y-%m-%d"), name, tp, 1.0 ]], columns=["Date", "Name", "Type", "Days"]) for i in range(delta)]
                        st.session_state.tracking = pd.concat([st.session_state.tracking] + recs, ignore_index=True)
                    
                    st.session_state.df = df
                    st.rerun()
