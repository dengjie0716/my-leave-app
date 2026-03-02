import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# 1. 映射 GitHub 上的文件名
SUMMARY_FILE = "summary.csv"
TRACKING_FILE = "tracking.csv"

def load_data():
    if not os.path.exists(SUMMARY_FILE):
        st.error(f"找不到文件: {SUMMARY_FILE}。请确保已上传并改名。")
        return None
    
    # 根据你的文件预览，表头在第3行 (index 2)
    df = pd.read_csv(SUMMARY_FILE, header=2)
    # 清理列名中的换行符和空格
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
    # 过滤掉空行
    df = df.dropna(subset=['Employee Name'])
    return df

# 保持数据状态
if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📅 员工假期自动管理系统")

if st.session_state.df is not None:
    df = st.session_state.df

    # --- 侧边栏录入 ---
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("input_form"):
            emp = st.selectbox("员工姓名", df['Employee Name'].unique())
            # 你的 7 种假期类型映射到表格列
            l_type = st.selectbox("请假类型", ["S (Sick)", "V (Vacation)", "JD (Jury)", "M (Maternity)", "B (Bereavement)", "U (Unpaid)"])
            days = st.number_input("总天数", min_value=0.5, step=0.5, value=1.0)
            date = st.date_input("起始日期")
            submit = st.form_submit_button("确认并自动扣除 P 假")

            if submit:
                idx = df.index[df['Employee Name'] == emp][0]
                
                # --- 查找 P 假的 Balance 列 ---
                # 你的表格中 "Paid Personal Leave Days" 后面通常跟着 Entitled, Used, Balance
                # 我们假设 Balance 在该大类标题后的第 2 个位置
                p_header = "Paid Personal Leave Days"
                p_start_idx = df.columns.get_loc(p_header)
                p_bal_idx = p_start_idx + 2
                
                current_p_bal = float(df.iloc[idx, p_bal_idx]) if not pd.isna(df.iloc[idx, p_bal_idx]) else 0
                
                # --- 自动扣除逻辑 ---
                p_deduct = min(current_p_bal, days)
                other_deduct = days - p_deduct
                
                # 1. 更新 P 假 Balance
                df.iloc[idx, p_bal_idx] = current_p_bal - p_deduct
                
                # 2. 更新其他假种 (例如 Sick 或 Vacation)
                # 根据你选择的类型找到对应的 Balance 列
                type_map = {
                    "S (Sick)": "Paid Sick Leave Days",
                    "V (Vacation)": "Paid Vacation Days",
                    "JD (Jury)": "Paid Jury Duty Leave Days",
                    "M (Maternity)": "Paid Maternity/ Paternity Leave (all calendar days)",
                    "B (Bereavement)": "Paid Bereavement",
                    "U (Unpaid)": "Unpaid/Special Leave"
                }
                
                target_header = type_map[l_type]
                t_start_idx = df.columns.get_loc(target_header)
                # 绝大多数假种的 Balance 都在标题后的第 2 列
                t_bal_idx = t_start_idx + 2 if "Paid" in target_header else t_start_idx + 1
                
                current_t_bal = float(df.iloc[idx, t_bal_idx]) if not pd.isna(df.iloc[idx, t_bal_idx]) else 0
                df.iloc[idx, t_bal_idx] = current_t_bal - other_deduct
                
                st.session_state.df = df
                st.success(f"更新成功！已优先扣除 {p_deduct} 天 P 假。")

    # --- 主界面 ---
    st.subheader("📊 员工假期余额实时概览 (Summary)")
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    # 下载更新后的文件
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载本月报表 (CSV)", data=csv_bytes, file_name=f"Update_{datetime.now().date()}.
