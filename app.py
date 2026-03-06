import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 1. 頁面基本設定與自訂 CSS
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
    .signal-box {
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 6px solid;
    }
    .box-buy { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .box-sell { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    .box-warn { background-color: #fff3cd; color: #856404; border-left-color: #ffc107; }
    .box-neutral { background-color: #e2e3e5; color: #383d41; border-left-color: #6c757d; }
    
    .signal-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; }
    .signal-desc { font-size: 1rem; margin-bottom: 10px; }
    .signal-advice { font-size: 0.95rem; background: rgba(255,255,255,0.6); padding: 10px; border-radius: 5px; }
    </style>
    
    <h1 class="main-title">📊 台股「週 KD」實戰策略分析儀</h1>
""", unsafe_allow_html=True)

# ==========================================
# 2. KD 值計算與資料抓取邏輯
# ==========================================
def calculate_kd(df, period=9):
    df['9W_High'] = df['High'].rolling(window=period).max()
    df['9W_Low'] = df['Low'].rolling(window=period).min()
    df['RSV'] = 100 * ((df['Close'] - df['9W_Low']) / (df['9W_High'] - df['9W_Low']))
    df['RSV'] = df['RSV'].fillna(50)
    
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
    ticker = f"{stock_id}.TW"
    df = yf.Ticker(ticker).history(period="2y", interval="1wk")
    if df.empty:
        ticker = f"{stock_id}.TWO"
        df = yf.Ticker(ticker).history(period="2y", interval="1wk")
    return df

# ==========================================
# 3. 使用者介面與核心診斷邏輯
# ==========================================
st.markdown("輸入台股代碼，系統將自動判斷目前的 **KD位階** 與 **交叉訊號**，並提供實戰資金控管建議。")

col1, col2 = st.columns([3, 1])
with col1:
    stock_id = st.text_input("請輸入台股代碼 (如: 006208, 00878)：", value="006208")
with col2:
    st.markdown("<br>", unsafe_allow_html=True) 
    search_btn = st.button("🔍 執行分析", use_container_width=True, type="primary")

st.divider()

if search_btn:
    if not stock_id:
        st.warning("⚠️ 請輸入股票代碼！")
    else:
        with st.spinner("正在解析籌碼與技術指標，請稍候..."):
            df = fetch_stock_data(stock_id)
            
            if df.empty:
                st.error("❌ 找不到該檔股票，請確認代碼是否正確。")
            else:
                df = calculate_kd(df)
                
                current_K = df['K'].iloc[-1]
                current_D = df['D'].iloc[-1]
                prev_K = df['K'].iloc[-2]
                prev_D = df['D'].iloc[-2]
                current_price = df['Close'].iloc[-1]
                last_date = df.index[-1].strftime("%Y-%m-%d")

                st.subheader(f"🎯 【{stock_id}】 數據更新至：{last_date}")
                
                col_k, col_d, col_p = st.columns(3)
                col_k.metric("本週 K 值", f"{current_K:.2f}")
                col_d.metric("本週 D 值", f"{current_D:.2f}")
                col_p.metric("最新收盤價", f"{current_price:.2f} 元")
                
                st.markdown("### 📋 系統綜合診斷報告")

                # ========================================
                # 診斷一：位階判斷 (超買/超賣/中性)
                # ========================================
                if current_K < 20 or current_D < 20:
                    st.markdown("""
                    <div class="signal-box box-buy">
                        <div class="signal-title">🟢 找低點 (超賣區)</div>
                        <div class="signal-desc">市場目前處於極度恐慌或超跌狀態，大家都在拋售，中長線投資價值浮現。</div>
                        <div class="signal-advice">
                            <b>💡 實戰建議：</b><br>
                            1. <b>切勿急於 All-in：</b> 指標在低檔可能發生「鈍化」（低了還能更低），千萬不要一次把資金打滿。<br>
                            2. <b>試單建倉：</b> 可準備總資金的 <b>20%</b> 開始逢低佈局，或者啟動「定期定額」。<br>
                            3. <b>等待確認：</b> 密切觀察後續是否出現「黃金交叉」來確認真正落底。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                elif current_K > 80 or current_D > 80:
                    st.markdown("""
                    <div class="signal-box box-sell">
                        <div class="signal-title">🔴 避開高點 (超買區)</div>
                        <div class="signal-desc">市場情緒過熱，追價意願雖高，但短線獲利了結的賣壓隨時會出籠。</div>
                        <div class="signal-advice">
                            <b>💡 實戰建議：</b><br>
                            1. <b>嚴格忍住不買：</b> 如果您手上有大筆現金想進場，請「空手觀望」，現在進場極容易買在山頂。<br>
                            2. <b>考慮分批停利：</b> 若手上已有持股且獲利豐厚，可考慮賣出 20%-30% 收回現金，保留戰力。<br>
                            3. 等待指標降溫回到 50 左右的中性區間再作打算。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="signal-box box-neutral">
                        <div class="signal-title">🔵 中性整理區間</div>
                        <div class="signal-desc">目前股價位階居中，沒有明顯的過熱或超跌跡象。</div>
                        <div class="signal-advice">
                            <b>💡 實戰建議：</b> 建議搭配季線(60MA)或半年線(120MA)等均線來輔助判斷支撐與壓力。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # ========================================
                # 診斷二：交叉訊號 (黃金交叉/死亡交叉)
                # ========================================
                if current_K > current_D and prev_K <= prev_D:
                    if current_K < 30:
                        st.markdown("""
                        <div class="signal-box box-buy">
                            <div class="signal-title">⭐ 強烈進場訊號 (低檔黃金交叉)</div>
                            <div class="signal-desc">K 值由下往上突破 D 值，且發生在低檔區，這是長線勝率極高的完美買點！</div>
                            <div class="signal-advice">
                                <b>💡 實戰建議：</b> 跌勢宣告結束，多軍發起反攻。建議可投入 <b>30% - 50%</b> 的資金建立核心部位！
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif current_K > 70:
                        st.markdown("""
                        <div class="signal-box box-warn">
                            <div class="signal-title">⚠️ 誘多風險 (高檔黃金交叉)</div>
                            <div class="signal-desc">雖然發生黃金交叉，但位階已在高檔，上漲空間有限，容易形成假突破。</div>