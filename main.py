import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        # 1. 定位表头行
        preview = pd.read_csv(target, header=None, nrows=10)
        header_idx = 0
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 2. 读取并清理
        df = pd.read_csv(target, header=header_idx)
        
        # 3. 自定义干净的列名列表 (根据你 CSV 的实际列顺序)
        # 我们根据每 3 列一组的规律手动定义
        clean_cols = [
            "Employee Name", "Department", "Join Date",  # 前3列
            "Vacation_Entitled", "Vacation_Used", "Vacation_Remaining", # 4,5,6
            "Sick_Entitled", "Sick_Used", "Sick_Remaining",             # 7,8,9
            "Personal_Entitled", "Personal_Used", "Personal_Remaining",  # 10,11,12
            "Jury_Entitled", "Jury_Used", "Jury_Remaining",             # 13,14,15
            "Maternity_Balance", "Bereavement_Balance", "Unpaid_Balance" # 16,17,18
        ]
        
        # 确保列名长度匹配，防止报错
        if len(df.columns) >= len(clean_cols):
            df.columns = clean_cols + list(df.columns[len(clean_cols):])
        else:
            # 如果列不够，就只替换前面有的
            df.columns = clean_cols[:len(df.columns)]

        # 4. 数据清理
        df = df[df['Employee Name'].notna()]
        df = df[df['Employee Name'].astype(str).str.len() > 1]
        
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期管理系统 (正式版)")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("leave_form"):
            names = sorted([n for n in df['Employee Name'].unique() if str(n) != 'nan'])
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("申请假种", ["Vacation", "Sick", "Personal", "Jury"])
            days = st.number_input("请假天数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并自动抵扣"):
                idx = df.index[df['Employee Name'] == selected_name][0]
                
                # --- 核心逻辑：优先扣除 Personal_Remaining (索引 11) ---
                p_rem_col = "Personal_Remaining"
                p_used_col = "Personal_Used"
                
                # 映射其它假种的列名
                target_map = {
                    "Vacation": "Vacation_Remaining",
                    "Sick": "Sick_Remaining",
                    "Personal": "Personal_Remaining",
                    "Jury": "Jury_Remaining"
                }
                
                # 1. 尝试从 Personal 扣除
                curr_p = pd.to_numeric(df.loc[idx, p_rem_col], errors='coerce') or 0
                p_deduct = min(curr_p, days)
                rem_to_deduct = days - p_deduct
                
                # 更新 Personal
                df.loc[idx, p_rem_col] = curr_p - p_deduct
                df.loc[idx, p_used_col] = (pd.to_numeric(df.loc[idx, p_used_col], errors='coerce') or 0) + p_deduct
                
                # 2. 如果还有剩余，扣除目标假种 (例如 Vacation)
                target_col = target_map.get(tp)
                if rem_to_deduct > 0:
                    curr_t = pd.to_numeric(df.loc[idx, target_col], errors='coerce') or 0
                    df.loc[idx, target_col] = curr_t - rem_to_deduct
                    # 同时增加对应假种的 Used 列 (Remaining 的前一列)
                    used_col = target_col.replace("Remaining", "Used")
                    df.loc[idx, used_col] = (pd.to_numeric(df.loc[idx, used_col], errors='coerce') or 0) + rem_to_deduct
                
                st.session_state.df = df
                st.success(f"✅ {selected_name} 更新成功！")

    # 显示表格
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最终版 Summary CSV", csv_bytes, "Leave_Summary_2026.csv")
