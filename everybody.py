import streamlit as st
import pandas as pd
import re

st.title("📊 通用版單價分析查詢工具")

# 上傳 Excel
uploaded_file = st.file_uploader("📤 上傳你的單價分析表 (.xls 或 .xlsx)", type=["xls", "xlsx"])

if uploaded_file:
    if "已確認" not in st.session_state:
        st.session_state["已確認"] = False

    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    sheet = st.selectbox("請選擇工作表：", sheet_names)
    skiprows = st.number_input("要跳過前幾列？（通常是 6~7 列）", min_value=0, value=6)

    df_raw = pd.read_excel(xls, sheet_name=sheet, skiprows=skiprows)
    df_raw.columns = df_raw.columns.str.strip()  # ✅ 移除欄位名稱前後空白
    st.write("📋 欄位名稱：", list(df_raw.columns))  # 顯示欄位名稱方便檢查
    st.write("\n👀 原始資料預覽：")
    st.dataframe(df_raw.head())

    # 使用者手動對應欄位（這裡反過來問）
    st.markdown("---")
    st.subheader("📌 請對應下列欄位")
    col_id = st.selectbox("🔢 項次欄（例如：1、2、3）", df_raw.columns)
    col_item = st.selectbox("🔖 項目及說明欄（例如：喬木、安安）", df_raw.columns)
    col_unit = st.selectbox("📏 單位欄：", df_raw.columns)

    if st.button("✅ 確認並開始查詢"):
        st.session_state["已確認"] = True
        df = df_raw.rename(columns={
            col_item: "項目及說明",
            col_id: "項次",
            col_unit: "單位"
        })
        df = df[df["項目及說明"].notna() & df["項次"].notna()]
        df["項目及說明"] = df["項目及說明"].astype(str).str.replace("\u3000", "").str.strip()  # ✅ 清除全形與半形空白
        df["項次"] = df["項次"].astype(str)  # ✅ 避免 Arrow 錯誤
        df["項次數值"] = pd.to_numeric(df["項次"], errors="coerce")
        st.session_state["df_ready"] = df

    # ✅ 查詢畫面只在確認後顯示
    if st.session_state["已確認"]:
        if "df_ready" not in st.session_state:
            st.stop()

        df = st.session_state["df_ready"]

        if "selected_items" not in st.session_state:
            st.session_state.selected_items = {}

        input_text = st.text_input("🔍 請輸入查詢關鍵字（可用 , 或 ， 分隔）", "喬木，吊卡車，技術工")
        keywords = [kw.strip() for kw in re.split(r"[，,]", input_text) if kw.strip()]
        sort_by_input = st.checkbox("依輸入順序排列", value=True)

        if keywords:
            filtered_all = pd.DataFrame()
            for i, kw in enumerate(keywords):
                temp = df[
                    df["項目及說明"].str.contains(kw, na=False) |
                    df["項次"].str.contains(kw, na=False)
                ].copy()
                temp["輸入順序"] = i
                filtered_all = pd.concat([filtered_all, temp])

            filtered_all = filtered_all.drop_duplicates(subset=["項目及說明", "單位"])

            if sort_by_input:
                filtered_all = filtered_all.sort_values(by=["輸入順序", "項次數值"])
            else:
                filtered_all = filtered_all.sort_values(by="項次數值")

            if filtered_all.empty:
                st.warning("⚠️ 沒有找到符合的工項，請檢查關鍵字或對應欄位是否正確")
                st.info("💡 可搜尋的項目包括：")
                preview_items = (df["項次"].astype(str) + "｜" + df["項目及說明"].astype(str)).drop_duplicates()
                st.write(preview_items.head(10))
            else:
                st.write(f"共找到 {len(filtered_all)} 筆資料，請勾選保留：")
                for _, row in filtered_all.iterrows():
                    row_id = f"{row['項次']}｜{row['項目及說明']}"  # ✅ 改為 項次｜項目及說明
                    default_checked = row_id in st.session_state.selected_items

                    if st.checkbox(row_id, value=default_checked, key=row_id):
                        st.session_state.selected_items[row_id] = row
                    else:
                        st.session_state.selected_items.pop(row_id, None)

        if st.session_state.selected_items:
            st.markdown("### ✅ 你保留的工項")
            selected_df = pd.DataFrame(st.session_state.selected_items.values())
            selected_df = selected_df.sort_values(by="項次數值")  # ✅ 加這行
            st.dataframe(selected_df.drop(columns=["項次數值", "輸入順序", "數量", "單價", "複價", "備註"], errors="ignore"))

            csv = selected_df.drop(columns=["項次數值", "輸入順序", "數量", "單價", "複價", "備註"], errors="ignore")\
                .to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 下載勾選工項", data=csv, file_name="保留工項.csv", mime="text/csv")
        else:
            st.info("尚未選取任何工項")
