import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# --- 1. 自动寻找仓库里的 CSV 文件 ---
all_files = os.listdir(".")
# 只要文件名里包含 'summary' 且是 csv 就拿来用
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target:
        return None
    try:
        # header=3 对应第4行。如果表格还是出不来，可以试着把 3 改成 0 或 1
        df = pd.read_csv(target, header=3)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 只要名字不为空的行
        df = df[df['Employee Name'].notna()]
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动更新系统")

if st.session_state.df is not None:
    df = st.session_state.df
    st.success(f"✅ 已识别到文件: {target}")
    
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("leave_form"):
            names = [n for n in df['Employee Name'].unique() if str(n) != 'nan']
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            if st.form_submit_button("确认并更新"):
                idx = df.index[df['Employee Name'] == name][0]
                # 设定位置：P=10, V=4, S=7... (如果扣错列了请告诉我数字)
                p_idx, pos_map = 10, {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                c_p = pd.to_numeric(df.iloc[idx, p_idx], errors='coerce') or 0
                p_deduct = min(c_p, days)
                rem = days - p_deduct
                
                df.iloc[idx, p_idx] = c_p - p_deduct
                t_idx = pos_map.get(tp, 4)
                c_t = pd.to_numeric(df.iloc[idx, t_idx], errors='coerce') or 0
                df.iloc[idx, t_idx] = c_t - rem
                
                st.session_state.df = df
                st.success(f"✅ {name} 更新成功！")

    st.dataframe(df, use_container_width=True)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载 CSV", csv_bytes, "updated_summary.csv")
else:
    st.error("❌ 仓库中虽有文件但无法解析，请检查 CSV 内部格式。")
    st.write("目前看到的文件列表：", all_files)
