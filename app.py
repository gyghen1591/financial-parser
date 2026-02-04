import streamlit as st
import pdfplumber
import pandas as pd
import io

# 1. 網頁基本設定
st.set_page_config(page_title="AI 財報解析助手", layout="wide")
st.title("🛡️ 專業財報 AI 解析助手 (智慧定位 + 平均值計算)")
st.info("支援：台股、美股 (10-K)、陸股 PDF 財報解析。")

# 2. 強化版關鍵字字典
KEYWORDS = {
    "revenue": ["Total net sales", "Total revenue", "Operating revenue", "營業收入", "营业收入", "Revenue"],
    "cost_of_sales": ["Cost of sales", "Cost of revenue", "Cost of goods sold", "營業成本", "营业成本", "Cost of revenue"],
    "receivables": ["Accounts receivable, net", "Accounts receivable", "應收帳款", "应收账款"],
    "payables": ["Accounts payable", "Accounts payable and accrued liabilities", "應付帳款", "应收账款"],
    "current_assets": ["Total current assets", "流動資產合計", "流动资产合计"],
    "current_liabilities": ["Total current liabilities", "流動負債合計", "流动负债合计"],
    "equity": ["Total shareholders' equity", "Total equity", "權益總額", "所有者权益合计"]
}

# 智慧定位標題
SECTION_TITLES = ["CONSOLIDATED BALANCE SHEETS", "CONSOLIDATED STATEMENTS OF INCOME", "資產負債表", "損益表"]

# 3. 數值清洗函數
def clean_val(v):
    if v is None or v == "": return 0
    s = str(v).replace(",", "").replace(" ", "").replace("$", "").replace("(", "-").replace(")", "")
    try: return float(s)
    except: return 0

# 4. 上傳介面
uploaded_file = st.file_uploader("📤 請上傳財報 PDF 檔案", type="pdf")

if uploaded_file:
    with st.spinner('🔍 正在智慧定位並提取數據...'):
        # --- 關鍵修正處：正確初始化 data 字典 ---
        data = {k: [0.0, 0.0] for k in KEYWORDS.keys()} 
        found_status = {k: False for k in KEYWORDS.keys()}
        
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and any(title in text.upper() for title in SECTION_TITLES):
                    tables = page.extract_tables()
                    for table in tables:
                        df = pd.DataFrame(table)
                        for _, row in df.iterrows():
                            if not row[0]: continue
                            item_name = str(row[0]).replace("\n", " ").strip()
                            
                            for key, kws in KEYWORDS.items():
                                if any(kw.lower() in item_name.lower() for kw in kws):
                                    nums = [clean_val(c) for c in row[1:] if clean_val(c) != 0]
                                    if len(nums) >= 2:
                                        data[key] = [nums[0], nums[1]]
                                        found_status[key] = True
                                    elif len(nums) == 1:
                                        data[key] = [nums[0], data[key][1]]
                                        found_status[key] = True
                                    break

        # --- 5. 數據缺失提醒 ---
        missing = [k for k, found in found_status.items() if not found]
        if missing:
            st.warning(f"⚠️ 偵測到數據缺失：{', '.join(missing)}")
        else:
            st.success("✅ 數據提取成功！")

        # --- 6. 核心指標計算 ---
        def calc_days(total, curr_v, prev_v):
            avg = (curr_v + prev_v) / 2 if prev_v != 0 else curr_v
            if total == 0 or avg == 0: return 0
            return 365 / (total / avg)

        res_rec_days = calc_days(data['revenue'][0], data['receivables'][0], data['receivables'][1])
        res_pay_days = calc_days(data['cost_of_sales'][0], data['payables'][0], data['payables'][1])
        curr_ratio = (data['current_assets'][0] / data['current_liabilities'][0] * 100) if data['current_liabilities'][0] != 0 else 0

        # --- 7. 結果呈現 ---
        df_display = pd.DataFrame({
            "財務指標": ["流動比率 (%)", "應收帳款天數 (平均)", "應付帳款天數 (平均)", "淨值", "本期營收", "本期營業成本"],
            "本期數據": [
                f"{curr_ratio:.2f}%", f"{res_rec_days:.1f} 天", f"{res_pay_days:.1f} 天", 
                f"{data['equity'][0]:,.0f}", f"{data['revenue'][0]:,.0f}", f"{data['cost_of_sales'][0]:,.0f}"
            ],
            "上期數據": [
                "-", "-", "-", f"{data['equity'][1]:,.0f}", f"{data['revenue'][1]:,.0f}", f"{data['cost_of_sales'][1]:,.0f}"
            ]
        })

        st.subheader("📋 財務分析報表")
        st.table(df_display)

        # --- 8. Excel 匯出 ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Financial_Analysis')
        
        st.download_button(
            label="📥 下載 Excel 報表",
            data=output.getvalue(),
            file_name=f"Report_{uploaded_file.name.split('.')[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
