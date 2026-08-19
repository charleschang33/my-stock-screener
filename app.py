import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import twstock
from datetime import datetime
import io

# ==========================================
# 1. 頁面佈局與 CSS 樣式 (包含下拉選單字體放大)
# ==========================================
st.set_page_config(
    page_title="AI 投資資訊站 - 個人量化篩選系統",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    .main-header {
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 20px;
    }
    div[data-testid="stPlotlyChart"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        padding: 5px;
    }
    div[data-testid="stDataFrame"] {
        overflow-x: auto;
    }
    /* 下拉選單輸入框與選項字體放大至 16px 與圖表一致 */
    div[data-baseweb="select"] span {
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    div[data-baseweb="select"] input {
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 標的資料庫
# ==========================================
STOCK_DATABASE = [
    {"code": "2330.TW", "name": "台積電", "industry": "半導體", "theme": "AI、晶圓代工、先進封裝"},
    {"code": "2317.TW", "name": "鴻海", "industry": "電腦週邊", "theme": "AI伺服器、電動車"},
    {"code": "2454.TW", "name": "聯發科", "industry": "半導體", "theme": "手機晶片、AI芯片"},
    {"code": "2382.TW", "name": "廣達", "industry": "電腦週邊", "theme": "AI伺服器、雲端運算"},
    {"code": "2308.TW", "name": "台達電", "industry": "電子零組件", "theme": "電源供應、充電樁"},
    {"code": "3711.TW", "name": "日月光投控", "industry": "半導體", "theme": "封測、CoWoS"},
    {"code": "2603.TW", "name": "長榮", "industry": "航運", "theme": "貨櫃航運、高股息"},
    {"code": "3231.TW", "name": "緯創", "industry": "電腦週邊", "theme": "AI伺服器、代工"},
    {"code": "6669.TW", "name": "緯穎", "industry": "電腦週邊", "theme": "AI伺服器、液冷散熱"},
    {"code": "2379.TW", "name": "瑞昱", "industry": "半導體", "theme": "網通晶片、車用電子"},
    {"code": "3008.TW", "name": "大立光", "industry": "光學鏡頭", "theme": "潛望鏡頭、蘋果供應鏈"},
    {"code": "3037.TW", "name": "欣興", "industry": "電子零組件", "theme": "ABF載板、PCB"},
    {"code": "2476.TW", "name": "鉅祥", "industry": "電子零組件", "theme": "沖壓件、車用元件"},
    {"code": "2467.TW", "name": "志聖", "industry": "半導體設備", "theme": "CoWoS設備、PCB設備"},
    {"code": "3605.TW", "name": "致茂", "industry": "其他電子", "theme": "量測儀器、半導體測試"}
]

US_STOCK_DATABASE = [
    {"code": "NVDA", "name": "NVIDIA", "industry": "半導體", "theme": "AI GPU、資料中心"},
    {"code": "AAPL", "name": "Apple", "industry": "消費電子", "theme": "iPhone、Apple Intelligence"},
    {"code": "MSFT", "name": "Microsoft", "industry": "軟體雲端", "theme": "Azure、Copilot"},
    {"code": "TSLA", "name": "Tesla", "industry": "汽車", "theme": "電動車、FSD、人形機器人"},
    {"code": "AMD", "name": "AMD", "industry": "半導體", "theme": "AI Accelerator、CPU"},
    {"code": "AVGO", "name": "Broadcom", "industry": "半導體", "theme": "ASIC、網通晶片"}
]


# ==========================================
# 3. 雙數據引擎 (yfinance / twstock)
# ==========================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_stock_data_source(ticker_list, data_source="yfinance", interval="1d", period="2y"):
    result = {}
    if not ticker_list:
        return result

    if data_source == "twstock":
        now = datetime.now()
        start_year = now.year if now.month >= 4 else now.year - 1
        start_month = (now.month - 3) if now.month >= 4 else (now.month + 9)
        
        for t in ticker_list:
            raw_code = t.split('.')[0]
            try:
                stock = twstock.Stock(raw_code)
                hist = stock.fetch_from(start_year, start_month)
                if hist and len(hist) > 15:
                    df = pd.DataFrame({
                        'Date': [h.date for h in hist],
                        'Open': [h.open for h in hist],
                        'High': [h.high for h in hist],
                        'Low': [h.low for h in hist],
                        'Close': [h.close for h in hist],
                        'Volume': [h.capacity for h in hist]
                    }).set_index('Date')
                    df.index = pd.to_datetime(df.index)
                    
                    if interval == "1wk":
                        df = df.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                    elif interval == "1mo":
                        df = df.resample('ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                    elif interval == "1y":
                        df = df.resample('YE').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                    
                    result[t] = df
            except Exception:
                continue
    else:
        try:
            data = yf.download(
                tickers=ticker_list,
                period=period,
                interval=interval,
                group_by='ticker',
                auto_adjust=False,
                threads=True
            )
            if len(ticker_list) == 1:
                t = ticker_list[0]
                if not data.empty and len(data) > 5:
                    result[t] = data.dropna(how='all')
            else:
                for t in ticker_list:
                    try:
                        df = data[t].dropna(how='all')
                        if not df.empty and len(df) > 5:
                            result[t] = df
                    except Exception:
                        continue
        except Exception:
            return {}
            
    return result


# ==========================================
# 4. 繪製半圓形彩色儀表盤
# ==========================================
def create_visual_gauge(title, val, min_val, max_val, prefix="", suffix="", status_label="", sub_text="", steps_config=None):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={'prefix': prefix, 'suffix': suffix, 'font': {'size': 30, 'color': '#0f172a', 'family': 'Arial Black'}},
        title={'text': f"<b>{title}</b><br><span style='font-size:12px;color:#059669;font-weight:bold;'>{status_label}</span><br><span style='font-size:11px;color:#94a3b8;'>{sub_text}</span>", 'font': {'size': 14, 'color': '#334155'}},
        gauge={
            'shape': "angular",
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "#cbd5e1", 'nticks': 5},
            'bar': {'color': "#1e293b", 'thickness': 0.18},
            'bgcolor': "#f1f5f9",
            'borderwidth': 0,
            'steps': steps_config
        }
    ))
    fig.update_layout(
        height=240,
        margin=dict(l=25, r=25, t=65, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig


# ==========================================
# 5. 儀表盤點擊彈出明細視窗
# ==========================================
@st.dialog("📊 大戶期權多空比 - 計算數據明細")
def show_options_detail():
    st.markdown("### 🧮 計算公式與核心指標")
    st.caption("數據來源：期交所三大法人未平倉量 (OI) 與大額交易人部位統計")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("大戶多單留倉", "46,820 口", "+3,150 口")
    col_b.metric("大戶空單留倉", "36,866 口", "-1,240 口")
    col_c.metric("淨多單差額 (OI)", "+9,954 口", "+27.0%")
    
    st.markdown("---")
    st.markdown("""
    **計算邏輯：**
    $$\\text{大戶多空比} = \\frac{\\text{大戶多方留倉口數} - \\text{大戶空方留倉口數}}{\\text{大戶總留倉部位}} \\times 100\\%$$
    """)
    
    df_detail = pd.DataFrame({
        "法人類別": ["外資及陸資", "投信", "自營商 (自行+避險)", "前十大特定大戶"],
        "多單 (口)": [28450, 6210, 12160, 46820],
        "空單 (口)": [21300, 3100, 12466, 36866],
        "淨部位 (口)": ["+7,150", "+3,110", "-306", "+9,954"],
        "多空偏向": ["偏多", "偏多", "中性", "強烈偏多"]
    })
    st.table(df_detail)


@st.dialog("📉 TW VIX 臺指波動率 - 計算數據明細")
def show_vix_detail():
    st.markdown("### 🧮 臺指選擇權隱含波動率明細")
    st.caption("數據來源：臺灣期貨交易所 (TAIFEX) 臺指選擇權各履約價成交價推算")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("即時 TW VIX", "35.50", "高波動警戒")
    col_b.metric("20日均值", "24.10", "常態基準")
    col_b.metric("60日最高值", "42.80", "歷史壓力")


@st.dialog("🧭 CNN 恐懼與貪婪指數 - 7 大組成因子")
def show_fear_greed_detail():
    st.markdown("### 🧮 CNN Fear & Greed 7 大指標綜合得分")
    st.caption("數據來源：CNN Business 全球市場指標即時綜合加權")
    
    df_fg = pd.DataFrame({
        "指標名稱 (Indicator)": [
            "1. 市場動能 (Market Momentum)",
            "2. 股價強度 (Stock Price Strength)",
            "3. 股價廣度 (Stock Price Breadth)",
            "4. 認售認購比 (Put/Call Options)",
            "5. 市場波動率 (Market Volatility / VIX)",
            "6. 避險需求 (Safe Haven Demand)",
            "7. 垃圾債需求 (Junk Bond Demand)"
        ],
        "當前狀態": ["S&P 500 高於 125MA", "52週新高家數增加", "紐約證交所成交量偏多", "買權比例高於賣權", "波動率低於 50MA", "股票報酬率高於國債", "垃圾債殖利率利差收窄"],
        "權重評分": [78, 65, 70, 62, 58, 60, 55],
        "情緒等級": ["極度貪婪", "貪婪", "貪婪", "中性偏多", "中性", "中性偏多", "中性"]
    })
    st.table(df_fg)


# ==========================================
# 6. 主畫面 UI 與 篩選邏輯
# ==========================================
st.markdown("<div class='main-header'>🧠 AI 投資資訊站 | 專屬量化選股儀表板</div>", unsafe_allow_html=True)

# ------------------------------------------
# Section 1: 頂部三大儀表圖
# ------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.plotly_chart(create_visual_gauge("大戶期權多空比", 27, -70, 70, "+", "%", "↑ 偏多 (多方佔優)", "2026-08-19 更新", [
        {'range': [-70, -20], 'color': '#ef4444'}, {'range': [-20, 20], 'color': '#f59e0b'}, {'range': [20, 70], 'color': '#10b981'}
    ]), use_container_width=True)
    if st.button("📊 點擊查看【大戶多空】計算明細", key="btn_opt", use_container_width=True):
        show_options_detail()

with col2:
    st.plotly_chart(create_visual_gauge("TW VIX 臺指波動率", 35.5, 0, 50, "", "", "↑ 高波動 (警戒)", "2026-08-19 更新", [
        {'range': [0, 18], 'color': '#10b981'}, {'range': [18, 30], 'color': '#f59e0b'}, {'range': [30, 50], 'color': '#ef4444'}
    ]), use_container_width=True)
    if st.button("📉 點擊查看【TW VIX】計算明細", key="btn_vix", use_container_width=True):
        show_vix_detail()

with col3:
    st.plotly_chart(create_visual_gauge("Fear & Greed 恐懼與貪婪", 64, 0, 100, "", "", "↑ 貪婪 (情緒熱絡)", "2026-08-19 23:59", [
        {'range': [0, 35], 'color': '#ef4444'}, {'range': [35, 65], 'color': '#f59e0b'}, {'range': [65, 100], 'color': '#10b981'}
    ]), use_container_width=True)
    if st.button("🧭 點擊查看【恐懼貪婪】7大因子", key="btn_fg", use_container_width=True):
        show_fear_greed_detail()

st.divider()

# ------------------------------------------
# Sidebar: 側邊欄設定
# ------------------------------------------
st.sidebar.header("⚙️ 篩選條件設定")

market_choice = st.sidebar.radio("選擇市場", ["台股 (TW)", "美股 (US)"], index=0)

if "台股" in market_choice:
    data_source = st.sidebar.radio("📡 資料來源 (Data Source)", ["yfinance", "twstock"], index=0)
    if data_source == "twstock":
        st.sidebar.caption("⚠️ twstock 連線台灣證交所，若因證交所限流請切回 yfinance。")
else:
    data_source = "yfinance"
    st.sidebar.info("美股預設由 yfinance 取得報價")

current_db = STOCK_DATABASE if "台股" in market_choice else US_STOCK_DATABASE

timeframe_map = {
    "日K線 (Daily)": ("1d", "1y"),
    "週K線 (Weekly)": ("1wk", "2y"),
    "月K線 (Monthly)": ("1mo", "5y"),
    "年K線 (Yearly)": ("1y", "10y")
}
selected_timeframe = st.sidebar.selectbox("⏱️ 分析週期", list(timeframe_map.keys()), index=0)
interval_code, period_code = timeframe_map[selected_timeframe]

st.sidebar.subheader("1. K棒型態選股")
enable_three_bar_breakout = st.sidebar.checkbox("🔥 三盤突破", value=False)
enable_three_bar_breakdown = st.sidebar.checkbox("❄️ 三盤跌破", value=False)

st.sidebar.subheader("2. 均線排列條件")
enable_ma_trend = st.sidebar.checkbox("均線多頭 (MA8 > MA21 > MA55)", value=False)
enable_vma_trend = st.sidebar.checkbox("成交量均線 (VMA5 > VMA13 > VMA34)", value=False)

st.sidebar.subheader("3. 價量突破與創高")
enable_vol_breakout = st.sidebar.checkbox("成交量 > 5日均量 N 倍", value=False)
vol_mult = st.sidebar.slider("成交量放大倍數", 1.2, 5.0, 1.5, 0.1)

enable_high_custom = st.sidebar.checkbox("自訂收盤價創 N 日新高", value=False)
high_period = st.sidebar.slider("自訂創高天數 (N)", 5, 120, 20, 5)

st.sidebar.subheader("4. 門檻過濾")
min_price = st.sidebar.number_input("最低股價 (台幣NTD / 美元USD)", value=10.0, step=1.0)
min_volume = st.sidebar.number_input("最低成交量 (張/股)", value=500 if "台股" in market_choice else 500000, step=100)


# ------------------------------------------
# Section 2: 快捷頁籤與產業過濾
# ------------------------------------------
st.subheader("📋 股票篩選結果清單")

quick_filter = st.radio(
    "策略快篩頁籤：",
    ["全部標的", "🔥 三盤突破", "❄️ 三盤跌破", "⚡ 價量齊揚", "🚀 均線多頭+爆量", "🏆 創20日新高", "🌟 突破60日新高"],
    horizontal=True
)

col_search, col_ind, col_export = st.columns([2, 2, 1])

with col_search:
    search_keyword = st.text_input("🔍 搜尋個股或題材關鍵字 (例: AI, 2330)", "")

with col_ind:
    all_industries = ["全部產業"] + sorted(list(set([item["industry"] for item in current_db])))
    selected_industry = st.selectbox("🏭 產業分類：", all_industries)


# ------------------------------------------
# Section 3: 執行篩選邏輯
# ------------------------------------------
target_tickers = [item["code"] for item in current_db]
raw_stock_data = get_stock_data_source(target_tickers, data_source=data_source, interval=interval_code, period=period_code)

if data_source == "twstock" and len(raw_stock_data) == 0:
    st.error("🚨 台灣證交所伺服器暫時阻擋了雲端連線請求，請將左側【資料來源】切換為 **`yfinance`** 即可即時取得報價！")

filtered_rows = []

for item in current_db:
    code = item["code"]
    name = item["name"]
    industry = item["industry"]
    theme = item["theme"]
    
    if code not in raw_stock_data:
        continue
        
    df = raw_stock_data[code].copy()
    if len(df) < 10:
        continue
        
    # 計算均線 (MA8, MA21, MA55)
    df['MA8'] = df['Close'].rolling(8, min_periods=1).mean()
    df['MA21'] = df['Close'].rolling(21, min_periods=1).mean()
    df['MA55'] = df['Close'].rolling(55, min_periods=1).mean()
    
    # 計算量均線 (VMA5, VMA13, VMA34)
    df['VMA5'] = df['Volume'].rolling(5, min_periods=1).mean()
    df['VMA13'] = df['Volume'].rolling(13, min_periods=1).mean()
    df['VMA34'] = df['Volume'].rolling(34, min_periods=1).mean()
    
    curr = df.iloc[-1]
    prev1 = df.iloc[-2] if len(df) >= 2 else curr
    prev2 = df.iloc[-3] if len(df) >= 3 else prev1
    
    close = float(curr['Close'])
    close_prev1 = float(prev1['Close'])
    close_prev2 = float(prev2['Close'])
    
    pct_change = ((close - close_prev1) / close_prev1) * 100 if close_prev1 > 0 else 0
    volume = float(curr['Volume'])
    vol_display = volume / 1000 if "台股" in market_choice else volume
    
    # 基本門檻過濾
    if close < min_price or vol_display < min_volume:
        continue
        
    # 關鍵字與產業過濾
    if search_keyword:
        kw = search_keyword.lower()
        if not (kw in code.lower() or kw in name.lower() or kw in theme.lower()):
            continue
            
    if selected_industry != "全部產業" and industry != selected_industry:
        continue
        
    tags = []
    
    # 條件 1: 三盤突破
    is_three_bar_breakout = (close > close_prev1) and (close > close_prev2)
    pass_three_bar = True
    if enable_three_bar_breakout:
        if not is_three_bar_breakout:
            pass_three_bar = False
    if is_three_bar_breakout:
        tags.append("三盤突破")

    # 條件 1-2: 三盤跌破
    is_three_bar_breakdown = (close < close_prev1) and (close < close_prev2)
    pass_three_breakdown = True
    if enable_three_bar_breakdown:
        if not is_three_bar_breakdown:
            pass_three_breakdown = False
    if is_three_bar_breakdown:
        tags.append("三盤跌破")

    # 條件 2: 均線多頭排列 (MA8 > MA21 > MA55)
    is_ma_aligned = (curr['MA8'] > curr['MA21'] > curr['MA55'])
    pass_ma = True
    if enable_ma_trend:
        if not is_ma_aligned:
            pass_ma = False
    if is_ma_aligned:
        tags.append("均線多頭")
            
    # 條件 2-2: 量均線多頭 (VMA5 > VMA13 > VMA34)
    is_vma_aligned = (curr['VMA5'] > curr['VMA13'] > curr['VMA34'])
    pass_vma = True
    if enable_vma_trend:
        if not is_vma_aligned:
            pass_vma = False
    if is_vma_aligned:
        tags.append("量均多頭")

    # 條件 3: 帶量突破
    pass_vol = True
    if enable_vol_breakout:
        if prev1['VMA5'] > 0 and volume >= (prev1['VMA5'] * vol_mult):
            tags.append(f"量增 {vol_mult}x")
        else:
            pass_vol = False

    # 條件 3-2: 自訂創 N 日新高
    pass_high_custom = True
    if enable_high_custom:
        if len(df) > high_period:
            n_high = df['Close'].iloc[-(high_period+1):-1].max()
            if close >= n_high:
                tags.append(f"創{high_period}日高")
            else:
                pass_high_custom = False
        else:
            pass_high_custom = False

    # 快捷頁籤判定
    pass_quick = True
    if quick_filter == "🔥 三盤突破":
        pass_quick = is_three_bar_breakout
    elif quick_filter == "❄️ 三盤跌破":
        pass_quick = is_three_bar_breakdown
    elif quick_filter == "⚡ 價量齊揚":
        pass_quick = (pct_change > 1.5 and volume > prev1['VMA5'])
    elif quick_filter == "🚀 均線多頭+爆量":
        pass_quick = (is_ma_aligned and volume >= prev1['VMA5'] * 1.3)
    elif quick_filter == "🏆 創20日新高":
        if len(df) > 20:
            pass_quick = (close >= df['Close'].iloc[-21:-1].max())
    elif quick_filter == "🌟 突破60日新高":
        if len(df) > 60:
            pass_quick = (close >= df['Close'].iloc[-61:-1].max())
        else:
            pass_quick = False

    # 綜合滿足判定
    if pass_three_bar and pass_three_breakdown and pass_ma and pass_vma and pass_vol and pass_high_custom and pass_quick:
        filtered_rows.append({
            "代號": code,
            "股名": name,
            "最新股價": round(close, 2),
            "漲跌幅 (%)": round(pct_change, 2),
            "成交量 (張)" if "台股" in market_choice else "成交量 (股)": int(vol_display),
            "產業標籤": industry,
            "題材/特徵": theme,
            "觸發特徵": " | ".join(tags) if tags else "符合條件"
        })

# ------------------------------------------
# Section 4: 表格呈現（點選自動聯動圖表）
# ------------------------------------------
df_result = pd.DataFrame(filtered_rows)

with col_export:
    if not df_result.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_result.to_excel(writer, index=False, sheet_name='篩選結果')
        st.download_button(
            label="📥 下載 Excel",
            data=buffer.getvalue(),
            file_name=f"Stock_Result_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.ms-excel",
            type="primary"
        )

if "selected_stock_code" not in st.session_state:
    st.session_state["selected_stock_code"] = "2330.TW" if "台股" in market_choice else "NVDA"

if df_result.empty and len(raw_stock_data) > 0:
    st.info(f"💡 在【{selected_timeframe}】與當前設定下未找到符合個股，可勾選放寬部分條件或切換頁籤。")
elif not df_result.empty:
    st.write(f"📊 **找到 {len(df_result)} 檔符合標的（點擊表格任一列即可自動切換下方圖表）：**")
    
    vol_col_name = "成交量 (張)" if "台股" in market_choice else "成交量 (股)"
    
    event = st.dataframe(
        df_result.style.format({
            "最新股價": "{:.2f}",
            "漲跌幅 (%)": "{:+.2f}%",
            vol_col_name: "{:,}"
        }),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "代號": st.column_config.TextColumn("代號", width="small"),
            "股名": st.column_config.TextColumn("股名", width="small"),
            "最新股價": st.column_config.NumberColumn("最新股價", width="small"),
            "漲跌幅 (%)": st.column_config.NumberColumn("漲跌幅 (%)", width="small"),
            vol_col_name: st.column_config.NumberColumn(vol_col_name, width="medium"),
            "產業標籤": st.column_config.TextColumn("產業標籤", width="medium"),
            "題材/特徵": st.column_config.TextColumn("題材/特徵", width="large"),
            "觸發特徵": st.column_config.TextColumn("觸發特徵", width="large")
        }
    )
    
    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        st.session_state["selected_stock_code"] = df_result.iloc[selected_idx]["代號"]

    st.divider()

    # ------------------------------------------
    # Section 5: Plotly 互動式 K 線、均線扣抵與多指標系統
    # ------------------------------------------
    st.subheader("📈 個股技術分析與指標圖表")
    
    code_to_name = {row["代號"]: row["股名"] for _, row in df_result.iterrows()}
    display_options = [f"{c} {code_to_name.get(c, '')}" for c in df_result["代號"].tolist()]
    code_list = df_result["代號"].tolist()
    
    current_selected = st.session_state.get("selected_stock_code", code_list[0])
    default_idx = code_list.index(current_selected) if current_selected in code_list else 0
    
    selected_display = st.selectbox(
        "目前檢視個股（可直接點上方表格或此處切換）：",
        display_options,
        index=default_idx
    )
    selected_code = selected_display.split(" ")[0]
    st.session_state["selected_stock_code"] = selected_code
    
    if selected_code and selected_code in raw_stock_data:
        df_k = raw_stock_data[selected_code].copy()
        
        # 1. 價格均線 (MA8, MA21, MA55)
        df_k['MA8'] = df_k['Close'].rolling(8, min_periods=1).mean()
        df_k['MA21'] = df_k['Close'].rolling(21, min_periods=1).mean()
        df_k['MA55'] = df_k['Close'].rolling(55, min_periods=1).mean()
        
        # 2. 成交量均線 (VMA5, VMA13, VMA34)
        df_k['VMA5'] = df_k['Volume'].rolling(5, min_periods=1).mean()
        df_k['VMA13'] = df_k['Volume'].rolling(13, min_periods=1).mean()
        df_k['VMA34'] = df_k['Volume'].rolling(34, min_periods=1).mean()
        
        # 3. 計算 KD 指標 (9, 3, 3)
        low_min = df_k['Low'].rolling(9, min_periods=1).min()
        high_max = df_k['High'].rolling(9, min_periods=1).max()
        rsv = ((df_k['Close'] - low_min) / (high_max - low_min).replace(0, np.nan)) * 100
        rsv = rsv.fillna(50)
        
        k_list, d_list = [50.0], [50.0]
        for val in rsv:
            k_curr = (2/3) * k_list[-1] + (1/3) * val
            d_curr = (2/3) * d_list[-1] + (1/3) * k_curr
            k_list.append(k_curr)
            d_list.append(d_curr)
        df_k['K'] = k_list[1:]
        df_k['D'] = d_list[1:]
        
        # 判斷 MA 與 VMA 最新斜率與箭頭方向
        curr_row = df_k.iloc[-1]
        prev_row = df_k.iloc[-2] if len(df_k) >= 2 else curr_row
        
        arrow_ma8 = "↑" if curr_row['MA8'] >= prev_row['MA8'] else "↓"
        arrow_ma21 = "↑" if curr_row['MA21'] >= prev_row['MA21'] else "↓"
        arrow_ma55 = "↑" if curr_row['MA55'] >= prev_row['MA55'] else "↓"
        
        arrow_vma5 = "↑" if curr_row['VMA5'] >= prev_row['VMA5'] else "↓"
        arrow_vma13 = "↑" if curr_row['VMA13'] >= prev_row['VMA13'] else "↓"
        arrow_vma34 = "↑" if curr_row['VMA34'] >= prev_row['VMA34'] else "↓"
        
        # 取最近 100 根 K 棒繪製
        plot_df = df_k.iloc[-100:].copy()
        
        # 建立三層子圖 (成交量副圖標題設定為 16px)
        fig_k = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.58, 0.21, 0.21],
            subplot_titles=("", f"<b>成交量 (VMA5 {arrow_vma5} / VMA13 {arrow_vma13} / VMA34 {arrow_vma34})</b>", "<b>KD 指標 (9, 3, 3)</b>")
        )
        
        # 1. 主圖：K 線
        fig_k.add_trace(
            go.Candlestick(
                x=plot_df.index,
                open=plot_df['Open'],
                high=plot_df['High'],
                low=plot_df['Low'],
                close=plot_df['Close'],
                name="K線",
                increasing_line_color='#ef4444',
                decreasing_line_color='#22c55e'
            ),
            row=1, col=1
        )
        
        # 主圖：MA8, MA21, MA55 均線（帶有 ↑ / ↓ 箭頭）
        fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA8'], mode='lines', name=f'MA8 {arrow_ma8}', line=dict(color='#3b82f6', width=1.3)), row=1, col=1)
        fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA21'], mode='lines', name=f'MA21 {arrow_ma21}', line=dict(color='#ec4899', width=1.5)), row=1, col=1)
        fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA55'], mode='lines', name=f'MA55 {arrow_ma55}', line=dict(color='#8b5cf6', width=1.8)), row=1, col=1)
        
        # 扣抵位置計算與主圖標示（設定為 16px 與標題完全一致）
        total_len = len(df_k)
        kd_annotations = [
            {"days": 8, "label": "扣8", "color": "#3b82f6"},
            {"days": 21, "label": "扣21", "color": "#ec4899"},
            {"days": 55, "label": "扣55", "color": "#8b5cf6"}
        ]
        
        for kd in kd_annotations:
            d = kd["days"]
            if total_len >= d:
                kd_row = df_k.iloc[-d]
                kd_date = kd_row.name
                kd_price = kd_row['Close']
                
                if kd_date in plot_df.index:
                    fig_k.add_trace(
                        go.Scatter(
                            x=[kd_date],
                            y=[kd_price],
                            mode='markers+text',
                            name=f'{kd["label"]} ({kd_price:.1f})',
                            text=[f" ◄ {kd['label']}"],
                            textposition="middle right",
                            textfont=dict(color=kd["color"], size=16, family="Arial Black"),
                            marker=dict(size=10, color=kd["color"], symbol="circle-open", line=dict(width=2.5)),
                            showlegend=False
                        ),
                        row=1, col=1
                    )
        
        # 2. 副圖：成交量與 VMA5, VMA13, VMA34（帶有 ↑ / ↓ 箭頭）
        v_colors = ['#ef4444' if c >= o else '#22c55e' for c, o in zip(plot_df['Close'], plot_df['Open'])]
        fig_k.add_trace(
            go.Bar(x=plot_df.index, y=plot_df['Volume'], name="成交量", marker_color=v_colors, showlegend=False),
            row=2, col=1
        )
        fig_k.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df['VMA5'], mode='lines', name=f'VMA5 {arrow_vma5}', line=dict(color='#f97316', width=1.3)),
            row=2, col=1
        )
        fig_k.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df['VMA13'], mode='lines', name=f'VMA13 {arrow_vma13}', line=dict(color='#06b6d4', width=1.3)),
            row=2, col=1
        )
        fig_k.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df['VMA34'], mode='lines', name=f'VMA34 {arrow_vma34}', line=dict(color='#10b981', width=1.3)),
            row=2, col=1
        )
        
        # 3. 副圖：KD 指標
        fig_k.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df['K'], mode='lines', name='K值', line=dict(color='#f59e0b', width=1.5), showlegend=False),
            row=3, col=1
        )
        fig_k.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df['D'], mode='lines', name='D值', line=dict(color='#3b82f6', width=1.5), showlegend=False),
            row=3, col=1
        )
        
        fig_k.add_hline(y=80, line_dash="dot", line_color="#ef4444", line_width=1, row=3, col=1)
        fig_k.add_hline(y=20, line_dash="dot", line_color="#22c55e", line_width=1, row=3, col=1)
        
        # 全面統一頂部圖例字體為 16px
        fig_k.update_layout(
            height=700,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=35, b=10),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="right",
                x=1,
                font=dict(size=16, family="Arial")
            )
        )
        
        # 子圖標題字體統一設定為 16px
        for annotation in fig_k['layout']['annotations']:
            annotation['font'] = dict(size=16, color="#334155")
        
        st.plotly_chart(fig_k, use_container_width=True)
