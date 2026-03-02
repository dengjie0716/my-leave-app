import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="假期管理与日历系统", layout="wide")

SUMMARY_FILE = "summary.csv"
TRACKING_FILE = "tracking.csv"

def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: return None
    try:
        # 增加容错：使用 low_memory=False 防止分块读取错误
        df_raw = pd.read_csv(target, header=None, low_memory=False)
        
        # 寻找包含 Employee 的行作为表头
        header_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 重新读取
        df = pd.read_csv(target, header=header_idx)
        
        # 精准强制列定义（即使你手动改乱了，程序也会强行掰回来）
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",
            "Sick_Paid", "Sick_Used", "Sick_Remaining",
            "Personal_Paid", "Personal_Used", "Personal_Remaining",
            "Jury_Used", "Maternity_Used", "Unpaid_Leave", "Placeholder", "Total_Days"
        ]
        
        # 截取或补齐列名
        df.columns = clean_cols[:len(df.columns)]
        
        # 清理行：去掉表头重复行、去掉姓名为空的行
        df = df[df["Employee Name"].astype(str) != "Employee Name"]
        df = df[df["Employee Name"].notna()]
        
        # 强制将所有数据列转为数字，防止你手动输入的“3”被识别成文字
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"数据解析失败，请检查 CSV 格式: {e}")
        return None

def load_tracking():
    if os.path.exists(TRACKING_FILE):
        try:
            t_df = pd.read_csv(TRACKING_FILE)
            if not t_df.empty and "Date" in t_df.columns:
                return t_df
        except: pass
    return pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = load_tracking()

st.title("📊 假期管理系统")

# 如果 Marie Gao 的数据加进去了，这里会显示
if st.session_state.df is not None:
    df = st.session_state.df
    
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总 (Summary)", "📅 日历模式 (Calendar)", "📜 历史记录 (Tracking)"])

    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary CSV", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("leave_form"):
            # 自动过滤掉无效人名
            names = sorted([n for n in df['Employee Name'].unique() if str(n) != 'nan'])
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            leave_date = st.date_input("请假日期", datetime.now())
            days = st.number_input("天数", 0.5, 30.0, 1.0, 0.5)
            mode = st.radio("操作类型", ["员工请假 (扣除)", "录入修正 (补回)"])
            
            if st.form_submit_button("确认提交"):
                idx = df.index[df['Employee Name'] == selected_name][0]
                calc_days = days if mode == "员工请假 (扣除)" else -days
                
                # --- Vacation 抵扣 Personal 逻辑 ---
                if tp == "Vacation":
                    p_rem, p_used = "Personal_Remaining", "Personal_Used"
                    curr_p = df.loc[idx, p_rem]
                    p_deduct = min(curr_p, calc_days) if calc_days > 0 else calc_days
                    rem_to_calc = calc_days - p_deduct
                    df.loc[idx, p_rem] = curr_p - p_deduct
                    df.loc[idx, p_used] = df.loc[idx, p_used] + p_deduct
                    df.loc[idx, "Vacation_Remaining"] -= rem_to_calc
                    df.loc[idx, "Vacation_Used"] += rem_to_calc
                else:
                    target_map = {"Sick":"Sick_Remaining","Personal":"Personal_Remaining","Jury":"Jury_Used","Maternity":"Maternity_Used","Unpaid":"Unpaid_Leave"}
                    t_col = target_map[tp]
                    if "Remaining" in t_col:
                        df.loc[idx, t_col] -= calc_days
                        u_col = t_col.replace("Remaining", "Used")
                        df.loc[idx, u_col] += calc_days
                    else:
                        df.loc[idx, t_col] += calc_days

                if mode == "员工请假 (扣除)":
                    new_rec = pd.DataFrame([[leave_date.strftime("%Y-%m-%d"), selected_name, tp, days]], columns=["Date", "Name", "Type", "Days"])
                    st.session_state.tracking = pd.concat([st.session_state.tracking, new_rec], ignore_index=True)
                
                st.session_state.df = df
                st.rerun()

    with tab2:
        # 日历展示逻辑... (同前)
        track_df = st.session_state.tracking
        if not track_df.empty:
            track_df['Date'] = pd.to_datetime(track_df['Date'])
            month = st.selectbox("月份选择", sorted(track_df['Date'].dt.strftime('%Y-%m').unique(), reverse=True))
            month_data = track_df[track_df['Date'].dt.strftime('%Y-%m') == month].sort_values("Date")
            for d, group in month_data.groupby(month_data['Date'].dt.date):
                st.write(f"🏷️ **{d}**: {', '.join([f'{r.Name}({r.Type})' for r in group.itertuples()])}")
        else:
            st.info("尚无记录")

    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)
else:
    st.error("❌ 无法加载数据。请检查 GitHub 仓库里的 summary.csv 第一行是否包含 'Employee Name'。")
