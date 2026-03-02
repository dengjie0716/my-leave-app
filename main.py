import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        preview = pd.read_csv(target, header=None, nrows=10)
        header_idx = 0
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        df = pd.read_csv(target, header=header_idx)
        
        # 统一表头
        clean_cols = [
            "Employee Name", "Department", "Join Date",
            "Vacation_Entitled", "Vacation_Used", "Vacation_Remaining",
            "Sick_Entitled", "Sick_Used", "Sick_Remaining",
            "Personal_Entitled", "Personal_Used", "Personal_Remaining",
            "Jury_Entitled", "Jury_Used", "Jury_Remaining",
            "Maternity_Balance", "Bereavement_Balance", "Unpaid_Balance"
        ]
        if len(df.columns) >= len(clean_cols):
            df.columns = clean_cols + list(df.columns[len(clean_cols):])
        else:
            df.columns = clean_cols[:len(df.columns)]
        
        df = df[df['Employee Name'].notna()]
        df = df[df['Employee Name'].astype(str).str.len() > 1]
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期管理系统 (支持录入修正)")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入与调整")
        with st.form("leave_form"):
            names = sorted([n for n in df['Employee Name'].unique() if str(n) != 'nan'])
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("申请假种", ["Vacation", "Sick", "Personal", "Jury"])
            
            # --- 模式选择：是请假还是改错 ---
            mode = st.radio("操作类型", ["员工请假 (扣除)", "录入修正 (补回)"])
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并提交"):
                idx = df.index[df['Employee Name'] == selected_name][0]
                
                # 如果是补回模式，计算时天数取反
                calc_days = days if mode == "员工请假 (扣除)" else -days
                
                p_rem_col, p_used_col = "Personal_Remaining", "Personal_Used"
                target_map = {
                    "Vacation": "Vacation_Remaining",
                    "Sick": "Sick_Remaining",
                    "Personal": "Personal_Remaining",
                    "Jury": "Jury_Remaining"
                }
                
                # 1. 计算 Personal 抵扣逻辑
                curr_p = pd.to_numeric(df.loc[idx, p_rem_col], errors='coerce') or 0
                if calc_days > 0:
                    p_deduct = min(curr_p, calc_days)
                else:
                    p_deduct = calc_days # 补回时直接减去负数，即加回
                
                rem_to_calc = calc_days - p_deduct
                
                # 更新 Personal 列
                df.loc[idx, p_rem_col] = curr_p - p_deduct
                df.loc[idx, p_used_col] = (pd.to_numeric(df.loc[idx, p_used_col], errors='coerce') or 0) + p_deduct
                
                # 2. 更新目标假种列
                target_col = target_map.get(tp)
                used_col = target_col.replace("Remaining", "Used")
                
                df.loc[idx, target_col] = (pd.to_numeric(df.loc[idx, target_col], errors='coerce') or 0) - rem_to_calc
                df.loc[idx, used_col] = (pd.to_numeric(df.loc[idx, used_col], errors='coerce') or 0) + rem_to_calc
                
                st.session_state.df = df
                st.success(f"✅ {selected_name} 已成功{mode} {days} 天")

    st.dataframe(df, use_container_width=True)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最新报表并同步到 GitHub", csv_bytes, "summary.csv")
else:
    st.info("请确保 summary.csv 已经上传。")
