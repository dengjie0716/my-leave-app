import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="假期管理系统", layout="wide")

all_files = os.listdir(".")
target = next((f for f in all_files if "summary" in f.lower() and f.endswith(".csv")), None)

def load_data():
    if not target: return None
    try:
        # 自动定位包含 Employee 的行
        preview = pd.read_csv(target, header=None, nrows=10)
        header_idx = 0
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 读取数据，并直接通过 names 参数覆盖所有表头，解决“两个表头”问题
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining", # 2,3,4
            "Sick_Paid", "Sick_Used", "Sick_Remaining",             # 5,6,7
            "Personal_Paid", "Personal_Used", "Personal_Remaining",  # 8,9,10
            "Jury_Paid", "Jury_Used", "Jury_Remaining",             # 11,12,13
            "Maternity_Paid", "Maternity_Used",                      # 14,15
            "Unpaid_Leave", "Total_Days"                            # 16,17
        ]
        
        # skiprows 跳过原本的表头行，使用自定义 names
        df = pd.read_csv(target, skiprows=header_idx + 1, names=clean_cols)
        
        # 清理空行
        df = df[df['Employee Name'].notna()]
        return df
    except Exception as e:
        st.error(f"读取失败: {e}")
        return None

if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 假期管理系统")

if st.session_state.df is not None:
    df = st.session_state.df
    
    with st.sidebar:
        st.header("📝 录入与修正")
        with st.form("leave_form"):
            names = sorted([n for n in df['Employee Name'].unique() if str(n) != 'nan'])
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("申请假种", ["Vacation", "Sick", "Personal", "Jury", "Maternity", "Unpaid"])
            mode = st.radio("操作类型", ["员工请假 (扣除)", "录入修正 (补回)"])
            days = st.number_input("天数", 0.5, 30.0, 1.0, 0.5)
            
            if st.form_submit_button("确认并提交"):
                idx = df.index[df['Employee Name'] == selected_name][0]
                calc_days = days if mode == "员工请假 (扣除)" else -days
                
                # --- 核心抵扣逻辑 ---
                p_rem_col = "Personal_Remaining"
                p_used_col = "Personal_Used"
                
                # 只有 Vacation 涉及 P 假抵扣
                if tp == "Vacation":
                    curr_p_rem = pd.to_numeric(df.loc[idx, p_rem_col], errors='coerce') or 0
                    if calc_days > 0: # 正常请假
                        p_deduct = min(curr_p_rem, calc_days)
                    else: # 补回
                        p_deduct = calc_days
                    
                    rem_to_calc = calc_days - p_deduct
                    
                    # 更新 Personal 列
                    df.loc[idx, p_rem_col] = curr_p_rem - p_deduct
                    df.loc[idx, p_used_col] = (pd.to_numeric(df.loc[idx, p_used_col], errors='coerce') or 0) + p_deduct
                    
                    # 更新 Vacation 列
                    curr_v_rem = pd.to_numeric(df.loc[idx, "Vacation_Remaining"], errors='coerce') or 0
                    curr_v_used = pd.to_numeric(df.loc[idx, "Vacation_Used"], errors='coerce') or 0
                    df.loc[idx, "Vacation_Remaining"] = curr_v_rem - rem_to_calc
                    df.loc[idx, "Vacation_Used"] = curr_v_used + rem_to_calc
                
                else:
                    # 其他假种直接扣除/补回，不碰 Personal
                    target_map = {
                        "Sick": "Sick_Remaining",
                        "Personal": "Personal_Remaining",
                        "Jury": "Jury_Remaining",
                        "Maternity": "Maternity_Used",
                        "Unpaid": "Unpaid_Leave"
                    }
                    t_col = target_map[tp]
                    curr_val = pd.to_numeric(df.loc[idx, t_col], errors='coerce') or 0
                    
                    # 如果是 Remaining 结尾的列，减去天数；如果是 Used/Leave 结尾的，加上天数
                    if "Remaining" in t_col:
                        df.loc[idx, t_col] = curr_val - calc_days
                        used_col = t_col.replace("Remaining", "Used")
                        curr_used = pd.to_numeric(df.loc[idx, used_col], errors='coerce') or 0
                        df.loc[idx, used_col] = curr_used + calc_days
                    else:
                        df.loc[idx, t_col] = curr_val + calc_days

                st.session_state.df = df
                st.success(f"✅ {selected_name} 处理完成")

    # 显示单一表头表格
    st.dataframe(df, use_container_width=True)
    
    # 导出
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下载最新报表 (用于更新仓库)", csv_bytes, "summary.csv")
