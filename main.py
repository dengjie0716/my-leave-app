import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

# 1. 精确匹配你的文件名
FILE_NAME = "Summary 2026.csv"

def load_data():
    if not os.path.exists(FILE_NAME):
        st.error(f"找不到文件: {FILE_NAME}")
        return None
    try:
        # header=3 对应 CSV 中的第4行（Employee Name 所在行）
        df = pd.read_csv(FILE_NAME, header=3)
        # 清理列名中的换行符和空格
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        # 只保留有名字的行，去掉空行
        return df.dropna(subset=['Employee Name'])
    except Exception as e:
        st.error(f"解析出错: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期自动更新系统 (2026)")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入申请")
        with st.form("input_form"):
            # 动态获取员工名单
            names = df['Employee Name'].unique().tolist()
            name = st.selectbox("选择员工", names)
            
            # 假种对应 (V=Vacation, S=Sick, JD=Jury, M=Maternity, B=Bereavement, U=Unpaid)
            tp = st.selectbox("假种", ["S", "V", "JD", "M", "B", "U"])
            days = st.number_input("总天数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并自动扣除 P 假"):
                row = df.index[df['Employee Name'] == name][0]
                
                # --- 根据你的表格列位置进行扣除 ---
                # P 假 Balance 索引通常在 10 左右
                p_idx = 10
                # 其它假种 Balance 位置映射 (基于你上传的表格结构)
                pos_map = {"V": 4, "S": 7, "JD": 13, "M": 15, "B": 16, "U": 17}
                
                # 转换数字
                curr_p = pd.to_numeric(df.iloc[row, p_idx], errors='coerce') or 0
                p_deduct = min(curr_p, days)
                rem_days = days - p_deduct
                # 更新目标假种 Balance
                target_idx = pos_map.get(tp, 4)
                curr_target = pd.to_numeric(df.iloc[row, target_idx], errors='coerce') or 0
                df.iloc[row, target_idx] = curr_target - rem_days
                
                st.session_state.df = df
                st.success(f"✅ {name} 更新成功！优先扣除 P:{p_deduct} 天")

    st.info(f"📁 当前数据来源: {FILE_NAME}")
    # 显示表格
    st.dataframe(df, use_container_width=True)
    
    # 导出 CSV
    csv_out = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载更新后的 CSV", csv_out, f"Updated_{FILE_NAME}", "text/csv")

else:
    st.warning("正在等待文件加载...")
