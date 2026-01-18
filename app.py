import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from google import genai # ✅ 使用新版 AI 套件
from google.genai import types
import json
import time

# ============================================================
# ⚙️ 頁面設定
# ============================================================
st.set_page_config(page_title="2026 PLAN", page_icon="🧪", layout="wide")

# CSS 美化
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton > button { border-radius: 8px; font-weight: bold; }
    .quiz-card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔑 核心連線設定 (最穩定版)
# ============================================================

# 1. Google Sheets 連線
try:
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file("google_key.json", scopes=scope)
    gc = gspread.authorize(creds)
except Exception as e:
    st.error(f"⚠️ Google Sheets 連線失敗: {e}")
    st.info("請確認 google_key.json 是否存在於資料夾中")
    gc = None
    st.stop()

# 2. Gemini AI 連線 (新版 Client 寫法)
try:
    if "GEMINI_API_KEY" in st.secrets:
        ai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        ai_client = None
except Exception as e:
    ai_client = None

# ============================================================
# 🔧 工具函式區
# ============================================================

def get_taiwan_time():
    return datetime.now() + timedelta(hours=8)

def get_current_quarter():
    month = get_taiwan_time().month
    if month <= 3: return 1
    elif month <= 6: return 2
    elif month <= 9: return 3
    else: return 4

# --- Google Sheets 讀取 (防錯核心) ---
@st.cache_data(ttl=60)
def load_data_from_gsheet(worksheet_name):
    """
    使用 get_values() 取代 get_all_records()
    這是解決 <Response [200]> 錯誤的關鍵
    """
    if not gc: return pd.DataFrame()
    try:
        sh = gc.open("Lab_Time_Master_DB")
        try:
            worksheet = sh.worksheet(worksheet_name)
        except:
            return pd.DataFrame() # 找不到分頁回傳空

        # ✅ 關鍵修改：抓取原始資料列
        rows = worksheet.get_values()
        
        # 檢查是否為空或只有標題
        if not rows or len(rows) < 2:
            return pd.DataFrame()
            
        header = rows[0]
        data = rows[1:]
        
        df = pd.DataFrame(data, columns=header)
        
        # 日期處理
        if '日期' in df.columns:
            df['Date_Obj'] = pd.to_datetime(df['日期'], errors='coerce').dt.date
            
        return df
    except Exception as e:
        print(f"DEBUG: 讀取 {worksheet_name} 錯誤: {e}")
        return pd.DataFrame()

# --- Google Sheets 寫入 ---
def save_log_to_gsheet(data_list):
    if not gc: return
    try:
        sh = gc.open("Lab_Time_Master_DB")
        try:
            ws = sh.worksheet("Logs")
        except:
            ws = sh.add_worksheet(title="Logs", rows=1000, cols=10)
            ws.append_row(['日期', '時間', '類別', '輸入', '輸出'])
        
        ws.append_row(data_list)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"寫入失敗: {e}")

def save_savings_to_gsheet(date, amount, note):
    if not gc: return False
    try:
        sh = gc.open("Lab_Time_Master_DB")
        try:
            ws = sh.worksheet("Finance")
        except:
            ws = sh.add_worksheet(title="Finance", rows=1000, cols=5)
            ws.append_row(['日期', '金額', '備註'])
        
        ws.append_row([str(date), amount, note])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"存錢紀錄失敗: {e}")
        return False

# --- 股市資料 ---
@st.cache_data(ttl=600) 
def get_market_data():
    data = {}
    try:
        btc = yf.Ticker("BTC-USD")
        hist = btc.history(period="2d")
        if len(hist) >= 2:
            data['btc_price'] = hist['Close'].iloc[-1]
            data['btc_change'] = ((data['btc_price'] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
        
        stock = yf.Ticker("006208.TW")
        hist_s = stock.history(period="2d")
        if len(hist_s) >= 2:
            data['stock_price'] = hist_s['Close'].iloc[-1]
            data['stock_change'] = ((data['stock_price'] - hist_s['Close'].iloc[-2]) / hist_s['Close'].iloc[-2]) * 100
        return data
    except:
        return None

# --- AI 語言學習 (新版 SDK) ---
def fetch_ai_word_quiz(language):
    if not ai_client: 
        st.warning("請先設定 GEMINI_API_KEY")
        return None
    
    prompt = f"""
    請生成一個 {language} 單字，程度適合初學者 (N4/A1)。
    請回傳純 JSON 格式，不要 markdown，欄位包含：
    word (單字), reading (發音), meaning (中文意思), example (例句), example_meaning (例句中譯),
    quiz_question (選擇題題目), options (四個選項陣列), answer_index (正確索引 0-3)
    """
    
    try:
        # ✅ 新版呼叫方式
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        if response.text:
             return json.loads(response.text)
        return None
    except Exception as e:
        st.error(f"AI 生成失敗: {e}")
        return None

# --- UI 元件：水罐 ---
def render_water_jar(current, target, label, unit="", color="#4facfe"):
    percentage = min((current / target * 100) if target > 0 else 0, 100)
    html_code = f"""
    <div style="display: flex; flex-direction: column; align-items: center; margin: 10px;">
        <div style="font-weight: bold; margin-bottom: 5px; color: #ddd;">{label}</div>
        <div style="
            width: 80px; height: 120px; 
            border: 4px solid #555; border-top: 0; border-radius: 0 0 15px 15px;
            background: rgba(255,255,255,0.05); position: relative; overflow: hidden;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        ">
            <div style="
                position: absolute; bottom: 0; left: 0; right: 0;
                height: {percentage}%;
                background: linear-gradient(180deg, {color} 0%, {color}88 100%);
                transition: height 1s ease-in-out;
                opacity: 0.8;
            ">
                <div style="width: 100%; height: 5px; background: rgba(255,255,255,0.3);"></div>
            </div>
            <div style="
                position: absolute; top: 50%; left: 0; right: 0; transform: translateY(-50%);
                text-align: center; font-weight: bold; text-shadow: 1px 1px 2px black; color: white; z-index: 2;
            ">
                {percentage:.0f}%
            </div>
        </div>
        <div style="margin-top: 5px; font-size: 0.8rem; color: #aaa;">
            {current:,.0f} / {target:,.0f} {unit}
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)

# --- 週曆視圖 ---
def render_weekly_view(df):
    if df.empty:
        st.info("尚無資料可顯示週曆")
        return

    today = get_taiwan_time().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    cols = st.columns(7)
    week_days = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        with cols[i]:
            if current_day == today:
                st.markdown(f":orange[**{week_days[i]}**]")
            else:
                st.markdown(f"**{week_days[i]}**")
            
            if 'Date_Obj' in df.columns:
                day_data = df[df['Date_Obj'] == current_day]
                if not day_data.empty:
                    for _, row in day_data.iterrows():
                        category = str(row.get('類別', ''))
                        content = str(row.get('輸入', ''))[:6] + ".."
                        if "研究" in category: st.info(f"🧪 {content}")
                        elif "程式" in category: st.success(f"💻 {content}")
                        elif "日文" in category or "德語" in category: st.warning(f"🗣️ {content}")
                        elif "理財" in category: st.success(f"📈 {content}")
                        else: st.caption(f"📝 {content}")
                else:
                    st.markdown("<div style='color:#333;'>.</div>", unsafe_allow_html=True)

# ============================================================
# 📊 側邊欄 Sidebar
# ============================================================
with st.sidebar:
    st.markdown("## 📈 市場快訊")
    market_data = get_market_data()
    col_btc, col_stock = st.columns(2)
    if market_data:
        col_btc.metric("BTC", f"${market_data.get('btc_price', 0):,.0f}", f"{market_data.get('btc_change', 0):+.1f}%")
        col_stock.metric("006208", f"{market_data.get('stock_price', 0):.1f}", f"{market_data.get('stock_change', 0):+.1f}%")
    else:
        st.caption("載入報價中...")

    st.markdown("---")
    
    # 💰 水罐與財務
    st.markdown("## 📊 累積資產")
    
    df_finance = load_data_from_gsheet("Finance")
    total_saved = 0
    if not df_finance.empty and '金額' in df_finance.columns:
        df_finance['金額'] = pd.to_numeric(df_finance['金額'], errors='coerce').fillna(0)
        total_saved = df_finance['金額'].sum()
    
    df_logs = load_data_from_gsheet("Logs")
    lang_count = 0
    if not df_logs.empty and '類別' in df_logs.columns:
        lang_count = len(df_logs[df_logs['類別'].astype(str).str.contains('日文|德語|英文')])

    col_jar1, col_jar2 = st.columns(2)
    with col_jar1:
        render_water_jar(total_saved, 100000, "存錢計畫", "$", "#4caf50")
    with col_jar2:
        render_water_jar(lang_count, 50, "語言等級", "xp", "#2196f3")

    with st.expander("💰 存入小豬撲滿", expanded=False):
        save_amount = st.number_input("本月存入", min_value=0, step=100)
        save_note = st.text_input("備註 (來源)")
        if st.button("存入!", type="primary"):
            if save_amount > 0:
                if save_savings_to_gsheet(get_taiwan_time().date(), save_amount, save_note):
                    st.success("存入成功！")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🧮 月預算試算")
    income = 25000
    food_expense = st.number_input("🍱 伙食費", value=15000, step=500, key="food")
    fun_expense = st.number_input("🎮 娛樂/旅遊", value=5000, step=500, key="fun")
    balance = income - food_expense - fun_expense
    balance_color = "#4caf50" if balance >= 0 else "#f44336"
    st.markdown(f"**結餘:** <span style='color:{balance_color}; font-weight:bold;'>${balance:,}</span>", unsafe_allow_html=True)

# ============================================================
# 🏠 主畫面 Main Area
# ============================================================
today_weekday = get_taiwan_time().strftime("%A")
weekday_map = {"Monday": "週一", "Tuesday": "週二", "Wednesday": "週三", "Thursday": "週四", "Friday": "週五", "Saturday": "週六", "Sunday": "週日"}
today_zh = weekday_map.get(today_weekday, today_weekday)

st.title("🧪 實驗室時間管理大師 2.0")
st.markdown(f"#### *今天是 **{today_zh}**，讓 AI 陪你累積資產與知識！*")

# 📅 今日任務
st.markdown("---")
st.markdown("## 📅 今日任務提醒")

if today_weekday in ["Monday", "Wednesday", "Friday"]:
    cols = st.columns(3)
    with cols[0]: st.info("🧪 **實驗室/上課**")
    with cols[1]: st.success("💪 **健身 1hr**\n胸推/伏地挺身")
    with cols[2]: st.warning("🇯🇵 **日語 30min**\nAPI 測驗啟動")
elif today_weekday in ["Tuesday", "Thursday"]:
    cols = st.columns(3)
    with cols[0]: st.info("🧪 **實驗室/上課**")
    with cols[1]: st.success("💻 **Python/交易 1.5hr**\n回測腳本")
    with cols[2]: st.warning("🇩🇪 **德語 30min**\nAPI 測驗啟動")
elif today_weekday == "Saturday":
    cols = st.columns(2)
    with cols[0]: st.success("🎬 **化學 YT 拍攝 3hr**")
    with cols[1]: st.info("🎮 **自由娛樂時間**")
else:
    cols = st.columns(3)
    with cols[0]: st.info("📖 **複習一週進度**")
    with cols[1]: st.warning("🧪 **準備下週實驗**")
    with cols[2]: st.success("😴 **休息充電**")

# ⏱️ 零碎時間選單
st.markdown("---")
st.markdown("## ⏱️ 零碎時間 / AI 語言導師")

if 'quiz_data' not in st.session_state: st.session_state.quiz_data = None
if 'quiz_answered' not in st.session_state: st.session_state.quiz_answered = False
if 'fragment_type' not in st.session_state: st.session_state.fragment_type = None

col1, col2, col3, col4 = st.columns(4)

def start_quiz(lang):
    st.session_state.fragment_type = "quiz"
    st.session_state.current_lang = lang
    with st.spinner(f"正在召喚 AI 老師生成 {lang} 考題..."):
        data = fetch_ai_word_quiz(lang)
        if data:
            st.session_state.quiz_data = data
            st.session_state.quiz_answered = False

with col1:
    if st.button("🇯🇵 日文特訓", use_container_width=True): start_quiz("日文")
with col2:
    if st.button("🇺🇸 英文特訓", use_container_width=True): start_quiz("英文")
with col3:
    if st.button("🇩🇪 德語特訓", use_container_width=True): start_quiz("德語")
with col4:
    if st.button("💻 深度工作", use_container_width=True): 
        st.session_state.fragment_type = "coding"
        st.toast("🚀 進入深度工作模式！")

if st.session_state.fragment_type == "quiz" and st.session_state.quiz_data:
    q = st.session_state.quiz_data
    st.markdown(f"### 🎯 {st.session_state.current_lang} 隨堂測驗")
    
    st.markdown(f"""
    <div class="quiz-card">
        <h2 style="color:#4facfe; text-align:center;">{q['word']}</h2>
        <p style="text-align:center; color:#aaa;">({q['reading']})</p>
        <hr style="border-color:#444;">
        <p style="font-size:1.1rem;"><b>Q: {q['quiz_question']}</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.quiz_answered:
        user_ans = st.radio("請選擇正確答案：", q['options'], index=None)
        if st.button("送出答案"):
            if user_ans:
                st.session_state.quiz_answered = True
                correct_ans = q['options'][q['answer_index']]
                if user_ans == correct_ans:
                    st.balloons()
                    st.success(f"✅ 答對了！ {q['word']} = {q['meaning']}")
                    log_data = [
                        get_taiwan_time().strftime("%Y-%m-%d"),
                        get_taiwan_time().strftime("%H:%M"),
                        f"{st.session_state.current_lang} 測驗",
                        f"學習單字: {q['word']}",
                        "測驗通過 (水罐 XP+1)"
                    ]
                    save_log_to_gsheet(log_data)
                    st.toast("💧 語言水罐已注入能量！")
                else:
                    st.error(f"❌ 答錯了... 正確答案是：{correct_ans}")
    else:
        st.markdown(f"""
        <div style="background:#263238; padding:15px; border-radius:8px; margin-top:10px;">
            <h4>📚 詳細解析</h4>
            <ul>
                <li><b>單字：</b>{q['word']} ({q['reading']})</li>
                <li><b>意思：</b>{q['meaning']}</li>
                <li><b>例句：</b>{q['example']}</li>
                <li><b>中譯：</b>{q['example_meaning']}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("下一題 ➡️"):
            start_quiz(st.session_state.current_lang)
            st.rerun()

elif st.session_state.fragment_type == "coding":
    st.info("💻 專注寫程式 / 論文 / 研究中...")

# 📊 季度 Tabs
st.markdown("---")
st.markdown("## 📊 季度執行重點")
current_quarter = get_current_quarter()
tab1, tab2, tab3, tab4 = st.tabs(["Q1 基礎", "Q2 深化", "Q3 實戰", "Q4 衝刺"])

with tab1:
    st.markdown("#### 1-3月 (建立基礎)")
    st.markdown("- 🇯🇵 複習 N5 文法, 背 N4 單字\n- 💻 Python 基礎 (Pandas)")
    if current_quarter == 1: st.success("👈 **Current**")
with tab2:
    st.markdown("#### 4-6月 (技能深化)")
    st.markdown("- 🇯🇵 N4 歷屆試題\n- 💻 寫第一個回測腳本")
    if current_quarter == 2: st.success("👈 **Current**")
with tab3:
    st.markdown("#### 7-9月 (實戰驗收)")
    st.markdown("- 🇯🇵 7 月日檢衝刺 / 檢討\n- 💻 模擬交易 (Paper Trading)\n- 🎬 YT 頻道優化")
    if current_quarter == 3: st.success("👈 **Current**")
with tab4:
    st.markdown("#### 10-12月 (衝刺總結)")
    st.markdown("- 🇯🇵 **12 月 JLPT N4 檢定**\n- 💻 實倉運作自動化交易\n- 🇩🇪 德語 A1/A2 檢定")
    if current_quarter == 4: st.success("👈 **Current**")

# ============================================================
# 📝 學習紀錄
# ============================================================
st.markdown("---")
st.markdown("## 📝 學習紀錄")

with st.form("learning_form", clear_on_submit=True):
    col_input, col_output = st.columns(2)
    with col_input:
        input_text = st.text_area("📥 輸入 (學了什麼)", height=80)
    with col_output:
        output_text = st.text_area("📤 輸出 (應用/心得)", height=80)
    
    category = st.selectbox("類別", ["🧪 研究/化學", "💻 Python/交易", "🇯🇵 日文", "🇩🇪 德語", "📈 理財", "💪 健身", "🎬 YouTube", "🎯 其他"])
    
    if st.form_submit_button("💾 儲存紀錄至雲端"):
        if input_text.strip():
            tw_time = get_taiwan_time()
            save_log_to_gsheet([
                tw_time.strftime("%Y-%m-%d"), 
                tw_time.strftime("%H:%M"), 
                category, 
                input_text.strip(), 
                output_text.strip()
            ])
            st.toast("✅ 雲端儲存成功！", icon="☁️")
            st.rerun()
        else:
            st.warning("⚠️ 請至少填寫內容")

# 顯示紀錄
if gc:
    df_logs = load_data_from_gsheet("Logs")
    if not df_logs.empty:
        view_tab1, view_tab2 = st.tabs(["🗓️ 本週戰情", "📋 歷史清單"])
        with view_tab1:
            render_weekly_view(df_logs)
        with view_tab2:
            st.dataframe(df_logs.sort_index(ascending=False).head(20), use_container_width=True)
else:
    st.info("⚠️ 請確認 Google Sheet 設定是否正確")

st.markdown("---")
st.caption("🧪 2026 PLAN | Powered by Gemini & Google Sheets")


