import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# 1. 網頁基本設定
st.set_page_config(page_title="全球財報 AI 解析助手", layout="wide")
st.title("🌐 全球財報 AI 解析助手 (美/台/陸/日股通用)")
st.info("支援語系：英文 (US)、繁體中文 (TW)、簡體中文 (CN)、日文 (JP)")

# 2. 多國語言關鍵字字典 (涵蓋美、台、陸、日股常見名稱)
KEYWORDS = {
    "revenue": [
        "Revenue", "Net sales", "Total revenue", "Operating revenue", 
        "營業收入", "营业收入", "売上高"
    ],
    "cost_of_sales": [
        "Cost of sales", "Cost of revenue", "Cost of goods sold", 
        "營業成本", "营业成本", "売上原価"
    ],
    "receivables": [
        "Accounts receivable", "Trade receivables", "Notes receivable", 
        "應收帳款", "应收账款", "売掛金", "受取手形"
    ],
    "payables": [
        "Accounts payable", "Trade payables", 
        "應付帳款", "应付账款", "買掛金", "支払手形"
    ],
    "current_assets": [
        "Total current assets", "流動資產合計", "流动资产合计", "流動資産合計"
    ],
    "current_liabilities": [
        "Total current liabilities", "流動負債合計", "流动负债合计", "流動負債合計"
    ],
    "equity": [
        "Total shareholders' equity", "Total equity", "Stockholders' equity",
        "權益總額", "歸屬於母公司業主之權益", "所有者权益合计", "純資産合計", "株主資本"
    ]
}

# 3. 數值清洗函數 (移除貨幣符號、處理括號負號、過濾非數字字元)
def clean_val(v):
    if v is None: return 0
    s = str(v).replace("(", "-").replace(")", "").replace("△", "-")
    s = re.sub(r'[^0-9.-]', '', s)
    try:
        return float(s) if s and s != "." else 0
    except:
        return 0

# 4. 上傳介面
uploaded_file = st.file_uploader("📤 請上傳財報 PDF (支援各國格式)", type="pdf")

if uploaded_file:
    with st.spinner('🔍 正在掃描並識別各國財報格式...'):
        # 初始化數據 {項目: [本期, 上期]}
        data = {k: [0.0, 0.0] for k in KEYWORDS.keys()}
        
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or not row[0]: continue
                        
                        # 清理科目名稱
                        item_name = str(row[0]).replace("\n", " ").strip()
                        
                        for key, kws in KEYWORDS.items():
                            # 使用「部分匹配」來增加通用性
                            if any(kw.lower() in item_name.lower() for kw in kws):
                                # 抓取該行中所有數字
                                nums = []
                                for cell in row[1:]:
                                    val = clean_val(cell)
                                    if val != 0:
                                        nums.append(val)
                                
                                # 根據抓到的數字數量分配本期與上期
                                if len(nums) >= 2:
                                    data[key] = [nums[0], nums[1]]
                                elif len(nums) == 1:
                                    # 若只有一筆，更新本期，不變動原本的上期數據
                                    data[key] = [nums[0], data[key][1]]
                                break

        # 5. 指標計算邏輯 (通用財務公式)
        def calc_days(total, curr, prev):
            avg = (curr + prev) / 2 if prev != 0 else curr
            return 365 / (total / avg) if total != 0 and avg != 0 else 0

        res_rec_days = calc_days(data['revenue'][0], data['receivables'][0], data['receivables'][1])
        res_pay_days = calc_days(data['cost_of_sales'][0], data['payables'][0], data['payables'][1])
        
        c_assets = data['current_assets'][0]
        c_liabs = data['current_liabilities'][0]
        curr_ratio = (c_assets / c_liabs * 100) if c_liabs != 0 else 0

        # 6. 結果表格呈現
        df_display = pd.DataFrame({
            "財務指標 (Financial Metrics)": [
                "流動比率 (Current Ratio %)", 
                "應收帳款天數 (Receivable Days)", 
                "應付帳款天數 (Payable Days)", 
                "股東權益 (Total Equity)", 
                "營業收入 (Revenue)", 
                "營業成本 (Cost of Sales)"
            ],
            "本期數據 (Current)": [
                f"{curr_ratio:.2f}%", f"{res_rec_days:.1f} 天", f"{res_pay_days:.1f} 天", 
                f"{data['equity'][0]:,.0f}", f"{data['revenue'][0]:,.0f}", f"{data['cost_of_sales'][0]:,.0f}"
            ],
            "上期數據 (Prior)": [
                "-", "-", "-", 
                f"{data['equity'][1]:,.0f}", f"{data['revenue'][1]:,.0f}", f"{data['cost_of_sales'][1]:,.0f}"
            ]
        })

        st.subheader("📋 跨國財報分析結果")
        st.table(df_display)
        
        # 7. Excel 下載
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False)
        st.download_button("📥 下載通用分析報表 (Excel)", output.getvalue(), "Global_Finance_Analysis.xlsx")
