import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 頁面基本設定 ---
st.set_page_config(
    page_title="專業個人量化選股系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 預設觀察池 ---
DEFAULT_TW_STOCKS = [
    "2330.TW", "2317.TW", "2454.TW", "2382.TW", "2308.TW",
    "3711.TW", "2412.TW", "2881.TW", "2882.TW", "2891.TW",
    "2603.TW", "2379.TW", "3008.TW", "3037.TW", "2303.TW",
    "3231.TW", "2357.TW", "6669.TW", "2609.TW", "2615.TW"
]

DEFAULT_US_STOCKS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
    "META", "TSLA", "AMD", "AVGO", "QCOM",
    "NFLX", "COST", "PLTR", "ARM", "SMCI"
]

# --- 資料抓取與快取 ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_data(tickers, interval="1d", period="1y"):
    """
    批次下載股價資料，快取1小時避免頻繁請求
    """
    if not tickers:
        return {}
    
    # 批次下載
    data = yf.download(tickers, period=period, interval=interval, group_by='ticker', auto_adjust=False, threads=True)
    
    result = {}
    if len(tickers) == 1:
        ticker = tickers[0]
        if not data.empty and len(data) > 60:
            result[ticker] = data.dropna(how='all')
    else:
        for ticker in tickers:
            try:
                df = data[ticker].dropna(how='all')
                if not df.empty and len(df) > 60:
                    result[ticker] = df
            except Exception:
                continue
    return result

# --- 側邊欄控制項 ---
st.sidebar.title("🔍 選股策略條件設定")

market = st.sidebar.radio("🌐 選擇市場", ["台股 (TW)", "美股 (US)"])

timeframe = st.sidebar.selectbox("⏱️ 分析週期", ["日K (1d)", "週K (1wk)"], index=0)
interval_param = "1d" if "日K" in timeframe else "1wk"
period_param = "2y" if "週K" in timeframe else "1y"

st.sidebar.markdown("---")
st.sidebar.subheader("1. 均線排列條件")
enable_ma_filter = st.sidebar.checkbox("啟用價格均線多頭排列且站上均線", value=True)
ma_short = st.sidebar.number_input("短期均線 (SMA)", value=8, min_value=2, max_value=200)
ma_mid = st.sidebar.number_input("中期均線 (SMA)", value=21, min_value=2, max_value=200)
ma_long = st.sidebar.number_input("長期均線 (SMA)", value=55, min_value=2, max_value=300)

enable_vma_filter = st.sidebar.checkbox("啟用成交量均線多頭排列", value=False)
vma_short = st.sidebar.number_input("短量均 (VMA)", value=5, min_value=2, max_value=100)
vma_mid = st.sidebar.number_input("中量均 (VMA)", value=13, min_value=2, max_value=100)
vma_long = st.sidebar.number_input("長量均 (VMA)", value=34, min_value=2, max_value=100)

st.sidebar.markdown("---")
st.sidebar.subheader("2. 價量突破型態")
enable_vol_breakout = st.sidebar.checkbox("當期成交量 > 5均量倍數 (帶量突破)", value=True)
vol_multiplier = st.sidebar.slider("成交量放大倍數", min_value=1.2, max_value=5.0, value=2.0, step=0.1)

enable_price_breakout = st.sidebar.checkbox("收盤價創 N 期新高", value=True)
price_high_days = st.sidebar.slider("創高天期 (N)", min_value=5, max_value=120, value=20, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("3. 流動性與門檻過濾")
min_price = st.sidebar.number_input("最低股價 (元/美元)", value=10.0, min_value=0.0, step=1.0)
min_vol = st.sidebar.number_input("最低成交量 (張/股)", value=500 if market == "台股 (TW)" else 500000, step=100)

st.sidebar.markdown("---")
st.sidebar.subheader("4. 自訂觀察清單")
custom_input = st.sidebar.text_area(
    "輸入股票代號（逗號或換行分隔）",
    value="\n".join(DEFAULT_TW_STOCKS if market == "台股 (TW)" else DEFAULT_US_STOCKS),
    height=120
)

# --- 資料解析與篩選邏輯 ---
ticker_list = [t.strip().upper() for t in custom_input.replace("\n", ",").split(",") if t.strip()]

st.title("📊 個人量化股票篩選系統")
st.caption(f"目前分析市場：{market} ｜ 分析週期：{timeframe} ｜ 觀察標的總數：{len(ticker_list)}")

if st.button("🚀 開始執行量化篩選", type="primary"):
    with st.spinner("正在取得即時數據並計算指標中..."):
        stock_data = fetch_stock_data(ticker_list, interval=interval_param, period=period_param)
        
        filtered_results = []
        
        for ticker, df in stock_data.items():
            if len(df) < max(ma_long, vma_long, price_high_days) + 5:
                continue
            
            # 指標計算
            df['SMA_S'] = df['Close'].rolling(window=ma_short).mean()
            df['SMA_M'] = df['Close'].rolling(window=ma_mid).mean()
            df['SMA_L'] = df['Close'].rolling(window=ma_long).mean()
            
            df['VMA_5'] = df['Volume'].rolling(window=5).mean()
            df['VMA_S'] = df['Volume'].rolling(window=vma_short).mean()
            df['VMA_M'] = df['Volume'].rolling(window=vma_mid).mean()
            df['VMA_L'] = df['Volume'].rolling(window=vma_long).mean()
            
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            close = float(curr['Close'])
            prev_close = float(prev['Close'])
            pct_change = ((close - prev_close) / prev_close) * 100
            volume = float(curr['Volume'])
            # 台股換算為「張數」(除以1000)
            vol_display = volume / 1000 if market == "台股 (TW)" else volume
            
            tags = []
            
            # 門檻過濾 (流動性與股價)
            if close < min_price or vol_display < min_vol:
                continue
            
            # 條件 1: 均線排列 (Close > MA_S > MA_M > MA_L)
            ma_pass = True
            if enable_ma_filter:
                ma_condition = (
                    close > curr['SMA_S'] and 
                    curr['SMA_S'] > curr['SMA_M'] and 
                    curr['SMA_M'] > curr['SMA_L']
                )
                if not ma_condition:
                    ma_pass = False
                else:
                    tags.append("均線多頭排列")
            
            # 條件 1-2: 量均線多頭 (VMA_S > VMA_M > VMA_L)
            vma_pass = True
            if enable_vma_filter:
                vma_condition = (curr['VMA_S'] > curr['VMA_M'] > curr['VMA_L'])
                if not vma_condition:
                    vma_pass = False
                else:
                    tags.append("量均多頭")
                    
            # 條件 2: 帶量突破 (Volume > 5MA_Vol * X)
            vol_pass = True
            if enable_vol_breakout:
                if curr['VMA_5'] > 0 and volume >= (prev['VMA_5'] * vol_multiplier):
                    tags.append(f"量增 {vol_multiplier}x")
                else:
                    vol_pass = False
            
            # 條件 2-2: 創 N 期新高 (Close >= 最近 N 期最高收盤價)
            price_high_pass = True
            if enable_price_breakout:
                n_period_high = df['Close'].iloc[-(price_high_days+1):-1].max()
                if close >= n_period_high:
                    tags.append(f"創 {price_high_days} 期新高")
                else:
                    price_high_pass = False
            
            # 綜合篩選判定
            if ma_pass and vma_pass and vol_pass and price_high_pass:
                filtered_results.append({
                    "代號": ticker,
                    "收盤價": round(close, 2),
                    "漲跌幅 (%)": round(pct_change, 2),
                    "成交量 (張)" if market == "台股 (TW)" else "成交量 (股)": int(vol_display),
                    "符合特徵": ", ".join(tags)
                })
        
        st.session_state['filtered_results'] = filtered_results
        st.session_state['stock_data'] = stock_data

# --- 呈現篩選結果表格 ---
if 'filtered_results' in st.session_state:
    results = st.session_state['filtered_results']
    if not results:
        st.warning("⚠️ 目前條件未篩選出符合的股票，建議適度放寬條件或增加觀察股票池。")
    else:
        st.success(f"🎉 篩選完成！共找到 **{len(results)}** 檔符合條件標的")
        df_result = pd.DataFrame(results)
        
        # 互動式表格展示
        st.dataframe(
            df_result.style.format({
                "收盤價": "{:.2f}",
                "漲跌幅 (%)": "{:+.2f}%",
                "成交量 (張)" if market == "台股 (TW)" else "成交量 (股)": "{:,}"
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        st.subheader("📈 個股技術分析互動圖表")
        
        selected_ticker = st.selectbox(
            "請選擇要查看技術圖表的股票：",
            options=[r["代號"] for r in results]
        )
        
        if selected_ticker and selected_ticker in st.session_state['stock_data']:
            df_plot = st.session_state['stock_data'][selected_ticker].copy()
            
            # 重新計算均線供繪圖
            df_plot['SMA_S'] = df_plot['Close'].rolling(window=ma_short).mean()
            df_plot['SMA_M'] = df_plot['Close'].rolling(window=ma_mid).mean()
            df_plot['SMA_L'] = df_plot['Close'].rolling(window=ma_long).mean()
            df_plot['VMA_5'] = df_plot['Volume'].rolling(window=5).mean()
            
            # 取最近 120 根 K 棒繪製
            df_plot = df_plot.iloc[-120:]
            
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3],
                subplot_titles=(f"{selected_ticker} K線與均線", "成交量與量均線")
            )
            
            # K線圖
            fig.add_trace(
                go.Candlestick(
                    x=df_plot.index,
                    open=df_plot['Open'],
                    high=df_plot['High'],
                    low=df_plot['Low'],
                    close=df_plot['Close'],
                    name="K線",
                    increasing_line_color='#FF3333',
                    decreasing_line_color='#00AA00'
                ),
                row=1, col=1
            )
            
            # 均線疊加
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_S'], mode='lines', name=f'{ma_short} MA', line=dict(width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_M'], mode='lines', name=f'{ma_mid} MA', line=dict(width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_L'], mode='lines', name=f'{ma_long} MA', line=dict(width=2)), row=1, col=1)
            
            # 成交量柱狀圖
            colors = ['#FF3333' if c >= o else '#00AA00' for c, o in zip(df_plot['Close'], df_plot['Open'])]
            fig.add_trace(
                go.Bar(x=df_plot.index, y=df_plot['Volume'], name="成交量", marker_color=colors, showlegend=False),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=df_plot.index, y=df_plot['VMA_5'], mode='lines', name='5 VMA', line=dict(color='orange', width=1.5)),
                row=2, col=1
            )
            
            fig.update_layout(
                height=650,
                xaxis_rangeslider_visible=False,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
