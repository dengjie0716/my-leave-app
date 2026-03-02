import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 自动定位文件 (不计较大小写和空格) ---
all_files = os.listdir(".")
target_file = next((f for f in all_files if "sum" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target_file:
        return None
    try:
        # header=3 对应你 CSV 里的第4行 (Employee Name 所在行)
        df = pd.read_csv(target_file, header=3)
        # 清理列名：去掉换行符和空格
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 移除 Employee Name 为空的无效行
        df = df.dropna(subset=['Employee Name'])
        return df
    except Exception as e:
        st.error(f"读取文件出错: {e}")
        return None

# 初始化数据状态
if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动更新系统 (2026)")

# --- 2. 逻辑判断 ---
if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入申请")
        with st.form("leave_form"):
            # 这里的下拉菜单会自动列出所有人选
            emp_list = df['Employee Name'].unique().tolist()
            name = st.selectbox("选择员工", emp_list)
            tp = st.selectbox("申请假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并同步"):
                row = df.index[df['Employee Name'] == name][0]
                
                # 索引定位 (P=10, V=4, S=7, JD=13, M=15, B=16, U=17)
                p_idx = 10
                pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                # 核心扣除逻辑
                c_p = pd.to_numeric(df.iloc[row, p_idx], errors='coerce') or 0
                p_deduct = min(c_p, days)
                rem = days - p_deduct
                
                # 更新余额
                df.iloc[row, p_idx] = c_p - p_deduct
                t_idx = pos_map.get(tp, 4)
                c_t = pd.to_numeric(df.iloc[row, t_idx], errors='coerce') or 0
                df.iloc[row, t_idx] = c_t - rem
                
                st.session_state.df = df
                st.success(f"✅ {name} 更新成功！")

    st.info(f"📁 成功匹配并加载文件: {target_file}")
    st.dataframe(df, use_container_width=True)
    
    # 下载功能
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载更新后的 CSV", csv_bytes, f"Updated_{target_file}", "text/csv")

else:
    st.error("❌ 依然找不到 Summary 文件！")
    st.write("仓库中的实际文件列表如下，请检查是否有 .csv 后缀：")
    st.write(all_files)
