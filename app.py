import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 1. 頁面基本設定與自訂 CSS (UI/UX 區塊)
# ==========================================
st.set_page_config(page_title="台股週 KD 實戰分析", page_icon="📊", layout="centered")

st.markdown("""
    <style>
    /* 隱藏官方選單與浮水印 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 自訂標題與版面配置 */
    .main-title {
        color: #1a252f;
        text-align: center;
        border-bottom: 3px solid #e74c3c;
        padding-bottom: 15px;
        margin-bottom: 20px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 狀態卡片設計 */
    .status-card {
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 15px;
        font-weight: bold;
        text-align: center;
        font-size: 1.1rem;
    }
    .status-safe { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .status-warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .status-danger { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .status-info { background-color: #cce5ff; color: #004085; border: 1px solid #b8daff; }
    </style>
    
    <h1 class="main-title">📊 台股「週 KD」進出場訊號分析儀</h1>
""", unsafe_allow_html=True)

# ==========================================
# 2. KD 值核心計算邏輯 (Python 後端區塊)
# ==========================================
def calculate_kd(df, period=9):
    """計算標準 KD 值 (預設 9 個週期)"""
    # 計算 9 週期內的最高價與最低價
    df['9W_High'] = df['High'].rolling(window=period).max()
    df['9W_Low'] = df['Low'].rolling(window=period).min()
    
    # 計算 RSV (未成熟隨機值)
    df['RSV'] = 100 * ((df['Close'] - df['9W_Low']) / (df['9W_High'] - df['9W_Low']))
    df['RSV'] = df['RSV'].fillna(50) # 遇到空值補 50
    
    # 計算 K 值與 D 值 (初始值設為 50)
    K_list, D_list = [50], [50]
    for rsv in df['RSV']:
        k = (2/3) * K_list[-1] + (1/3) * rsv
        d = (2/3) * D_list[-1] + (1/3) * k
        K_list.append(k)
        D_list.append(d)
        
    df['K'] = K_list[1:]
    df['D'] = D_list[1:]
    return df

def fetch_stock_data(stock_id):
    """抓取台股資料，自動判斷上市(.TW)或上櫃(.TWO)"""
    ticker = f"{stock_id}.TW"
    # 抓取過去 2 年的「週線」資料 (interval="1wk")
    df = yf.Ticker(ticker).history(period="2y", interval="1wk")
    if df.empty:
        # 如果上市找不到，找上櫃
        ticker = f"{stock_id}.TWO"
        df = yf.Ticker(ticker).history(period="2y", interval="1wk")
    return df

# ==========================================
# 3. 使用者介面與互動
# ==========================================
st.markdown("輸入台股代碼（如 `00878`, `2330`），系統將自動抓取週線資料，並判斷目前的 KD 位階與黃金交叉訊號。")

col1, col2 = st.columns([3, 1])
with col1:
    stock_id = st.text_input("請輸入台股代碼：", value="006208")
with col2:
    st.markdown("<br>", unsafe_allow_html=True) # 排版微調
    search_btn = st.button("🔍 分析", use_container_width=True, type="primary")

st.divider()

if search_btn:
    if not stock_id:
        st.warning("⚠️ 請輸入股票代碼！")
    else:
        with st.spinner("正在計算技術指標，請稍候..."):
            df = fetch_stock_data(stock_id)
            
            if df.empty:
                st.error("❌ 找不到該檔股票，請確認代碼是否正確。")
            else:
                # 執行 KD 計算
                df = calculate_kd(df)
                
                # 取得最近兩週的 KD 數值
                current_K = df['K'].iloc[-1]
                current_D = df['D'].iloc[-1]
                prev_K = df['K'].iloc[-2]
                prev_D = df['D'].iloc[-2]
                current_price = df['Close'].iloc[-1]
                last_date = df.index[-1].strftime("%Y-%m-%d")

                # --- 分析結果顯示 ---
                st.subheader(f"🎯 【{stock_id}】 數據更新至：{last_date}")
                
                col_k, col_d, col_p = st.columns(3)
                col_k.metric("本週 K 值", f"{current_K:.2f}")
                col_d.metric("本週 D 值", f"{current_D:.2f}")
                col_p.metric("最新收盤價", f"{current_price:.2f} 元")
                
                # --- 核心邏輯判斷 (超買/超賣/黃金交叉) ---
                st.markdown("### 💡 實戰策略判定")
                
                # 1. 判斷超買/超賣
                if current_K < 20 or current_D < 20:
                    st.markdown('<div class="status-safe">🟢 找低點 (超賣區)：目前股價處於低檔區，市場恐慌超跌，是尋找買點的好時機！</div>', unsafe_allow_html=True)
                elif current_K > 80 or current_D > 80:
                    st.markdown('<div class="status-danger">🔴 避開高點 (超買區)：目前股價過熱，隨時可能面臨回檔壓力，建議空手觀望，切勿追高！</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="status-info">🔵 中性區間：目前股價位階居中，請搭配均線或基本面輔助觀察。</div>', unsafe_allow_html=True)
                    
                # 2. 判斷黃金交叉/死亡交叉
                if current_K > current_D and prev_K <= prev_D:
                    # 如果 K < 30 的黃金交叉，訊號最強
                    if current_K < 30:
                        st.markdown('<div class="status-safe">⭐ 強烈進場訊號：低檔發生「週 KD 黃金交叉」！勝率極高，可考慮分批建倉。</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="status-warning">⚡ 週 KD 黃金交叉：趨勢轉強，但位階偏高，請控制資金比例。</div>', unsafe_allow_html=True)
                elif current_K < current_D and prev_K >= prev_D:
                    st.markdown('<div class="status-danger">⚠️ 週 KD 死亡交叉：趨勢轉弱，建議保守應對，留意下行風險。</div>', unsafe_allow_html=True)

                # --- 繪製簡單的趨勢圖 ---
                st.markdown("### 📈 近半年週 KD 走勢圖")
                # 取最近 26 週 (半年) 的資料來畫圖
                chart_data = df[['K', 'D']].tail(26)
                st.line_chart(chart_data)

# ==========================================
# 4. 嵌入前端互動區塊 (JS/HTML)
# ==========================================
st.divider()
components.html(
    """
    <div style="background-color: #2c3e50; padding: 20px; border-radius: 8px; color: white; text-align: center;">
        <h4 style="margin-top: 0;">🛠️ 前端互動擴充區 (JavaScript)</h4>
        <p>您可以利用 JS 將上述分析結果做成浮動視窗，或串接 TradingView 圖表。</p>
        <button onclick="showAlert()" 
            style="background: #e74c3c; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px;">
            測試 JS 點擊事件
        </button>
    </div>

    <script>
        function showAlert() {
            alert("✅ JavaScript 運作正常！未來可以在這裡開發更炫的看盤動畫！");
        }
    </script>
    """,
    height=150
)