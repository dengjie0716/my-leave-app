import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 1. 基础配置
st.set_page_config(page_title="假期管理系统", layout="wide")

# 文件名映射
SUMMARY_FILE = "summary.csv"
TRACKING_FILE = "tracking.csv"

# 2. 加载数据
def load_data():
    if not os.path.exists(SUMMARY_FILE):
        st.error(f"找不到文件: {SUMMARY_FILE}。请确保已在 GitHub 上传此文件。")
        return None
    
    # 你的 Summary CSV 结构：真正的表头在第4行（index为3）
    # 我们读取时尝试处理复杂的列名
    try:
        df = pd.read_csv(SUMMARY_FILE, header=3)
        # 清理列名：去除换行符、空格，并处理未命名的列
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 过滤掉员工姓名为空的行
        df = df.dropna(subset=['Employee Name'])
        return df
    except Exception as e:
        st.error(f"解析 CSV 失败: {e}")
        return None

# 保持数据在内存中
if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📅 员工假期自动管理系统 (P假优先)")

if st.session_state.df is not None:
    df = st.session_state.df

    # --- 侧边栏：录入 ---
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("input_form"):
            emp = st.selectbox("选择员工", df['Employee Name'].unique())
            
            # 假期类型定义
            l_type = st.selectbox("假种", ["S (Sick)", "V (Vacation)", "JD (Jury)", "M (Maternity)", "B (Bereavement)", "U (Un
