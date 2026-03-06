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
    
    /* RWD 儀表板網格系統 */
    .metric-card {
        background-color: #ffffff; border: 1px solid #e9ecef; border-radius: 12px;
        padding: 15px 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex; flex-direction: column; justify-content: center;
    }
    .metric-title { font-size: 0.95rem; color: #6c757d; font-weight: bold; margin-bottom: 8px; }
    .metric-value { font-size: 1.6rem; font-weight: 900; color: #212529; margin: 0; }
    .metric-delta { font-size: 1rem; font-weight: bold; margin-top: 5px; }
    
    .text-red { color: #dc3545; }
    .text-green { color: #28a745; }
    .text-gray { color: #6c757d; font-weight: normal;}

    .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }

    @media (max-width: 768px) {
        .grid-4 { grid-template-columns: repeat(2, 1fr); }
        .metric-value { font-size: 1.3rem; }
        .metric-title { font-size: 0.85rem; }
        .metric-delta { font-size: 0.9rem; }
    }
    
    /* 快捷鍵按鈕微調 */
    div.stButton > button {
        border-radius: 20px;
        padding: 2px 10px;
    }
    </style>
    <h1 class="main-title">🦅 台股終極決策系統</h1>
""", unsafe_allow_html=True)

# ==========================================
# 2. 狀態管理 (Session State) 與 名稱解析
# ==========================================
# 初始化搜尋歷史與輸入框狀態
if 'history' not in st.session_state:
    st.session_state.history = ['006208', '00878', '2330'] # 預設快捷鍵
if 'stock_input' not in st.session_state:
    st.session_state.stock_input = '006208'

def set_stock_input(ticker_or_name):
    """點擊快捷鍵時，將值塞入輸入框的回呼函式"""
    st.session_state.stock_input = ticker_or_name

@st.cache_data(ttl=86400) # 快取一天
def load_stock_mapping():
    """抓取證交所 OpenAPI 建立名稱與代碼的字典"""
    # 預設一些常見的 ETF 與股票，確保網路斷線時依然可用
    mapping = {
        "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息",
        "006208": "富邦台50", "00919": "群益台灣精選高息", "2330": "台積電",
        "2317": "鴻海", "2454": "聯發科", "4746": "台耀", "00981A": "主動統一台股增長"
    }
    try:
        # 抓取台股上市清單
        res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=5)
        if res.status_code == 200:
            for item in res.json():
                mapping[item['Code']] = item['Name']
    except:
        pass
    return mapping

def resolve_stock(user_input, mapping):
    """解析輸入：判斷是代碼還是名稱"""
    user_input = str(user_input).strip()
    
    # 如果輸入的是名稱 (中文字)
    if not user_input.isdigit():
        for code, name in mapping.items():
            if user_input in name: # 支援模糊搜尋，如輸入「富邦台」會配對到「富邦台50」
                return code, name
        return user_input, user_input # 找不到則原樣回傳
        
    # 如果輸入的是代碼
    name = mapping.get(user_input, "未知名稱")
    return user_input, name

# 載入台股字典
stock_dict = load_stock_mapping()

# ==========================================
# 3. HTML 卡片產生器
# ==========================================
def create_html_card(title, value_str, delta=0, pct=0, neutral_text=None):
    if neutral_text:
        color_class = "text-gray"
        delta_html = neutral_text
    else:
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
# 4. 核心資料抓取模組
# ==========================================
def fetch_current_price(ticker):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")
        if len(hist) >= 2:
            return {"price": hist['Close'].iloc[-1], "change": hist['Close'].iloc[-1] - hist['Close'].iloc[-2], "pct": ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100}
        return None
    except:
        return None

def fetch_dividend_yield(ticker, current_price):
    try:
        tk = yf.Ticker(ticker)
        divs = tk.dividends
        if divs is not None and not divs.empty:
            now = pd.Timestamp.now(tz=divs.index.tz) if divs.index.tz else pd.Timestamp.now()
            recent_divs = divs[divs.index >= now - pd.DateOffset(years=1)]
            if not recent_divs.empty:
                return recent_divs.sum(), (recent_divs.sum() / current_price) * 100
    except:
        pass
    return 0.0, 0.0

@st.cache_data(ttl=60)
def fetch_global_indices():
    tickers = {"台股大盤": "^TWII", "標普 500": "^GSPC", "那斯達克": "^IXIC", "黃金期貨": "GC=F"}
    results = {}
    for name, ticker in tickers.items():
        data = fetch_current_price(ticker)
        if data: results[name] = data
    return results

def calculate_indicators(df, period=9):
    df['9W_High'], df['9W_Low'] = df['High'].rolling(period).max(), df['Low'].rolling(period).min()
    df['RSV'] = (100 * ((df['Close'] - df['9W_Low']) / (df['9W_High'] - df['9W_Low']))).fillna(50)
    K_list, D_list = [50], [50]
    for rsv in df['RSV']:
        k = (2/3) * K_list[-1] + (1/3) * rsv
        d = (2/3) * D_list[-1] + (1/3) * k
        K_list.append(k); D_list.append(d)
    df['K'], df['D'] = K_list[1:], D_list[1:]
    df['13W_MA'], df['26W_MA'], df['52W_MA'] = df['Close'].rolling(13).mean(), df['Close'].rolling(26).mean(), df['Close'].rolling(52).mean()
    return df

def fetch_stock_data(stock_id):
    ticker = f"{stock_id}.TW"
    df = yf.Ticker(ticker).history(period="2y", interval="1wk")
    if df.empty: df = yf.Ticker(f"{stock_id}.TWO").history(period="2y", interval="1wk")
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
            news_list.append({'title': item.find('title').text, 'link': item.find('link').text})
    except: pass
    return news_list

# ==========================================
# 5. 操作面板與快捷鍵區
# ==========================================
# 顯示快捷鍵歷史紀錄
st.markdown("⚡ **近期搜尋 / 快捷鍵：**")
hist_cols = st.columns(5)
for idx, h_ticker in enumerate(st.session_state.history):
    # 解析歷史代碼的名稱顯示在按鈕上
    _, h_name = resolve_stock(h_ticker, stock_dict)
    hist_cols[idx].button(f"{h_name}", key=f"btn_{h_ticker}", on_click=set_stock_input, args=(h_ticker,))

# 輸入區塊並列排版 (使用 session_state 綁定)
col_input, col_btn_analyze, col_btn_refresh = st.columns([3, 2, 1])

with col_input:
    # 這裡的 key="stock_input" 讓它與 session_state 完美連動
    raw_input = st.text_input("🔍 支援輸入台股代碼或名稱 (如: 00878, 台積電)：", key="stock_input")

with col_btn_analyze:
    st.markdown("<br>", unsafe_allow_html=True)
    search_btn = st.button("🚀 啟動完整分析", use_container_width=True, type="primary")

with col_btn_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 重整", use_container_width=True):
        st.rerun()

# 進行名稱解析！把使用者輸入的轉回純代碼與真實名稱
target_ticker, target_name = resolve_stock(raw_input, stock_dict)

# 當輸入新標的時，更新搜尋歷史紀錄 (維持最多 5 個)
if raw_input and target_ticker not in st.session_state.history and target_ticker.isdigit():
    st.session_state.history.insert(0, target_ticker)
    if len(st.session_state.history) > 5:
        st.session_state.history.pop()

st.markdown("<br>", unsafe_allow_html=True)

# 抓取個股與殖利率資料
stock_data = fetch_current_price(f"{target_ticker}.TW")
if not stock_data or stock_data['price'] == 0:
    stock_data = fetch_current_price(f"{target_ticker}.TWO")

ttm_div, div_yield = 0.0, 0.0
if stock_data and stock_data['price'] > 0:
    ttm_div, div_yield = fetch_dividend_yield(f"{target_ticker}.TW", stock_data['price'])

# ==========================================
# 6. 【首頁關注】網格顯示 (加入中英文合併顯示)
# ==========================================
st.markdown("#### 🎯 首頁關注")

# 這裡把名稱與代碼合併顯示，例如：富邦台50 (006208)
display_title = f"{target_name} ({target_ticker})"

if stock_data and stock_data['price'] > 0:
    card_stock = create_html_card(display_title, f"{stock_data['price']:,.2f}", stock_data['change'], stock_data['pct'])
else:
    card_stock = create_html_card(display_title, "無資料", neutral_text="-")

if div_yield > 0:
    card_yield = create_html_card("估算年化殖利率", f"{div_yield:.2f} %", neutral_text=f"近一年配息: {ttm_div:.2f} 元")
else:
    card_yield = create_html_card("估算年化殖利率", "無配息", neutral_text="-")

st.markdown(f'<div class="grid-2">{card_stock}{card_yield}</div>', unsafe_allow_html=True)

# ==========================================
# 7. 【全球大盤】網格顯示
# ==========================================
st.markdown("#### 🌐 全球大盤與指數")
global_data = fetch_global_indices()

cards_html = ""
for name, data in global_data.items():
    cards_html += create_html_card(f"📊 {name}", f"{data['price']:,.2f}", data['change'], data['pct'])

st.markdown(f'<div class="grid-4">{cards_html}</div>', unsafe_allow_html=True)
st.divider()

# ==========================================
# 8. 主體分析模塊 (點擊按鈕後觸發)
# ==========================================
if search_btn:
    if not target_ticker:
        st.warning("⚠️ 請輸入股票代碼或名稱！")
    else:
        with st.spinner(f"正在分析 {target_name} ({target_ticker})，請稍候..."):
            df = fetch_stock_data(target_ticker)
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
                        st.error(f"🚨 VIX恐慌指數: {vix_value:.2f}")
                    elif vix_value >= 20:
                        st.warning(f"⚠️ VIX恐慌指數: {vix_value:.2f}")
                    else:
                        st.success(f"✅ VIX恐慌指數: {vix_value:.2f}")
                    
                    st.markdown("### 📰 最新財經頭條")
                    if news_data:
                        for item in news_data:
                            st.markdown(f'<div class="news-item"><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a></div>', unsafe_allow_html=True)

                with left_col:
                    st.markdown("### 💰 系統實戰策略建議")
                    if vix_value >= 30 and current_price <= ma_13:
                        st.markdown(f"""
                        <div class="signal-box box-blackswan">
                            <div class="signal-title">🚨 危機入市模式啟動</div>
                            <div class="signal-advice">
                                🎯 第一批 (現價)：<span class="price-target">{current_price:.2f} 元</span><br>
                                🎯 第二批 (半年線)：約 <span class="price-target">{ma_26:.2f} 元</span><br>
                                🎯 第三批 (年線)：約 <span class="price-target">{ma_52:.2f} 元</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif current_price > ma_13:
                        st.markdown(f"""
                        <div class="signal-box box-warn">
                            <div class="signal-title">📈 多頭強勢區 (請忍住不買)</div>
                            <div class="signal-advice">🎯 耐心等待季線回檔：約 <span class="price-target">{ma_13:.2f} 元</span></div>
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
                    st.line_chart(df[['Close', '13W_MA', '26W_MA', '52W_MA']].tail(52))