import streamlit as st
import pandas as pd
import re
import os

st.title("📊 通用版單價分析查詢工具")

# —— 安全讀 Excel 檔案的函式（自動判斷 .xls / .xlsx） ——
def read_excel_safely(file, sheet_name=None, skiprows=0):
    import os
    ext = os.path.splitext(file.name)[1].lower()
    st.write(f"📄 嘗試讀取檔案：{file.name} (副檔名：{ext})")

    if ext == ".xls":
        df = pd.read_excel(file, sheet_name=sheet_name, skiprows=skiprows, engine="xlrd")
    elif ext == ".xlsx":
        df = pd.read_excel(file, sheet_name=sheet_name, skiprows=skiprows, engine="openpyxl")
    else:
        raise ValueError("❌ 僅支援 .xls 或 .xlsx 檔案")

    return df




# —— 上傳兩份 Excel：單價分析 & 植栽規格
main_file = st.file_uploader(
    "📄 上傳單價分析表 (.xls/.xlsx)", type=["xls", "xlsx"], key="main_uploader"
)
plant_file = st.file_uploader(
    "🌱 上傳植栽規格表 (.xls/.xlsx)", type=["xls", "xlsx"], key="plant_uploader"
)

# —— 處理單價分析主表
if main_file:
    # 初始化
    if "df_main" not in st.session_state:
        st.session_state.df_main = None
        st.session_state.selected_items = {}
        st.session_state.refresh = False

    # 讀取主表
    try:
        xls_main = pd.ExcelFile(main_file)
        sheet_main = st.selectbox("請選擇單價分析工作表：", xls_main.sheet_names)
        skip_main = st.number_input("跳過主表前幾列？", min_value=0, value=6)

        df_main = read_excel_safely(main_file, sheet_name=sheet_main, skiprows=skip_main)
        df_main.columns = df_main.columns.str.strip()
        st.write("📋 主表欄位：", list(df_main.columns))
        st.dataframe(df_main.head())

    except Exception as e:
        st.error(f"❌ 主表讀取失敗：{e}")
        st.stop()

    # 對應主表必要欄位
    st.markdown("---")
    st.subheader("📌 對應主表欄位")
    col_id = st.selectbox("🔢 項次欄：", df_main.columns, key="col_id")
    col_desc = st.selectbox("🔖 說明欄：", df_main.columns, key="col_desc")
    col_unit = st.selectbox("📏 單位欄：", df_main.columns, key="col_unit")

    if st.button("✅ 確認並開始查詢", key="confirm_main"):
        df = (
            df_main.rename(columns={col_desc: "項目及說明", col_id: "項次", col_unit: "單位"})
                   .query('`項目及說明`.notna() and `項次`.notna()')
                   .assign(
                       項目及說明=lambda d: d["項目及說明"].astype(str).str.replace("　", "").str.strip(),
                       項次=lambda d: d["項次"].astype(str)
                   )
        )
        st.session_state.df_ready = df
        st.session_state.selected_items = {}
        st.session_state.refresh = False

# —— 處理植栽規格表
if plant_file:
    # 讀取植栽表
    sheet_plant = st.selectbox("請選擇植栽表工作表：", xls_plant.sheet_names)
    skip_plant = st.number_input("跳過植栽表前幾列？", min_value=0, value=0)
    try:
        df_plant = read_excel_safely(plant_file, sheet_name=sheet_plant, skiprows=skip_plant)
        df_plant.columns = df_plant.columns.str.strip()
        st.write("📋 植栽表欄位：", list(df_plant.columns))
        st.dataframe(df_plant.head())
    except Exception as e:
        st.error(f"❌ 植栽表讀取失敗：{e}")
        st.stop()

    # 對應植栽表必要欄位
    st.markdown("---")
    st.subheader("📌 對應植栽表欄位")
    p_col_group = st.selectbox("🔢 群組欄：", df_plant.columns, key="p_col_group")
    p_col_spec = st.selectbox("🔖 規格說明欄：", df_plant.columns, key="p_col_spec")
    p_col_name = st.selectbox("🔖 品種欄：", df_plant.columns, key="p_col_name")

    df_plant_clean = (
        df_plant.rename(columns={
            p_col_group: "group",
            p_col_spec: "說明",
            p_col_name: "品種"
        })
        .dropna(subset=["group", "說明", "品種"] )
    )
    # 欄位型態
    df_plant_clean["group"] = df_plant_clean["group"].astype(int)
    df_plant_clean["說明"] = df_plant_clean["說明"].astype(str)
    df_plant_clean["品種"] = df_plant_clean["品種"].astype(str)

    # 搜尋及勾選植栽
    st.subheader("🌸 植栽規格查詢")
    kw_plant = st.text_input("🔍 搜尋植栽關鍵字（可多個，用 , 、 或 ， 分隔）：", key="kw_plant")

    # 1️⃣ 拆出所有關鍵字
    keywords = [k.strip() for k in re.split(r"[,，、]", kw_plant) if k.strip()]

    # 2️⃣ 只有有輸入才篩，多關鍵字以 or 方式組成正則
    if keywords:
        pattern = "|".join(map(re.escape, keywords))
        df_pla_filt = df_plant_clean[
            df_plant_clean["品種"].str.contains(pattern, na=False)
        ]
    else:
        # 空白時只顯示前 5 筆
        df_pla_filt = df_plant_clean.head(5)

    df_pla_filt = df_pla_filt.sort_values("group").reset_index(drop=True)

    for _, row in df_pla_filt.iterrows():
        label = f"{row['group']}｜{row['品種']}，{row['說明']}"
        cb = f"plant_{row['group']}_{row['品種']}"
        checked = cb in st.session_state.selected_items
        if st.checkbox(label, key=cb, value=checked):
            st.session_state.selected_items[cb] = {
                "項次": str(row["group"]),
                "項目及說明": f"{row['品種']}，{row['說明']}",
                "單位": "株",
                "項次數值": float(row["group"])
            }
        else:
            st.session_state.selected_items.pop(cb, None)

# —— 工項關鍵字查詢及彙整 ——
if "df_ready" in st.session_state and st.session_state.df_ready is not None:
    df = st.session_state.df_ready

    st.subheader("🚧 工項規格查詢")
    # 關鍵字查詢
    kw = st.text_input("🔍 查詢工項關鍵字：（可多個，用 , 、 或 ， 分隔）", "技術工", key="kw_item")
    kws = [x.strip() for x in re.split(r"[，,、]", kw) if x.strip()]
    sort_input = st.checkbox("依輸入順序排列", value=False)


    if kws:
        frames = []
        for i, w in enumerate(kws):
            tmp = df[df["項目及說明"].str.contains(w, na=False) | df["項次"].str.contains(w, na=False)].copy()
            tmp["輸入順序"] = i
            tmp["項次數值"] = tmp["項次"].str.extract(r"(\d+)")[0].astype(float)
            frames.append(tmp)
        filt = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["項目及說明","單位"])
        # 排序
        if sort_input:
            filt = filt.sort_values(by=["輸入順序","項次數值"]).reset_index(drop=True)
        else:
            filt = filt.sort_values(by=["項次數值"]).reset_index(drop=True)

        st.write(f"共找到 {len(filt)} 筆資料，請勾選保留：")
        for idx, row in filt.iterrows():
            raw = str(row["項次"])  # 原始可能是 "分析表33"、"1.329" 等
            pid = raw.split(".", 1)[1] if raw.startswith("1.") else raw
            label = f"{pid}｜{row['項目及說明']}"
            key = f"item_{pid}|{idx}"  # 用純數字當 key
            checked = key in st.session_state.selected_items
            if st.checkbox(label, key=key, value=checked):
                st.session_state.selected_items[key] = {
                    **row.to_dict(),
                    "項次": pid,  # 也把存進去的「項次」換成純數字
                    "項次數值": float(pid)  # 更新排序用欄位
                }
            else:
                st.session_state.selected_items.pop(key, None)
        # 重新整理
        if st.button("🔁 重新查詢/整理彙總", key="btn_refresh"):
            # 1. 清空你自己管理的選項
            st.session_state.selected_items = {}

            # 2. 把所有以 item_ 或 plant_ 開頭的 checkbox state 也設為 False
            for cb_key in list(st.session_state.keys()):
                if cb_key.startswith("item_") or cb_key.startswith("plant_"):
                    st.session_state[cb_key] = False

    # 彙整 & 下載
    if st.session_state.selected_items:
        st.markdown("### ✅ 你保留的工項")
        df_sel = pd.DataFrame(list(st.session_state.selected_items.values()))
        df_sel["純項次"] = df_sel["項次"].astype(str).str.extract(r"(\d+)")[0].astype(int)
        df_sel = df_sel.sort_values(by="純項次").reset_index(drop=True)
        df_sel["項次"] = df_sel["純項次"].astype(str)
        disp = df_sel.drop(columns=["純項次","輸入順序","數量","單價","複價","備註"], errors="ignore")
        st.dataframe(disp)
        csv = disp.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 下載勾選工項", data=csv, file_name="保留工項.csv", mime="text/csv")
    else:
        st.info("尚未選取任何工項")
