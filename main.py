import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        # 1. 寻找表头所在行
        raw_df = pd.read_csv(target, header=None, nrows=15)
        header_idx = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 2. 读取全部数据
        # 不再用 names 自动匹配，而是读进来后强行替换
        df = pd.read_csv(target, header=header_idx)
        
        # 3. 核心：定义你需要的唯一干净表头
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining",
            "Sick_Paid", "Sick_Used", "Sick_Remaining",
            "Personal_Paid", "Personal_Used", "Personal_Remaining",
            "Jury_Paid", "Jury_Used", "Jury_Remaining",
            "Maternity_Paid", "Maternity_Used",
            "Unpaid_Leave", "Total_Days"
        ]
        
        # 强制将列名对齐，如果列数多于定义的，补上序号
        current_len = len(df.columns)
        final_cols = clean_cols[:current_len]
        if current_len > len(clean_cols):
            final_cols += [f"Extra_{i}" for i in range(len(clean_cols), current_len)]
        
        df.columns = final_cols
        
        # 4. 关键：删除读进来的第一行（如果它长得像原表头的话）
        # 我们过滤掉名字里包含 "Name" 或 "Employee" 的那一数据行
        df = df[df["Employee Name"].astype(str) != "Employee Name"]
        
        # 清理空行
        df = df[df['Employee Name'].notna()]
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期管理系统")

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
                
                # --- Vacation 优先扣 P 逻辑 ---
                p_rem_col, p_used_col = "Personal_Remaining", "Personal_Used"
                
                if tp == "Vacation":
                    curr_p_rem = pd.to_numeric(df.loc[idx, p_rem_col], errors='coerce') or 0
                    p_deduct = min(curr_p_rem, calc_days) if calc_days > 0 else calc_days
                    rem_to_calc = calc_days - p_deduct
                    
                    # 更新 Personal
                    df.loc[idx, p_rem_col] = curr_p_rem - p_deduct
                    df.loc[idx, p_used_col] = (pd.to_numeric(df.loc[idx, p_used_col], errors='coerce') or 0) + p_deduct
                    
                    # 更新 Vacation
                    v_rem, v_used = "Vacation_Remaining", "Vacation_Used"
                    df.loc[idx, v_rem] = (pd.to_numeric(df.loc[idx, v_rem], errors='coerce') or 0) - rem_to_calc
                    df.loc[idx, v_used] = (pd.to_numeric(df.loc[idx, v_used], errors='coerce') or 0) + rem_to_calc
                
                else:
                    # 其他假种直接操作
                    target_map = {
                        "Sick": "Sick_Remaining", "Personal": "Personal_Remaining",
                        "Jury": "Jury_Remaining", "Maternity": "Maternity_Used", "Unpaid": "Unpaid_Leave"
                    }
                    t_col = target_map[tp]
                    curr_val = pd.to_numeric(df.loc[idx, t_col], errors='coerce') or 0
                    
                    if "Remaining" in t_col:
                        df.loc[idx, t_col] = curr_val - calc_days
                        u_col = t_col.replace("Remaining", "Used")
                        df.loc[idx, u_col] = (pd.to_numeric(df.loc[idx, u_col], errors='coerce') or 0) + calc_days
                    else:
                        df.loc[idx, t_col] = curr_val + calc_days

                st.session_state.df = df
                st.success(f"✅ {selected_name} 处理成功")

    st.dataframe(df, use_container_width=True)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最新报表", csv_bytes, "summary.csv")
