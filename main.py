import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 核心修复：直接指定你仓库里的精确文件名 ---
FILE_NAME = "Summary 2026.csv"

def load_data():
    if not os.path.exists(FILE_NAME):
        # 如果找不到，尝试列出所有文件来排查
        st.error(f"找不到文件: {FILE_NAME}")
        st.write("当前目录文件:", os.listdir("."))
        return None
    try:
        # header=3 对应你 CSV 里的第4行 (Employee Name 所在行)
        df = pd.read_csv(FILE_NAME, header=3)
        # 清理列名中的空格和换行符
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 只保留 Employee Name 不为空的行
        df = df.dropna(subset=['Employee Name'])
        return df
    except Exception as e:
        st.error(f"解析出错: {e}")
        return None

# 初始化 Session State，确保数据在操作时不丢失
if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动更新系统 (2026)")

if st.session_state.df is not None:
    df = st.session_state.df
    
    # --- 2. 侧边栏操作 ---
    with st.sidebar:
        st.header("📝 录入请假申请")
        with st.form("input_form"):
            # 自动抓取所有员工名字
            emp_list = df['Employee Name'].unique().tolist()
            name = st.selectbox("选择员工", emp_list)
            
            # 假种映射
            tp = st.selectbox("申请假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("请假天数", min_value=0.5, step=0.5, value=1.0)
            
            if st.form_submit_button("确认并自动更新"):
                # 找到对应行
                idx = df.index[df['Employee Name'] == name][0]
                
                # --- 核心扣除逻辑 (根据你表格列的相对位置) ---
                # P 假 Balance 约在第 11 列 (索引10)
                p_idx = 10 
                # 其它假种 Balance 索引映射
                pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                # 读取当前余额并转换为数字
                curr_p = pd.to_numeric(df.iloc[idx, p_idx], errors='coerce') or 0
                
                # 优先扣除 P 假
                p_deduct = min(curr_p, days)
                rem_days = days - p_deduct
                
                # 执行更新
                df.iloc[idx, p_idx] = curr_p - p_deduct
                
                target_idx = pos_map.get(tp, 4)
                curr_t = pd.to_numeric(df.iloc[idx, target_idx], errors='coerce') or 0
                df.iloc[idx, target_idx] = curr_t - rem_days
                
                # 保存状态并反馈
                st.session_state.df = df
                st.success(f"✅ {name} 更新成功！优先扣除 P 假: {p_deduct}")

    # --- 3. 主界面展示 ---
    st.info(f"📁 已成功连接文件: {FILE_NAME}")
    st.dataframe(df, use_container_width=True)
    
    # 下载更新后的文件
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下载最新报表 (CSV)",
        data=csv_bytes,
        file_name=f"Update_{FILE_NAME}",
        mime='text/csv'
    )
else:
    st.warning("正在检查文件路径，请稍候...")
