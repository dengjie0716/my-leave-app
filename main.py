import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        # 读取数据
        df = pd.read_csv(target, header=3)
        
        # --- 核心：重命名 Unnamed 列 ---
        # 我们根据位置给列起新名字
        new_cols = list(df.columns)
        
        # 定义一个简单的修复函数
        def rename_at(idx, name):
            if idx < len(new_cols):
                new_cols[idx] = name

        # 根据你的表格结构（通常每3列为一个假种：Entitled, Used, Balance）
        rename_at(3, "Vacation_Entitled")
        rename_at(4, "Vacation_Used")
        rename_at(5, "Vacation_Remaining")
        
        rename_at(6, "Sick_Entitled")
        rename_at(7, "Sick_Used")
        rename_at(8, "Sick_Remaining")
        
        rename_at(9, "Personal_Entitled")
        rename_at(10, "Personal_Used")
        rename_at(11, "Personal_Remaining")
        
        # 应用新列名并清理换行符
        df.columns = [str(c).replace('\n', ' ').strip() for c in new_cols]
        
        # 过滤掉名字为空的行
        df = df[df['Employee Name'].notna()]
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📅 假期管理系统 (已优化表头)")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("leave_form"):
            names = [n for n in df['Employee Name'].unique() if str(n) != 'nan']
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["V", "S", "P", "JD", "M"])
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并自动更新"):
                idx = df.index[df['Employee Name'] == name][0]
                
                # --- 自动抵扣逻辑 ---
                # 现在的逻辑：优先扣除 Personal_Remaining (索引 11)
                p_rem_idx = 11
                
                # 其它假的 Remaining 索引
                mapping = {
                    "V": 5,  # Vacation Remaining
                    "S": 8,  # Sick Remaining
                    "P": 11, # Personal Remaining
                    "JD": 14 # 假设 Jury 在后面
                }
                
                # 读取 P 假余额
                curr_p = pd.to_numeric(df.iloc[idx, p_rem_idx], errors='coerce') or 0
                p_deduct = min(curr_p, days)
                left_over = days - p_deduct
                
                # 1. 更新 P 假的 Used 和 Remaining
                df.iloc[idx, p_rem_idx] = curr_p - p_deduct
                # 自动增加 Used (索引 10)
                curr_p_used = pd.to_numeric(df.iloc[idx, 10], errors='coerce') or 0
                df.iloc[idx, 10] = curr_p_used + p_deduct
                
                # 2. 如果还有剩余，扣除目标假种
                target_rem_idx = mapping.get(tp, 5)
                curr_t = pd.to_numeric(df.iloc[idx, target_rem_idx], errors='coerce') or 0
                df.iloc[idx, target_rem_idx] = curr_t - left_over
                
                st.session_state.df = df
                st.success(f"✅ 更新成功！{name} 优先扣除 P 假 {p_deduct} 天")

    st.dataframe(df, use_container_width=True)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最新报表", csv_bytes, "leave_summary_updated.csv")
