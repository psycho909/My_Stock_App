import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd

# ==========================================
# 1. 頁面基本設定 (Python)
# ==========================================
st.set_page_config(page_title="台股 EPS 查詢系統", page_icon="📈", layout="centered")

# ==========================================
# 2. 注入自訂 CSS (您的前端主戰場 1)
# 這裡可以使用 CSS 徹底改變 Streamlit 的預設外觀
# ==========================================
st.markdown("""
    <style>
    /* 隱藏 Streamlit 官方的右上角選單與底部浮水印 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 自訂主標題樣式 */
    .custom-title {
        color: #2c3e50;
        text-align: center;
        font-family: 'Arial', sans-serif;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        margin-bottom: 25px;
    }
    
    /* 自訂所有按鈕的樣式 (覆蓋預設) */
    .stButton>button {
        background-color: #3498db !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        transition: 0.3s !important;
    }
    .stButton>button:hover {
        background-color: #2980b9 !important;
        transform: scale(1.02) !important;
    }
    </style>
    
    <h1 class="custom-title">📈 台股 EPS 季報與年度加總查詢</h1>
""", unsafe_allow_html=True)

# ==========================================
# 3. 建立使用者輸入介面 (Python 結合 Streamlit 排版)
# ==========================================
col1, col2 = st.columns(2)
with col1:
    stock_id = st.text_input("請輸入股票代號 (例如: 4746)", value="4746")
with col2:
    year = st.text_input("請輸入查詢年度 (西元年)", value="2025")

btn_col1, btn_col2 = st.columns([1, 1])
with btn_col1:
    search_btn = st.button("🔍 開始查詢", use_container_width=True)
with btn_col2:
    if st.button("🔄 重設 / 清除", use_container_width=True):
        st.rerun()

st.divider()

# ==========================================
# 4. 核心資料處理與爬蟲邏輯 (純 Python)
# ==========================================
if search_btn:
    if not stock_id or not year:
        st.warning("⚠️ 請輸入完整的股票代號與年度！")
    else:
        with st.spinner(f"正在抓取 【{stock_id}】 {year} 年的資料..."):
            url = "https://api.finmindtrade.com/api/v4/data"
            parameter = {
                "dataset": "TaiwanStockFinancialStatements",
                "data_id": str(stock_id),
                "start_date": f"{year}-01-01",
                "end_date": f"{year}-12-31"
            }

            try:
                res = requests.get(url, params=parameter)
                data = res.json()

                if data.get("msg") != "success" or len(data.get("data", [])) == 0:
                    st.error("❌ 找不到相關資料，可能是股票代號錯誤，或該年度財報尚未公布。")
                else:
                    df = pd.DataFrame(data["data"])
                    eps_df = df[df['type'] == 'EPS'].copy()

                    if eps_df.empty:
                        st.error("❌ 找不到該年度的 EPS 數據。")
                    else:
                        st.success(f"✅ 成功獲取 【{stock_id}】 {year} 年 EPS 資料！")
                        
                        total_eps = 0.0
                        results = []

                        for index, row in eps_df.iterrows():
                            date = row['date']
                            eps_value = float(row['value'])
                            total_eps += eps_value

                            if "-03-" in date: quarter = "Q1 (第一季)"
                            elif "-06-" in date or "-05-" in date: quarter = "Q2 (第二季)"
                            elif "-09-" in date or "-08-" in date: quarter = "Q3 (第三季)"
                            elif "-12-" in date or "-11-" in date: quarter = "Q4 (第四季)"
                            else: quarter = date

                            results.append({"季度": quarter, "單季 EPS (元)": eps_value})

                        # 顯示年度總和與表格
                        st.metric(label=f"💰 {year} 年累計 EPS 總和", value=f"{total_eps:.2f} 元")
                        st.table(pd.DataFrame(results))
                        st.caption("💡 若只顯示到 Q3，代表 Q4 年報尚未公布。")

            except Exception as e:
                st.error(f"⚠️ 連線錯誤: {e}")

# ==========================================
# 5. 嵌入完整的 HTML/JS 互動區塊 (您的前端主戰場 2)
# 這裡是一個獨立的 Iframe，可以盡情發揮您的 JavaScript 實力
# ==========================================
components.html(
    """
    <div style="text-align: center; margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 10px; border: 2px dashed #adb5bd;">
        <h4 style="color: #495057; font-family: sans-serif; margin-bottom: 15px;">👨‍💻 前端技能展示區</h4>
        <button onclick="triggerInteractiveJS()" 
                style="padding: 10px 20px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
            點擊觸發 JavaScript 動畫
        </button>
        <p id="js-output" style="margin-top: 15px; color: #dc3545; font-weight: bold; font-size: 18px; transition: 0.5s;"></p>
    </div>

    <script>
        function triggerInteractiveJS() {
            const output = document.getElementById('js-output');
            output.innerText = '🎉 JS 執行成功！未來可以把 Chart.js 或 D3.js 的動態圖表寫在這個區塊！';
            output.style.transform = 'scale(1.1)';
            setTimeout(() => { output.style.transform = 'scale(1)'; }, 300);
        }
    </script>
    """,
    height=200
)