import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

# 1. 自动找文件
fs = os.listdir(".")
f = next((x for x in fs if "summary" in x.lower() and x.endswith(".csv")), None)

def load():
    if not f: return None
    try:
        # header=3 对应第4行表头
        d = pd.read_csv(f, header=3)
        d.columns = [str(c).replace('\n',' ').strip() for c in d.columns]
        return d.dropna(subset=['Employee Name'])
    except: return None

if 'df' not in st.session_state:
    st.session_state.df = load()

st.title("📊 假期自动更新系统")

if st.session_state.df is not None:
    df = st.session_state.df
    with st.sidebar:
        st.header("录入")
        with st.form("f1"):
            name = st.selectbox("员工", df['Employee Name'].unique())
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 15.0, 1.0, 0.5)
            if st.form_submit_button("确认"):
                row = df.index[df['Employee Name'] == name][0]
                # 索引: P=10, V=4, S=7, JD=13, M=15, B=16, U=17
                p_idx = 10
                pos = {"V":4, "S":7, "JD":13, "M":15, "B":16, "U":17}
                
                # 核心计算
                c_p = pd.to_numeric(df.iloc[row, p_idx], errors='coerce') or 0
                p_ded = min(c_p, days)
                rem = days - p_ded
                
                df.iloc[row, p_idx] = c_p - p_ded
                t_idx = pos.get(tp, 4)
                c_t = pd.to_numeric(df.iloc[row, t_idx], errors='coerce') or 0
                df.iloc[row, t_idx] = c_t - rem
                
                st.session_state.df = df
                st.success(f"已更新: {name}")
                st.info(f"文件: {f}")
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载 CSV", csv, "Update.csv", "text/csv")
else:
    st.error("未找到 summary 2026.csv")
