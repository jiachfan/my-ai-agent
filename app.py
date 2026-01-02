import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from datetime import datetime

# --- [1. 基础配置与持久化] ---
st.set_page_config(page_title="2026 AI 交易系统", layout="centered")
DATA_FILE = "account_store.csv"

def load_account():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            cash = float(df.loc[df['type'] == 'cash', 'val1'].values[0])
            holdings = {row['ticker']: {"shares": float(row['val1']), "cost": float(row['val2'])} 
                        for _, row in df[df['type'] == 'holding'].iterrows()}
            return cash, holdings
        except: return 100000.0, {}
    return 100000.0, {}

def save_account():
    data = [{"type": "cash", "ticker": "CASH", "val1": st.session_state.cash, "val2": 0}]
    for t, info in st.session_state.holdings.items():
        data.append({"type": "holding", "ticker": t, "val1": info['shares'], "val2": info['cost']})
    pd.DataFrame(data).to_csv(DATA_FILE, index=False)

if 'initialized' not in st.session_state:
    c, h = load_account()
    st.session_state.cash, st.session_state.holdings = c, h
    st.session_state.initialized = True

def bark_push(title, content):
    key = st.secrets.get("BARK_KEY")
    if key:
        try: requests.get(f"https://api.day.app/{key}/{title}/{content}")
        except: pass

# --- [2. 市场数据抓取] ---
@st.cache_data(ttl=600)
def get_market_intelligence():
    tickers = list(set(["MSFT", "AAPL", "NVDA", "TSLA", "LLY", "UNH", "NEE", "COST", "AMD", "GOOGL"] + list(st.session_state.holdings.keys())))
    intelligence = {}
    for t in tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period="14d")
            delta = h['Close'].diff()
            gain = (delta.where(delta > 0, 0)).mean()
            loss = (-delta.where(delta < 0, 0)).mean()
            rs = gain / (loss + 0.00001)
            rsi = 100 - (100 / (1+rs))
            intelligence[t] = {
                "price": h['Close'].iloc[-1],
                "change": (h['Close'].iloc[-1]/h['Close'].iloc[-2]-1)*100,
                "pe": s.info.get('trailingPE', 0),
                "growth": s.info.get('earningsQuarterlyGrowth', 0),
                "name": s.info.get('shortName', t),
                "rsi": rsi
            }
        except: continue
    return intelligence

market_data = get_market_intelligence()

# --- [3. 页面布局] ---
st.title("🤖 2026 AI 专家协作系统")
tab_scan, tab_buy, tab_sell, tab_portfolio = st.tabs(["🌟 猎手发现", "➕ 买入审查", "➖ 卖出决策", "💰 账户持仓"])

# --- TAB 1: 发现潜力 (Agent 7) ---
with tab_scan:
    st.subheader("Agent 7: 潜力股扫描")
    potentials = [t for t, v in market_data.items() if 0 < v['pe'] < 45 and v['growth'] > 0.1]
    for t in potentials:
        v = market_data[t]
        st.markdown(f"""<div style="background:#161b22; padding:12px; border-radius:10px; border-left:5px solid #ffd700; margin-bottom:10px;">
            <b>{t}</b> | {v['name']} | RSI: {v['rsi']:.1f}</div>""", unsafe_allow_html=True)
        if st.button(f"提交 {t} 买入审查", key=f"scan_{t}"):
            st.session_state.pending_buy = t
            st.success("已载入买入队列")

# --- TAB 2: 买入逻辑 (Agent 4) ---
with tab_buy:
    st.subheader("Agent 4: 买入准入审查")
    selected_b = st.selectbox("买入标的", list(market_data.keys()), index=list(market_data.keys()).index(st.session_state.get('pending_buy', "NVDA")))
    b_amount = st.number_input("拟买入数量", min_value=1, value=10, key="buy_amt")
    b_price = market_data[selected_b]['price']
    b_total = b_price * b_amount
    
    # 风险评估逻辑
    if market_data[selected_b]['rsi'] > 70:
        st.error("🚫 Agent 4: 技术面严重超买，建议暂缓。")
    elif b_total > st.session_state.cash:
        st.error("🚫 Agent 4: 现金余额不足。")
    else:
        st.success("✅ Agent 4: 风险可控，准许执行。")
        if st.button("🚀 执行买入"):
            st.session_state.cash -= b_total
            hold = st.session_state.holdings.get(selected_b, {"shares": 0, "cost": 0})
            new_shares = hold['shares'] + b_amount
            new_cost = (hold['shares']*hold['cost'] + b_total) / new_shares
            st.session_state.holdings[selected_b] = {"shares": new_shares, "cost": new_cost}
            save_account()
            bark_push("交易成功", f"已买入 {b_amount} 股 {selected_b}")
            st.rerun()

# --- TAB 3: 卖出逻辑 (Agent 4) ---
with tab_sell:
    st.subheader("Agent 4: 卖出决策审查")
    if not st.session_state.holdings:
        st.info("当前无持仓，无需卖出。")
    else:
        selected_s = st.selectbox("选择要卖出的持仓", list(st.session_state.holdings.keys()))
        hold_info = st.session_state.holdings[selected_s]
        s_price = market_data[selected_s]['price']
        s_amount = st.number_input("卖出数量", min_value=1, max_value=int(hold_info['shares']), value=int(hold_info['shares']))
        
        profit_pct = (s_price / hold_info['cost'] - 1) * 100
        st.metric("单股盈亏", f"${s_price - hold_info['cost']:.2f}", f"{profit_pct:.2f}%")

        # Agent 4 卖出建议
        if profit_pct > 25:
            st.warning("💡 Agent 4 建议：利润丰厚，建议卖出部分以锁定收益。")
        elif profit_pct < -10:
            st.error("💡 Agent 4 建议：已触发 10% 止损线，请检查公司基本面是否恶化。")
        else:
            st.info("💡 Agent 4 建议：目前波动属于正常范围，可继续持有。")

        if st.button("🚨 确认执行卖出"):
            sell_value = s_amount * s_price
            st.session_state.cash += sell_value
            if s_amount == hold_info['shares']:
                del st.session_state.holdings[selected_s]
            else:
                st.session_state.holdings[selected_s]['shares'] -= s_amount
            
            save_account()
            bark_push("卖出成功", f"已卖出 {s_amount} 股 {selected_s}，回收资金 ${sell_value:.2f}")
            st.success("卖出成功，资金已到账。")
            st.rerun()

# --- TAB 4: 持仓分布 ---
with tab_portfolio:
    st.subheader("资产实时概览")
    col1, col2 = st.columns(2)
    total_stock_val = sum(info['shares'] * market_data.get(t, {'price':0})['price'] for t, info in st.session_state.holdings.items())
    col1.metric("总资产", f"${total_stock_val + st.session_state.cash:,.2f}")
    col2.metric("可用现金", f"${st.session_state.cash:,.2f}")
    
    if st.session_state.holdings:
        labels = list(st.session_state.holdings.keys()) + ["现金"]
        values = [info['shares']*market_data.get(t, {'price':0})['price'] for t, info in st.session_state.holdings.items()] + [st.session_state.cash]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
