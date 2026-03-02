import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. 基础配置 ---
st.set_page_config(page_title="假期管理系统", layout="wide")
SUMMARY_FILE = "summary.csv"

# --- 2. 加载数据 (跳过表头行) ---
def load_data():
    if not os.path.exists(SUMMARY_FILE):
        st.error(f"找不到文件: {SUMMARY_FILE}。请确保 GitHub 仓库中有此文件。")
        return None
    try:
        # header=3 表示从第4行开始读取数据
        df = pd.read_csv(SUMMARY_FILE, header=3)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        df = df.dropna(subset=['Employee Name'])
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动抵扣系统 (P假优先)")

if st.session_state.df is not None:
    df = st.session_state.df

    # --- 3. 侧边栏：录入功能 ---
    with st.sidebar:
        st.header("📝 录入新申请")
        with st.form("leave_form"):
            emp = st.selectbox("选择员工", df['Employee Name'].unique())
            l_type = st.selectbox("申请假种", ["S (Sick)", "V (Vacation)", "JD (Jury)", "M (Maternity)", "B (Bereavement)", "U (Unpaid)"])
            days = st.number_input("天数", min_value=0.5, step=0.5, value=1.0)
            submit = st.form_submit_button
