import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        # 1. 读取原始数据（不设 header，先扫一遍）
        raw_df = pd.read_csv(target, header=None, nrows=10)
        header_idx = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 2. 正式读取
        df = pd.read_csv(target, header=header_idx)
        
        # 3. 强制修复列名：处理 Unnamed 和 换行符
        new_cols = []
        for i, col in enumerate(df.columns):
            c_name = str(col).replace('\n', ' ').strip()
            if "Unnamed" in c_name or c_name == "nan":
                # 根据位置逻辑赋予名字（基于每3列一个循环的规律）
                # 你的表格通常是：Entitled(0), Used(1), Balance/Remaining(2)
                pos = i % 3 
                if pos == 1: c_name = f"Used_{i}"
                elif pos == 2: c_name = f"Remaining_{i}"
                else: c_name = f"Category_{i}"
            new_cols.append(c_name)
        df.columns = new_cols

        # 4. 寻找“姓名列”的真正索引（模糊匹配）
        name_col = next((c for c in df.columns if "Employee" in c and "Name" in c), None)
        if not name_col:
            # 如果还是找不到，强制把第一列设为姓名列
            name_col = df.columns[0]
            df.rename(columns={name_col: "Employee Name"}, inplace=True)
            name_col = "Employee Name"
        
        # 5. 清理数据：删除姓名为空的行
        df = df[df[name_col].notna()]
        df = df[df[name_col].astype(str).str.len() > 1]
        
        # 将确定的姓名列存入 session，方便后面调用
        st.session_state.name_column = name_col
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📅 假期管理系统 (表头自动修复版)")

if st.session_state.df is not None:
    df = st.session_state.df
    name_col = st.session_state.name_column
    
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("leave_form"):
            names = [n for n in df[name_col].unique() if str(n) != 'nan']
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["V", "S", "P", "JD", "M"])
            days = st.number_input("天_数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并自动更新"):
                idx = df.index[df[name_col] == selected_name][0]
                
                # --- 根据位置进行抵扣 (请根据实际显示列核对索引) ---
                # 假设 P 假的 Remaining 在第 11 列 (索引11)
                p_rem_idx = 11
                # 映射其它 Remaining 列索引
                mapping = {"V": 5, "S": 8, "P": 11, "JD": 14}
                
                curr_p = pd.to_numeric(df.iloc[idx, p_rem_idx], errors='coerce') or 0
                p_deduct = min(curr_p, days)
                left_over = days - p_deduct
                
                # 更新 P 假 Balance
                df.iloc[idx, p_rem_idx] = curr_p - p_deduct
                
                # 如果有剩余，扣除对应假种
                target_idx = mapping.get(tp, 5)
                curr_t = pd.to_numeric(df.iloc[idx, target_idx], errors='coerce') or 0
                df.iloc[idx, target_idx] = curr_t - left_over
                
                st.session_state.df = df
                st.success(f"✅ {selected_name} 更新成功！")

    st.success(f"✅ 已识别姓名列为: [{name_col}]")
    st.dataframe(df, use_container_width=True)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最新报表", csv_bytes, "updated_leave.csv")
