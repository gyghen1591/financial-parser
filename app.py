import streamlit as st
import pdfplumber
import pandas as pd
import io

# 1. 網頁基本設定
st.set_page_config(page_title="AI 財報解析助手", layout="wide")
st.title("🛡️ 專業財報 AI 解析助手 (智慧定位 + 平均值計算)")
st.info("支援：台灣 (繁體)、美國 (10-K)、中國 (簡體) 的 PDF 財報解析。")

# 2. 強化版關鍵字字典 (涵蓋三地慣用語)
KEYWORDS = {
    "revenue": ["營業收入", "Total net sales", "Total revenue", "Operating revenue", "营业收入"],
    "cost_of_sales": ["營業成本", "Cost of sales", "Cost of revenue", "Cost of goods sold", "营业成本"],
    "receivables": ["應收帳款淨額", "Accounts receivable, net", "Accounts receivable", "應收帳款", "应收账款"],
    "payables": ["應付帳款", "Accounts payable", "Accounts payable and accrued liabilities", "应付账款"],
    "current_assets": ["流動資產合計", "Total current assets", "流动资产合计", "流動資產"],
    "current_liabilities": ["流動負債合計", "Total current liabilities", "流动负债合计", "流動負債"],
    "equity": ["權益總額", "Total equity", "Total shareholders' equity", "所有者权益合计", "歸屬於母公司"]
}

# 報表區段標題 (用於智慧定位頁面)
SECTION_TITLES = ["CONSOLIDATED BALANCE SHEETS", "CONSOLIDATED STATEMENTS OF INCOME", "資產負債表", "損益表"]

# 3. 數值清洗函數
def clean_val(v):
    if v is None or v == "": return 0
    s = str(v).replace(",", "").replace(" ", "").replace("(", "-").replace(")", "").replace("$", "")
    try: return float(s)
    except: return 0

# 4. 上傳介面
uploaded_file = st.file_uploader("📤 請上傳財報 PDF 檔案", type="pdf")

if uploaded_file:
    with st.spinner('🔍 正在智慧掃描報表並提取數據...'):
        # 格式：{key: [本期值, 上期值]}
        data = {k: [0.0, 0.0] for k in KEYWORDS.keys()}
        found_status = {k: False for k in KEYWORDS.keys()}
        
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # 智慧定位：只有包含報表標題的頁面才深入解析表格
                if text and any(title in text.upper() for title in SECTION_TITLES):
                    tables = page.extract_tables()
                    for table in tables:
                        df = pd.DataFrame(table)
                        for _, row in df.iterrows():
                            if not row[0]: continue
                            item_name = str(row[0]).replace("\n", " ").strip()
                            
                            for key, kws in KEYWORDS.items():
                                if any(kw.lower() in item_name.lower() for kw in kws):
                                    # 抓取該列中所有看起來像數字的儲存格
                                    nums = [clean_val(c) for c in row[1:] if clean_val(c) != 0]
                                    if len(nums) >= 2:
                                        data[key] = [nums[0], nums[1]]
                                        found_status[key] = True
                                    elif len(nums) == 1:
                                        # 若只抓到一個數字，保留為本期，不覆蓋已有的上期數據
                                        data[key] = [nums[0], data[key][1]]
                                        found_status[key] = True
                                    break

        # --- 5. 數據缺失檢測 ---
        missing_items = [k for k, found in found_status.items() if not found]
        if missing_items:
            st.warning(f"⚠️ 警告：以下項目未能在 PDF 中尋獲，可能導致計算不準：{', '.join(missing_items)}")
        else:
            st.success("✅ 所有關鍵數據提取成功！")

        # --- 6. 指標計算邏輯 (平均值) ---
        def calc_days(total, curr_val, prev_val):
            # 公式：365 / (總額 / 平均餘額)
            avg = (curr_val + prev_val) / 2 if prev_val != 0 else curr_val
            if total == 0 or avg == 0: return 0
            return 365 / (total / avg)

        res_rec_days = calc_days(data['revenue'][0], data['receivables'][0], data['receivables'][1])
        res_pay_days = calc_days(data['cost_of_sales'][0], data['payables'][0], data['payables'][1])
        curr_ratio = (data['current_assets'][0] / data['current_liabilities'][0] * 100) if data['current_liabilities'][0] != 0 else 0

        # --- 7. 顯示結果表格 ---
        df_display = pd.DataFrame({
            "財務指標項目": ["流動比率 (%)", "應收帳款天數 (平均)", "應付帳款天數 (平均)", "淨值 (股東權益)", "本期營業收入", "本期營業成本"],
            "本期解析數據": [
                f"{curr_ratio:.2f}%", f"{res_rec_days:.1f} 天", f"{res_pay_days:.1f} 天", 
                f"{data['equity'][0]:,.0f}", f"{data['revenue'][0]:,.0f}", f"{data['cost_of_sales'][0]:,.0f}"
            ],
            "上期解析數據": [
                "-", "-", "-", f"{data['equity'][1]:,.0f}", f"{data['revenue'][1]:,.0f}", f"{data['cost_of_sales'][1]:,.0f}"
            ]
        })

        st.subheader("📋 財務分析結果預覽")
        st.table(df_display)

        # --- 8. Excel 匯出按鈕 (此按鈕通常顯示在表格下方) ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False, sheet_name='財務數據分析')
        
        st.download_button(
            label="📥 下載 Excel 分析報表",
            data=buffer.getvalue(),
            file_name=f"Analysis_{uploaded_file.name.split('.')[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
