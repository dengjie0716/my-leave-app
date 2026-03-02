import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 基础配置 (必须放在最前面) ---
st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 2. 初始化数据逻辑 (防止白屏的关键) ---
if 'summary' not in st.session_state:
    # 建立初始名单和7种假期余额
    initial_data = {
        'Name': ['Betty', 'John', 'Sarah', 'Alex'],
        'P': [5.0, 5.0, 5.0, 5.0],    # Personal Day (优先扣除)
        'S': [10.0, 10.0, 10.0, 10.0], # Sick Leave
        'V': [15.0, 15.0, 15.0, 15.0], # Vacation
        'JD': [5.0, 5.0, 5.0, 5.0],   # Jury Duty
        'M': [0.0, 0.0, 0.0, 0.0],    # Maternity
        'B': [3.0, 3.0, 3.0, 3.0],    # Bereavement
        'U': [99.0, 99.0, 99.0, 99.0]  # Unpaid
    }
    st.session_state.summary = pd.DataFrame(initial_data)

if 'tracking' not in st.session_state:
    st.session_state.tracking = pd.DataFrame(columns=['Date', 'Name', 'Type', 'Days', 'Detail'])

# --- 3. 界面标题 ---
st.title("🏢 员工假期自动管理系统 (2026)")
st.markdown("---")

# --- 4. 侧边栏：录入功能 ---
with st.sidebar:
    st.header("📝 录入请假申请")
    with st.form("leave_form"):
        name = st.selectbox("选择员工", st.session_state.summary['Name'].tolist())
        l_type = st.selectbox("申请假种", ['S', 'V', 'JD', 'M', 'B', 'U'])
        days = st.number_input("请假总天数", min_value=0.5, step=0.5, value=1.0)
        date = st.date_input("起始日期", datetime.now())
        
        submit = st.form_submit_button("确认提交并自动扣除")

        if submit:
            # 获取该员工在表格中的位置
            idx = st.session_state.summary.index[st.session_state.summary['Name'] == name][0]
            current_p = st.session_state.summary.at[idx, 'P']
            
            # 【核心逻辑】：优先扣除 P
            p_deduct = min(current_p, days)
            other_deduct = days - p_deduct
            
            # 更新余额
            st.session_state.summary.at[idx, 'P'] -= p_deduct
            if other_deduct > 0:
                st.session_state.summary.at[idx, l_type] -= other_deduct
            
            # 记录追踪日志
            log_detail = f"P扣除:{p_deduct}, {l_type}扣除:{other_deduct}"
            new_record = pd.DataFrame([{
                'Date': date.strftime('%Y-%m-%d'),
                'Name': name,
                'Type': l_type,
                'Days': days,
                'Detail': log_detail
            }])
            st.session_state.tracking = pd.concat([st.session_state.tracking, new_record], ignore_index=True)
            st.success(f"✅ 提交成功！已自动抵扣余额。")

# --- 5. 主页面展示 ---
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("📊 员工假期余额 (Summary)")
    # 使用 container 包装防止白屏渲染失败
    with st.container():
        st.dataframe(st.session_state.summary, use_container_width=True, hide_index=True)
    
    # 下载按钮
    csv = st.session_state.summary.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 下载本月报表 (CSV)",
        data=csv,
        file_name=f"Leave_Update_{datetime.now().strftime('%Y%m')}.csv",
        mime='text/csv'
    )

with col2:
    st.subheader("🗓️ 最近请假记录 (Tracking)")
    if not st.session_state.tracking.empty:
        st.table(st.session_state.tracking.tail(10))
    else:
        st.info("暂无请假记录")

st.info("💡 提示：系统会自动检测 P 假余额。若 P 假足够，则优先扣除 P 假；若不足，剩余部分扣除申请的假种。")

