import streamlit as st
import pdfplumber
import pandas as pd
import io

# 1. 網頁基本設定
st.set_page_config(page_title="AI 財報解析助手", layout="wide")
st.title("🛡️ 專業財報 AI 解析助手 (NVIDIA 10-K 優化版)")

# 2. 精準關鍵字字典 (根據 nvda test.pdf 內容調整)
KEYWORDS = {
    "revenue": ["Revenue"],
    "cost_of_sales": ["Cost of revenue"],
    "receivables": ["Accounts receivable, net"],
    "payables": ["Accounts payable"],
    "current_assets": ["Total current assets"],
    "current_liabilities": ["Total current liabilities"],
    "equity": ["Total shareholders' equity"]
}

# 報表區段標題
SECTION_TITLES = ["CONSOLIDATED BALANCE SHEETS", "CONSOLIDATED STATEMENTS OF INCOME"]

# 3. 強化版數值清洗函數
def clean_val(v):
    if v is None or v == "": return 0
    # 處理 $ 符號、逗號、空格以及括號負號
    s = str(v).replace("$", "").replace(",", "").replace(" ", "").replace("(", "-").replace(")", "")
    try: return float(s)
    except: return 0

# 4. 上傳介面
uploaded_file = st.file_uploader("📤 請上傳 NVIDIA 財報 PDF", type="pdf")

if uploaded_file:
    with st.spinner('🔍 正在精準提取數據...'):
        # 正確初始化數據字典 (修正之前的 TypeError)
        data = {k: [0.0, 0.0] for k in KEYWORDS.keys()}
        found_status = {k: False for k in KEYWORDS.keys()}
        
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # 智慧定位頁面
                if text and any(title in text.upper() for title in SECTION_TITLES):
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row or not row[0]: continue
                            item_name = str(row[0]).replace("\n", " ").strip()
                            
                            for key, kws in KEYWORDS.items():
                                if any(kw.lower() == item_name.lower() for kw in kws):
                                    # 提取該行中所有非零數字
                                    nums = []
                                    for cell in row[1:]:
                                        val = clean_val(cell)
                                        if val != 0: nums.append(val)
                                    
                                    if len(nums) >= 2:
                                        data[key] = [nums[0], nums[1]]
                                        found_status[key] = True
                                    elif len(nums) == 1:
                                        data[key] = [nums[0], data[key][1]]
                                        found_status[key] = True
                                    break

        # --- 5. 計算指標 ---
        def calc_days(total, curr_v, prev_v):
            avg = (curr_v + prev_v) / 2 if prev_v != 0 else curr_v
            return 365 / (total / avg) if total != 0 and avg != 0 else 0

        res_rec_days = calc_days(data['revenue'][0], data['receivables'][0], data['receivables'][1])
        res_pay_days = calc_days(data['cost_of_sales'][0], data['payables'][0], data['payables'][1])
        curr_ratio = (data['current_assets'][0] / data['current_liabilities'][0] * 100) if data['current_liabilities'][0] != 0 else 0

        # --- 6. 結果呈現 ---
        df_display = pd.DataFrame({
            "財務指標": ["流動比率 (%)", "應收帳款天數 (平均)", "應付帳款天數 (平均)", "淨值 (百萬)", "本期營收 (百萬)", "本期成本 (百萬)"],
            "本期 (Jan 26, 2025)": [
                f"{curr_ratio:.2f}%", f"{res_rec_days:.1f} 天", f"{res_pay_days:.1f} 天", 
                f"{data['equity'][0]:,.0f}", f"{data['revenue'][0]:,.0f}", f"{data['cost_of_sales'][0]:,.0f}"
            ],
            "上期 (Jan 28, 2024)": [
                "-", "-", "-", f"{data['equity'][1]:,.0f}", f"{data['revenue'][1]:,.0f}", f"{data['cost_of_sales'][1]:,.0f}"
            ]
        })

        st.subheader("📋 NVIDIA 財務數據分析")
        st.table(df_display)

        # --- 7. 下載按鈕 ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 下載 Excel 報表",
            data=output.getvalue(),
            file_name="NVIDIA_Analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
