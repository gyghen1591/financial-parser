import streamlit as st
import pdfplumber
import pandas as pd
import io

# 設定網頁標題
st.set_page_config(page_title="專業財報 AI 解析", layout="wide")
st.title("🛡️ 專業財報 AI 解析助手 (智慧分頁定位版)")

# 強化版關鍵字字典
KEYWORDS = {
    "revenue": ["Total net sales", "Total revenue", "Operating revenue", "營業收入", "营业收入"],
    "cost_of_sales": ["Cost of sales", "Cost of revenue", "Cost of goods sold", "營業成本", "营业成本"],
    "receivables": ["Accounts receivable, net", "Accounts receivable", "應收帳款", "应收账款"],
    "payables": ["Accounts payable", "Accounts payable and accrued liabilities", "應付帳款", "应付账款"],
    "current_assets": ["Total current assets", "流動資產合計", "流动资产合计"],
    "current_liabilities": ["Total current liabilities", "流動負債合計", "流动负债合计"],
    "equity": ["Total shareholders' equity", "Total equity", "權益總額", "所有者权益合计"]
}

# 報表標題定位 (確保抓對頁面)
SECTION_TITLES = ["CONSOLIDATED BALANCE SHEETS", "CONSOLIDATED STATEMENTS OF INCOME", "資產負債表", "損益表"]

def clean_val(v):
    if v is None or v == "": return 0
    s = str(v).replace(",", "").replace(" ", "").replace("(", "-").replace(")", "").replace("$", "")
    try: return float(s)
    except: return 0

uploaded_file = st.file_uploader("上傳財報 PDF (支援 10-K / 台股 / 陸股)", type="pdf")

if uploaded_file:
    with st.spinner('🔍 智慧掃描報表中...這可能需要一點時間...'):
        data = {k: [0.0, 0.0] for k in KEYWORDS.keys()}
        found_status = {k: False for k in KEYWORDS.keys()}
        
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # 只有當頁面包含報表關鍵標題時，才深入解析表格
                if text and any(title in text.upper() for title in SECTION_TITLES):
                    tables = page.extract_tables()
                    for table in tables:
                        df = pd.DataFrame(table)
                        for _, row in df.iterrows():
                            if not row[0]: continue
                            item = str(row[0]).replace("\n", " ").strip()
                            
                            for key, kws in KEYWORDS.items():
                                if any(kw.lower() in item.lower() for kw in kws):
                                    # 過濾掉非數字欄位，抓取前兩筆有效數字
                                    nums = [clean_val(c) for c in row[1:] if clean_val(c) != 0]
                                    if len(nums) >= 2:
                                        data[key] = [nums[0], nums[1]]
                                        found_status[key] = True
                                    elif len(nums) == 1:
                                        data[key] = [nums[0], data[key][1] if data[key][1] != 0 else 0.0]
                                        found_status[key] = True
                                    break

        # --- 計算指標 (同前) ---
        # ... (計算邏輯與之前相同) ...
        
        # 顯示警示與結果 (同前)
        st.success("解析完成！")
        # ... (顯示表格與 Excel 下載邏輯) ...
