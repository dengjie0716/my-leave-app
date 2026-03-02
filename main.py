import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# 1. 锁定文件
target_file = "Summary 2026.csv"

def load_data():
    if not os.path.exists(target_file):
        return None
    try:
        # 先读取几行看看 Employee Name 在哪一行
        temp_df = pd.read_csv(target_file, nrows=10, header=None)
        header_row = 0
        for i, row in temp_df.iterrows():
            if row.astype(str).str.contains("Employee Name").any():
                header_row = i
                break
        
        # 使用找到的行作为表头重新读取
        df = pd.read_csv(target_file, header=header_row)
        # 清理列名：去掉换行符和首尾空格
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 核心：必须确保 Employee Name 这一列不为空
        df = df[df['Employee Name'].notfillna('').str.strip() != '']
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
            # 过滤掉可能的 NaN
            names = [n for n in df['Employee Name'].unique() if str(n) != 'nan']
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 10.0, 1.0, 0.5)
            
            if st.form_submit_button("确认更新"):
                idx = df.index[df['Employee Name'] == name][0]
                
                # 设定索引（基于你的表格：V=4, S=7, P=10, JD=13）
                p_idx = 10
                pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                # 计算与扣除
                curr_p = pd.to_numeric(df.iloc[idx, p_idx], errors='coerce') or 0
                p_deduct = min(curr_p, days)
                rem = days - p_deduct
                
                df.iloc[idx, p_idx] = curr_p - p_deduct
                t_idx = pos_map.get(tp, 4)
                curr_t = pd.to_numeric(df.iloc[idx, t_idx], errors='coerce') or 0
                df.iloc[idx, t_idx] = curr_t - rem
                
                st.session_state.df = df
                st.success(f"✅ {name} 更新成功！")

    st.success(f"✅ 已加载: {target_file}")
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载 CSV", csv_bytes, "Updated_Leave.csv")
else:
    st.error("❌ 读取 CSV 失败，请检查文件内容是否正确。")
