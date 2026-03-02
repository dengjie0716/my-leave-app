import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. 配置 ---
st.set_page_config(page_title="假期管理系统", layout="wide")

# 自动寻找包含 "summary" 字样的 csv 文件
all_files = os.listdir(".")
summary_file = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

# --- 2. 加载数据 ---
def load_data():
    if not summary_file:
        st.error(f"未在仓库中找到包含 'summary' 的 CSV 文件。当前文件有: {all_files}")
        return None
    try:
        # 根据你的表格结构，从第4行开始读取 (header=3)
        df = pd.read_csv(summary_file, header=3)
        # 清理列名
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 移除空行
        df = df.dropna(subset=['Employee Name'])
        return df
    except Exception as e:
        st.error(f"解析文件 {summary_file} 出错: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动更新系统 (2026)")

if st.session_state.df is not None:
    df = st.session_state.df

    # --- 3. 侧边栏：录入申请 ---
    with st.sidebar:
        st.header("📝 录入新假单")
        with st.form("input_form"):
            emp = st.selectbox("选择员工", df['Employee Name'].unique())
            l_type = st.selectbox("假种", ["S (Sick)", "V (Vacation)", "JD (Jury)", "M (Maternity)", "B (Bereavement)", "U (Unpaid)"])
            days = st.number_input("天数", min_value=0.5, step=0.5, value=1.0)
            submit = st.form_submit_button("确认并自动抵扣 P 假")

            if submit:
                idx = df.index[df['Employee Name'] == emp][0]
                
                # --- 核心逻辑 (根据列索引位置扣除) ---
                # P 假 Balance 大约在第 11 列 (索引 10)
                p_idx = 10 
                # 其它假种位置映射
                type_pos = {"V (Vacation)": 4, "S (Sick)": 7, "JD (Jury)": 13, "M (Maternity)": 15, "B (Bereavement)": 16, "U (Unpaid)": 17}
                
                # 转换为数字处理
                curr_p = pd.to_numeric(df.iloc[idx, p_idx], errors='coerce') or 0
                
                p_deduct = min(curr_p, days)
                rem = days - p_deduct
                
                # 更新 P 假
                df.iloc[idx, p_idx] = curr_p - p_deduct
                
                # 更新主假种
                target_idx = type_pos.get(l_type, 4)
                curr_t = pd.to_numeric(df.iloc[idx, target_idx], errors='coerce') or 0
                df.iloc[idx, target_idx] = curr_t - rem
                
                st.session_state.df = df
                st.success(f"✅ {emp} 更新成功！扣除 P:{p_deduct}, {l_type}:{rem}")

    # --- 4. 展示 ---
    st.info(f"正在读取文件: {summary_file}")
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_out =
