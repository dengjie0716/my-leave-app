import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

# 1. 获取当前目录下所有文件
all_files = os.listdir(".")
# 2. 搜索逻辑：只要文件名包含 'summary' 且以 '.csv' 结尾
f = next((x for x in all_files if "summary" in x.lower() and x.endswith(".csv")), None)

def load():
    if not f: return None
    try:
        # header=3 对应你的 Excel/CSV 中的第4行作为表头
        d = pd.read_csv(f, header=3)
        # 清理列名中的空格和换行
        d.columns = [str(c).replace('\n',' ').strip() for c in d.columns]
        return d.dropna(subset=['Employee Name'])
    except Exception as e:
        st.error(f"解析出错: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load()

st.title("📊 假期自动更新系统")

if st.session_state.df is not None:
    df = st.session_state.df
    with st.sidebar:
        st.header("录入申请")
        with st.form("f1"):
            name = st.selectbox("员工", df['Employee Name'].unique())
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            if st.form_submit_button("确认"):
                row = df.index[df['Employee Name'] == name][0]
                # 根据你表格列的位置索引
                p_idx, pos = 10, {"V":4, "S":7, "JD":13, "M":15, "B":16, "U":17}
                
                c_p = pd.to_numeric(df.iloc[row, p_idx], errors='coerce') or 0
                p_ded = min(c_p, days)
                rem = days - p_ded
                
                df.iloc[row, p_idx] = c_p - p_ded
                t_idx = pos.get(tp, 4)
                c_t = pd.to_numeric(df.iloc[row, t_idx], errors='coerce') or 0
                df.iloc[row, t_idx] = c_t - rem
                
                st.session_state.df = df
                st.success(f"已更新: {name}")

    st.info(f"📁 成功加载文件: {f}")
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载更新后的 CSV", csv, f"Update_{f}", "text/csv")
else:
    st.error("❌ 依然找不到文件！")
    st.write("当前仓库里的文件列表如下，请检查是否有你的 CSV：")
    st.write(all_files)
