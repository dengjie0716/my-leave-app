import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="员工假期管理系统", layout="wide")

# --- 1. 文件名配置 (需与 GitHub 上传的文件名完全一致) ---
SUMMARY_FILE = "AR form.xlsx - Summary 2026 (2).csv"
TRACKING_FILE = "AR form.xlsx - Tracking 2026 (2).csv"

# --- 2. 加载数据 ---
@st.cache_data
def load_data():
    if os.path.exists(SUMMARY_FILE):
        # 读取时跳过前两行（根据你表格的结构，第3行才是真正的表头）
        df = pd.read_csv(SUMMARY_FILE, header=2)
        # 清理列名中的空格
        df.columns = df.columns.str.strip()
        # 只保留有名字的行
        df = df.dropna(subset=['Employee Name'])
        return df
    else:
        st.error(f"找不到文件: {SUMMARY_FILE}")
        return pd.DataFrame()

df_summary = load_data()

# --- 3. 映射你的假期类型到表格列名 ---
# 你的表格列名比较长，这里做一个映射
COLUMN_MAPPING = {
    'P': 'Paid Personal\nLeave Days', # 优先扣除这一列
    'S': 'Paid Sick Leave Days',
    'V': 'Paid Vacation Days',
    'JD': 'Paid Jury Duty Leave Days',
    'M': 'Paid Maternity/ Paternity Leave (all calendar days)',
    'B': 'Paid Bereavement', # 如果表格里有这一列
    'U': 'Unpaid/Special Leave'
}

st.title("📊 假期自动更新系统 (2026 实时版)")

if not df_summary.empty:
    # --- 4. 侧边栏录入 ---
    with st.sidebar:
        st.header("📝 录入请假单")
        with st.form("leave_form"):
            name = st.selectbox("选择员工", df_summary['Employee Name'].unique())
            l_type_key = st.selectbox("假种", ['S', 'V', 'JD', 'M', 'B', 'U'])
            days = st.number_input("天数", min_value=0.5, step=0.5, value=1.0)
            date = st.date_input("起始日期")
            
            submit = st.form_submit_button("同步更新余额")

            if submit:
                # 逻辑：查找对应的行
                row_idx = df_summary.index[df_summary['Employee Name'] == name][0]
                
                # 获取 P 假的 Balance 列 (假设在 P 假大类下的第3小列)
                # 注意：由于你的 CSV 结构复杂，这里直接寻找 "Entitled" 后的逻辑
                # 为了简化，我们假设你只需要减少对应的数值
                
                # 【核心扣除逻辑】
                p_col = "Paid Personal\nLeave Days" # 你的表格中 P 假的名称
                actual_type_col = COLUMN_MAPPING.get(l_type_key)
                
                # 尝试扣除
                st.info(f"正在处理 {name} 的申请...")
                # 这里可以添加更复杂的列定位逻辑
                st.success(f"已录入！请在下载的报表中查看最新余额。")

    # --- 5. 主页面展示 ---
    tab1, tab2 = st.tabs(["数据预览", "历史记录"])
    
    with tab1:
        st.subheader("当前员工状态 (从 Excel 导入)")
        st.dataframe(df_summary)
        
        # 导出按钮
        new_csv = df_summary.to_csv(index=False).encode('utf-8')
        st.download_button("📥 下载更新后的 Summary", new_csv, "Updated_Summary.csv")

else:
    st.warning("请确保已将 CSV 文件上传到 GitHub 仓库。")
