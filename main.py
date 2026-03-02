import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="假期管理系统", layout="wide")

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
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 日历预览", "📜 历史记录"])

    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("input_form"):
            name_col = df.columns[0]
            names = sorted([str(n) for n in df[name_col].unique() if str(n) != 'nan'])
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("申请假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            
            # --- 关键修改：将 max_value 提高到 100.0 ---
            days = st.number_input("天_数", min_value=0.5, max_value=100.0, value=1.0, step=0.5)
            
            ldate = st.date_input("日期", datetime.now())
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            def get_col(keywords):
                for col in df.columns:
                    if all(k.lower() in col.lower() for k in keywords):
                        return col
                return None

            if st.form_submit_button("确认提交"):
                idx = df.index[df[name_col] == name][0]
                val = days if mode == "请假 (扣除)" else -days
                
                # 逻辑匹配
                v_rem = get_col(["Vacation", "Remaining"])
                v_used = get_col(["Vacation", "Used"])
                p_rem = get_col(["Personal", "Remaining"])
                p_used = get_col(["Personal", "Used"])

                if tp == "Vacation" and p_rem:
                    p_curr = df.loc[idx, p_rem]
                    p_deduct = min(p_curr, val) if val > 0 else val
                    rest = val - p_deduct
                    df.loc[idx, p_rem] -= p_deduct
                    if p_used: df.loc[idx, p_used] += p_deduct
                    if v_rem: df.loc[idx, v_rem] -= rest
                    if v_used: df.loc[idx, v_used] += rest
                else:
                    target_kw = {
                        "Sick": ["Sick", "Remaining"],
                        "Personal": ["Personal", "Remaining"],
                        "Jury": ["Jury", "Used"],
                        "Maternity": ["Maternity", "Used"],
                        "Unpaid": ["Unpaid"]
                    }
                    t_col = get_col(target_kw[tp])
                    if t_col:
                        if "Remaining" in t_col:
                            df.loc[idx, t_col] -= val
                            u_col = t_col.replace("Remaining", "Used").replace("remaining", "used")
                            if u_col in df.columns: df.loc[idx, u_col] += val
                        else:
                            df.loc[idx, t_col] += val
                
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
