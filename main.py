import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 获取所有 CSV 文件 ---
all_files = os.listdir(".")
csv_files = [f for f in all_files if f.endswith(".csv")]

# 优先找包含 Summary 的文件，找不到就取第一个 CSV
target_file = next((f for f in csv_files if "Summary" in f), None)
if not target_file and csv_files:
    target_file = csv_files[0]

def load_data(file_path):
    try:
        # header=3 对应第4行
        df = pd.read_csv(file_path, header=3)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 只要 Employee Name 这一列有内容的行
        return df.dropna(subset=['Employee Name'])
    except Exception as e:
        st.error(f"读取文件 {file_path} 失败: {e}")
        return None

# 初始化数据
if 'df' not in st.session_state:
    if target_file:
        st.session_state.df = load_data(target_file)
    else:
        st.session_state.df = None

st.title("📊 假期自动更新系统")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 请假录入")
        with st.form("my_form"):
            names = df['Employee Name'].unique().tolist()
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 10.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并同步"):
                row_idx = df.index[df['Employee Name'] == name][0]
                
                # 设定列位置 (P=10, V=4, S=7, JD=13, M=15)
                p_idx = 10
                pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                # 核心逻辑
                curr_p = pd.to_numeric(df.iloc[row_idx, p_idx], errors='coerce') or 0
                p_deduct = min(curr_p, days)
                rem = days - p_deduct
                
                df.iloc[row_idx, p_idx] = curr_p - p_deduct
                target_idx = pos_map.get(tp, 4)
                curr_t = pd.to_numeric(df.iloc[row_idx, target_idx], errors='coerce') or 0
                df.iloc[row_idx, target_idx] = curr_t - rem
                
                st.session_state.df = df
                st.success(f"已更新: {name}")

    st.success(f"✅ 已加载文件: {target_file}")
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载 CSV", csv_bytes, "Updated_Leave.csv")
else:
    st.error("❌ 依然加载失败！")
    st.write("目前系统在仓库里看到的文件有：", all_files)
    st.write("检测到的 CSV 文件有：", csv_files)
