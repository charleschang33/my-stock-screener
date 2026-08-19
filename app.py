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
# 1. 頁面佈局與 CSS 樣式
# ==========================================
st.set_page_config(page_title="AI 投資資訊站", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp {
    background-color: #f8fafc;
}
.main-header {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 12px;
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
div[data-baseweb="select"] span {
    font-size: 16px !important;
    font-weight: 600 !important;
}
div[data-baseweb="select"] input {
    font-size: 16px !important;
}
.market-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 8px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    min-height: 96px;
}
.market-title {
    font-size: 12px;
    color: #64748b;
    font-weight: 600;
    margin-bottom: 4px;
    white-space: nowrap;
}
.market-val {
    font-size: 18px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 4px;
}
.badge-up {
    display: inline-block;
    background-color: #fee2e2;
    color: #dc2626;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 6px;
}
.badge-down {
    display: inline-block;
    background-color: #dcfce7;
    color: #16a34a;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 6px;
}
.breadth-bar {
    display: flex;
    height: 12px;
    border-radius: 6px;
    overflow: hidden;
    margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 標的與大盤/總經指數資料庫
# ==========================================
MARKET_INDICES = [
    {"code": "^GSPC", "name": "S&P 500 (美股標普)"},
    {"code": "^IXIC", "name": "Nasdaq (那斯達克)"},
    {"code": "TX=F", "name": "臺指期貨 (指數)"},
    {"code": "^TWII", "name": "加權指數 (大盤)"},
    {"code": "^TWOII", "name": "櫃買指數 (OTC)"},
    {"code": "TWD=X", "name": "美元/台幣匯率"},
    {"code": "GC=F", "name": "國際黃金期貨"}
]

STOCK_DATABASE = [
    {"code": "2330.TW", "name": "台積電", "industry": "半導體", "theme": "AI、晶圓代工、先進封裝"},
    {"code": "2317.TW", "name": "鴻海", "industry": "電腦週邊", "theme": "AI伺服器、電動車"},
    {"code": "2454.TW", "name": "聯發科", "industry": "半導體", "theme": "手機晶片、AI芯片"},
    {"code": "2382.TW", "name": "廣達", "industry": "電腦週邊", "theme": "AI伺服器、雲端運算"},
    {"code": "2308.TW", "name": "台達電", "industry": "電子零組件", "theme": "電源供應、充電樁"},
    {"code": "3711.TW", "name": "日月光投控", "industry": "半導體", "theme": "封測、CoWoS"},
    {"code": "2603.TW", "name": "長榮", "industry": "航運海運", "theme": "貨櫃航運、高股息"},
    {"code": "3231.TW", "name": "緯創", "industry": "電腦週邊", "theme": "AI伺服器、代工"},
    {"code": "6669.TW", "name": "緯穎", "industry": "電腦週邊", "theme": "AI伺服器、液冷散熱"},
    {"code": "2379.TW", "name": "瑞昱", "industry": "半導體", "theme": "網通晶片、車用電子"},
    {"code": "3008.TW", "name": "大立光", "industry": "光電/鏡頭", "theme": "潛望鏡頭、蘋果供應鏈"},
    {"code": "3037.TW", "name": "欣興", "industry": "電子零組件", "theme": "ABF載板、PCB"},
    {"code": "2476.TW", "name": "鉅祥", "industry": "電子零組件", "theme": "沖壓件、車用元件"},
    {"code": "2467.TW", "name": "志聖", "industry": "其他電子/設備", "theme": "CoWoS設備、PCB設備"},
    {"code": "3605.TW", "name": "致茂", "industry": "其他電子/設備", "theme": "量測儀器、半導體測試"}
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
# 3. 輔助運算函式 (DMI 指標)
# ==========================================
def calculate_dmi(df, period=14):
    high_diff = df['High'].diff()
    low_diff = -df['Low'].diff()
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
    
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    tr_sum = tr.rolling(period, min_periods=1).sum().replace(0, np.nan)
    p_di = (pd.Series(plus_dm, index=df.index).rolling(period, min_periods=1).sum() / tr_sum * 100).fillna(0)
    m_di = (pd.Series(minus_dm, index=df.index).rolling(period, min_periods=1).sum() / tr_sum * 100).fillna(0)
    dx = ((p_di - m_di).abs() / (p_di + m_di).replace(0, np.nan) * 100).fillna(0)
    adx = dx.rolling(period, min_periods=1).mean().fillna(0)
    return p_di, m_di, adx


# ==========================================
# 4. 數據引擎
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def get_stock_data_source(ticker_list, data_source="yfinance", interval="1d", period="2y"):
    result = {}
    if not ticker_list:
        return result

    is_yearly = (interval == "1y" or interval == "YE")
    fetch_interval = "1mo" if is_yearly else interval
    fetch_period = "max" if is_yearly else period

    if data_source == "twstock" and interval == "1d":
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
                    result[t] = df
            except Exception:
                continue
    else:
        try:
            data = yf.download(
                tickers=ticker_list,
                period=fetch_period,
                interval=fetch_interval,
                auto_adjust=False,
                threads=True
            )
            
            if data.empty:
                return {}

            if len(ticker_list) == 1:
                t = ticker_list[0]
                df = data.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    if t in df.columns.levels[1]:
                        df = df.xs(t, axis=1, level=1)
                    else:
                        df.columns = df.columns.get_level_values(0)
                df = df.dropna(how='all')
                
                if is_yearly and not df.empty and 'Close' in df.columns:
                    df = df.resample('YE').agg({
                        'Open': 'first',
                        'High': 'max',
                        'Low': 'min',
                        'Close': 'last',
                        'Volume': 'sum'
                    }).dropna()
                    
                if not df.empty and 'Close' in df.columns:
                    result[t] = df
            else:
                for t in ticker_list:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            if t in data.columns.levels[1]:
                                df = data.xs(t, axis=1, level=1).dropna(how='all')
                            else:
                                df = data[t].dropna(how='all')
                        else:
                            df = data.dropna(how='all')
                            
                        if is_yearly and not df.empty and 'Close' in df.columns:
                            df = df.resample('YE').agg({
                                'Open': 'first',
                                'High': 'max',
                                'Low': 'min',
                                'Close': 'last',
                                'Volume': 'sum'
                            }).dropna()
                            
                        if not df.empty and 'Close' in df.columns:
                            result[t] = df
                    except Exception:
                        continue
        except Exception:
            return {}
            
    return result


# ==========================================
# 5. 繪製半圓形彩色儀表盤
# ==========================================
def create_visual_gauge(title, val, min_val, max_val, prefix="", suffix="", status_label="", sub_text="", steps_config=None, label_color="#059669"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={'prefix': prefix, 'suffix': suffix, 'font': {'size': 30, 'color': '#0f172a', 'family': 'Arial Black'}},
        title={'text': f"<b>{title}</b><br><span style='font-size:12px;color:{label_color};font-weight:bold;'>{status_label}</span><br><span style='font-size:11px;color:#94a3b8;'>{sub_text}</span>", 'font': {'size': 14, 'color': '#334155'}},
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
# 6. 儀表盤點擊彈出明細視窗
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
# 7. 主畫面 UI 與 篩選邏輯
# ==========================================
st.markdown("<div class='main-header'>🧠 AI 投資資訊站 | 專屬量化選股儀表板</div>", unsafe_allow_html=True)

if "selected_stock_code" not in st.session_state:
    st.session_state["selected_stock_code"] = "2330.TW"

# ------------------------------------------
# Section 0: 大盤與各項行情看板
# ------------------------------------------
m_col1, m_col2, m_col3, m_col4, m_col5, m_col6, m_col7, m_col8 = st.columns(8)

with m_col1:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">🇺🇸 S&P 500</div>
        <div class="market-val">5,620.85</div>
        <div class="badge-up">↑ +28.40 (+0.51%)</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📈 看標普", key="btn_idx_sp500", use_container_width=True):
        st.session_state["selected_stock_code"] = "^GSPC"

with m_col2:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">💻 Nasdaq</div>
        <div class="market-val">17,850.30</div>
        <div class="badge-up">↑ +112.60 (+0.63%)</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📈 看那指", key="btn_idx_nasdaq", use_container_width=True):
        st.session_state["selected_stock_code"] = "^IXIC"

with m_col3:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">⚡ 臺指期指數</div>
        <div class="market-val">23,860.00</div>
        <div class="badge-up">↑ +168.00 (+0.71%)</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📈 看臺指期", key="btn_idx_fut", use_container_width=True):
        st.session_state["selected_stock_code"] = "TX=F"

with m_col4:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">🇹🇼 加權指數</div>
        <div class="market-val">23,825.40</div>
        <div class="badge-up">↑ +145.20 (+0.61%)</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📈 看大盤", key="btn_idx_twii", use_container_width=True):
        st.session_state["selected_stock_code"] = "^TWII"

with m_col5:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">🏢 櫃買指數</div>
        <div class="market-val">268.35</div>
        <div class="badge-up">↑ +1.85 (+0.69%)</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📈 看櫃買", key="btn_idx_twoii", use_container_width=True):
        st.session_state["selected_stock_code"] = "^TWOII"

with m_col6:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">🎯 選擇權 P/C</div>
        <div class="market-val">118.5%</div>
        <div class="badge-up">↑ 偏多支撐強勁</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📊 波動率", key="btn_idx_opt", use_container_width=True):
        show_vix_detail()

with m_col7:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">💵 美元/台幣</div>
        <div class="market-val">31.91</div>
        <div class="badge-up">↑ 升值 (+0.25%)</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📈 看台幣", key="btn_idx_twd", use_container_width=True):
        st.session_state["selected_stock_code"] = "TWD=X"

with m_col8:
    st.markdown("""
    <div class="market-card">
        <div class="market-title">🥇 國際黃金</div>
        <div class="market-val">4,395.80</div>
        <div class="badge-up">↑ +18.40 (+0.42%)</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("📈 看黃金", key="btn_idx_gold", use_container_width=True):
        st.session_state["selected_stock_code"] = "GC=F"

st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

# ------------------------------------------
# Section 1: 頂部三大儀表圖
# ------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.plotly_chart(create_visual_gauge("大戶期權多空比", 27, -70, 70, "+", "%", "↑ 偏多 (多方佔優)", "2026-08-19 更新", [
        {'range': [-70, -20], 'color': '#ef4444'}, {'range': [-20, 20], 'color': '#f59e0b'}, {'range': [20, 70], 'color': '#10b981'}
    ], label_color="#059669"), use_container_width=True)
    if st.button("📊 點擊查看【大戶多空】計算明細", key="btn_opt", use_container_width=True):
        show_options_detail()

with col2:
    st.plotly_chart(create_visual_gauge("TW VIX 臺指波動率", 35.5, 0, 50, "", "", "↑ 高波動 (警戒)", "2026-08-19 更新", [
        {'range': [0, 18], 'color': '#10b981'}, {'range': [18, 30], 'color': '#f59e0b'}, {'range': [30, 50], 'color': '#ef4444'}
    ], label_color="#ef4444"), use_container_width=True)
    if st.button("📉 點擊查看【TW VIX】計算明細", key="btn_vix", use_container_width=True):
        show_vix_detail()

with col3:
    st.plotly_chart(create_visual_gauge("Fear & Greed 恐懼與貪婪", 64, 0, 100, "", "", "↑ 貪婪 (情緒熱絡)", "2026-08-19 23:59", [
        {'range': [0, 35], 'color': '#10b981'}, {'range': [35, 65], 'color': '#f59e0b'}, {'range': [65, 100], 'color': '#ef4444'}
    ], label_color="#ef4444"), use_container_width=True)
    if st.button("🧭 點擊查看【恐懼貪婪】7大因子", key="btn_fg", use_container_width=True):
        show_fear_greed_detail()

# ------------------------------------------
# Section 1.5: 族群成交量價比較 與 個股漲跌分佈
# ------------------------------------------
col_sec_left, col_sec_right = st.columns([1.1, 0.9])

with col_sec_left:
    st.markdown("#### 🔥 台股主要族群成交量與漲跌幅比較")
    sector_data = pd.DataFrame({
        "族群名稱": ["半導體", "電腦週邊", "電子零組件", "其他電子/設備", "光電/鏡頭", "航運海運", "金融保險", "綠能重電"],
        "成交金額 (億)": [1680, 840, 430, 310, 195, 210, 165, 120],
        "成交比重 (%)": [42.5, 21.3, 10.9, 7.8, 4.9, 5.3, 4.2, 3.1],
        "族群平均漲跌 (%)": [1.45, 0.82, -0.45, 1.85, 2.10, 0.35, -0.20, 0.95]
    })

    fig_sector = make_subplots(specs=[[{"secondary_y": True}]])
    fig_sector.add_trace(
        go.Bar(
            x=sector_data["族群名稱"],
            y=sector_data["成交金額 (億)"],
            name="成交金額 (億元)",
            marker_color="#3b82f6",
            hovertemplate="<b>%{x}</b><br>成交金額: %{y} 億<br>資金比重: %{customdata}%<extra></extra>",
            customdata=sector_data["成交比重 (%)"]
        ),
        secondary_y=False
    )
    scatter_colors = ['#ef4444' if pct >= 0 else '#22c55e' for pct in sector_data["族群平均漲跌 (%)"]]
    fig_sector.add_trace(
        go.Scatter(
            x=sector_data["族群名稱"],
            y=sector_data["族群平均漲跌 (%)"],
            name="族群漲跌幅 (%)",
            mode="lines+markers+text",
            line=dict(color="#f59e0b", width=2.5),
            marker=dict(size=8, color=scatter_colors),
            text=[f"{pct:+.2f}%" for pct in sector_data["族群平均漲跌 (%)"]],
            textposition="top center",
            textfont=dict(color=scatter_colors, size=11, family="Arial Black")
        ),
        secondary_y=True
    )
    fig_sector.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    fig_sector.update_yaxes(title_text="成交金額 (億)", secondary_y=False, showgrid=True, gridcolor="#f1f5f9")
    fig_sector.update_yaxes(title_text="漲跌幅 (%)", secondary_y=True, showgrid=False, range=[-1.2, 3.2])
    st.plotly_chart(fig_sector, use_container_width=True)

with col_sec_right:
    c_head_left, c_head_right = st.columns([1.5, 1])
    with c_head_left:
        st.markdown("#### 📊 個股漲跌分佈")
    with c_head_right:
        market_breadth_type = st.radio("市場：", ["上市", "上櫃"], horizontal=True, label_visibility="collapsed")

    if market_breadth_type == "上市":
        b_labels = ["漲停", ">5%", "2-5%", "0-2%", "平盤", "0-2%", "2-5%", "<5%", "跌停"]
        b_counts = [9, 13, 71, 294, 115, 483, 105, 20, 1]
        b_colors = ["#dc2626", "#ef4444", "#f87171", "#fca5a5", "#94a3b8", "#86efac", "#4ade80", "#22c55e", "#16a34a"]
        up_cnt, down_cnt, flat_cnt = 387, 609, 115
        total_cnt = up_cnt + down_cnt + flat_cnt
    else:
        b_labels = ["漲停", ">5%", "2-5%", "0-2%", "平盤", "0-2%", "2-5%", "<5%", "跌停"]
        b_counts = [15, 22, 95, 260, 80, 310, 85, 18, 2]
        b_colors = ["#dc2626", "#ef4444", "#f87171", "#fca5a5", "#94a3b8", "#86efac", "#4ade80", "#22c55e", "#16a34a"]
        up_cnt, down_cnt, flat_cnt = 392, 415, 80
        total_cnt = up_cnt + down_cnt + flat_cnt

    fig_breadth = go.Figure(go.Bar(
        x=b_labels,
        y=b_counts,
        text=b_counts,
        textposition='outside',
        textfont=dict(size=11, family="Arial Black", color="#334155"),
        marker_color=b_colors,
        hovertemplate="<b>%{x}</b>: %{y} 家<extra></extra>"
    ))
    fig_breadth.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=25, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[0, max(b_counts) * 1.25])
    )
    st.plotly_chart(fig_breadth, use_container_width=True)

    up_pct = (up_cnt / total_cnt) * 100
    down_pct = (down_cnt / total_cnt) * 100
    flat_pct = (flat_cnt / total_cnt) * 100

    st.markdown(f"""
    <div class="breadth-bar">
        <div style="width: {up_pct:.1f}%; background-color: #ef4444;"></div>
        <div style="width: {flat_pct:.1f}%; background-color: #94a3b8;"></div>
        <div style="width: {down_pct:.1f}%; background-color: #22c55e;"></div>
    </div>
    <div style="text-align: center; font-size: 13px; font-weight: 700; color: #334155;">
        漲跌家數比 <span style="color:#ef4444;">{up_cnt} ({up_pct:.1f}%)</span> : <span style="color:#22c55e;">{down_cnt} ({down_pct:.1f}%)</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("👇 **點選下方族群名稱，立即展開成分股與量價明細：**")
selected_sector_tab = st.radio(
    "選擇要檢視成分股的族群：",
    sector_data["族群名稱"].tolist(),
    horizontal=True,
    label_visibility="collapsed"
)

sector_stock_rows = []
for s_item in STOCK_DATABASE:
    if s_item["industry"] == selected_sector_tab:
        sector_stock_rows.append(s_item)

if sector_stock_rows:
    st.info(f"📂 **【{selected_sector_tab}】族群成分股列表（點擊可直接切換下方 K 線圖表）：**")
    sec_cols = st.columns(len(sector_stock_rows))
    for idx, s_info in enumerate(sector_stock_rows):
        with sec_cols[idx]:
            st.markdown(f"**{s_info['name']}** (`{s_info['code']}`)")
            st.caption(f"題材：{s_info['theme']}")
            if st.button(f"🔍 檢視 {s_info['name']} K線", key=f"btn_sec_stk_{s_info['code']}", use_container_width=True):
                st.session_state["selected_stock_code"] = s_info["code"]
else:
    st.caption(f"💡 目前資料庫中【{selected_sector_tab}】暫無獨立成分股收錄。")

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
selected_timeframe = st.sidebar.selectbox("⏱️ 選股分析週期", list(timeframe_map.keys()), index=0)
interval_code, period_code = timeframe_map[selected_timeframe]

st.sidebar.subheader("1. K棒型態選股")
enable_three_bar_breakout = st.sidebar.checkbox("🔥 三盤突破", value=False)
enable_three_bar_breakdown = st.sidebar.checkbox("❄️ 三盤跌破", value=False)

st.sidebar.subheader("2. 均線排列條件")
enable_ma_trend = st.sidebar.checkbox("均線多頭 (MA8 > MA21 > MA55)", value=False)
enable_vma_trend = st.sidebar.checkbox("成交量均線 (VMA5 > VMA13 > VMA34)", value=False)

st.sidebar.subheader("3. 🎯 DMI 多空指標條件")
enable_dmi_pdi_day = st.sidebar.checkbox("DMI +DI(日) >= 門檻", value=False)
dmi_pdi_min_day = st.sidebar.number_input("+DI(日) 最低門檻", value=37.0, step=1.0)

enable_dmi_week_bull = st.sidebar.checkbox("+DI(週) > -DI(週)", value=False)
enable_dmi_week_adx = st.sidebar.checkbox("ADX(週) > -DI(週)", value=False)
enable_week_ma5_ma20 = st.sidebar.checkbox("週均線 5MA > 20MA", value=False)

st.sidebar.subheader("4. 價量突破與創高")
enable_vol_breakout = st.sidebar.checkbox("成交量 > 5日均量 N 倍", value=False)
vol_mult = st.sidebar.slider("成交量放大倍數", 1.2, 5.0, 1.5, 0.1)

enable_high_custom = st.sidebar.checkbox("自訂收盤價創 N 日新高", value=False)
high_period = st.sidebar.slider("自訂創高天數 (N)", 5, 120, 20, 5)

st.sidebar.subheader("5. 門檻過濾")
min_price = st.sidebar.number_input("最低股價 (台幣NTD / 美元USD)", value=10.0, step=1.0)
min_volume = st.sidebar.number_input("最低成交量 (張/股)", value=500 if "台股" in market_choice else 500000, step=100)


# ------------------------------------------
# Section 2: 快捷頁籤與產業過濾
# ------------------------------------------
st.subheader("📋 股票篩選結果清單")

quick_filter = st.radio(
    "策略快篩頁籤：",
    ["全部標的", "🎯 DMI強勢波段", "🔥 三盤突破", "❄️ 三盤跌破", "⚡ 價量齊揚", "🚀 均線多頭+爆量", "🏆 創20日新高", "🌟 突破60日新高"],
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

raw_weekly_data = {}
if enable_dmi_week_bull or enable_dmi_week_adx or enable_week_ma5_ma20 or quick_filter == "🎯 DMI強勢波段":
    raw_weekly_data = get_stock_data_source(target_tickers, data_source="yfinance", interval="1wk", period="2y")

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
    if len(df) < 5 or 'Close' not in df.columns:
        continue
        
    df['MA8'] = df['Close'].rolling(8, min_periods=1).mean()
    df['MA21'] = df['Close'].rolling(21, min_periods=1).mean()
    df['MA55'] = df['Close'].rolling(55, min_periods=1).mean()
    
    df['VMA5'] = df['Volume'].rolling(5, min_periods=1).mean()
    df['VMA13'] = df['Volume'].rolling(13, min_periods=1).mean()
    df['VMA34'] = df['Volume'].rolling(34, min_periods=1).mean()
    
    p_di_day, m_di_day, adx_day = calculate_dmi(df, 14)
    df['Plus_DI'] = p_di_day
    df['Minus_DI'] = m_di_day
    df['ADX'] = adx_day
    
    curr = df.iloc[-1]
    prev1 = df.iloc[-2] if len(df) >= 2 else curr
    prev2 = df.iloc[-3] if len(df) >= 3 else prev1
    
    close = float(curr['Close'])
    close_prev1 = float(prev1['Close'])
    close_prev2 = float(prev2['Close'])
    
    pct_change = ((close - close_prev1) / close_prev1) * 100 if close_prev1 > 0 else 0
    volume = float(curr['Volume'])
    vol_display = volume / 1000 if "台股" in market_choice else volume
    
    if close < min_price or vol_display < min_volume:
        continue
        
    if search_keyword:
        kw = search_keyword.lower()
        if not (kw in code.lower() or kw in name.lower() or kw in theme.lower()):
            continue
            
    if selected_industry != "全部產業" and industry != selected_industry:
        continue
        
    tags = []
    
    is_three_bar_breakout = (close > close_prev1) and (close > close_prev2)
    pass_three_bar = True
    if enable_three_bar_breakout:
        if not is_three_bar_breakout:
            pass_three_bar = False
    if is_three_bar_breakout:
        tags.append("三盤突破")

    is_three_bar_breakdown = (close < close_prev1) and (close < close_prev2)
    pass_three_breakdown = True
    if enable_three_bar_breakdown:
        if not is_three_bar_breakdown:
            pass_three_breakdown = False
    if is_three_bar_breakdown:
        tags.append("三盤跌破")

    is_ma_aligned = (curr['MA8'] > curr['MA21'] > curr['MA55'])
    pass_ma = True
    if enable_ma_trend:
        if not is_ma_aligned:
            pass_ma = False
    if is_ma_aligned:
        tags.append("均線多頭")
            
    is_vma_aligned = (curr['VMA5'] > curr['VMA13'] > curr['VMA34'])
    pass_vma = True
    if enable_vma_trend:
        if not is_vma_aligned:
            pass_vma = False
    if is_vma_aligned:
        tags.append("量均多頭")

    pass_dmi_day = True
    if enable_dmi_pdi_day:
        if curr['Plus_DI'] >= dmi_pdi_min_day:
            tags.append(f"+DI(日)≥{int(dmi_pdi_min_day)}")
        else:
            pass_dmi_day = False

    pass_dmi_wk_bull = True
    pass_dmi_wk_adx = True
    pass_wk_ma = True
    
    is_dmi_wk_bull = False
    is_dmi_wk_adx = False
    is_wk_ma_aligned = False
    
    if code in raw_weekly_data and len(raw_weekly_data[code]) >= 5:
        df_wk = raw_weekly_data[code].copy()
        p_di_wk, m_di_wk, adx_wk = calculate_dmi(df_wk, 14)
        df_wk['Plus_DI'] = p_di_wk
        df_wk['Minus_DI'] = m_di_wk
        df_wk['ADX'] = adx_wk
        df_wk['MA5'] = df_wk['Close'].rolling(5, min_periods=1).mean()
        df_wk['MA20'] = df_wk['Close'].rolling(20, min_periods=1).mean()
        
        curr_wk = df_wk.iloc[-1]
        
        is_dmi_wk_bull = (curr_wk['Plus_DI'] > curr_wk['Minus_DI'])
        is_dmi_wk_adx = (curr_wk['ADX'] > curr_wk['Minus_DI'])
        is_wk_ma_aligned = (curr_wk['MA5'] > curr_wk['MA20'])
        
        if enable_dmi_week_bull:
            if is_dmi_wk_bull:
                tags.append("+DI(週)>-DI(週)")
            else:
                pass_dmi_wk_bull = False
                
        if enable_dmi_week_adx:
            if is_dmi_wk_adx:
                tags.append("ADX(週)>-DI(週)")
            else:
                pass_dmi_wk_adx = False
                
        if enable_week_ma5_ma20:
            if is_wk_ma_aligned:
                tags.append("週5MA>20MA")
            else:
                pass_wk_ma = False

    pass_vol = True
    if enable_vol_breakout:
        if prev1['VMA5'] > 0 and volume >= (prev1['VMA5'] * vol_mult):
            tags.append(f"量增 {vol_mult}x")
        else:
            pass_vol = False

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

    pass_quick = True
    if quick_filter == "🎯 DMI強勢波段":
        pass_quick = (curr['Plus_DI'] >= 30 and is_dmi_wk_bull and is_dmi_wk_adx and is_wk_ma_aligned)
    elif quick_filter == "🔥 三盤突破":
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

    if pass_three_bar and pass_three_breakdown and pass_ma and pass_vma and pass_vol and pass_high_custom and pass_dmi_day and pass_dmi_wk_bull and pass_dmi_wk_adx and pass_wk_ma and pass_quick:
        filtered_rows.append({
            "代號": code,
            "股名": name,
            "最新股價": round(close, 2),
            "漲跌幅 (%)": round(pct_change, 2),
            "+DI (日)": round(curr['Plus_DI'], 1),
            "成交量 (張)" if "台股" in market_choice else "成交量 (股)": int(vol_display),
            "產業標籤": industry,
            "題材/特徵": theme,
            "觸發特徵": " | ".join(tags) if tags else "符合條件"
        })

# ------------------------------------------
# Section 4: 表格呈現
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

if df_result.empty and len(raw_stock_data) > 0:
    st.info(f"💡 在【{selected_timeframe}】與當前設定下未找到符合個股，可勾選放寬部分條件或切換頁籤。")
elif not df_result.empty:
    st.write(f"📊 **找到 {len(df_result)} 檔符合標的（點擊表格任一列即可自動切換下方圖表）：**")
    
    vol_col_name = "成交量 (張)" if "台股" in market_choice else "成交量 (股)"
    
    event = st.dataframe(
        df_result.style.format({
            "最新股價": "{:.2f}",
            "漲跌幅 (%)": "{:+.2f}%",
            "+DI (日)": "{:.1f}",
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
            "+DI (日)": st.column_config.NumberColumn("+DI (日)", width="small"),
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
    # Section 5: Plotly 互動式 K 線與多週期、多指標切換系統
    # ------------------------------------------
    st.subheader("📈 技術分析與多週期圖表")
    
    all_view_options = {}
    for idx_item in MARKET_INDICES:
        all_view_options[idx_item["code"]] = f"📊 {idx_item['name']} ({idx_item['code']})"
    for _, row in df_result.iterrows():
        all_view_options[row["代號"]] = f"{row['代號']} {row['股名']}"
        
    code_list = list(all_view_options.keys())
    current_selected = st.session_state.get("selected_stock_code", code_list[0])
    
    if current_selected not in code_list:
        code_list.insert(0, current_selected)
        all_view_options[current_selected] = f"📊 {current_selected}"
        
    default_idx = code_list.index(current_selected)
    
    col_stock_sel, col_tf_sel, col_ind_sel = st.columns([1.2, 1.8, 1.2])
    
    with col_stock_sel:
        selected_display = st.selectbox(
            "目前檢視標的：",
            [all_view_options[c] for c in code_list],
            index=default_idx
        )
        selected_code = list(all_view_options.keys())[[all_view_options[c] for c in code_list].index(selected_display)]
        st.session_state["selected_stock_code"] = selected_code

    chart_tf_map = {
        "5分K": ("5m", "5d"),
        "15分K": ("15m", "1mo"),
        "30分K": ("30m", "1mo"),
        "60分K": ("60m", "3mo"),
        "日K": ("1d", "1y"),
        "週K": ("1wk", "2y"),
        "月K": ("1mo", "5y"),
        "年K": ("1y", "max")
    }
    
    with col_tf_sel:
        chart_tf = st.radio(
            "⏱️ 圖表週期：",
            list(chart_tf_map.keys()),
            index=4,
            horizontal=True
        )

    with col_ind_sel:
        indicator_choice = st.selectbox(
            "📊 副圖技術指標：",
            ["DMI 趨向指標 (14)", "KD 指標 (9,3,3)", "RSI 強弱指標 (6,12)", "MACD 指標 (12,26,9)"],
            index=0
        )
        
    c_interval, c_period = chart_tf_map[chart_tf]
    chart_stock_dict = get_stock_data_source([selected_code], data_source="yfinance", interval=c_interval, period=c_period)
    
    if selected_code and selected_code in chart_stock_dict:
        df_k = chart_stock_dict[selected_code].copy()
        
        if not df_k.empty and 'Close' in df_k.columns and len(df_k) >= 2:
            df_k['MA8'] = df_k['Close'].rolling(8, min_periods=1).mean()
            df_k['MA21'] = df_k['Close'].rolling(21, min_periods=1).mean()
            df_k['MA55'] = df_k['Close'].rolling(55, min_periods=1).mean()
            
            df_k['VMA5'] = df_k['Volume'].rolling(5, min_periods=1).mean()
            df_k['VMA13'] = df_k['Volume'].rolling(13, min_periods=1).mean()
            df_k['VMA34'] = df_k['Volume'].rolling(34, min_periods=1).mean()
            
            # KD
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

            # RSI
            delta = df_k['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=6, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=6, min_periods=1).mean()
            rs = gain / loss.replace(0, np.nan)
            df_k['RSI6'] = (100 - (100 / (1 + rs))).fillna(50)

            gain12 = (delta.where(delta > 0, 0)).rolling(window=12, min_periods=1).mean()
            loss12 = (-delta.where(delta < 0, 0)).rolling(window=12, min_periods=1).mean()
            rs12 = gain12 / loss12.replace(0, np.nan)
            df_k['RSI12'] = (100 - (100 / (1 + rs12))).fillna(50)

            # MACD
            exp12 = df_k['Close'].ewm(span=12, adjust=False).mean()
            exp26 = df_k['Close'].ewm(span=26, adjust=False).mean()
            df_k['DIF'] = exp12 - exp26
            df_k['MACD'] = df_k['DIF'].ewm(span=9, adjust=False).mean()
            df_k['OSC'] = df_k['DIF'] - df_k['MACD']

            # DMI
            p_di, m_di, adx = calculate_dmi(df_k, 14)
            df_k['Plus_DI'] = p_di
            df_k['Minus_DI'] = m_di
            df_k['ADX'] = adx
            
            curr_row = df_k.iloc[-1]
            prev_row = df_k.iloc[-2] if len(df_k) >= 2 else curr_row
            
            # 最新斜率與紅綠箭頭判定
            arrow_ma8 = "<span style='color:#ef4444;'>↑</span>" if curr_row['MA8'] >= prev_row['MA8'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_ma21 = "<span style='color:#ef4444;'>↑</span>" if curr_row['MA21'] >= prev_row['MA21'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_ma55 = "<span style='color:#ef4444;'>↑</span>" if curr_row['MA55'] >= prev_row['MA55'] else "<span style='color:#22c55e;'>↓</span>"
            
            arrow_vma5 = "<span style='color:#ef4444;'>↑</span>" if curr_row['VMA5'] >= prev_row['VMA5'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_vma13 = "<span style='color:#ef4444;'>↑</span>" if curr_row['VMA13'] >= prev_row['VMA13'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_vma34 = "<span style='color:#ef4444;'>↑</span>" if curr_row['VMA34'] >= prev_row['VMA34'] else "<span style='color:#22c55e;'>↓</span>"

            arrow_pdi = "<span style='color:#ef4444;'>↑</span>" if curr_row['Plus_DI'] >= prev_row['Plus_DI'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_mdi = "<span style='color:#ef4444;'>↑</span>" if curr_row['Minus_DI'] >= prev_row['Minus_DI'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_adx = "<span style='color:#ef4444;'>↑</span>" if curr_row['ADX'] >= prev_row['ADX'] else "<span style='color:#22c55e;'>↓</span>"

            arrow_k = "<span style='color:#ef4444;'>↑</span>" if curr_row['K'] >= prev_row['K'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_d = "<span style='color:#ef4444;'>↑</span>" if curr_row['D'] >= prev_row['D'] else "<span style='color:#22c55e;'>↓</span>"

            arrow_rsi6 = "<span style='color:#ef4444;'>↑</span>" if curr_row['RSI6'] >= prev_row['RSI6'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_rsi12 = "<span style='color:#ef4444;'>↑</span>" if curr_row['RSI12'] >= prev_row['RSI12'] else "<span style='color:#22c55e;'>↓</span>"

            arrow_dif = "<span style='color:#ef4444;'>↑</span>" if curr_row['DIF'] >= prev_row['DIF'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_macd = "<span style='color:#ef4444;'>↑</span>" if curr_row['MACD'] >= prev_row['MACD'] else "<span style='color:#22c55e;'>↓</span>"
            arrow_osc = "<span style='color:#ef4444;'>↑</span>" if curr_row['OSC'] >= prev_row['OSC'] else "<span style='color:#22c55e;'>↓</span>"
            
            plot_df = df_k.iloc[-100:].copy()
            
            if "DMI" in indicator_choice:
                ind_sub_title = f"<b>DMI 趨向指標 (+DI {arrow_pdi} / -DI {arrow_mdi} / ADX {arrow_adx})</b>"
            elif "KD" in indicator_choice:
                ind_sub_title = f"<b>KD 指標 (K {arrow_k} / D {arrow_d})</b>"
            elif "RSI" in indicator_choice:
                ind_sub_title = f"<b>RSI 強弱指標 (RSI6 {arrow_rsi6} / RSI12 {arrow_rsi12})</b>"
            else:
                ind_sub_title = f"<b>MACD 指標 (DIF {arrow_dif} / MACD {arrow_macd} / OSC {arrow_osc})</b>"

            fig_k = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                row_heights=[0.54, 0.23, 0.23],
                subplot_titles=("", f"<b>成交量 (VMA5 {arrow_vma5} / VMA13 {arrow_vma13} / VMA34 {arrow_vma34})</b>", ind_sub_title)
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
            
            # 主圖線條名稱回歸純淨，Hover 視窗即時顯示當日數值
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA8'], mode='lines', name='MA8', line=dict(color='#3b82f6', width=1.3)), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA21'], mode='lines', name='MA21', line=dict(color='#ec4899', width=1.5)), row=1, col=1)
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA55'], mode='lines', name='MA55', line=dict(color='#8b5cf6', width=1.8)), row=1, col=1)
            
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
                                name=f'{kd["label"]}',
                                text=[f" ◄ {kd['label']}"],
                                textposition="middle right",
                                textfont=dict(color=kd["color"], size=16, family="Arial Black"),
                                marker=dict(size=10, color=kd["color"], symbol="circle-open", line=dict(width=2.5)),
                                showlegend=False
                            ),
                            row=1, col=1
                        )
            
            # 2. 副圖：成交量
            v_colors = ['#ef4444' if c >= o else '#22c55e' for c, o in zip(plot_df['Close'], plot_df['Open'])]
            fig_k.add_trace(
                go.Bar(x=plot_df.index, y=plot_df['Volume'], name="成交量", marker_color=v_colors, showlegend=False),
                row=2, col=1
            )
            fig_k.add_trace(
                go.Scatter(x=plot_df.index, y=plot_df['VMA5'], mode='lines', name='VMA5', line=dict(color='#f97316', width=1.3)),
                row=2, col=1
            )
            fig_k.add_trace(
                go.Scatter(x=plot_df.index, y=plot_df['VMA13'], mode='lines', name='VMA13', line=dict(color='#06b6d4', width=1.3)),
                row=2, col=1
            )
            fig_k.add_trace(
                go.Scatter(x=plot_df.index, y=plot_df['VMA34'], mode='lines', name='VMA34', line=dict(color='#10b981', width=1.3)),
                row=2, col=1
            )
            
            # 3. 第 3 層副圖（Hover 時顯示純淨指標名與當日數值）
            if "DMI" in indicator_choice:
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Plus_DI'], mode='lines', name='+DI', line=dict(color='#ef4444', width=1.5)), row=3, col=1)
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Minus_DI'], mode='lines', name='-DI', line=dict(color='#22c55e', width=1.5)), row=3, col=1)
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['ADX'], mode='lines', name='ADX', line=dict(color='#f59e0b', width=1.5)), row=3, col=1)
                fig_k.add_hline(y=25, line_dash="dot", line_color="#94a3b8", line_width=1, row=3, col=1)

            elif "KD" in indicator_choice:
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['K'], mode='lines', name='K值', line=dict(color='#f59e0b', width=1.5)), row=3, col=1)
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['D'], mode='lines', name='D值', line=dict(color='#3b82f6', width=1.5)), row=3, col=1)
                fig_k.add_hline(y=80, line_dash="dot", line_color="#ef4444", line_width=1, row=3, col=1)
                fig_k.add_hline(y=20, line_dash="dot", line_color="#22c55e", line_width=1, row=3, col=1)

            elif "RSI" in indicator_choice:
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI6'], mode='lines', name='RSI 6日', line=dict(color='#ec4899', width=1.5)), row=3, col=1)
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI12'], mode='lines', name='RSI 12日', line=dict(color='#64748b', width=1.3)), row=3, col=1)
                fig_k.add_hline(y=70, line_dash="dot", line_color="#ef4444", line_width=1, row=3, col=1)
                fig_k.add_hline(y=30, line_dash="dot", line_color="#22c55e", line_width=1, row=3, col=1)

            elif "MACD" in indicator_choice:
                osc_colors = ['#ef4444' if o >= 0 else '#22c55e' for o in plot_df['OSC']]
                fig_k.add_trace(go.Bar(x=plot_df.index, y=plot_df['OSC'], name='OSC柱', marker_color=osc_colors), row=3, col=1)
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['DIF'], mode='lines', name='DIF', line=dict(color='#f59e0b', width=1.5)), row=3, col=1)
                fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MACD'], mode='lines', name='MACD', line=dict(color='#3b82f6', width=1.5)), row=3, col=1)
                fig_k.add_hline(y=0, line_dash="solid", line_color="#cbd5e1", line_width=1, row=3, col=1)
            
            fig_k.update_layout(
                height=740,
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=35, b=10),
                hovermode="x",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.01,
                    xanchor="right",
                    x=1,
                    font=dict(size=16, family="Arial")
                )
            )

            # 跨圖垂直十字引導虛線
            fig_k.update_xaxes(
                showspikes=True,
                spikemode="across",
                spikesnap="cursor",
                spikedash="dot",
                spikethickness=1,
                spikecolor="#94a3b8"
            )
            
            for annotation in fig_k['layout']['annotations']:
                annotation['font'] = dict(size=16, color="#334155")
            
            st.plotly_chart(fig_k, use_container_width=True)
        else:
            st.warning("⚠️ 該標的在當前週期下暫無足夠歷史數據。")
