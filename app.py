import streamlit as st
import pdfplumber
import pandas as pd
import io

# 1. 網頁基本設定
st.set_page_config(page_title="專業財報 AI 解析助手", layout="wide")
st.title("🛡️ 專業財報 AI 解析助手 (智慧定位 + 平均值計算)")
st.info("支援：台股、美股 (10-K)、陸股 PDF 財報。自動計算平均應收/應付帳款週轉天數。")

# 2. 強化版關鍵字字典：涵蓋不同國家財報的慣用語
KEYWORDS = {
    "revenue": ["Total net sales", "Total revenue", "Operating revenue", "營業收入", "营业收入", "Revenue"],
    "cost_of_sales": ["Cost of sales", "Cost of revenue", "Cost of goods sold", "營業成本", "营业成本", "Cost of revenue"],
    "receivables": ["Accounts receivable, net", "Accounts receivable", "應收帳款", "应收账款", "Accounts receivable, net"],
    "payables": ["Accounts payable", "Accounts payable and accrued liabilities", "應付帳款", "应收账款", "Accounts payable"],
    "current_assets": ["Total current assets", "流動資產合計", "流动资产合计", "Total current assets"],
    "current_liabilities": ["Total current liabilities", "流動負債合計", "流动负债合计", "Total current liabilities"],
    "equity": ["Total shareholders' equity", "Total equity", "權益總額", "所有者权益合计", "Total shareholders' equity"]
}

# 智慧定位用標題：幫助程式在百頁 PDF 中直接找到財報頁面
SECTION_TITLES = ["CONSOLIDATED BALANCE SHEETS", "CONSOLIDATED STATEMENTS OF INCOME", "資產負債表", "損益表"]

# 3. 數值清洗函數：處理金額中的逗號、括號、貨幣符號
def clean_val(v):
    if v is None or v == "": return 0
    s = str(v).replace(",", "").replace(" ", "").replace("$", "").replace("(", "-").replace(")", "")
    try: return float(s)
    except: return 0

# 4. 上傳介面
uploaded_file = st.file_uploader("📤 請上傳財報 PDF 檔案", type="pdf")

if uploaded_file:
    with st.spinner('🔍 正在智慧定位並提取數據...'):
        # 格式：{key: [本期值, 上期值]}
        data = {k: [0.0, 0.0] for k in KEYWORDS.items()}
        found_status = {k: False for k in KEYWORDS.keys()}
        
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # 智慧定位：確認頁面是否包含報表標題
                if text and any(title in text.upper() for title in SECTION_TITLES):
                    tables = page.extract_tables()
                    for table in tables:
                        df = pd.DataFrame(table)
                        for _, row in df.iterrows():
                            if not row[0]: continue
                            # 取得科目名稱並進行比對
                            item_name = str(row[0]).replace("\n", " ").strip()
                            
                            for key, kws in KEYWORDS.items():
                                if any(kw.lower() in item_name.lower() for kw in kws):
                                    # 提取該列中前兩個有效數字（通常為本期與上期）
                                    nums = [clean_val(c) for c in row[1:] if clean_val(c) != 0]
                                    if len(nums) >= 2:
                                        data[key] = [nums[0], nums[1]]
                                        found_status[key] = True
                                    elif len(nums) == 1:
                                        # 若只抓到一個數字，更新本期，保留已有的上期數據
                                        data[key] = [nums[0], data[key][1]]
                                        found_status[key] = True
                                    break

        # --- 5. 數據缺失提醒 ---
        missing = [k for k, found in found_status.items() if not found]
        if missing:
            st.warning(f"⚠️ 警告：部分數據缺失 ({', '.join(missing)})，建議檢查 PDF 內容或調整關鍵字。")
        else:
            st.success("✅ 數據提取成功！")

        # --- 6. 核心指標計算 (採用期初期末平均值) ---
        def calc_days(total_amount, curr_val, prev_val):
            # 公式：365 / (營收或成本 / 平均餘額)
            avg_balance = (curr_val + prev_val) / 2 if prev_val != 0 else curr_val
            if total_amount == 0 or avg_balance == 0: return 0
            return 365 / (total_amount / avg_balance)

        res_rec_days = calc_days(data['revenue'][0], data['receivables'][0], data['receivables'][1])
        res_pay_days = calc_days(data['cost_of_sales'][0], data['payables'][0], data['payables'][1])
        curr_ratio = (data['current_assets'][0] / data['current_liabilities'][0] * 100) if data['current_liabilities'][0] != 0 else 0

        # --- 7. 結果呈現 ---
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

        # --- 8. Excel 匯出按鈕 ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False, sheet_name='財務分析報告')
        
        st.download_button(
            label="📥 下載 Excel 分析報表",
            data=buffer.getvalue(),
            file_name=f"Report_{uploaded_file.name.split('.')[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
