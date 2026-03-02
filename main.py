def load_data():
    if not target: return None
    try:
        # 1. 定位表头
        preview = pd.read_csv(target, header=None, nrows=15)
        header_idx = 0
        for i, row in preview.iterrows():
            if row.astype(str).str.contains("Employee").any():
                header_idx = i
                break
        
        # 2. 重新对齐列名 (在 Unpaid 后面增加了一个占位列)
        clean_cols = [
            "Employee Name", "Employee#", 
            "Vacation_Paid", "Vacation_Used", "Vacation_Remaining", # 2,3,4
            "Sick_Paid", "Sick_Used", "Sick_Remaining",             # 5,6,7
            "Personal_Paid", "Personal_Used", "Personal_Remaining",  # 8,9,10
            "Jury_Used",                                           # 11
            "Maternity_Used",                                        # 12
            "Unpaid_Leave",                                        # 13
            "Empty_Space",                                         # 14 (这一列就是挤走 Total 的那个 Unnamed)
            "Total_Days"                                           # 15
        ]
        
        # 读取数据
        df = pd.read_csv(target, header=header_idx)
        
        # 强制对齐列名
        current_cols = list(df.columns)
        if len(current_cols) >= len(clean_cols):
            df.columns = clean_cols + current_cols[len(clean_cols):]
        else:
            df.columns = clean_cols[:len(current_cols)]
        
        # 3. 彻底清除重复的表头行
        df = df[df["Employee Name"].astype(str) != "Employee Name"]
        df = df[df["Employee Name"].notna()]
        
        return df
    except Exception as e:
        st.error(f"对齐失败: {e}")
        return None
