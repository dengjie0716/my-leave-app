# ... (前面的代码保持不变，直接修改 sidebar 里的 form 部分) ...

    with st.sidebar:
        st.header("📝 假期调整录入")
        with st.form("leave_form"):
            names = sorted([n for n in df['Employee Name'].unique() if str(n) != 'nan'])
            selected_name = st.selectbox("选择员工", names)
            tp = st.selectbox("假种", ["Vacation", "Sick", "Personal", "Jury"])
            
            # --- 新增：操作模式选择 ---
            mode = st.radio("操作类型", ["员工请假 (扣除)", "录入修正 (补回)"])
            
            days = st.number_input("天数", 0.5, 20.0, 1.0, 0.5)
            
            if st.form_submit_button("确认提交"):
                idx = df.index[df['Employee Name'] == selected_name][0]
                
                # 如果是补回模式，把天数变成负数参与计算
                calc_days = days if mode == "员工请假 (扣除)" else -days
                
                p_rem_col = "Personal_Remaining"
                p_used_col = "Personal_Used"
                target_map = {
                    "Vacation": "Vacation_Remaining",
                    "Sick": "Sick_Remaining",
                    "Personal": "Personal_Remaining",
                    "Jury": "Jury_Remaining"
                }
                
                # 1. 优先处理 Personal 逻辑
                curr_p = pd.to_numeric(df.loc[idx, p_rem_col], errors='coerce') or 0
                
                # 如果是扣除，优先扣 P 假；如果是补回，直接按比例返还
                if calc_days > 0:
                    p_deduct = min(curr_p, calc_days)
                else:
                    # 补回时，假设先补回 P 假（或者你可以根据需要调整）
                    p_deduct = calc_days 
                
                rem_to_calc = calc_days - p_deduct
                
                # 更新 Personal 列
                df.loc[idx, p_rem_col] = curr_p - p_deduct
                df.loc[idx, p_used_col] = (pd.to_numeric(df.loc[idx, p_used_col], errors='coerce') or 0) + p_deduct
                
                # 2. 处理目标假种列
                target_col = target_map.get(tp)
                used_col = target_col.replace("Remaining", "Used")
                
                curr_t_rem = pd.to_numeric(df.loc[idx, target_col], errors='coerce') or 0
                curr_t_used = pd.to_numeric(df.loc[idx, used_col], errors='coerce') or 0
                
                df.loc[idx, target_col] = curr_t_rem - rem_to_calc
                df.loc[idx, used_col] = curr_t_used + rem_to_calc
                
                st.session_state.df = df
                st.success(f"✅ {selected_name} 的 {tp} 已{mode} {days} 天")

# ... (后面的代码保持不变) ...
