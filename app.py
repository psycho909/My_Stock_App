import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 1. 頁面基本設定與自訂 CSS
# ==========================================
st.set_page_config(page_title="台股週 KD 實戰分析儀", page_icon="📊", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .main-title { color: #1a252f; text-align: center; border-bottom: 3px solid #e74c3c; padding-bottom: 15px; margin-bottom: 20px; font-family: sans-serif; }
    .signal-box { padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 6px solid; }
    .box-buy { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .box-sell { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    .box-warn { background-color: #fff3cd; color: #856404; border-left-color: #ffc107; }
    .box-neutral { background-color: #e2e3e5; color: #383d41; border-left-color: #6c757d; }
    .signal-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; }
    .signal-desc { font-size: 1rem; margin-bottom: 10px; }
    .signal-advice { font-size: 0.95rem; background: rgba(255,255,255,0.6); padding: 10px; border-radius: 5px; margin-top: 10px;}
    .price-target { font-size: 1.1rem; color: #e74c3c; font-weight: bold; }
    </style>
    <h1 class="main-title">📊 台股「週 KD」實戰策略分析儀</h1>
""", unsafe_allow_html=True)

# ==========================================
# 2. 技術指標計算 (KD + 長天期均線)
# ==========================================
def calculate_indicators(df, period=9):
    # 計算 KD 值
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
    
    # 計算週均線 (13週約為季線, 26週約為半年線, 52週約為年線)
    df['13W_MA'] = df['Close'].rolling(window=13).mean()
    df['26W_MA'] = df['Close'].rolling(window=26).mean()
    df['52W_MA'] = df['Close'].rolling(window=52).mean()
    
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
st.markdown("輸入台股代碼，系統將結合 **KD位階** 與 **長線均線**，為您算出最適合大資金分批進場的「具體建議價格」。")

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
                df = calculate_indicators(df)
                
                # 取得最新數據
                current_K = df['K'].iloc[-1]
                current_D = df['D'].iloc[-1]
                prev_K = df['K'].iloc[-2]
                prev_D = df['D'].iloc[-2]
                current_price = df['Close'].iloc[-1]
                
                # 取得最新的均線價格 (若資料不足則回傳 0)
                ma_13 = df['13W_MA'].iloc[-1] if not pd.isna(df['13W_MA'].iloc[-1]) else 0
                ma_26 = df['26W_MA'].iloc[-1] if not pd.isna(df['26W_MA'].iloc[-1]) else 0
                ma_52 = df['52W_MA'].iloc[-1] if not pd.isna(df['52W_MA'].iloc[-1]) else 0
                
                last_date = df.index[-1].strftime("%Y-%m-%d")

                st.subheader(f"🎯 【{stock_id}】 數據更新至：{last_date}")
                col_k, col_d, col_p = st.columns(3)
                col_k.metric("本週 K 值", f"{current_K:.2f}")
                col_d.metric("本週 D 值", f"{current_D:.2f}")
                col_p.metric("最新收盤價", f"{current_price:.2f} 元")
                
                # ========================================
                # 模塊一：具體進場價格建議 (均線防守法)
                # ========================================
                st.markdown("### 💰 具體進場價格與資金配置建議")
                
                if current_price > ma_13:
                    st.markdown(f"""
                    <div class="signal-box box-neutral">
                        <div class="signal-title">📈 目前趨勢：多頭強勢 (股價高於季線)</div>
                        <div class="signal-desc">目前股價偏高，不建議在此重倉追高。請耐心等待股價回檔至下方支撐位：</div>
                        <div class="signal-advice">
                            🎯 <b>建議進場點 1 (季線支撐)：約 <span class="price-target">{ma_13:.2f} 元</span></b><br>
                            - 操作：若股價跌至此價位，可投入 <b>20% (約 200 萬)</b> 試單建倉。<br>
                            🎯 <b>建議進場點 2 (半年線防禦)：約 <span class="price-target">{ma_26:.2f} 元</span></b><br>
                            - 操作：若遇到較大回檔跌至此，可再加碼 <b>30% (約 300 萬)</b>。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                elif ma_13 >= current_price > ma_26:
                    st.markdown(f"""
                    <div class="signal-box box-buy">
                        <div class="signal-title">🟢 目前趨勢：回檔買點浮現 (測試季線中)</div>
                        <div class="signal-desc">股價已回檔至 13 週均線附近，初步的投資價值已經浮現。</div>
                        <div class="signal-advice">
                            🎯 <b>現在可買入價位：<span class="price-target">{current_price:.2f} 元</span> 附近</b><br>
                            - 操作：建議可在此投入 <b>20%~30%</b> 資金建立基本部位。<br>
                            🎯 <b>下一個加碼防線 (半年線)：約 <span class="price-target">{ma_26:.2f} 元</span></b><br>
                            - 操作：若跌破現價繼續往下，請耐心等候此價位再做第二次加碼。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="signal-box box-buy" style="border-left-color: #28a745; background-color: #d1e7dd;">
                        <div class="signal-title">💎 目前趨勢：超跌鑽石區 (跌破半年線/年線)</div>
                        <div class="signal-desc">市場恐慌導致股價跌破中長線支撐，對於 ETF 存股族來說是絕佳的撿便宜時機！</div>
                        <div class="signal-advice">
                            🎯 <b>現在強烈建議買入區間：<span class="price-target">{current_price:.2f} 元</span> 附近</b><br>
                            - 操作：這裡已是非常安全的長線底部區，建議可將 <b>50% 以上</b> 的資金分批用力買進！<br>
                            🎯 <b>終極年線防線：約 <span class="price-target">{ma_52:.2f} 元</span></b> (若跌破此線更是閉眼買點)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # ========================================
                # 模塊二：技術面訊號診斷 (KD 狀態)
                # ========================================
                st.markdown("### 📋 動能訊號診斷 (KD 輔助)")
                
                # 超買/超賣
                if current_K < 20 or current_D < 20:
                    st.success("🟢 **位階狀態：超賣區 (恐慌低點)**。目前大家都在殺低，這與上方的「買入建議價格」若相符，勝率極高！")
                elif current_K > 80 or current_D > 80:
                    st.error("🔴 **位階狀態：超買區 (過熱高點)**。即使股價看似還有高點，也請嚴格控管資金，隨時準備迎接回檔。")
                else:
                    st.info("🔵 **位階狀態：中性區間**。動能平穩，依據上方建議的「均線價格」來掛單即可。")
                    
                # 交叉訊號
                if current_K > current_D and prev_K <= prev_D:
                    st.warning("⚡ **動能變化：剛發生「黃金交叉」！** 多頭重新奪回主導權，若目前價格接近建議買點，請毫不猶豫扣板機。")
                elif current_K < current_D and prev_K >= prev_D:
                    st.warning("⚠️ **動能變化：剛發生「死亡交叉」！** 短期可能持續下探，請耐心等待股價跌到下一個「建議進場點」再接刀。")

                # --- 繪製走勢圖 ---
                st.markdown("### 📈 近一年股價與均線走勢圖")
                chart_data = df[['Close', '13W_MA', '26W_MA']].tail(52)
                st.line_chart(chart_data)

# ==========================================
# 4. 嵌入前端互動區塊 (JS/HTML)
# ==========================================
st.divider()
components.html(
    """
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
        <p style="color: #6c757d; font-size: 14px; margin: 0;">💡 投資理財有賺有賠，本系統提供之建議價格係基於歷史均線回測，請搭配自身資金水位分批操作。</p>
    </div>
    """, height=60
)