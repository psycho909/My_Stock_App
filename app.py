import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET

# ==========================================
# 1. 頁面基本設定與 RWD 自訂 CSS
# ==========================================
st.set_page_config(page_title="台股實戰分析儀", page_icon="🦅", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .main-title { color: #1a252f; text-align: center; border-bottom: 3px solid #e74c3c; padding-bottom: 15px; margin-bottom: 20px; font-family: sans-serif; font-size: 1.8rem;}
    
    /* 分析結果卡片設計 */
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
    
    /* ========================================= */
    /* 🚀 專屬 RWD 儀表板網格系統 (突破 Streamlit 限制) */
    /* ========================================= */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 15px 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-title { font-size: 0.95rem; color: #6c757d; font-weight: bold; margin-bottom: 8px; }
    .metric-value { font-size: 1.6rem; font-weight: 900; color: #212529; margin: 0; }
    .metric-delta { font-size: 1rem; font-weight: bold; margin-top: 5px; }
    
    /* 統一台灣習慣：紅漲綠跌 */
    .text-red { color: #dc3545; }
    .text-green { color: #28a745; }
    .text-gray { color: #6c757d; font-weight: normal;}

    /* 網格佈局：首頁關注 (永遠 2 欄) */
    .grid-2 {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }

    /* 網格佈局：全球大盤 (PC 4 欄) */
    .grid-4 {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }

    /* 📱 手機版專屬設定：螢幕寬度小於 768px 時觸發 */
    @media (max-width: 768px) {
        .grid-4 {
            grid-template-columns: repeat(2, 1fr); /* 手機版強制變成 2 欄 */
        }
        .metric-value { font-size: 1.3rem; } /* 手機版字體稍微縮小避免跑版 */
        .metric-title { font-size: 0.85rem; }
        .metric-delta { font-size: 0.9rem; }
    }
    </style>
    <h1 class="main-title">🦅 台股終極決策系統</h1>
""", unsafe_allow_html=True)

# ==========================================
# 2. HTML 卡片產生器 (取代原廠 st.metric)
# ==========================================
def create_html_card(title, value_str, delta=0, pct=0, neutral_text=None):
    """將數據轉換成我們自訂的 HTML 卡片，強制紅漲綠跌"""
    if neutral_text:
        # 專門給「殖利率」用的中性顯示
        color_class = "text-gray"
        delta_html = neutral_text
    else:
        # 股價漲跌邏輯
        if delta > 0:
            color_class = "text-red"
            delta_html = f"▲ {abs(delta):.2f} ({abs(pct):.2f}%)"
        elif delta < 0:
            color_class = "text-green"
            delta_html = f"▼ {abs(delta):.2f} ({abs(pct):.2f}%)"
        else:
            color_class = "text-gray"
            delta_html = "平盤"
            
    return f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value_str}</div>
        <div class="metric-delta {color_class}">{delta_html}</div>
    </div>
    """

# ==========================================
# 3. 核心資料抓取模組
# ==========================================
def fetch_current_price(ticker):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")
        if len(hist) >= 2:
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            change = current_price - prev_price
            pct_change = (change / prev_price) * 100
            return {"price": current_price, "change": change, "pct": pct_change}
        return None
    except:
        return None

def fetch_dividend_yield(ticker, current_price):
    try:
        tk = yf.Ticker(ticker)
        divs = tk.dividends
        if divs is not None and not divs.empty:
            now = pd.Timestamp.now(tz=divs.index.tz) if divs.index.tz else pd.Timestamp.now()
            one_year_ago = now - pd.DateOffset(years=1)
            recent_divs = divs[divs.index >= one_year_ago]
            if not recent_divs.empty:
                total_dividend = recent_divs.sum()
                if current_price > 0:
                    div_yield = (total_dividend / current_price) * 100
                    return total_dividend, div_yield
    except:
        pass
    return 0.0, 0.0

@st.cache_data(ttl=60)
def fetch_global_indices():
    tickers = {"台股大盤": "^TWII", "標普 500": "^GSPC", "那斯達克": "^IXIC", "黃金期貨": "GC=F"}
    results = {}
    for name, ticker in tickers.items():
        data = fetch_current_price(ticker)
        if data:
            results[name] = data
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
            news_list.append({'title': title, 'link': link})
    except:
        pass
    return news_list

# ==========================================
# 4. 操作面板與輸入區
# ==========================================
col_input, col_btn_analyze, col_btn_refresh = st.columns([3, 2, 1])
with col_input:
    stock_id = st.text_input("🔍 請輸入觀察台股代碼：", value="00878")
with col_btn_analyze:
    st.markdown("<br>", unsafe_allow_html=True)
    search_btn = st.button("🚀 啟動完整分析", use_container_width=True, type="primary")
with col_btn_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 重整", use_container_width=True):
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# 抓取個股與殖利率資料
stock_ticker = f"{stock_id}.TW"
stock_data = fetch_current_price(stock_ticker)
if not stock_data or stock_data['price'] == 0:
    stock_ticker = f"{stock_id}.TWO"
    stock_data = fetch_current_price(stock_ticker)

ttm_div, div_yield = 0.0, 0.0
if stock_data and stock_data['price'] > 0:
    ttm_div, div_yield = fetch_dividend_yield(stock_ticker, stock_data['price'])

# ==========================================
# 5. 【首頁關注】網格顯示 (永遠 2 欄)
# ==========================================
st.markdown("#### 🎯 首頁關注")

# 準備個股卡片 HTML
if stock_data and stock_data['price'] > 0:
    card_stock = create_html_card(f"個股報價 ({stock_id})", f"{stock_data['price']:,.2f}", stock_data['change'], stock_data['pct'])
else:
    card_stock = create_html_card(f"個股報價 ({stock_id})", "無資料", neutral_text="-")

# 準備殖利率卡片 HTML
if div_yield > 0:
    card_yield = create_html_card("估算年化殖利率", f"{div_yield:.2f} %", neutral_text=f"近一年配息: {ttm_div:.2f} 元")
else:
    card_yield = create_html_card("估算年化殖利率", "無配息", neutral_text="-")

# 注入 HTML 網格 (自動套用上面的 grid-2 CSS)
st.markdown(f"""
    <div class="grid-2">
        {card_stock}
        {card_yield}
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 6. 【全球大盤】網格顯示 (PC 4 欄 / 手機 2 欄)
# ==========================================
st.markdown("#### 🌐 全球大盤與指數")
global_data = fetch_global_indices()

cards_html = ""
for name, data in global_data.items():
    cards_html += create_html_card(f"📊 {name}", f"{data['price']:,.2f}", data['change'], data['pct'])

# 注入 HTML 網格 (自動套用 grid-4，並在手機版自動觸發 media query 變成 2 欄)
st.markdown(f"""
    <div class="grid-4">
        {cards_html}
    </div>
""", unsafe_allow_html=True)

st.divider()

# ==========================================
# 7. 主體分析模塊 (點擊按鈕後觸發)
# ==========================================
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
                current_price = df['Close'].iloc[-1]
                ma_13 = df['13W_MA'].iloc[-1] if not pd.isna(df['13W_MA'].iloc[-1]) else 0
                ma_26 = df['26W_MA'].iloc[-1] if not pd.isna(df['26W_MA'].iloc[-1]) else 0
                ma_52 = df['52W_MA'].iloc[-1] if not pd.isna(df['52W_MA'].iloc[-1]) else 0

                left_col, right_col = st.columns([2, 1])

                with right_col:
                    st.markdown("### 🌍 市場情緒與時事")
                    if vix_value >= 30:
                        st.error(f"🚨 VIX恐慌指數: {vix_value:.2f} (極度恐慌)")
                    elif vix_value >= 20:
                        st.warning(f"⚠️ VIX恐慌指數: {vix_value:.2f} (市場警戒)")
                    else:
                        st.success(f"✅ VIX恐慌指數: {vix_value:.2f} (情緒穩定)")
                    
                    st.markdown("### 📰 最新財經頭條")
                    if news_data:
                        for item in news_data:
                            title = item['title']
                            link = item['link']
                            st.markdown(f"""
                            <div class="news-item">
                                <a href="{link}" target="_blank" class="news-title">{title}</a>
                            </div>
                            """, unsafe_allow_html=True)

                with left_col:
                    st.markdown("### 💰 系統實戰策略建議")
                    if vix_value >= 30 and current_price <= ma_13:
                        st.markdown(f"""
                        <div class="signal-box box-blackswan">
                            <div class="signal-title">🚨 危機入市模式啟動</div>
                            <div class="signal-desc">全球發生系統性風險。這是十年難得一見的重分配機會！</div>
                            <div class="signal-advice">
                                🎯 第一批 (現價)：<span class="price-target">{current_price:.2f} 元</span> (投入 20%)<br>
                                🎯 第二批 (半年線)：約 <span class="price-target">{ma_26:.2f} 元</span> (投入 30%)<br>
                                🎯 第三批 (年線)：約 <span class="price-target">{ma_52:.2f} 元</span> (重壓 50%)
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif current_price > ma_13:
                        st.markdown(f"""
                        <div class="signal-box box-warn">
                            <div class="signal-title">📈 多頭強勢區 (請忍住不買)</div>
                            <div class="signal-advice">
                                🎯 耐心等待季線回檔：約 <span class="price-target">{ma_13:.2f} 元</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="signal-box box-buy">
                            <div class="signal-title">🟢 常態回檔買點 (測試長線支撐)</div>
                            <div class="signal-advice">
                                🎯 目前的建議進場價：<span class="price-target">{current_price:.2f} 元</span><br>
                                🎯 下方防守線：<span class="price-target">{ma_26:.2f} ~ {ma_52:.2f} 元</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("### 📈 近一年走勢與防守均線")
                    chart_data = df[['Close', '13W_MA', '26W_MA', '52W_MA']].tail(52)
                    st.line_chart(chart_data)