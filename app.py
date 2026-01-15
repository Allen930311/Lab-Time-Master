import streamlit as st
import random
import csv
import os
from datetime import datetime

# ============================================================
# 🧪 實驗室時間管理大師 - Lab Time Master
# ============================================================

st.set_page_config(
    page_title="實驗室時間管理大師",
    page_icon="🧪",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #fafafa; }
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
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .finance-card {
        background: linear-gradient(135deg, #232526 0%, #414345 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 0.5rem;
    }
    .quarter-card {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        border-left: 4px solid;
    }
    .q1 { background: #fff3e0; border-color: #ff9800; }
    .q2 { background: #e8f5e9; border-color: #4caf50; }
    .q3 { background: #e3f2fd; border-color: #2196f3; }
    .q4 { background: #fce4ec; border-color: #e91e63; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 📚 日文單字資料庫 (JLPT N4 程度)
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

# ============================================================
# 📅 計算當前季度
# ============================================================
def get_current_quarter():
    month = datetime.now().month
    if month <= 3: return 1
    elif month <= 6: return 2
    elif month <= 9: return 3
    else: return 4

current_quarter = get_current_quarter()
today_weekday = datetime.now().strftime("%A")
weekday_map = {"Monday": "週一", "Tuesday": "週二", "Wednesday": "週三", 
               "Thursday": "週四", "Friday": "週五", "Saturday": "週六", "Sunday": "週日"}
today_zh = weekday_map.get(today_weekday, today_weekday)

# ============================================================
# 📊 側邊欄 - 2026 年度目標 & 財務
# ============================================================
with st.sidebar:
    st.markdown("## 🎯 2026 年度目標")
    st.markdown("---")
    
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
        st.warning("⚠️ 剛好打平，建議保留緊急備用金")
    elif balance < 0:
        st.error("❌ 超支！請調整支出")
    else:
        st.success(f"✅ 可存入備用金: ${balance:,}")
    
    st.markdown("---")
    
    # 📈 股票目標
    st.markdown("### 📈 006208 存股進度")
    stock_target = st.number_input("年度目標張數", value=12, min_value=1, step=1, key="stock_target")
    stock_current = st.number_input("目前累積", value=0, min_value=0, step=1, key="stock_current")
    stock_progress = min((stock_current / stock_target * 100) if stock_target > 0 else 0, 100)
    st.progress(stock_progress / 100)
    st.markdown(f"**進度:** {stock_current}/{stock_target} 張 ({stock_progress:.0f}%)")
    
    st.markdown("---")
    
    # 🇯🇵 JLPT N4 進度
    st.markdown("### 🇯🇵 JLPT N4 進度")
    jlpt_vocab = st.slider("單字", 0, 100, 30, key="jlpt_vocab")
    jlpt_grammar = st.slider("文法", 0, 100, 25, key="jlpt_grammar")
    jlpt_reading = st.slider("閱讀", 0, 100, 20, key="jlpt_reading")
    jlpt_listening = st.slider("聽力", 0, 100, 15, key="jlpt_listening")
    jlpt_overall = (jlpt_vocab + jlpt_grammar + jlpt_reading + jlpt_listening) / 4
    st.progress(jlpt_overall / 100)
    st.markdown(f"**整體:** {jlpt_overall:.0f}%")
    
    st.markdown("---")
    
    # 🇩🇪 德語進度
    st.markdown("### 🇩🇪 德語 A1/A2")
    german_progress = st.slider("德語進度", 0, 100, 0, key="german")
    st.progress(german_progress / 100)
    
    st.markdown("---")
    st.markdown("*📅 " + datetime.now().strftime("%Y-%m-%d") + "*")

# ============================================================
# 主要區域
# ============================================================
st.markdown("# 🧪 實驗室時間管理大師")
st.markdown(f"#### *今天是 **{today_zh}**，善用每一刻！*")

# ============================================================
# 📅 今日任務提醒 (根據星期)
# ============================================================
st.markdown("---")
st.markdown("## 📅 今日任務提醒")

if today_weekday in ["Monday", "Wednesday", "Friday"]:
    cols = st.columns(3)
    with cols[0]:
        st.info("🧪 **實驗室/上課**")
    with cols[1]:
        st.success("💪 **健身 1hr**\n胸推/伏地挺身")
    with cols[2]:
        st.warning("🇯🇵 **日語 30min**\nN4 單字/文法")
        
elif today_weekday in ["Tuesday", "Thursday"]:
    cols = st.columns(3)
    with cols[0]:
        st.info("🧪 **實驗室/上課**")
    with cols[1]:
        st.success("💻 **Python/交易 1.5hr**\n回測腳本練習")
    with cols[2]:
        st.warning("🇩🇪 **德語 30min**\nA1/A2 學習")
        
elif today_weekday == "Saturday":
    cols = st.columns(2)
    with cols[0]:
        st.success("🎬 **化學 YT 拍攝剪輯 3-4hr**\n實驗室日常/反應解析")
    with cols[1]:
        st.info("🎮 **自由娛樂時間**\n放鬆一下！")
        
else:  # Sunday
    cols = st.columns(3)
    with cols[0]:
        st.info("📖 **複習一週進度**")
    with cols[1]:
        st.warning("🧪 **準備下週實驗**")
    with cols[2]:
        st.success("😴 **休息充電**")

# ============================================================
# ⏱️ 零碎時間選單
# ============================================================
st.markdown("---")
st.markdown("## ⏱️ 零碎時間選單")

col1, col2, col3 = st.columns(3)

if 'fragment_content' not in st.session_state:
    st.session_state.fragment_content = None
if 'fragment_type' not in st.session_state:
    st.session_state.fragment_type = None

with col1:
    if st.button("⚡ 5 分鐘\n快速日文", key="btn_5min", use_container_width=True):
        st.session_state.fragment_content = random.choice(JAPANESE_WORDS)
        st.session_state.fragment_type = "japanese"

with col2:
    if st.button("📄 15 分鐘\n閱讀論文摘要", key="btn_15min", use_container_width=True):
        st.session_state.fragment_type = "paper"

with col3:
    if st.button("💻 30+ 分鐘\n寫程式或筆記", key="btn_30min", use_container_width=True):
        st.session_state.fragment_type = "coding"

# 顯示零碎時間內容
if st.session_state.fragment_type == "japanese":
    word = st.session_state.fragment_content
    st.markdown("### 🇯🇵 今日日文單字")
    col_word, col_info = st.columns([1, 2])
    with col_word:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
                    padding: 2rem; border-radius: 16px; text-align: center; color: white;">
            <div style="font-size: 3.5rem;">{word['word']}</div>
            <div style="font-size: 1.3rem; opacity: 0.9;">{word['reading']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_info:
        st.markdown(f"**📖 中文意思:** {word['meaning']}")
        st.markdown("**💡 學習技巧:** 大聲唸 3 次 → 造句 → 聯想記憶")

elif st.session_state.fragment_type == "paper":
    st.markdown("### 📄 論文摘要閱讀")
    st.success("📚 花 15 分鐘閱讀一篇論文摘要，記下 3 個重點！")
    st.checkbox("開啟 arXiv / PubMed / Google Scholar")
    st.checkbox("找一篇相關論文")
    st.checkbox("記下 3 個重點")
    st.checkbox("寫一句話總結")

elif st.session_state.fragment_type == "coding":
    st.markdown("### 💻 深度工作時間")
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("**💻 程式:** 修 Bug / 新功能 / 回測腳本")
    with col_b:
        st.info("**✍️ 寫作:** 研究筆記 / 論文 / 部落格")

# ============================================================
# 📊 季度執行重點
# ============================================================
st.markdown("---")
st.markdown("## 📊 季度執行重點")

q_cols = st.columns(4)

quarters = [
    ("Q1", "1-3月", "建立基礎", ["複習 N5 文法", "背 N4 單字", "Python 基礎", "化學 YT 第一支", "每週健身 3 次"], "q1", 1),
    ("Q2", "4-6月", "技能深化", ["N4 歷屆試題", "報名 7 月日檢", "回測腳本", "每月 1 支影片", "德語 A1 開始"], "q2", 2),
    ("Q3", "7-9月", "實戰驗收", ["7 月日檢衝刺", "模擬交易測試", "YT 系列影片", "檢視股票累積"], "q3", 3),
    ("Q4", "10-12月", "衝刺總結", ["12 月 N4 日檢", "德語檢定", "小額實倉操作", "健身成果紀錄"], "q4", 4),
]

for i, (q_name, months, title, tasks, css_class, q_num) in enumerate(quarters):
    with q_cols[i]:
        is_current = "👈 現在" if q_num == current_quarter else ""
        st.markdown(f"**{q_name} ({months})** {is_current}")
        st.markdown(f"*{title}*")
        for task in tasks[:3]:
            st.markdown(f"• {task}")

# ============================================================
# 📝 學習紀錄
# ============================================================
st.markdown("---")
st.markdown("## 📝 學習紀錄")

LOG_FILE = os.path.join(os.path.dirname(__file__), "learning_log.csv")

with st.form("learning_form", clear_on_submit=True):
    col_input, col_output = st.columns(2)
    with col_input:
        st.markdown("**📥 輸入 (學了什麼)**")
        input_text = st.text_area("輸入", placeholder="例如：閱讀機器學習第三章...", height=100, label_visibility="collapsed")
    with col_output:
        st.markdown("**📤 輸出 (學到什麼)**")
        output_text = st.text_area("輸出", placeholder="例如：理解梯度下降，用 Python 實作...", height=100, label_visibility="collapsed")
    
    category = st.selectbox("類別", ["📚 研究", "💻 程式", "🇯🇵 日文", "🇩🇪 德語", "📈 理財", "💪 健身", "🎬 YouTube", "🎯 其他"])
    
    if st.form_submit_button("💾 儲存紀錄", use_container_width=True):
        if input_text.strip() and output_text.strip():
            file_exists = os.path.isfile(LOG_FILE)
            with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['日期', '時間', '類別', '輸入', '輸出'])
                writer.writerow([datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"), category, input_text.strip(), output_text.strip()])
            st.success("✅ 儲存成功！")
        else:
            st.warning("⚠️ 請填寫輸入和輸出")

# 顯示最近紀錄
if os.path.isfile(LOG_FILE):
    import pandas as pd
    try:
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        if not df.empty:
            st.markdown("### 📊 最近紀錄")
            st.dataframe(df.tail(5).iloc[::-1], use_container_width=True, hide_index=True)
    except: pass

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #95a5a6;'>🧪 實驗室時間管理大師 | 建立習慣，成就目標 | 2026</div>", unsafe_allow_html=True)
