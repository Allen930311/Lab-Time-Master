import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types
import json
import time
import random
import arxiv

# ============================================================
# ⚙️ 頁面設定
# ============================================================
st.set_page_config(page_title="2026 PLAN", page_icon="🧪", layout="wide")

# ============================================================
# 🎨 UI 高級化工程 (CSS)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 10% 20%, #1a1c2e 0%, #0e1117 90%);
    }

    /* 高級感卡片 */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
    }
    
    .quiz-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        margin-bottom: 20px;
    }

    /* 按鈕優化 */
    .stButton > button {
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔑 核心連線設定 (Secrets 優先)
# ============================================================

# 1. Google Sheets 連線
try:
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # 優先從 Streamlit Secrets 讀取
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        key_dict = dict(st.secrets["connections"]["gsheets"])
        creds = Credentials.from_service_account_info(key_dict, scopes=scope)
        gc = gspread.authorize(creds)
    # 本地開發備用 (google_key.json) - 記得將此檔案加入 .gitignore
    else:
        try:
            creds = Credentials.from_service_account_file("google_key.json", scopes=scope)
            gc = gspread.authorize(creds)
        except FileNotFoundError:
            # 如果連本地檔案都沒有，就設為 None，讓程式不崩潰但顯示警告
            gc = None
except Exception as e:
    st.error(f"⚠️ Google Sheets 連線失敗: {e}")
    gc = None

# 2. Gemini AI 連線
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

# --- Google Sheets 讀取 ---
@st.cache_data(ttl=60)
def load_data_from_gsheet(worksheet_name):
    if not gc: return pd.DataFrame()
    try:
        sh = gc.open("Lab_Time_Master_DB")
        try:
            worksheet = sh.worksheet(worksheet_name)
        except:
            return pd.DataFrame() 

        rows = worksheet.get_values()
        if not rows or len(rows) < 2:
            return pd.DataFrame()
            
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header)
        
        if '日期' in df.columns:
            df['Date_Obj'] = pd.to_datetime(df['日期'], errors='coerce').dt.date
            
        return df
    except Exception as e:
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

# --- arXiv 論文抓取 ---
def fetch_daily_papers():
    """每天抓取最新的化學相關論文"""
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query = 'cat:physics.chem-ph OR all:chemistry',
            max_results = 5,
            sort_by = arxiv.SortCriterion.SubmittedDate
        )
        papers = []
        for result in client.results(search):
            papers.append([
                result.published.strftime("%Y-%m-%d"),
                result.title,
                ", ".join([a.name for a in result.authors[:3]]),
                result.summary.replace("\n", " ")[:200] + "...",
                result.entry_id
            ])
        return papers
    except Exception as e:
        print(f"arXiv Error: {e}")
        return []

def update_papers_if_new():
    if not gc: return None
    df_papers = load_data_from_gsheet("Papers")
    today_str = get_taiwan_time().strftime("%Y-%m-%d")
    
    need_update = False
    if df_papers.empty:
        need_update = True
    else:
        if '日期' in df_papers.columns:
            last_date = str(df_papers.iloc[-1]['日期'])
            if last_date != today_str:
                need_update = True
        else:
            need_update = True

    if need_update:
        new_papers = fetch_daily_papers()
        if not new_papers: return False
        try:
            sh = gc.open("Lab_Time_Master_DB")
            try:
                ws = sh.worksheet("Papers")
            except:
                ws = sh.add_worksheet(title="Papers", rows=1000, cols=5)
                ws.append_row(['日期', '標題', '作者', '摘要', '連結'])
            
            for paper in new_papers:
                # 簡單防重複：只寫入今天的
                if paper[0] == today_str:
                    ws.append_row(paper)
            
            st.toast(f"✅ 已更新今日 ({today_str}) 論文！")
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"論文更新失敗: {e}")
            return False
    return False

# ============================================================
# 🤖 AI 強化版核心函式
# ============================================================

# --- 1. AI 每日任務 ---
@st.cache_data(ttl=3600*6)
def fetch_ai_daily_tasks(weekday_str):
    if not ai_client: return None
    
    strategies = {
        "Monday": "今天是啟動日，重點在於規劃與專注。",
        "Tuesday": "今天是執行日，重點在於 Deep Work。",
        "Wednesday": "今天是小週末，重點在於檢查進度。",
        "Thursday": "今天是衝刺日，重點在於攻克難題。",
        "Friday": "今天是總結日，重點在於收尾。",
        "Saturday": "今天是創作與學習日，重點在於跨領域。",
        "Sunday": "今天是休息與佈局日，重點在於恢復。"
    }
    strategy = strategies.get(weekday_str, "保持專注。")
    
    prompt = f"""
    角色：時間管理教練。
    學員：化學研究生(有機金屬)、加密貨幣交易員(Python量化)、日德語學習者。
    情境：今天是 {weekday_str}。{strategy}
    任務：生成 3 個具體任務 (Research, Coding, Growth)。
    回傳格式：JSON Array
    [
        {{"name": "標題", "type": "🧪 研究", "desc": "描述", "style": "info"}},
        {{"name": "標題", "type": "💻 程式", "desc": "描述", "style": "success"}},
        {{"name": "標題", "type": "📚 自我提升", "desc": "描述", "style": "warning"}}
    ]
    """
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        if response.text: return json.loads(response.text)
        return None
    except:
        return None

# --- 2. AI 單字測驗 (防重複 & 隨機情境) ---
def get_learned_words_history(lang):
    if not gc: return []
    try:
        df = load_data_from_gsheet("Logs")
        if df.empty or '輸入' not in df.columns: return []
        words = []
        filter_key = "日文" if "日" in lang else ("德" if "德" in lang else "英")
        target_rows = df[df['類別'].astype(str).str.contains(filter_key, na=False)]
        for content in target_rows['輸入']:
            if "學習單字:" in str(content):
                words.append(str(content).split("學習單字:")[-1].strip())
        return words[-60:]
    except:
        return []

def fetch_ai_word_quiz(language, difficulty="N4/A2"):
    if not ai_client: 
        st.warning("請先設定 GEMINI_API_KEY")
        return None
    
    topics = ["實驗室", "投資", "旅遊", "餐廳", "緊急狀況", "科技", "情緒", "天氣", "職場"]
    selected_topic = random.choice(topics)
    exclude_list = get_learned_words_history(language)
    exclude_str = ", ".join(exclude_list) if exclude_list else "無"

    prompt = f"""
    角色：嚴格的 {language} 老師。
    任務：出一個「單字測驗」。
    主題：{selected_topic}
    程度：{difficulty}
    排除名單：[{exclude_str}]
    
    回傳 JSON：
    {{
        "word": "單字",
        "reading": "發音/假名",
        "meaning": "中文意思",
        "example": "例句",
        "example_meaning": "例句中譯",
        "quiz_question": "選擇題題目",
        "options": ["A", "B", "C", "D"],
        "answer_index": 正確索引(0-3)
    }}
    """
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=1.1
            )
        )
        if response.text: return json.loads(response.text)
        return None
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            st.warning("⏳ AI 額度用完，切換至離線題庫")
            return get_offline_quiz(language)
        else:
            st.error(f"AI Error: {e}")
            return None

def get_offline_quiz(language):
    # 簡單的離線題庫備用
    offline_quizzes = {
        "日文": [{"word": "研究 (けんきゅう)", "reading": "けんきゅう", "meaning": "研究", "example": "...", "example_meaning": "...", "quiz_question": "研究?", "options": ["A","B","C","D"], "answer_index": 0}],
        "英文": [{"word": "Experiment", "reading": "...", "meaning": "實驗", "example": "...", "example_meaning": "...", "quiz_question": "Meaning?", "options": ["Test","Run","Eat","Sleep"], "answer_index": 0}]
    }
    return random.choice(offline_quizzes.get(language, offline_quizzes["英文"]))

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
        ">
            <div style="
                position: absolute; bottom: 0; left: 0; right: 0;
                height: {percentage}%;
                background: linear-gradient(180deg, {color} 0%, {color}88 100%);
                transition: height 1s ease-in-out;
                opacity: 0.8;
            "></div>
            <div style="
                position: absolute; top: 50%; left: 0; right: 0; transform: translateY(-50%);
                text-align: center; font-weight: bold; color: white; z-index: 2;
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
        st.info("尚無資料")
        return
    today = get_taiwan_time().date()
    start_of_week = today - timedelta(days=today.weekday())
    cols = st.columns(7)
    week_days = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        with cols[i]:
            if current_day == today: st.markdown(f":orange[**{week_days[i]}**]")
            else: st.markdown(f"**{week_days[i]}**")
            
            if 'Date_Obj' in df.columns:
                day_data = df[df['Date_Obj'] == current_day]
                if not day_data.empty:
                    for _, row in day_data.iterrows():
                        content = str(row.get('輸入', ''))
                        display = "✅" if "完成:" in content else "📝"
                        st.caption(display)
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

    st.markdown("---")
    st.markdown("## 📊 累積資產")
    
    df_finance = load_data_from_gsheet("Finance")
    total_saved = df_finance['金額'].astype(float).sum() if not df_finance.empty and '金額' in df_finance.columns else 0
    
    df_logs = load_data_from_gsheet("Logs")
    total_xp = 0
    if not df_logs.empty and '類別' in df_logs.columns:
        lang_count = len(df_logs[df_logs['類別'].astype(str).str.contains('日文|德語|英文|學習')])
        task_bonus = len(df_logs[df_logs['輸入'].astype(str).str.contains('完成:')])
        total_xp = lang_count + task_bonus

    col_jar1, col_jar2 = st.columns(2)
    with col_jar1: render_water_jar(total_saved, 100000, "存錢", "$", "#4caf50")
    with col_jar2: render_water_jar(total_xp, 100, "知識", "XP", "#2196f3")

    with st.expander("💰 存入小豬撲滿"):
        save_amount = st.number_input("金額", min_value=0, step=100)
        save_note = st.text_input("備註")
        if st.button("存入", type="primary"):
            if save_amount > 0 and save_savings_to_gsheet(get_taiwan_time().date(), save_amount, save_note):
                st.success("成功！")
                time.sleep(1)
                st.rerun()

    st.markdown("---")
    st.markdown("### 🧮 月預算")
    income = 25000
    food_expense = st.number_input("🍱 伙食", value=15000, step=500)
    fun_expense = st.number_input("🎮 娛樂", value=5000, step=500)
    balance = income - food_expense - fun_expense
    st.markdown(f"**結餘:** ${balance:,}")

# ============================================================
# 🏠 主畫面 Main Area
# ============================================================
today_weekday = get_taiwan_time().strftime("%A")
weekday_map = {"Monday": "週一", "Tuesday": "週二", "Wednesday": "週三", "Thursday": "週四", "Friday": "週五", "Saturday": "週六", "Sunday": "週日"}
today_zh = weekday_map.get(today_weekday, today_weekday)

st.title("🧪 實驗室時間管理大師 2.0")
st.markdown(f"#### *今天是 **{today_zh}**，讓 AI 陪你累積資產與知識！*")

# --- 自動觸發：論文更新檢查 ---
if 'papers_checked' not in st.session_state:
    update_papers_if_new()
    st.session_state.papers_checked = True

# --- 每日任務區 ---
st.markdown("---")
col_t1, col_t2 = st.columns([5, 1])
with col_t1: st.markdown("## 📅 今日任務 (AI Coach)")
with col_t2: 
    if st.button("🔄"): st.cache_data.clear(); st.rerun()

ai_tasks = fetch_ai_daily_tasks(today_weekday)
if not ai_tasks:
    ai_tasks = [{"name": "任務規劃中...", "type": "系統", "desc": "請稍後再試", "style": "info"}]

# 讀取已完成紀錄
done_tasks_list = []
if gc:
    df_logs_check = load_data_from_gsheet("Logs")
    if not df_logs_check.empty:
        today_str = get_taiwan_time().strftime("%Y-%m-%d")
        done_tasks_list = df_logs_check[df_logs_check['日期'] == today_str]['輸入'].tolist()

cols = st.columns(len(ai_tasks))
for i, task in enumerate(ai_tasks):
    with cols[i]:
        task_id = f"完成: {task['name']}"
        is_done = any(task_id in log for log in done_tasks_list)
        
        if task['style'] == 'info': st.info(f"**{task['name']}**")
        elif task['style'] == 'success': st.success(f"**{task['name']}**")
        else: st.warning(f"**{task['name']}**")
        st.caption(task['desc'])
        
        if is_done:
            st.button("✅ 完成", key=f"done_{i}", disabled=True)
        else:
            if st.button("⬜ 挑戰", key=f"btn_{i}"):
                save_log_to_gsheet([
                    get_taiwan_time().strftime("%Y-%m-%d"),
                    get_taiwan_time().strftime("%H:%M"),
                    task['type'], task_id, "AI 任務 (XP+5)"
                ])
                st.toast("任務達成！")
                time.sleep(1)
                st.rerun()

# --- 零碎時間 & 測驗區 ---
st.markdown("---")
st.markdown("## ⏱️ 零碎時間 / 語言特訓")

if 'quiz_data' not in st.session_state: st.session_state.quiz_data = None
if 'quiz_answered' not in st.session_state: st.session_state.quiz_answered = False
if 'fragment_type' not in st.session_state: st.session_state.fragment_type = None

c1, c2, c3, c4 = st.columns(4)
def start_quiz(lang):
    st.session_state.fragment_type = "quiz"
    st.session_state.current_lang = lang
    with st.spinner(f"生成 {lang} 題目中..."):
        data = fetch_ai_word_quiz(lang)
        if data:
            st.session_state.quiz_data = data
            st.session_state.quiz_answered = False

with c1: 
    if st.button("🇯🇵 日文", use_container_width=True): start_quiz("日文")
with c2: 
    if st.button("🇺🇸 英文", use_container_width=True): start_quiz("英文")
with c3: 
    if st.button("🇩🇪 德語", use_container_width=True): start_quiz("德語")
with c4:
    if st.button("💻 深度工作", use_container_width=True): 
        st.session_state.fragment_type = "coding"

# 測驗卡片顯示邏輯 (重點修復部分)
if st.session_state.fragment_type == "quiz" and st.session_state.quiz_data:
    q = st.session_state.quiz_data
    st.markdown(f"### 🎯 {st.session_state.current_lang} 測驗")
    
    # 未作答前隱藏單字
    if not st.session_state.quiz_answered:
        d_word, d_read = "❓❓❓", "???"
    else:
        d_word, d_read = q['word'], q['reading']

    st.markdown(f"""
    <div class="quiz-card">
        <h2 style="color:#4facfe; text-align:center;">{d_word}</h2>
        <p style="text-align:center; color:#aaa;">({d_read})</p>
        <hr style="border-color:#444;">
        <p style="font-size:1.1rem;"><b>Q: {q['quiz_question']}</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.quiz_answered:
        ans = st.radio("答案：", q['options'], index=None)
        if st.button("送出"):
            if ans:
                st.session_state.quiz_answered = True
                if ans == q['options'][q['answer_index']]:
                    st.balloons()
                    st.success("✅ 正確！")
                    save_log_to_gsheet([
                        get_taiwan_time().strftime("%Y-%m-%d"),
                        get_taiwan_time().strftime("%H:%M"),
                        f"{st.session_state.current_lang}測驗",
                        f"學習: {q['word']}", "通過 (XP+1)"
                    ])
                else:
                    st.error(f"❌ 錯誤，答案是：{q['options'][q['answer_index']]}")
                st.rerun()
    else:
        st.info(f"💡 解析：{q['word']} = {q['meaning']} ({q['example']})")
        if st.button("下一題 ➡️"):
            start_quiz(st.session_state.current_lang)
            st.rerun()

elif st.session_state.fragment_type == "coding":
    st.info("💻 專注模式開啟：請關閉通訊軟體，專注於程式碼或論文。")

# --- 季度目標 & 論文 Tab ---
st.markdown("---")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Q1 基礎", "Q2 深化", "Q3 實戰", "Q4 衝刺", "📰 每日論文"])

with tab1: st.markdown("- 🇯🇵 N5/N4\n- 💻 Python 基礎")
with tab2: st.markdown("- 🇯🇵 N4 歷屆\n- 💻 回測腳本")
with tab3: st.markdown("- 💻 模擬交易\n- 🎬 YT 頻道")
with tab4: st.markdown("- 🇯🇵 **12月 N4 檢定**\n- 💻 實盤交易")
with tab5:
    st.markdown("### 🧪 最新化學/物理論文 (arXiv)")
    if st.button("🔄 手動刷新論文"):
        update_papers_if_new()
        st.rerun()
    
    if gc:
        df_papers = load_data_from_gsheet("Papers")
        if not df_papers.empty:
            df_papers = df_papers.sort_values(by="日期", ascending=False).head(10)
            for _, row in df_papers.iterrows():
                with st.expander(f"📄 {row.get('日期','')} | {row.get('標題','')}"):
                    st.write(f"**作者:** {row.get('作者','')}")
                    st.write(f"**摘要:** {row.get('摘要','')}")
                    st.markdown(f"[🔗 閱讀原文]({row.get('連結','')})")
        else:
            st.info("尚無資料，請點擊刷新。")

# --- 學習紀錄 Input ---
st.markdown("---")
st.markdown("## 📝 學習紀錄")
with st.form("log_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    inp = c1.text_area("📥 輸入", height=80)
    out = c2.text_area("📤 輸出", height=80)
    cat = st.selectbox("類別", ["🧪 研究", "💻 程式", "🇯🇵 日文", "🇩🇪 德語", "📈 理財", "💪 健身", "🎬 YT"])
    if st.form_submit_button("💾 儲存"):
        if inp:
            save_log_to_gsheet([
                get_taiwan_time().strftime("%Y-%m-%d"),
                get_taiwan_time().strftime("%H:%M"),
                cat, inp, out
            ])
            st.toast("儲存成功")
            st.rerun()

# 顯示紀錄
if gc:
    df_logs = load_data_from_gsheet("Logs")
    if not df_logs.empty:
        t1, t2 = st.tabs(["本週", "歷史"])
        with t1: render_weekly_view(df_logs)
        with t2: st.dataframe(df_logs.sort_index(ascending=False).head(20), use_container_width=True)

st.caption("🧪 2026 PLAN | Powered by Gemini")





