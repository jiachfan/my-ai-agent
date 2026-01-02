import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from datetime import datetime

# --- [1. 配置与持久化层] ---
st.set_page_config(page_title="2026 AI 交易系统", layout="centered")

DATA_FILE = "account_store.csv"

def load_account():
    """从本地文件读取账户数据"""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            cash = float(df.loc[df['type'] == 'cash', 'val1'].values[0])
            holdings = {}
            h_df = df[df['type'] == 'holding']
            for _, row in h_df.iterrows():
                holdings[row['ticker']] = {"shares": float(row['val1']), "cost": float(row['val2'])}
            return cash, holdings
        except: return 100000.0, {}
    return 100000.0, {}

def save_account():
    """保存账户数据到文件"""
    data = [{"type": "cash", "ticker": "CASH", "val1": st.session_state.cash, "val2": 0}]
    for t, info in st.session_state.holdings.items():
        data.append({"type": "holding", "ticker": t, "val1": info['shares'], "val2": info['cost']})
    pd.DataFrame(data).to_csv(DATA_FILE, index=False)

# 初始化 Session State
if 'initialized' not in st.session_state:
    c, h = load_account()
    st.session_state.cash = c
    st.session_state.holdings = h
    st.session_state.initialized = True

# --- [2. 安全推送层] ---
def bark_push(title, content):
    key = st.secrets.get("BARK_KEY")
    if key:
        try: requests.get(f"https://api.day.app/{key}/{title}/{content}")
        except: pass

# --- [3. Agent 数据逻辑层] ---
@st.cache_data(ttl=600)
def get_market_intelligence():
    tickers = ["MSFT", "AAPL", "NVDA", "TSLA", "LLY", "UNH", "NEE", "COST", "AMD", "GOOGL"]
    intelligence = {}
    for t in tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period="2d")
            info = s.info
            intelligence[t] = {
                "price": h['Close'].iloc[-1],
                "change": (h['Close'].iloc[-1]/h['Close'].iloc[-2]-1)*100,
                "pe": info.get('trailingPE', 0),
                "growth": info.get('earningsQuarterlyGrowth', 0),
                "name": info.get('shortName', t)
            }
        except: continue
    return intelligence

# --- [4. UI 渲染层] ---
st.title("🤖 2026 AI 多 Agent 协作系统")
market_data = get_market_intelligence()

tab_scan, tab_trade, tab_portfolio = st.tabs(["🌟 猎手发现", "🛡️ 风险决策", "💰 账户持仓"])

# --- TAB 1: Agent 7 潜力股发现 ---
with tab_scan:
    st.subheader("Agent 7: 潜力股扫描结果")
    # 筛选：PE < 40 且 增长 > 10%
    potentials = [t for t, v in market_data.items() if 0 < v['pe'] < 40 and v['growth'] > 0.1]
    
    for t in potentials:
        v = market_data[t]
        with st.container():
            st.markdown(f"""
            <div style="background:#161b22; padding:15px; border-radius:10px; border-left:5px solid #ffd700; margin-bottom:10px;">
                <b style="font-size:18px;">{t}</b> | {v['name']}<br>
                <small>现价: ${v['price']:.2f} | PE: {v['pe']:.1f} | 增长: {v['growth']*100:.1f}%</small>
            </div>
            """, unsafe_allow_html=True)
            # 允许直接加入购买序列
            if st.button(f"📥 将 {t} 移交 Agent 4 审查", key=f"btn_{t}"):
                st.session_state.pending_ticker = t
                st.success(f"{t} 已加入决策队列，请切换至风险决策页。")

# --- TAB 2: Agent 4 风险审查与买入 ---
with tab_trade:
    st.subheader("Agent 4: 交易准入审查")
    
    # 自动获取上个页面传递的 Ticker
    default_t = st.session_state.get('pending_ticker', "NVDA")
    selected_t = st.selectbox("当前审查标的", list(market_data.keys()), index=list(market_data.keys()).index(default_t))
    
    amount = st.number_input("拟买入股数", min_value=1, value=10)
    price = market_data[selected_t]['price']
    total_cost = price * amount
    
    # Agent 4 的风险计算
    risk_ratio = (total_cost / (st.session_state.cash + sum(v['shares']*market_data.get(k, {'price':0})['price'] for k,v in st.session_state.holdings.items()) + 0.1)) * 100
    
    st.warning(f"Agent 4 报告：拟建仓位占总资产 {risk_ratio:.1f}%")
    
    if st.button("🚀 Agent 1 执行买入"):
        if total_cost > st.session_state.cash:
            st.error("拒绝：现金不足。")
        else:
            # 更新持仓
            st.session_state.cash -= total_cost
            if selected_t in st.session_state.holdings:
                h = st.session_state.holdings[selected_t]
                new_shares = h['shares'] + amount
                new_cost = (h['shares']*h['cost'] + total_cost) / new_shares
                st.session_state.holdings[selected_t] = {"shares": new_shares, "cost": new_cost}
            else:
                st.session_state.holdings[selected_t] = {"shares": amount, "cost": price}
            
            save_account() # 持久化保存
            bark_push("交易成功", f"Agent 1 已买入 {amount} 股 {selected_t}")
            st.balloons()
            st.success("交易已完成，数据已存档。")

# --- TAB 3: 持仓与分布 ---
with tab_portfolio:
    st.subheader("资产分布与盈亏")
    
    if not st.session_state.holdings:
        st.write("目前没有持仓。")
        st.metric("可用现金", f"${st.session_state.cash:,.2f}")
    else:
        # 饼图
        labels = list(st.session_state.holdings.keys()) + ["现金"]
        values = [v['shares']*market_data.get(k, {'price':0})['price'] for k,v in st.session_state.holdings.items()] + [st.session_state.cash]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # 盈亏表
        p_data = []
        for t, info in st.session_state.holdings.items():
            curr_p = market_data.get(t, {'price':0})['price']
            p_data.append({
                "代码": t, "持股": info['shares'], 
                "成本": f"${info['cost']:.2f}", "现价": f"${curr_p:.2f}",
                "盈亏": f"{(curr_p - info['cost'])*info['shares']:+.2f}",
                "涨跌幅": f"{(curr_p/info['cost']-1)*100:+.2f}%"
            })
        st.table(pd.DataFrame(p_data))
        st.button("手动同步存档", on_click=save_account)
