import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="假期管理系统", layout="wide")

def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: 
        st.error("仓库中未找到任何包含 'summary' 的 CSV 文件")
        return None
    try:
        # 1. 读取原始数据
        df_raw = pd.read_csv(target, header=None, low_memory=False)
        
        # 2. 寻找表头行
        header_idx = None
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains("Employee", case=False).any():
                header_idx = i
                break
        
        if header_idx is None:
            st.error("CSV 文件中找不到表头行。")
            return None

        # 3. 以该行读取，并动态处理列名
        df = pd.read_csv(target, header=header_idx)
        
        # 你的标准 16 列模板
        base_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",
            "Sick_Paid", "Sick_Used", "Sick_Remaining",
            "Personal_Paid", "Personal_Used", "Personal_Remaining",
            "Jury_Used", "Maternity_Used", "Unpaid_Leave", "Placeholder", "Total_Days"
        ]
        
        # --- 核心修复：动态对齐列名 ---
        actual_col_count = len(df.columns)
        if actual_col_count <= len(base_cols):
            # 如果文件列数少于或等于模板，按需截取
            df.columns = base_cols[:actual_col_count]
        else:
            # 如果文件列数多于模板（比如你有 17 列），自动补齐剩余的名字
            extra_cols = [f"Extra_{i}" for i in range(len(base_cols), actual_col_count)]
            df.columns = base_cols + extra_cols
        
        # 4. 清理数据
        df = df[df["Employee Name"].astype(str).str.contains("Employee", case=False) == False]
        df = df[df["Employee Name"].notna()]
        
        # 5. 转换数字（从第3列开始）
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"读取过程中发生错误: {e}")
        return None

# 初始化数据状态
if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    st.session_state.tracking = pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

st.title("📊 假期管理与日历系统")

if st.session_state.df is not None:
    df = st.session_state.df
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 日历预览", "📜 历史记录"])

    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("input_form"):
            names = sorted([str(n) for n in df["Employee Name"].unique() if str(n) != 'nan'])
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            ldate = st.date_input("日期", datetime.now())
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            if st.form_submit_button("确认提交"):
                idx = df.index[df["Employee Name"] == name][0]
                val = days if mode == "请假 (扣除)" else -days
                
                # Vacation 优先抵扣 Personal_Remaining (根据 base_cols，这是第 11 列，索引 10)
                if tp == "Vacation":
                    p_rem_col, v_rem_col = "Personal_Remaining", "Vacation_Remaining"
                    p_curr = df.loc[idx, p_rem_col]
                    p_deduct = min(p_curr, val) if val > 0 else val
                    rest = val - p_deduct
                    
                    df.loc[idx, p_rem_col] -= p_deduct
                    df.loc[idx, "Personal_Used"] += p_deduct
                    df.loc[idx, v_rem_col] -= rest
                    df.loc[idx, "Vacation_Used"] += rest
                else:
                    mapping = {"Sick":"Sick_Remaining","Personal":"Personal_Remaining","Jury":"Jury_Used","Maternity":"Maternity_Used","Unpaid":"Unpaid_Leave"}
                    target = mapping[tp]
                    if "Remaining" in target:
                        df.loc[idx, target] -= val
                        u_col = target.replace("Remaining", "Used")
                        df.loc[idx, u_col] += val
                    else:
                        df.loc[idx, target] += val
                
                new_row = pd.DataFrame([[ldate.strftime("%Y-%m-%d"), name, tp, days]], columns=["Date", "Name", "Type", "Days"])
                st.session_state.tracking = pd.concat([st.session_state.tracking, new_row], ignore_index=True)
                st.session_state.df = df
                st.rerun()

    with tab2:
        track = st.session_state.tracking
        if not track.empty:
            track['Date'] = pd.to_datetime(track['Date'])
            for d, group in track.groupby(track['Date'].dt.date):
                st.write(f"📅 **{d}**: {', '.join([f'{r.Name}({r.Type})' for r in group.itertuples()])}")
        else: st.info("暂无记录")

    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)
        st.download_button("📥 下载 Tracking", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")
        
