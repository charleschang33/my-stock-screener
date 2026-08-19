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
        number={'prefix': prefix, 'suffix': suffix, 'font': {'size': 32, 'color': '#0f172a', 'family': 'Arial Black'}},
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
    fig.update_layout(height=220, margin=dict(l=25, r=25, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig


# ==========================================
# 5. 主畫面 UI 與 篩選邏輯
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

with col2:
    st.plotly_chart(create_visual_gauge("TW VIX 臺指波動率", 35.5, 0, 50, "", "", "↑ 高波動 (警戒)", "2026-08-19 更新", [
        {'range': [0, 18], 'color': '#10b981'}, {'range': [18, 30], 'color': '#f59e0b'}, {'range': [30, 50], 'color': '#ef4444'}
    ]), use_container_width=True)

with col3:
    st.plotly_chart(create_visual_gauge("Fear & Greed 恐懼與貪婪", 64, 0, 100, "", "", "↑ 貪婪 (情緒熱絡)", "2026-08-19 23:59", [
        {'range': [0, 35], 'color': '#ef4444'}, {'range': [35, 65], 'color': '#f59e0b'}, {'range': [65, 100], 'color': '#10b981'}
    ]), use_container_width=True)

st.divider()

# ------------------------------------------
# Sidebar: 側邊欄設定
# ------------------------------------------
st.sidebar.header("⚙️ 篩選條件設定")

# 1. 市場與資料源選擇
market_choice = st.sidebar.radio("選擇市場", ["台股 (TW)", "美股 (US)"], index=0)

if "台股" in market_choice:
    data_source = st.sidebar.radio("📡 資料來源 (Data Source)", ["yfinance", "twstock"], index=0)
    if data_source == "twstock":
        st.sidebar.caption("⚠️ twstock 連線台灣證交所，若因證交所限流請切回 yfinance。")
else:
    data_source = "yfinance"
    st.sidebar.info("美股預設由 yfinance 取得報價")

current_db = STOCK_DATABASE if "台股" in market_choice else US_STOCK_DATABASE

# 2. 分析週期
timeframe_map = {
    "日K線 (Daily)": ("1d", "1y"),
    "週K線 (Weekly)": ("1wk", "2y"),
    "月K線 (Monthly)": ("1mo", "5y"),
    "年K線 (Yearly)": ("1y", "10y")
}
selected_timeframe = st.sidebar.selectbox("⏱️ 分析週期", list(timeframe_map.keys()), index=0)
interval_code, period_code = timeframe_map[selected_timeframe]

st.sidebar.subheader("1. K棒型態選股")
enable_three_bar_breakout = st.sidebar.checkbox("🔥 三盤突破 (今收 > 昨收 且 今收 > 前日收)", value=False)

st.sidebar.subheader("2. 均線排列條件")
enable_ma_trend = st.sidebar.checkbox("均線多頭 (Close > MA8 > MA21 > MA55)", value=False)
enable_vma_trend = st.sidebar.checkbox("成交量均線 VMA5 > VMA13 > VMA34", value=False)

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
    ["全部標的", "🔥 三盤突破", "⚡ 價量齊揚", "🚀 均線多頭+爆量", "🏆 創20日新高", "🌟 突破60日新高"],
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
        
    # 計算均線
    df['MA8'] = df['Close'].rolling(8, min_periods=1).mean()
    df['MA20'] = df['Close'].rolling(20, min_periods=1).mean()
    df['MA21'] = df['Close'].rolling(21, min_periods=1).mean()
    df['MA55'] = df['Close'].rolling(55, min_periods=1).mean()
    df['MA60'] = df['Close'].rolling(60, min_periods=1).mean()
    
    # 計算量均線
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
    
    # 條件 1: 三盤突破 (今收 > 昨收 且 今收 > 前天收)
    is_three_bar_breakout = (close > close_prev1) and (close > close_prev2)
    pass_three_bar = True
    if enable_three_bar_breakout:
        if not is_three_bar_breakout:
            pass_three_bar = False
    if is_three_bar_breakout:
        tags.append("三盤突破")

    # 條件 2: 均線多頭排列
    pass_ma = True
    if enable_ma_trend:
        if not (close > curr['MA8'] > curr['MA21'] > curr['MA55']):
            pass_ma = False
        else:
            tags.append("均線多頭")
            
    # 條件 2-2: 量均線多頭
    pass_vma = True
    if enable_vma_trend:
        if (curr['VMA5'] > curr['VMA13'] > curr['VMA34']):
            tags.append("量均多頭")
        else:
            pass_vma = False

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
    elif quick_filter == "⚡ 價量齊揚":
        pass_quick = (pct_change > 1.5 and volume > prev1['VMA5'])
    elif quick_filter == "🚀 均線多頭+爆量":
        pass_quick = (close > curr['MA8'] > curr['MA21'] and volume >= prev1['VMA5'] * 1.3)
    elif quick_filter == "🏆 創20日新高":
        if len(df) > 20:
            pass_quick = (close >= df['Close'].iloc[-21:-1].max())
    elif quick_filter == "🌟 突破60日新高":
        if len(df) > 60:
            pass_quick = (close >= df['Close'].iloc[-61:-1].max())
        else:
            pass_quick = False

    # 綜合滿足判定
    if pass_three_bar and pass_ma and pass_vma and pass_vol and pass_high_custom and pass_quick:
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
# Section 4: 表格與下載
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
    st.write(f"📊 **找到 {len(df_result)} 檔符合標的（資料來源：{data_source} ｜ 週期：{selected_timeframe}）：**")
    st.dataframe(
        df_result.style.format({
            "最新股價": "{:.2f}",
            "漲跌幅 (%)": "{:+.2f}%",
            "成交量 (張)" if "台股" in market_choice else "成交量 (股)": "{:,}"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()

    # ------------------------------------------
    # Section 5: Plotly 互動式 K 線
    # ------------------------------------------
    st.subheader("📈 個股技術分析圖表")
    selected_code = st.selectbox("請選擇個股檢視 K 線：", df_result["代號"].tolist())
    
    if selected_code and selected_code in raw_stock_data:
        df_k = raw_stock_data[selected_code].copy()
        
        df_k['MA8'] = df_k['Close'].rolling(8, min_periods=1).mean()
        df_k['MA20'] = df_k['Close'].rolling(20, min_periods=1).mean()
        df_k['MA60'] = df_k['Close'].rolling(60, min_periods=1).mean()
        df_k['VMA5'] = df_k['Volume'].rolling(5, min_periods=1).mean()
        
        df_k = df_k.iloc[-100:]
        
        fig_k = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{selected_code} ({selected_timeframe}) K線與均線走勢", "成交量與 5 均量")
        )
        
        # K線
        fig_k.add_trace(
            go.Candlestick(
                x=df_k.index,
                open=df_k['Open'],
                high=df_k['High'],
                low=df_k['Low'],
                close=df_k['Close'],
                name="K線",
                increasing_line_color='#ef4444',
                decreasing_line_color='#22c55e'
            ),
            row=1, col=1
        )
        
        # 均線
        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA8'], mode='lines', name='MA8', line=dict(color='#3b82f6', width=1.2)), row=1, col=1)
        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA20'], mode='lines', name='20MA (月線)', line=dict(color='#f59e0b', width=1.8)), row=1, col=1)
        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA60'], mode='lines', name='60MA (季線)', line=dict(color='#8b5cf6', width=2.0)), row=1, col=1)
        
        # 成交量
        v_colors = ['#ef4444' if c >= o else '#22c55e' for c, o in zip(df_k['Close'], df_k['Open'])]
        fig_k.add_trace(
            go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color=v_colors, showlegend=False),
            row=2, col=1
        )
        fig_k.add_trace(
            go.Scatter(x=df_k.index, y=df_k['VMA5'], mode='lines', name='5 均量', line=dict(color='#f97316', width=1.5)),
            row=2, col=1
        )
        
        fig_k.update_layout(
            height=550,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_k, use_container_width=True)
