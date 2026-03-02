import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

FILE = "summary.csv"

def load_data():
    if not os.path.exists(FILE):
        st.error(f"找不到文件 {FILE}")
        return None
    try:
        # 自动寻找包含 "Employee Name" 的表头行
        preview = pd.read_csv(FILE, nrows=20, header=None)
        header_idx = 0
        found = False
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee Name").any():
                header_idx = i
                found = True
                break
        
        if not found:
            st.error("在 CSV 文件中没找到 'Employee Name' 列")
            return None

        df = pd.read_csv(FILE, header=header_idx)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 过滤掉名字为空或无效的行
        df = df[df['Employee Name'].notna()]
        df = df[df['Employee Name'].astype(str).str.strip() != ""]
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

# 初始化数据
if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📅 假期自动更新系统 (P假优先)")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("leave_form"):
            # 获取名单
            names = [n for n in df['Employee Name'].unique() if str(n) != 'nan']
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            
            submit = st.form_submit_button("确认并更新")
            
            if submit:
                # 寻找匹配行
                match = df.index[df['Employee Name'] == name]
                if len(match) > 0:
                    idx = match[0]
                    # 预设位置: P=10, V=4, S=7, JD=13...
                    p_idx = 10
                    pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                    
                    c_p = pd.to_numeric(df.iloc[idx, p_idx], errors='coerce') or 0
                    p_deduct = min(c_p, days)
                    rem = days - p_deduct
                    
                    # 更新
                    df.iloc[idx, p_idx] = c_p - p_deduct
                    t_idx = pos_map.get(tp, 4)
                    c_t = pd.to_numeric(df.iloc[idx, t_idx], errors='coerce') or 0
                    df.iloc[idx, t_idx] = c_t - rem
                    
                    st.session_state.df = df
                    st.success(f"✅ {name} 数据已更新！")
                else:
                    st.error("找不到该员工")

    st.success("✅ 数据加载成功")
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载更新后的 Summary", csv_bytes, "updated_summary.csv")
else:
    st.info("请检查 summary.csv 文件是否已正确上传并命名。")
