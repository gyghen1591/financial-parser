import streamlit as st
import pdfplumber
import pandas as pd
import io

st.set_page_config(page_title="專業財報分析助手", layout="wide")

st.title("📊 專業財報分析 (含缺失數據自動檢測)")

# 擴充後的關鍵字，增加美股 10-K 兼容性
KEYWORDS = {
    "revenue": ["營業收入", "Total net sales", "Total revenue", "Operating revenue", "營業收入淨額"],
    "cost_of_sales": ["營業成本", "Cost of sales", "Cost of revenue", "Cost of goods sold"],
    "receivables": ["應收帳款", "Accounts receivable", "Accounts receivable, net", "應收帳款淨額"],
    "payables": ["應付帳款", "Accounts payable", "Accounts payable and accrued liabilities"],
    "current_assets": ["流動資產合計", "Total current assets", "流动资产合计"],
    "current_liabilities": ["流動負債合計", "Total current liabilities", "流动负债合计"],
    "equity": ["權益總額", "Total equity", "Total shareholders' equity", "所有者权益合计"]
}

def clean_val(v):
    if v is None or v == "": return 0
    s = str(v).replace(",", "").replace(" ", "").replace("(", "-").replace(")", "")
    try: return float(s)
    except: return 0

uploaded_file = st.file_uploader("請上傳財報 PDF", type="pdf")

if uploaded_file:
    with st.spinner('正在精確解析並檢查數據完整性...'):
        # 格式：{key: [本期, 上期]}
        data = {k: [0.0, 0.0] for k in KEYWORDS.keys()}
        found_status = {k: False for k in KEYWORDS.keys()} # 紀錄是否抓到本期數據
        
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    df = pd.DataFrame(table)
                    for _, row in df.iterrows():
                        if not row[0]: continue
                        item = str(row[0]).replace(" ", "").replace("\n", "")
                        
                        for key, kws in KEYWORDS.items():
                            if any(kw in item for kw in kws):
                                nums = [clean_val(c) for c in row[1:] if clean_val(c) != 0]
                                if len(nums) >= 2:
                                    data[key] = [nums[0], nums[1]]
                                    found_status[key] = True
                                elif len(nums) == 1:
                                    data[key] = [nums[0], 0.0]
                                    found_status[key] = True
                                break

        # --- 1. 缺失數據檢測區 ---
        missing_items = [k for k, found in found_status.items() if not found]
        if missing_items:
            st.warning(f"⚠️ 偵測到部分數據缺失：{', '.join(missing_items)}。這可能是因為表格跨頁或關鍵字不符。")
            st.info("💡 建議：請檢查 PDF 中的科目名稱是否與程式預設關鍵字一致。")
        else:
            st.success("✅ 所有關鍵核心數據皆已成功提取！")

        # --- 2. 指標計算 ---
        def calc_days(total, start_val, end_val):
            avg = (start_val + end_val) / 2 if start_val != 0 else end_val
            if total == 0 or avg == 0: return 0
            return 365 / (total / avg)

        res_rec_days = calc_days(data['revenue'][0], data['receivables'][1], data['receivables'][0])
        res_pay_days = calc_days(data['cost_of_sales'][0], data['payables'][1], data['payables'][0])
        
        # --- 3. 顯示結果表格 ---
        # 這裡加入顏色標註，若為 0 則顯示為紅色 N/A
        def format_val(val, is_currency=True):
            if val == 0: return "N/A (未抓取)"
            return f"{val:,.0f}" if is_currency else f"{val:.2f}"

        df_display = pd.DataFrame({
            "財務指標": ["流動比率", "應收帳款天數 (平均)", "應付帳款天數 (平均)", "淨值", "本期營收", "本期營業成本"],
            "本期解析結果": [
                f"{(data['current_assets'][0]/data['current_liabilities'][0]*100):.2f}%" if data['current_liabilities'][0] != 0 else "N/A",
                f"{res_rec_days:.1f} 天",
                f"{res_pay_days:.1f} 天",
                format_val(data['equity'][0]),
                format_val(data['revenue'][0]),
                format_val(data['cost_of_sales'][0])
            ],
            "上期解析結果": [
                "-", "-", "-", format_val(data['equity'][1]), format_val(data['revenue'][1]), format_val(data['cost_of_sales'][1])
            ]
        })

        st.subheader("📋 財務分析報表")
        st.table(df_display)

        # 匯出 Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False, sheet_name='財務分析')
        
        st.download_button("📥 下載 Excel 報表", data=output.getvalue(), file_name="analysis_report.xlsx")
