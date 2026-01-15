import streamlit as st
import random
import csv
import os
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf # 記得確保有安裝這兩個套件

# ============================================================
# ⚙️ 頁面設定 (必須放在第一行)
# ============================================================
st.set_page_config(
    page_title="實驗室時間管理大師",
    page_icon="🧪",
    layout="wide"
)

# ============================================================
# 🔧 工具函式區 (時區與快取)
# ============================================================

# 1. 取得台灣時間 (解決 Streamlit Cloud 時區問題)
def get_taiwan_time():
    return datetime.now() + timedelta(hours=8)

# 2. 抓取股價 (加入快取 Cache，每 10 分鐘才更新一次，避免 App 卡頓)
@st.cache_data(ttl=600) 
def get_market_data():
    data = {}
    try:
        # 比特幣
        btc = yf.Ticker("BTC-USD")
        btc_hist = btc.history(period="2d")
        if len(btc_hist) >= 2:
            data['btc_price'] = btc_hist['Close'].iloc[-1]
            data['btc_change'] = ((data['btc_price'] - btc_hist['Close'].iloc[-2]) / btc_hist['Close'].iloc[-2]) * 100
        
        # 006208
        stock = yf.Ticker("006208.TW")
        stock_hist = stock.history(period="2d")
        if len(stock_hist) >= 2:
            data['stock_price'] = stock_hist['Close'].iloc[-1]
            data['stock_change'] = ((data['stock_price'] - stock_hist['Close'].iloc[-2]) / stock_hist['Close'].iloc[-2]) * 100
            
        return data
    except Exception:
        return None

# 3. 週曆視圖函式 (已修正時區)
def render_weekly_view(df):
    """顯示本週七天的學習紀錄"""
    
    # 處理日期格式
    if '日期' in df.columns:
        df['Date_Obj'] = pd.to_datetime(df['日期']).dt.date
    
    # 計算本週一 (使用台灣時間)
    today = get_taiwan_time().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    # 建立 7 個欄位
    cols = st.columns(7)
    week_days = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        
        with cols[i]:
            # 標題：今天特別標註
            if current_day == today:
                st.markdown(f":orange[**{week_days[i]}**]")
                st.caption(f"**{current_day.month}/{current_day.day}** (今日)")
            else:
                st.markdown(f"**{week_days[i]}**")
                st.caption(f"{current_day.month}/{current_day.day}")
            
            # 篩選這一天的資料
            day_data = df[df['Date_Obj'] == current_day]
            
            if not day_data.empty:
                for _, row in day_data.iterrows():
                    category = row['類別']
                    # 內容太長截斷
                    raw_content = str(row['輸入'])
                    content = raw_content[:10] + ".." if len(raw_content) > 10 else raw_content
                    
                    if "研究" in category or "化學" in category:
                        st.info(f"🧪 {content}")
                    elif "程式" in category or "Python" in category:
                        st.success(f"💻 {content}")
                    elif "日文" in category:
                        st.warning(f"🇯🇵 {content}")
                    elif "德語" in category:
                        st.warning(f"🇩🇪 {content}")
                    elif "理財" in category:
                        st.success(f"📈 {content}")
                    elif "健身" in category:
                        st.info(f"💪 {content}")
                    elif "YouTube" in category:
                        st.error(f"🎬 {content}")
                    else:
                        st.caption(f"📝 {content}")
            else:
                st.markdown("<div style='color:#eee; font-size:0.8rem; border-top:1px solid #333; margin-top:5px;'>.</div>", unsafe_allow_html=True)

# ============================================================
# 🎨 CSS 美化
# ============================================================
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255,255,255,0.1);
    }
    .finance-card {
        background: linear-gradient(135deg, #232526 0%, #414345 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 📚 資料庫與參數
# ============================================================
JAPANESE_WORDS = [
    {"word": "勉強", "reading": "べんきょう", "meaning": "學習"},
    {"word": "研究", "reading": "けんきゅう", "meaning": "研究"},
    {"word": "実験", "reading": "じっけん", "meaning": "實驗"},
    {"word": "結果", "reading": "けっか", "meaning": "結果"},
    {"word": "問題", "reading": "もんだい", "meaning": "問題"},
    {"word": "答え", "reading": "こたえ", "meaning": "答案"},
    {"word": "質問", "reading": "しつもん", "meaning": "問題、提問"},
    {"word": "説明", "reading": "せつめい", "meaning": "說明"},
    {"word": "理由", "reading": "りゆう", "meaning": "理由"},
    {"word": "方法", "reading": "ほうほう", "meaning": "方法"},
    {"word": "計画", "reading": "けいかく", "meaning": "計畫"},
    {"word": "準備", "reading": "じゅんび", "meaning": "準備"},
    {"word": "練習", "reading": "れんしゅう", "meaning": "練習"},
    {"word": "復習", "reading": "ふくしゅう", "meaning": "複習"},
    {"word": "予習", "reading": "よしゅう", "meaning": "預習"},
    {"word": "発表", "reading": "はっぴょう", "meaning": "發表"},
    {"word": "報告", "reading": "ほうこく", "meaning": "報告"},
    {"word": "会議", "reading": "かいぎ", "meaning": "會議"},
    {"word": "資料", "reading": "しりょう", "meaning": "資料"},
    {"word": "論文", "reading": "ろんぶん", "meaning": "論文"},
]

def get_current_quarter():
    month = get_taiwan_time().month
    if month <= 3: return 1
    elif month <= 6: return 2
    elif month <= 9: return 3
    else: return 4

current_quarter = get_current_quarter()
today_weekday = get_taiwan_time().strftime("%A")
weekday_map = {"Monday": "週一", "Tuesday": "週二", "Wednesday": "週三", 
               "Thursday": "週四", "Friday": "週五", "Saturday": "週六", "Sunday": "週日"}
today_zh = weekday_map.get(today_weekday, today_weekday)

# ============================================================
# 📊 側邊欄 Sidebar
# ============================================================
with st.sidebar:
    st.markdown("## 📈 市場快訊")
    
    # 使用 Cache 的資料，加快 App 速度
    market_data = get_market_data()
    
    col_btc, col_stock = st.columns(2)
    if market_data:
        col_btc.metric("BTC", f"${market_data.get('btc_price', 0):,.0f}", f"{market_data.get('btc_change', 0):+.1f}%")
        col_stock.metric("006208", f"{market_data.get('stock_price', 0):.1f}", f"{market_data.get('stock_change', 0):+.1f}%")
    else:
        col_btc.metric("BTC", "N/A")
        col_stock.metric("006208", "N/A")
    
    st.caption("報價每 10 分鐘更新一次")
    st.markdown("---")
    
    # 🎯 2026 年度目標
    st.markdown("## 🎯 2026 年度目標")
    
    # 💰 財務規劃
    st.markdown("### 💰 財務規劃")
    st.markdown("""
    <div class="finance-card">
        <div style="font-size: 0.9rem;">月預算</div>
        <div style="font-size: 1.5rem; font-weight: bold;">$25,000</div>
    </div>
    """, unsafe_allow_html=True)
    
    income = 25000
    food_expense = st.number_input("🍱 伙食費", value=15000, step=500, key="food")
    fun_expense = st.number_input("🎮 娛樂/旅遊", value=5000, step=500, key="fun")
    invest_amount = st.number_input("📈 投資 006208", value=5000, step=500, key="invest")
    
    balance = income - food_expense - fun_expense - invest_amount
    balance_color = "#4caf50" if balance >= 0 else "#f44336"
    st.markdown(f"**結餘:** <span style='color:{balance_color}; font-weight:bold;'>${balance:,}</span>", unsafe_allow_html=True)
    
    if balance == 0:
        st.warning("⚠️ 剛好打平，注意備用金")
    elif balance < 0:
        st.error("❌ 超支！請調整支出")
    else:
        st.success(f"✅ 可存入備用金: ${balance:,}")
    
    st.markdown("---")
    
    # 📈 股票目標
    st.markdown("### 📈 006208 存股")
    stock_target = st.number_input("年度目標 (股)", value=1000, min_value=1, step=100)
    stock_current = st.number_input("目前累積 (股)", value=0.0, min_value=0.0, step=0.1) # 允許小數點
    stock_progress = min((stock_current / stock_target * 100) if stock_target > 0 else 0, 100)
    st.progress(stock_progress / 100)
    st.markdown(f"**進度:** {stock_current}/{stock_target} 張 ({stock_progress:.0f}%)")
    
    st.markdown("---")
    
    # 語言進度
    st.markdown("### 🇯🇵 JLPT N4")
    jlpt_overall = st.slider("整體進度", 0, 100, 30, key="jlpt")
    st.progress(jlpt_overall / 100)
    # ==========================================
    # 請將這段加在 Sidebar 的最後面
    # ==========================================
    st.markdown("---")
    st.markdown("### ⚙️ 資料管理")
    
    # 檢查檔案是否存在，存在才顯示下載按鈕
    if os.path.exists("learning_log.csv"):
        with open("learning_log.csv", "rb") as f:
            st.download_button(
                label="📥 下載 CSV 備份",
                data=f,
                file_name="learning_log_backup.csv",
                mime="text/csv",
                key="download-csv"
            )
    else:
        st.caption("尚無紀錄可下載")

# ============================================================
# 🏠 主畫面 Main Area
# ============================================================
st.markdown("# 🧪 實驗室時間管理大師")
st.markdown(f"#### *今天是 **{today_zh}**，善用每一刻！*")

# 📅 今日任務提醒
st.markdown("---")
st.markdown("## 📅 今日任務提醒")

if today_weekday in ["Monday", "Wednesday", "Friday"]:
    cols = st.columns(3)
    with cols[0]: st.info("🧪 **實驗室/上課**")
    with cols[1]: st.success("💪 **健身 1hr**\n胸推/伏地挺身")
    with cols[2]: st.warning("🇯🇵 **日語 30min**\nN4 單字/文法")
        
elif today_weekday in ["Tuesday", "Thursday"]:
    cols = st.columns(3)
    with cols[0]: st.info("🧪 **實驗室/上課**")
    with cols[1]: st.success("💻 **Python/交易 1.5hr**\n回測腳本")
    with cols[2]: st.warning("🇩🇪 **德語 30min**\nA1/A2 學習")
        
elif today_weekday == "Saturday":
    cols = st.columns(2)
    with cols[0]: st.success("🎬 **化學 YT 拍攝 3hr**")
    with cols[1]: st.info("🎮 **自由娛樂時間**")
        
else:  # Sunday
    cols = st.columns(3)
    with cols[0]: st.info("📖 **複習一週進度**")
    with cols[1]: st.warning("🧪 **準備下週實驗**")
    with cols[2]: st.success("😴 **休息充電**")

# ⏱️ 零碎時間選單
st.markdown("---")
st.markdown("## ⏱️ 零碎時間選單")

col1, col2, col3 = st.columns(3)

if 'fragment_content' not in st.session_state:
    st.session_state.fragment_content = None
if 'fragment_type' not in st.session_state:
    st.session_state.fragment_type = None

with col1:
    if st.button("⚡ 5 分鐘\n快速日文", key="btn_5min", use_container_width=True):
        st.toast("📖 載入日文單字卡...", icon="🇯🇵")
        st.session_state.fragment_content = random.choice(JAPANESE_WORDS)
        st.session_state.fragment_type = "japanese"

with col2:
    if st.button("📄 15 分鐘\n閱讀論文摘要", key="btn_15min", use_container_width=True):
        st.toast("📚 準備論文閱讀清單...", icon="📄")
        st.session_state.fragment_type = "paper"

with col3:
    if st.button("💻 30+ 分鐘\n寫程式或筆記", key="btn_30min", use_container_width=True):
        st.toast("🚀 進入深度工作模式！", icon="💻")
        st.session_state.fragment_type = "coding"

# 顯示選單內容
if st.session_state.fragment_type == "japanese":
    word = st.session_state.fragment_content
    st.markdown("### 🇯🇵 今日日文單字")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
                    padding: 1.5rem; border-radius: 16px; text-align: center; color: white;">
            <div style="font-size: 3rem;">{word['word']}</div>
            <div style="font-size: 1.2rem; opacity: 0.9;">{word['reading']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"**意思:** {word['meaning']}")
        st.markdown("**技巧:** 大聲唸 3 次 → 造句")

elif st.session_state.fragment_type == "paper":
    st.markdown("### 📄 論文摘要閱讀")
    st.success("找一篇相關論文，記下 3 個重點！")
    st.checkbox("1. 開啟 Google Scholar")
    st.checkbox("2. 記下 Key Findings")
    st.checkbox("3. 寫入下方紀錄")

elif st.session_state.fragment_type == "coding":
    st.markdown("### 💻 深度工作")
    st.info("修 Bug / 寫回測策略 / 寫論文")

# 📊 季度 Tabs
st.markdown("---")
st.markdown("## 📊 季度執行重點")

tab1, tab2, tab3, tab4 = st.tabs(["Q1 基礎", "Q2 深化", "Q3 實戰", "Q4 衝刺"])

with tab1:
    st.markdown("#### 1-3月 (建立基礎)")
    st.markdown("- 🇯🇵 複習 N5 文法, 背 N4 單字\n- 💻 Python 基礎 (Pandas)")
    if current_quarter == 1: st.success("👈 **Current**")

with tab2:
    st.markdown("#### 4-6月 (技能深化)")
    st.markdown("- 🇯🇵 N4 歷屆試題\n- 💻 寫第一個回測腳本")
    if current_quarter == 2: st.success("👈 **Current**")

# ... 其他季度省略，可依此類推 ...

# ============================================================
# 📝 學習紀錄 (資料庫核心)
# ============================================================
st.markdown("---")
st.markdown("## 📝 學習紀錄")

LOG_FILE = "learning_log.csv"

with st.form("learning_form", clear_on_submit=True):
    col_input, col_output = st.columns(2)
    with col_input:
        input_text = st.text_area("📥 輸入 (學了什麼)", height=80)
    with col_output:
        output_text = st.text_area("📤 輸出 (應用/心得)", height=80)
    
    category = st.selectbox("類別", ["🧪 研究/化學", "💻 Python/交易", "🇯🇵 日文", "🇩🇪 德語", "📈 理財", "💪 健身", "🎬 YouTube", "🎯 其他"])
    
    if st.form_submit_button("💾 儲存紀錄", use_container_width=True):
        if input_text.strip():
            file_exists = os.path.isfile(LOG_FILE)
            with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['日期', '時間', '類別', '輸入', '輸出'])
                
                # 🔥 這裡使用 get_taiwan_time() 確保寫入的是台灣時間
                tw_time = get_taiwan_time()
                writer.writerow([
                    tw_time.strftime("%Y-%m-%d"), 
                    tw_time.strftime("%H:%M"), 
                    category, 
                    input_text.strip(), 
                    output_text.strip()
                ])
            st.toast("✅ 儲存成功！", icon="💾")
            st.rerun() # 強制刷新以顯示新資料
        else:
            st.warning("⚠️ 請至少填寫內容")

# 顯示紀錄
if os.path.isfile(LOG_FILE):
    try:
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        if not df.empty:
            view_tab1, view_tab2 = st.tabs(["🗓️ 本週戰情 (Weekly)", "📋 歷史清單 (List)"])
            
            with view_tab1:
                render_weekly_view(df.copy())
            
            with view_tab2:
                st.dataframe(df.tail(20).iloc[::-1], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"讀取錯誤: {e}")

st.markdown("---")
st.caption("🧪 實驗室時間管理大師 | 2026 Edition")
