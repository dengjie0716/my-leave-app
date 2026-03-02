import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="假期管理系统", layout="wide")

# 1. 自动定位文件
all_files = os.listdir(".")
summary_file = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not summary_file: return None
    try:
        # header=3 对应你 CSV 里的第4行表头
        df = pd.read_csv(summary_file, header=3)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        return df.dropna(subset=['Employee Name'])
    except: return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动更新系统 (P假优先)")

if st.session_state.df is not None:
    df = st.session_state.df
    with st.sidebar:
        st.header("📝 录入")
        with st.form("input_form"):
            emp = st.selectbox("员工", df['Employee Name'].unique())
            l_type = st.selectbox("假种", ["S (Sick)", "V (Vacation)", "JD (Jury)", "M (Maternity)", "B (Bereavement)", "U (Unpaid)"])
            days = st.number_input("天数", min_value=0.5, step=0.5, value=1.0)
            if st.form_submit_button("确认更新"):
                idx = df.index[df['Employee Name'] == emp][0]
                # 索引位置：P=10, V=4, S=7, JD=13, M=15, B=16, U=17
                p_idx, pos = 10, {"V (Vacation)": 4, "S (Sick)": 7, "JD (Jury)": 13, "M (Maternity)": 15, "B (Bereavement)": 16, "U (Unpaid)": 17}
                
                curr_p = pd.to_numeric(df.iloc[idx, p_idx], errors='
