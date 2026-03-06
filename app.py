import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET

# ==========================================
# 1. 頁面基本設定與自訂 CSS
# ==========================================
st.set_page_config(page_title="台股實戰分析儀 (技術+籌碼+時事)", page_icon="🦅", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .main-title { color: #1a252f; text-align: center; border-bottom: 3px solid #e74c3c; padding-bottom: 15px; margin-bottom: 20px; font-family: sans-serif; }
    .signal-box { padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 6px solid; }
    .box-buy { background-color: #d4edda; color: #155724; border-left-color: #28a745; }
    .box-sell { background-color: #f8d7da; color: #721c24; border-left-color: #dc3545; }
    .box-warn { background-color: #fff3cd; color: #856404; border-left-color: #ffc107; }
    .box-blackswan { background-color: #343a40; color: #f8f9fa; border-left-color: #dc3545; }
    .signal-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; }
    .signal-desc { font-size: 1rem; margin-bottom: 10px; }
    .signal-advice { font-size: 0.95rem; background: rgba(255,255,255,0.8); color:#000; padding: 10px; border-radius: 5px; margin-top: 10px;}
    .price-target { font-size: 1.1rem; color: #e74c3c; font-weight: bold; }
    .news-item { border-bottom: 1px dashed #ced4da; padding: 12px 0; }
    .news-title { font-weight: bold; color: #0056b3; text-decoration: none; font-size: 1.05rem; display: block; margin-bottom: 5px;}
    .news-title:hover { color: #003d82; text-decoration: underline; }
    .news-date { color: #6c757d; font-size: 0.85rem; }
    
    /* 儀表板卡片微調 */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 10px 15px;
        border-radius: 8px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    </style>
    <h1 class="main-title">🦅 台股終極決策系統 (技術分析 + 時事恐慌偵測)</h1>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心資料抓取模組
# ==========================================
@st.cache_data(ttl=60) # 快取 60 秒，避免頻繁重整導致 Yahoo 阻擋
def fetch_global_indices():
    """抓取全球四大指數與黃金的最新報價"""
    # ^TWII: 台股加權, ^GSPC: 標普500, ^DJI: 道瓊, ^IXIC: 那斯達克, GC=F: 黃金期貨
    tickers = {"台股大盤": "^TWII", "標普 500": "^GSPC", "道瓊工業": "^DJI", "那斯達克": "^IXIC", "黃金期貨(盎司)": "GC=F"}
    results = {}
    
    for name, ticker in tickers.items():
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period="5d")
            if len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                change = current_price - prev_price
                pct_change = (change / prev_price) * 100
                results[name] = {"price": current_price, "change": change, "pct": pct_change}
            else:
                results[name] = {"price": 0, "change": 0, "pct": 0}
        except:
            results[name] = {"price": 0, "change": 0, "pct": 0}
    return results

def calculate_indicators(df, period=9):
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

def fetch_vix():
    vix_df = yf.Ticker("^VIX").history(period="5d")
    return vix_df['Close'].iloc[-1] if not vix_df.empty else 20.0

def fetch_taiwan_finance_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    news_list = []
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            news_list.append({'title': title, 'link': link, 'date': pub_date})
    except:
        pass
    return news_list

# ==========================================
# 3. 頂部模塊：全球市場儀表板
# ==========================================
st.markdown("### 🌐 全球即時行情儀表板")
with st.spinner("正在獲取全球最新行情..."):
    global_data = fetch_global_indices()
    
    # 建立 5 個並排的欄位來顯示數據
    cols = st.columns(5)
    for idx, (name, data) in enumerate(global_data.items()):
        if data['price'] > 0:
            # 判斷漲跌幅的顏色 (台灣習慣紅漲綠跌，但 Streamlit 預設是綠漲紅跌)
            # 這裡我們使用 Streamlit 內建的 metric，若要反轉顏色可加上 delta_color="inverse"
            cols[idx].metric(
                label=name, 
                value=f"{data['price']:,.2f}", 
                delta=f"{data['change']:.2f} ({data['pct']:.2f}%)"
            )
        else:
            cols[idx].metric(label=name, value="無資料", delta="-")

st.divider()

# ==========================================
# 4. 主體分析模塊
# ==========================================
st.markdown("結合 **全球恐慌指數 (VIX)**、**即時頭條** 與 **週 KD 均線**，為大資金佈局找出最安全的入市點。")

col1, col2 = st.columns([4, 1])
with col1:
    stock_id = st.text_input("請輸入台股代碼 (如: 006208, 00878)：", value="006208")
with col2:
    st.markdown("<br>", unsafe_allow_html=True) 
    search_btn = st.button("🚀 啟動全方位分析", use_container_width=True, type="primary")

st.divider()

if search_btn:
    if not stock_id:
        st.warning("⚠️ 請輸入股票代碼！")
    else:
        with st.spinner("正在掃描技術指標與總經數據，請稍候..."):
            df = fetch_stock_data(stock_id)
            vix_value = fetch_vix()
            news_data = fetch_taiwan_finance_news()
            
            if df.empty:
                st.error("❌ 找不到該檔股票，請確認代碼是否正確。")
            else:
                df = calculate_indicators(df)
                current_K = df['K'].iloc[-1]
                current_D = df['D'].iloc[-1]
                current_price = df['Close'].iloc[-1]
                ma_13 = df['13W_MA'].iloc[-1] if not pd.isna(df['13W_MA'].iloc[-1]) else 0
                ma_26 = df['26W_MA'].iloc[-1] if not pd.isna(df['26W_MA'].iloc[-1]) else 0
                ma_52 = df['52W_MA'].iloc[-1] if not pd.isna(df['52W_MA'].iloc[-1]) else 0
                last_date = df.index[-1].strftime("%Y-%m-%d")

                left_col, right_col = st.columns([2, 1])

                with right_col:
                    st.markdown("### 🌍 總體經濟與市場情緒")
                    if vix_value >= 30:
                        st.error(f"🚨 恐慌指數 (VIX): {vix_value:.2f} (極度恐慌)")
                        st.markdown("**系統判定：黑天鵝事件/系統性風險！市場正處於非理性拋售。**")
                    elif vix_value >= 20:
                        st.warning(f"⚠️ 恐慌指數 (VIX): {vix_value:.2f} (市場警戒)")
                        st.markdown("**系統判定：市場波動加劇，隨時可能回檔。**")
                    else:
                        st.success(f"✅ 恐慌指數 (VIX): {vix_value:.2f} (情緒穩定)")
                        st.markdown("**系統判定：全球總經環境相對穩定，依技術面操作即可。**")
                    
                    st.markdown("### 📰 Google 最新財經頭條")
                    if news_data:
                        for item in news_data:
                            title = item['title']
                            link = item['link']
                            date_str = item['date'][:22] 
                            st.markdown(f"""
                            <div class="news-item">
                                <a href="{link}" target="_blank" class="news-title">{title}</a>
                                <span class="news-date">🕒 {date_str}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("暫時無法取得新聞，請稍後再試。")

                with left_col:
                    st.markdown(f"### 🎯 【{stock_id}】 數據更新至：{last_date}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("最新收盤價", f"{current_price:.2f} 元")
                    m2.metric("本週 K 值", f"{current_K:.2f}")
                    m3.metric("本週 D 值", f"{current_D:.2f}")
                    
                    st.markdown("### 💰 系統實戰策略建議")
                    
                    if vix_value >= 30 and current_price <= ma_13:
                        st.markdown(f"""
                        <div class="signal-box box-blackswan">
                            <div class="signal-title">🚨 危機入市模式啟動 (黑天鵝/突發利空)</div>
                            <div class="signal-desc">全球發生重大系統性風險。對於大資金部位來說，這是十年難得一見的財富重分配機會！</div>
                            <div class="signal-advice">
                                🎯 <b>【大資金金字塔建倉法】</b><br>
                                1. <b>第一批 (恐慌殺盤)：<span class="price-target">{current_price:.2f} 元</span></b> ➡️ 投入 <b>20%</b> 資金。<br>
                                2. <b>第二批 (跌至半年線)：約 <span class="price-target">{ma_26:.2f} 元</span></b> ➡️ 投入 <b>30%</b> 資金。<br>
                                3. <b>第三批 (跌至年線)：約 <span class="price-target">{ma_52:.2f} 元</span></b> ➡️ 投入 <b>50%</b> 資金 (重壓區)。
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif current_price > ma_13:
                        st.markdown(f"""
                        <div class="signal-box box-warn">
                            <div class="signal-title">📈 多頭強勢區 (請忍住不買)</div>
                            <div class="signal-desc">目前股價偏高，且市場沒有恐慌跡象，不適合大資金單筆進場。</div>
                            <div class="signal-advice">
                                🎯 <b>耐心等待季線回檔：約 <span class="price-target">{ma_13:.2f} 元</span></b><br>
                                - 建議將資金保留，或僅用極小資金定期定額買進。
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="signal-box box-buy">
                            <div class="signal-title">🟢 常態回檔買點 (測試長線支撐)</div>
                            <div class="signal-desc">股價已修正至合理的長天期均線附近。</div>
                            <div class="signal-advice">
                                🎯 <b>目前的建議進場價：<span class="price-target">{current_price:.2f} 元</span></b><br>
                                - 操作：若 KD 也同步進入 20 以下(超賣區)，可投入 <b>30%</b> 資金佈局。<br>
                                🎯 <b>下方防守線 (半年線/年線)：<span class="price-target">{ma_26:.2f} ~ {ma_52:.2f} 元</span></b>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("### 📈 近一年走勢與防守均線")
                    chart_data = df[['Close', '13W_MA', '26W_MA', '52W_MA']].tail(52)
                    st.line_chart(chart_data)