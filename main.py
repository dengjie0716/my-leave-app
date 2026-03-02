import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="假期管理系统", layout="wide")

def load_data():
    all_files = os.listdir(".")
    target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)
    if not target: 
        st.error("仓库中未找到任何包含 'summary' 的 CSV 文件")
        return None
    try:
        # 1. 尝试用不同的编码读取，防止中文或特殊字符导致加载失败
        try:
            df_raw = pd.read_csv(target, header=None, encoding='utf-8-sig')
        except:
            df_raw = pd.read_csv(target, header=None, encoding='gbk')
        
        # 2. 暴力搜索：寻找 'Employee' 所在的行索引
        header_idx = None
        for i, row in df_raw.iterrows():
            # 只要这一行任何一个格子包含 "Employee"
            if row.astype(str).str.contains("Employee", case=False).any():
                header_idx = i
                break
        
        if header_idx is None:
            st.error("CSV 文件中找不到包含 'Employee' 的表头行，请检查文件第一行。")
            return None

        # 3. 重新以该行作为表头读取数据
        df = pd.read_csv(target, header=header_idx)
        
        # 4. 强行应用你的 16 列标准模板，修复手动修改导致的列名漂移
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining", # 2,3,4
            "Sick_Paid", "Sick_Used", "Sick_Remaining",             # 5,6,7
            "Personal_Paid", "Personal_Used", "Personal_Remaining",  # 8,9,10
            "Jury_Used", "Maternity_Used", "Unpaid_Leave", "Placeholder", "Total_Days"
        ]
        
        # 只取文件现有的列数进行匹配，防止溢出
        df.columns = clean_cols[:len(df.columns)]
        
        # 5. 清理：删掉原本的表头行(如果它还在数据里)，并删掉姓名为空的行
        df = df[df["Employee Name"].astype(str).str.contains("Employee") == False]
        df = df[df["Employee Name"].notna()]
        
        # 6. 数据转换：确保所有数字列都是数字类型
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"读取过程中发生错误: {e}")
        return None

# 初始化数据
if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'tracking' not in st.session_state:
    # 自动创建 tracking 结构，防止空文件报错
    st.session_state.tracking = pd.DataFrame(columns=["Date", "Name", "Type", "Days"])

st.title("📊 假期管理与日历系统")

if st.session_state.df is not None:
    df = st.session_state.df
    tab1, tab2, tab3 = st.tabs(["📊 余额汇总", "📅 日历预览", "📜 历史记录"])

    with tab1:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 下载最新 Summary", df.to_csv(index=False).encode('utf-8-sig'), "summary.csv")

    with st.sidebar:
        st.header("📝 录入请假")
        with st.form("input_form"):
            names = sorted(df["Employee Name"].unique().tolist())
            name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            ldate = st.date_input("日期", datetime.now())
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            mode = st.radio("模式", ["请假 (扣除)", "修正 (补回)"])
            
            if st.form_submit_button("确认提交"):
                idx = df.index[df["Employee Name"] == name][0]
                val = days if mode == "请假 (扣除)" else -days
                
                # 只有 Vacation 抵扣 Personal
                if tp == "Vacation":
                    p_rem_col, v_rem_col = "Personal_Remaining", "Vacation_Remaining"
                    # 先看 Personal 余额
                    p_curr = df.loc[idx, p_rem_col]
                    p_deduct = min(p_curr, val) if val > 0 else val
                    rest = val - p_deduct
                    
                    df.loc[idx, p_rem_col] -= p_deduct
                    df.loc[idx, "Personal_Used"] += p_deduct
                    df.loc[idx, v_rem_col] -= rest
                    df.loc[idx, "Vacation_Used"] += rest
                else:
                    # 其他假种逻辑
                    mapping = {"Sick":"Sick_Remaining","Personal":"Personal_Remaining","Jury":"Jury_Used","Maternity":"Maternity_Used","Unpaid":"Unpaid_Leave"}
                    target = mapping[tp]
                    if "Remaining" in target:
                        df.loc[idx, target] -= val
                        u_col = target.replace("Remaining", "Used")
                        df.loc[idx, u_col] += val
                    else:
                        df.loc[idx, target] += val
                
                # 更新 tracking
                new_row = pd.DataFrame([[ldate.strftime("%Y-%m-%d"), name, tp, days]], columns=["Date", "Name", "Type", "Days"])
                st.session_state.tracking = pd.concat([st.session_state.tracking, new_row], ignore_index=True)
                st.session_state.df = df
                st.rerun()

    with tab2:
        track = st.session_state.tracking
        if not track.empty:
            track['Date'] = pd.to_datetime(track['Date'])
            for d, group in track.groupby(track['Date'].dt.date):
                st.write(f"📅 **{d}**: {', '.join([f'{r.Name}({r.Type})' for r in group.itertuples()])}")
        else: st.info("暂无记录")

    with tab3:
        st.dataframe(st.session_state.tracking, use_container_width=True)
        st.download_button("📥 下载 Tracking", st.session_state.tracking.to_csv(index=False).encode('utf-8-sig'), "tracking.csv")
