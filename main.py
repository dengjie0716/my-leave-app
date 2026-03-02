import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        # 1. 定位表头
        preview = pd.read_csv(target, header=None, nrows=15)
        header_idx = 0
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 2. 严格按照你描述的顺序定义列名
        # 顺序：Name, ID, Vac(3), Sick(3), Personal(3), Jury(1), Mat(1), Unpaid(1), Total(1)
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",  # 2,3,4
            "Sick_Paid", "Sick_Used", "Sick_Remaining",              # 5,6,7
            "Personal_Paid", "Personal_Used", "Personal_Remaining",   # 8,9,10
            "Jury_Used",       # 11 (你提到只需要 Used)
            "Maternity_Used",    # 12 (你提到只需要 Used)
            "Unpaid_Leave",    # 13
            "Total_Days"       # 14
        ]
        
        # 读取数据
        df = pd.read_csv(target, header=header_idx)
        
        # 强制对齐列名
        if len(df.columns) >= len(clean_cols):
            df.columns = clean_cols + list(df.columns[len(clean_cols):])
        else:
            df.columns = clean_cols[:len(df.columns)]
        
        # 3. 彻底清除重复的表头行
        df = df[df["Employee Name"].astype(str) != "Employee Name"]
        df = df[df["Employee Name"].notna()]
        
        return df
    except Exception as e:
        st.error(f"对齐失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期管理系统 (列对齐修正版)")

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
                
                # --- 修正后的逻辑 ---
                if tp == "Vacation":
                    # 只有 Vacation 优先扣 Personal_Remaining (索引10)
                    p_rem, p_used = "Personal_Remaining", "Personal_Used"
                    curr_p = pd.to_numeric(df.loc[idx, p_rem], errors='coerce') or 0
                    
                    p_deduct = min(curr_p, calc_days) if calc_days > 0 else calc_days
                    rem_to_calc = calc_days - p_deduct
                    
                    # 更新 Personal
                    df.loc[idx, p_rem] = curr_p - p_deduct
                    df.loc[idx, p_used] = (pd.to_numeric(df.loc[idx, p_used], errors='coerce') or 0) + p_deduct
                    
                    # 更新 Vacation
                    v_rem, v_used = "Vacation_Remaining", "Vacation_Used"
                    df.loc[idx, v_rem] = (pd.to_numeric(df.loc[idx, v_rem], errors='coerce') or 0) - rem_to_calc
                    df.loc[idx, v_used] = (pd.to_numeric(df.loc[idx, v_used], errors='coerce') or 0) + rem_to_calc
                
                else:
                    # 其他假种映射
                    target_map = {
                        "Sick": "Sick_Remaining",
                        "Personal": "Personal_Remaining",
                        "Jury": "Jury_Used",
                        "Maternity": "Maternity_Used",
                        "Unpaid": "Unpaid_Leave"
                    }
                    t_col = target_map[tp]
                    curr_val = pd.to_numeric(df.loc[idx, t_col], errors='coerce') or 0
                    
                    if "Remaining" in t_col:
                        # 扣除余额类 (Sick/Personal)
                        df.loc[idx, t_col] = curr_val - calc_days
                        u_col = t_col.replace("Remaining", "Used")
                        df.loc[idx, u_col] = (pd.to_numeric(df.loc[idx, u_col], errors='coerce') or 0) + calc_days
                    else:
                        # 累加已休类 (Jury/Maternity/Unpaid)
                        df.loc[idx, t_col] = curr_val + calc_days

                st.session_state.df = df
                st.success(f"✅ {selected_name} 更新成功")

    st.dataframe(df, use_container_width=True)
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最新报表", csv_bytes, "summary.csv")
