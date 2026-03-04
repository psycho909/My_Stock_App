import streamlit as st
import sqlite3
import pandas as pd

# ==========================================
# 1. 資料庫初始化設定 (如果沒有檔案，會自動建立)
# ==========================================
def init_db():
    # 連線到資料庫 (檔案會自動命名為 watchlist.db，存在同一資料夾)
    conn = sqlite3.connect('watchlist.db')
    cursor = conn.cursor()
    # 建立資料表 (如果不存在的話)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            note TEXT,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 每次網頁載入時，確保資料庫已經準備好
init_db()

# ==========================================
# 2. 定義對資料庫的「寫入」與「讀取」功能
# ==========================================
def add_record(stock_id, stock_name, note):
    """將新資料寫入 SQLite"""
    conn = sqlite3.connect('watchlist.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO stocks (stock_id, stock_name, note) 
        VALUES (?, ?, ?)
    ''', (stock_id, stock_name, note))
    conn.commit()
    conn.close()

def get_all_records():
    """讀取資料庫中的所有資料，並轉換成 Pandas 表格"""
    conn = sqlite3.connect('watchlist.db')
    # Pandas 非常強大，可以直接吃 SQL 語法並轉換成表格
    df = pd.read_sql_query('SELECT stock_id AS 股票代號, stock_name AS 股票名稱, note AS 觀察筆記, create_time AS 新增時間 FROM stocks ORDER BY id DESC', conn)
    conn.close()
    return df

# ==========================================
# 3. Streamlit 網頁介面設計
# ==========================================
st.set_page_config(page_title="我的股票觀察名單", page_icon="📁")
st.title("📁 我的股票觀察名單 (SQLite 實戰)")
st.markdown("這是一個串接 SQLite 資料庫的範例，您可以新增資料，並即時顯示在下方。")

# --- 區塊 A：新增資料的表單 ---
# 使用 st.form 可以把輸入框包起來，按下送出按鈕後才一次執行，避免網頁一直重新整理
with st.form("add_stock_form"):
    st.subheader("✍️ 新增觀察標的")
    col1, col2 = st.columns(2)
    with col1:
        input_id = st.text_input("股票代號 (例: 2330)")
    with col2:
        input_name = st.text_input("股票名稱 (例: 台積電)")
    
    input_note = st.text_area("觀察筆記 (例: 預計跌破 1000 元買進)")
    
    # 表單的送出按鈕
    submitted = st.form_submit_button("💾 儲存至資料庫", type="primary")

    if submitted:
        if input_id == "" or input_name == "":
            st.error("⚠️ 股票代號與名稱為必填項目！")
        else:
            # 呼叫上面定義好的寫入功能
            add_record(input_id, input_name, input_note)
            st.success(f"✅ 成功將【{input_name}】加入資料庫！")
            st.rerun() # 重新整理網頁，讓下方的表格立刻更新

st.divider()

# --- 區塊 B：顯示資料庫內容 ---
st.subheader("📋 目前資料庫內容")

# 呼叫讀取功能，獲取表格資料
df = get_all_records()

if df.empty:
    st.info("💡 目前資料庫是空的，請在上方新增您的第一筆資料！")
else:
    # 使用 st.dataframe 顯示漂亮的互動式表格
    st.dataframe(df, use_container_width=True, hide_index=True)