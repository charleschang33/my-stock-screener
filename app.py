import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# ==========================================
# 1. 頁面佈局與自訂 CSS 樣式
# ==========================================
st.set_page_config(
    page_title="AI 投資資訊站 - 個人量化篩選系統",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自訂 CSS，維持乾淨現代 UI
st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    .main-header {
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 預設資料集 (台股/美股標的)
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
# 3. 數據抓取與快取處理
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_batch_stock_data(ticker_list, interval="1d", period="1y"):
    if not ticker_list:
        return {}
    
    try:
        data = yf.download(
            tickers=ticker_list,
            period=period,
            interval=interval,
            group_by='ticker',
            auto_adjust=False,
            threads=True
        )
    except Exception:
        return {}
    
    result = {}
    if len(ticker_list) == 1:
        ticker = ticker_list[0]
        if not data.empty and len(data) > 20:
            result[ticker] = data.dropna(how='all')
    else:
        for ticker in ticker_list:
            try:
                df = data[ticker].dropna(how='all')
                if not df.empty and len(df) > 20:
                    result[ticker] = df
            except Exception:
                continue
    return result


# ==========================================
# 4. 繪製頂部半環形情緒儀表圖 (修復 ValueError 問題)
# ==========================================
def create_gauge_chart(title, value, suffix="", min_val=0, max_val=100, steps=None, current_status=""):
    gauge_dict = {
        'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "#cbd5e1"},
        'bar': {'color': "#1e293b", 'width': 0.2},
        'bgcolor': "white",
        'borderwidth': 0
    }
    
    if steps:
        gauge_dict['steps'] = steps
        
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': suffix, 'font': {'size': 30, 'color': '#0f172a'}},
        title={'text': f"<b>{title}</b><br><span style='font-size:12px;color:gray'>{current_status}</span>", 'font': {'size': 15, 'color': '#334155'}},
        gauge=gauge_dict
    ))
    
    fig.update_layout(
        height=170,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig


# ==========================================
# 5. 主畫面 UI 與篩選邏輯
# ==========================================

st.markdown("<div class='main-header'>🧠 AI 投資資訊站 | 專屬量化選股儀表板</div>", unsafe_allow_html=True)

# ------------------------------------------
# Section 1: 頂部三大市場情緒儀表圖
# ------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    fig1 = create_gauge_chart(
        title="大戶期權多空比",
        value=27,
        suffix="%",
        min_val=-70,
        max_val=70,
        current_status="偏多 | 最新更新",
        steps=[
            {'range': [-70, -20], 'color': '#ef4444'},
            {'range': [-20, 20], 'color': '#f59e0b'},
            {'range': [20, 70], 'color': '#22c55e'}
        ]
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = create_gauge_chart(
        title="TW VIX 臺指波動率",
        value=35.5,
        suffix="",
        min_val=0,
        max_val=50,
        current_status="高波動 | 最新更新",
        steps=[
            {'range': [0, 18], 'color': '#22c55e'},
            {'range': [18, 30], 'color': '#f59e0b'},
            {'range': [30, 50], 'color': '#ef4444'}
        ]
    )
    st.plotly_chart(fig2, use_container_width=True)

with col3:
    fig3 = create_gauge_chart(
        title="Fear & Greed CNN 恐懼與貪婪",
        value=64,
        suffix="",
        min_val=0,
        max_val=100,
        current_status="貪婪 | 最新更新",
        steps=[
            {'range': [0, 35], 'color': '#ef4444'},
            {'range': [35, 65], 'color': '#f59e0b'},
            {'range': [65, 100], 'color': '#22c55e'}
        ]
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ------------------------------------------
# Sidebar: 側邊欄進階參數設定
# ------------------------------------------
st.sidebar.header("⚙️ 篩選條件設定")

market_choice = st.sidebar.radio("選擇市場", ["台股 (TW)", "美股 (US)"], index=0)
current_db = STOCK_DATABASE if "台股" in market_choice else US_STOCK_DATABASE

timeframe = st.sidebar.selectbox("分析週期", ["日K線 (1d)", "週K線 (1wk)"], index=0)
interval_code = "1d" if "日K" in timeframe else "1wk"
period_code = "2y" if "週K" in timeframe else "1y"

st.sidebar.subheader("1. 均線與價量設定")
enable_ma_trend = st.sidebar.checkbox("股價在 MA8, 21, 55 之上且多頭排列", value=True)
enable_vma_trend = st.sidebar.checkbox("成交量均線 VMA5 > VMA13 > VMA34", value=False)

st.sidebar.subheader("2. 帶量突破與創高")
enable_vol_breakout = st.sidebar.checkbox("成交量 > 5日均量 N 倍", value=True)
vol_mult = st.sidebar.slider("成交量放大倍數", 1.2, 5.0, 2.0, 0.1)

enable_high_breakout = st.sidebar.checkbox("收盤價創 N 期新高", value=True)
high_period = st.sidebar.slider("創高天數", 5, 120, 20, 5)

st.sidebar.subheader("3. 流動性過濾門檻")
min_price = st.sidebar.number_input("最低股價 (元/美元)", value=10.0, step=1.0)
min_volume = st.sidebar.number_input("最低成交量 (張/股)", value=500 if "台股" in market_choice else 500000, step=100)


# ------------------------------------------
# Section 2: 快捷頁籤與產業過濾
# ------------------------------------------
st.subheader("📋 股票篩選結果清單")

quick_filter = st.radio(
    "策略快篩頁籤：",
    ["全部標的", "⚡ 收盤後強勢", "🔥 價量齊揚", "🚀 均線多頭+爆量", "🏆 創20日新高"],
    horizontal=True
)

col_search, col_ind, col_export = st.columns([2, 2, 1])

with col_search:
    search_keyword = st.text_input("🔍 搜尋個股或題材關鍵字 (例: AI, 2330)", "")

with col_ind:
    all_industries = ["全部產業"] + sorted(list(set([item["industry"] for item in current_db])))
    selected_industry = st.selectbox("🏭 產業分類：", all_industries)

# ------------------------------------------
# Section 3: 執行篩選
# ------------------------------------------
target_tickers = [item["code"] for item in current_db]
raw_stock_data = get_batch_stock_data(target_tickers, interval=interval_code, period=period_code)

filtered_rows = []

for item in current_db:
    code = item["code"]
    name = item["name"]
    industry = item["industry"]
    theme = item["theme"]
    
    if code not in raw_stock_data:
        continue
        
    df = raw_stock_data[code].copy()
    if len(df) < 55:
        continue
        
    # 計算均線
    df['MA8'] = df['Close'].rolling(8).mean()
    df['MA21'] = df['Close'].rolling(21).mean()
    df['MA55'] = df['Close'].rolling(55).mean()
    
    # 計算量均線
    df['VMA5'] = df['Volume'].rolling(5).mean()
    df['VMA13'] = df['Volume'].rolling(13).mean()
    df['VMA34'] = df['Volume'].rolling(34).mean()
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    close = float(curr['Close'])
    prev_close = float(prev['Close'])
    pct_change = ((close - prev_close) / prev_close) * 100
    volume = float(curr['Volume'])
    vol_display = volume / 1000 if "台股" in market_choice else volume
    
    # 門檻過濾
    if close < min_price or vol_display < min_volume:
        continue
        
    # 關鍵字與產業過濾
    if search_keyword:
        kw = search_keyword.lower()
        if not (kw in code.lower() or kw in name.lower() or kw in theme.lower()):
            continue
            
    if selected_industry != "全部產業" and industry != selected_industry:
        continue
        
    # 條件判斷
    pass_ma = True
    if enable_ma_trend:
        pass_ma = (close > curr['MA8'] > curr['MA21'] > curr['MA55'])
        
    pass_vma = True
    if enable_vma_trend:
        pass_vma = (curr['VMA5'] > curr['VMA13'] > curr['VMA34'])
        
    pass_vol = True
    if enable_vol_breakout:
        pass_vol = (curr['VMA5'] > 0 and volume >= (prev['VMA5'] * vol_mult))
        
    pass_high = True
    if enable_high_breakout:
        n_high = df['Close'].iloc[-(high_period+1):-1].max()
        pass_high = (close >= n_high)
        
    # 快捷頁籤判定
    pass_quick = True
    if quick_filter == "⚡ 收盤後強勢":
        pass_quick = (pct_change > 1.0)
    elif quick_filter == "🔥 價量齊揚":
        pass_quick = (pct_change > 2.0 and volume > prev['VMA5'])
    elif quick_filter == "🚀 均線多頭+爆量":
        pass_quick = (close > curr['MA8'] > curr['MA21'] and volume >= prev['VMA5'] * 1.5)
    elif quick_filter == "🏆 創20日新高":
        n20_high = df['Close'].iloc[-21:-1].max()
        pass_quick = (close >= n20_high)

    if pass_ma and pass_vma and pass_vol and pass_high and pass_quick:
        tags = []
        if close > curr['MA8'] > curr['MA21'] > curr['MA55']:
            tags.append("均線多頭")
        if volume >= prev['VMA5'] * 1.8:
            tags.append("帶量突破")
        if close >= df['Close'].iloc[-21:-1].max():
            tags.append("創20日高")
            
        filtered_rows.append({
            "代號": code,
            "股名": name,
            "最新股價": round(close, 2),
            "漲跌幅 (%)": round(pct_change, 2),
            "成交量 (張)" if "台股" in market_choice else "成交量 (股)": int(vol_display),
            "產業標籤": industry,
            "題材/特徵": theme,
            "策略符合特徵": " | ".join(tags) if tags else "符合條件"
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
            file_name=f"Stock_Screener_Result_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.ms-excel",
            type="primary"
        )

if df_result.empty:
    st.info("💡 目前條件下未找到符合個股，可適度放寬側邊欄過濾條件或切換不同頁籤。")
else:
    st.write(f"📊 **找到 {len(df_result)} 檔符合標的：**")
    
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
        
        df_k['MA8'] = df_k['Close'].rolling(8).mean()
        df_k['MA21'] = df_k['Close'].rolling(21).mean()
        df_k['MA55'] = df_k['Close'].rolling(55).mean()
        df_k['VMA5'] = df_k['Volume'].rolling(5).mean()
        
        df_k = df_k.iloc[-100:]
        
        fig_k = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{selected_code} 技術走勢", "成交量")
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
        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA8'], mode='lines', name='MA8', line=dict(color='#3b82f6', width=1.5)), row=1, col=1)
        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA21'], mode='lines', name='MA21', line=dict(color='#f59e0b', width=1.5)), row=1, col=1)
        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA55'], mode='lines', name='MA55', line=dict(color='#8b5cf6', width=2)), row=1, col=1)
        
        # 成交量
        v_colors = ['#ef4444' if c >= o else '#22c55e' for c, o in zip(df_k['Close'], df_k['Open'])]
        fig_k.add_trace(
            go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color=v_colors, showlegend=False),
            row=2, col=1
        )
        fig_k.add_trace(
            go.Scatter(x=df_k.index, y=df_k['VMA5'], mode='lines', name='5日量均', line=dict(color='#f97316', width=1.5)),
            row=2, col=1
        )
        
        fig_k.update_layout(
            height=550,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_k, use_container_width=True)
