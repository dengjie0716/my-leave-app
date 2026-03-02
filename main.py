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
        # --- 核心改进：自动寻找表头所在行 ---
        # 先读取前20行，看看 Employee Name 到底在第几行
        preview = pd.read_csv(FILE, nrows=20, header=None)
        header_idx = 0
        found = False
        
        for i, row in preview.iterrows():
            # 在这一行的所有格子里搜 "Employee Name"
            if row.astype(str).str.contains("Employee Name").any():
                header_idx = i
                found = True
                break
        
        if not found:
            st.error("在 CSV 文件中没找到 'Employee Name' 这一列，请检查表格内容。")
            return None

        # 用找到的行号作为 header 重新读取
        df = pd.read_csv(FILE, header=header_idx)
        
        # 清理列名：去掉空格和换行符
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # 再次确保 'Employee Name' 列存在
        if 'Employee Name' not in df.columns:
            st.error(f"匹配失败，当前的表头是: {list(df.columns)}")
            return None
            
        # 过滤掉名字为空的行
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
    
    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("leave_form"):
            # 获取名单
            names = [n for n in df['Employee Name'].unique() if str(n) != 'nan']
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
          days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并更新"):
                # 找到行
                idx = df.index[df['Employee Name'] == name][0]
                
                # 预设列索引（根据你的表格结构：V在第4列, S在第7列, P在第10列）
                # 如果更新后发现扣错列了，请告诉我，我们再调这些数字
                p_idx = 10
                pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                # 转换数字并扣除
                c_p = pd.to_numeric(df.iloc[idx, p_idx], errors='coerce') or 0
                p_deduct = min(c_p, days)
                rem = days - p_deduct
                
                df.iloc[idx, p_idx] = c_p - p_deduct
                t_idx = pos_map.get(tp, 4)
                c_t = pd.to_numeric(df.iloc[idx, t_idx], errors='coerce') or 0
                df.iloc[idx, t_idx] = c_t - rem
                
                st.session_state.df = df
                st.success(f"✅ {name} 数据已更新！")

    st.success(f"✅ 成功加载文件并识别表头！")
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载更新后的 Summary", csv_bytes, "updated_summary.csv")
else:
    st.info("等待数据加载中...")
