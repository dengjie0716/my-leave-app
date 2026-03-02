import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# 锁定简单的文件名
FILE = "summary.csv"

def load_data():
    if not os.path.exists(FILE):
        return None
    try:
        # header=3 对应第4行。如果读出来不对，我们可以微调这个数字
        df = pd.read_csv(FILE, header=3)
        # 清理列名
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 确保只保留有员工姓名的行
        df = df[df['Employee Name'].notna()]
        return df
    except Exception as e:
        st.error(f"读取 CSV 失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动更新系统")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("my_form"):
            # 获取员工名单
            names = [n for n in df['Employee Name'].unique() if str(n) != 'nan']
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 10.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并更新"):
                idx = df.index[df['Employee Name'] == name][0]
                
                # 设定列位置（V=4, S=7, P=10, JD=13...）
                p_idx = 10
                pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                # 扣除逻辑
                curr_p = pd.to_numeric(df.iloc[idx, p_idx], errors='coerce') or 0
                p_deduct = min(curr_p, days)
                rem = days - p_deduct
                
                # 更新余额
                df.iloc[idx, p_idx] = curr_p - p_deduct
                t_idx = pos_map.get(tp, 4)
                curr_t = pd.to_numeric(df.iloc[idx, t_idx], errors='coerce') or 0
                df.iloc[idx, t_idx] = curr_t - rem
                
                st.session_state.df = df
                st.success(f"✅ {name} 数据已更新！")

    st.success(f"✅ 已加载文件: {FILE}")
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载更新后的 Summary", csv_bytes, "updated_summary.csv")
else:
    st.error(f"❌ 找不到文件 {FILE}，请确认 GitHub 里的文件名已改为 summary.csv")
