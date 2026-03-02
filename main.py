import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        # 寻找表头行
        preview = pd.read_csv(target, header=None, nrows=10)
        header_idx = 0
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        df = pd.read_csv(target, header=header_idx)
        
        # --- 核心：完全匹配你描述的列名 ---
        new_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",
            "Sick_Paid", "Sick_Used", "Sick_Remaining",
            "Personal_Paid", "Personal_Used", "Personal_Remaining",
            "Jury_Paid", "Jury_Used", "Jury_Remaining",
            "Maternity_Paid", "Maternity_Used", # 按照你说的列顺序
            "Unpaid_Leave", "Total_Days"
        ]
        
        # 自动补全剩余列名（防止列数不匹配）
        if len(df.columns) > len(new_cols):
            new_cols += [f"Col_{i}" for i in range(len(new_cols), len(df.columns))]
        df.columns = new_cols[:len(df.columns)]
        
        # 清理空行
        df = df[df['Employee Name'].notna()]
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期管理系统 (自定义列匹配)")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入与修正")
        with st.form("leave_form"):
            names = sorted([n for n in df['Employee Name'].unique() if str(n) != 'nan'])
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("申请假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            mode = st.radio("操作类型", ["员工请假 (扣除)", "录入修正 (补回)"])
            days = st.number_input("天数", 0.5, 30.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并提交"):
                idx = df.index[df['Employee Name'] == selected_name][0]
                calc_days = days if mode == "员工请假 (扣除)" else -days
                
                # --- 根据你提供的列顺序定位 (Remaining 列) ---
                # Vacation_Rem=4, Sick_Rem=7, Personal_Rem=10, Jury_Rem=13
                p_rem_col = "Personal_Remaining"
                p_used_col = "Personal_Used"
                
                target_map = {
                    "Vacation": "Vacation_Remaining",
                    "Sick": "Sick_Remaining",
                    "Personal": "Personal_Remaining",
                    "Jury": "Jury_Remaining",
                    "Maternity": "Maternity_Used", # 特殊处理
                    "Unpaid": "Unpaid_Leave"      # 特殊处理
                }

                # 1. 优先从 Personal 扣除 (如果是 Vacation/Sick/Personal/Jury)
                if tp in ["Vacation", "Sick", "Personal", "Jury"]:
                    curr_p_rem = pd.to_numeric(df.loc[idx, p_rem_col], errors='coerce') or 0
                    if calc_days > 0:
                        p_deduct = min(curr_p_rem, calc_days)
                    else:
                        p_deduct = calc_days
                    
                    rem_to_calc = calc_days - p_deduct
                    
                    # 更新 Personal
                    df.loc[idx, p_rem_col] = curr_p_rem - p_deduct
                    df.loc[idx, p_used_col] = (pd.to_numeric(df.loc[idx, p_used_col], errors='coerce') or 0) + p_deduct
                else:
                    # Maternity 或 Unpaid 不参与 P 假抵扣
                    rem_to_calc = calc_days

                # 2. 更新目标假种
                target_col = target_map.get(tp)
                df.loc[idx, target_col] = (pd.to_numeric(df.loc[idx, target_col], errors='coerce') or 0) + (rem_to_calc if "Used" in target_col or "Leave" in target_col else -rem_to_calc)
                
                # 同步更新对应的 Used 列 (如果是 Rem 列被减，对应的 Used 就要加)
                if "Remaining" in target_col:
                    used_col = target_col.replace("Remaining", "Used")
                    df.loc[idx, used_col] = (pd.to_numeric(df.loc[idx, used_col], errors='coerce') or 0) + rem_to_calc

                st.session_state.df = df
                st.success(f"✅ {selected_name} 已成功处理")

    st.dataframe(df, use_container_width=True)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最新报表", csv_bytes, "summary.csv")
         
