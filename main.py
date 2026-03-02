import streamlit as st
import pandas as pd
import os
import requests
import base64
from datetime import datetime, timedelta
import calendar

# --- 1. 配置信息 (从 Secrets 读取) ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
BRANCH = "main" 

def save_to_github(file_path, df):
    """自动将 DataFrame 转换为 CSV 并推送到 GitHub"""
    csv_content = df.to_csv(index=False).encode('utf-8-sig')
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # 获取文件的 sha (GitHub 更新必需)
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    data = {
        "message": f"Auto-update {file_path} via App",
        "content": base64.b64encode(csv_content).decode("utf-8"),
        "branch": BRANCH
    }
    if sha: data["sha"] = sha
    
    put_res = requests.put(url, json=data, headers=headers)
    return put_res.status_code in [200, 201]

# --- 2. 加载数据 ---
@st.cache_data(ttl=10) # 每10秒检查一次更新
def load_data():
    all_files = os.listdir(".")
    s_target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), "summary.csv")
    t_target = next((f for f in all_files if "tracking" in f.lower() and f.endswith(".csv")), "tracking.csv")
    
    # 这里省略具体的 pd.read_csv 细节，保持与之前逻辑一致
    # ... (此处包含你之前的表格解析代码)
    return df, track

# --- 3. UI 界面 ---
st.title("🚀 全自动假期管理系统")
if 'df' not in st.session_state:
    st.session_state.df, st.session_state.tracking = load_data()

# 侧边栏录入
with st.sidebar:
    st.header("📝 录入请假")
    with st.form("auto_form"):
        # ... (选择员工、日期、天数等输入框)
        if st.form_submit_button("🚀 提交并同步 GitHub"):
            # 1. 执行计算逻辑 (更新 session_state.df 和 tracking)
            # ... 
            
            # 2. 自动同步
            with st.spinner("正在同步至 GitHub..."):
                s1 = save_to_github("summary.csv", st.session_state.df)
                s2 = save_to_github("tracking.csv", st.session_state.tracking)
                if s1 and s2:
                    st.success("✅ 数据已自动保存至 GitHub！无需下载。")
                    st.rerun()
                else:
                    st.error("❌ 同步失败，请检查 Token 权限。")

# 页面主体显示日历和表格...
