import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from datetime import datetime

# --- [1. 基础配置与持久化层] ---
st.set_page_config(page_title="2026 AI 交易系统", layout="centered")

DATA_FILE = "account_store.csv"

def load_account():
    """从 CSV 读取账户，确保刷新不掉档"""
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
    """保存数据到 CSV"""
    data = [{"type": "cash", "ticker": "CASH", "val1": st.session_state.cash, "val2": 0}]
    for t, info in st.session_state.holdings.items():
        data.append({"type": "holding", "ticker": t, "val1": info['shares'], "val2": info['cost']})
    pd.DataFrame(data).to_csv(DATA_FILE, index=False)

# 初始化状态
if 'initialized' not in st.session_state:
    c, h = load_account()
    st.session_state.cash, st.session_state.holdings = c, h
    st.session_state.initialized = True

def bark_push(title, content):
    key = st.secrets.get("BARK_KEY")
    if key:
        try: requests.get(f"https://api.day.app/{key}/{title}/{content}")
        except: pass

# --- [2. 市场情报层 (Agent 3 & 7)] ---
@st.cache_data(ttl=600)
def get_market_intelligence():
    # 基础监控池 + 已持有的票
    base_tickers = ["MSFT", "AAPL", "NVDA", "TSLA", "LLY", "UNH", "NEE", "COST", "AMD", "GOOGL"]
    all_to_scan = list(set(base_tickers + list(st.session_state.holdings.keys())))
    
    intelligence = {}
    for t in all_to_scan:
        try:
            s = yf.Ticker(t)
            h = s.history(period="14d")
            if h.empty: continue
            
            # 简单 RSI 计算
            delta = h['Close'].diff()
            gain = (delta.where(delta > 0, 0)).mean()
            loss = (-delta.where(delta < 0, 0)).mean()
            rs = gain / (loss + 0.00001)
            rsi = 100 - (100 / (1+rs))
            
            info = s.info
            intelligence[t] = {
                "price": h['Close'].iloc[-1],
                "change": (h['Close'].iloc[-1]/h['Close'].iloc[-2]-1)*100,
                "pe": info.get('trailingPE', 0),
                "growth": info.get('earningsQuarterlyGrowth', 0),
                "name": info.get('shortName', t),
                "rsi": rsi
            }
        except: continue
    return intelligence

market_data = get_market_intelligence()

# --- [3. 页面渲染层] ---
st.title("🤖 2026 AI 多 Agent 协作系统")

tab_scan, tab_buy, tab_sell, tab_portfolio = st.tabs(["🌟 猎手发现", "➕ 买入审查", "➖ 卖出决策", "💰 账户持仓"])

# --- TAB 1: 发现潜力 (Agent 7) ---
with tab_scan:
    st.subheader("Agent 7: 潜力股扫描")
    potentials = [t for t, v in market_data.items() if 0 < v['pe'] < 45 and v['growth'] > 0.1]
    
    if not potentials:
        st.write("目前暂无符合低估值高增长的标的。")
    
    for t in potentials:
        v = market_data[t]
        st.markdown(f"""<div style="background:#161b22; padding:12px; border-radius:10px; border-left:5px solid #ffd700; margin-bottom:10px;">
            <b>{t}</b> | {v['name']} | RSI: {v['rsi']:.1f} | 增长: {v['growth']*100:.1f}%</div>""", unsafe_allow_html=True)
        if st.button(f"提交 {t} 买入审查", key=f"scan_{t}"):
            st.session_state.pending_buy = t
            st.success(f"{t} 已载入决策队列，请切换标签页。")

# --- TAB 2: 买入逻辑 (Agent 4 修复版) ---
with tab_buy:
    st.subheader("Agent 4: 风险官买入准入")
    
    available_tickers = list(market_data.keys())
    if not available_tickers:
        st.warning("等待市场数据同步...")
    else:
        # 修复 ValueError: 确保默认值在列表中
        pending = st.session_state.get('pending_buy', "NVDA")
        default_idx = available_tickers.index(pending) if pending in available_tickers else 0
        
        selected_b = st.selectbox("选择买入目标", available_tickers, index=default_idx)
        b_amount = st.number_input("拟买入数量", min_value=1, value=10)
        
        v = market_data[selected_b]
        b_total = v['price'] * b_amount
        
        # Agent 4 实时评估
        st.markdown("#### 🛡️ 风险官评估意见")
        if v['rsi'] > 70:
            st.error(f"❌ 严重超买：{selected_b} 当前 RSI 为 {v['rsi']:.1f}，追高风险极高！")
        elif b_total > st.session_state.cash:
            st.error("❌ 资金不足：账户现金无法覆盖本次交易。")
        else:
            st.success(f"✅ 准许执行：预计占用现金 ${b_total:,.2f}。")
            if st.button("🚀 Agent 1 执行买入"):
                st.session_state.cash -= b_total
                hold = st.session_state.holdings.get(selected_b, {"shares": 0, "cost": 0})
                new_shares = hold['shares'] + b_amount
                new_cost = (hold['shares']*hold['cost'] + b_total) / new_shares
                st.session_state.holdings[selected_b] = {"shares": new_shares, "cost": new_cost}
                save_account()
                bark_push("买入成功", f"Agent 1 已买入 {b_amount} 股 {selected_b}")
                st.balloons()
                st.rerun()

# --- TAB 3: 卖出逻辑 (新增) ---
with tab_sell:
    st.subheader("Agent 4: 卖出决策审查")
    my_holdings = list(st.session_state.holdings.keys())
    
    if not my_holdings:
        st.info("当前无持仓。")
    else:
        selected_s = st.selectbox("选择卖出持仓", my_holdings)
        h_info = st.session_state.holdings[selected_s]
        curr_price = market_data[selected_s]['price']
        s_amount = st.number_input("卖出数量", min_value=1, max_value=int(h_info['shares']), value=int(h_info['shares']))
        
        profit_pct = (curr_price / h_info['cost'] - 1) * 100
        st.metric("实时盈亏", f"${curr_price - h_info['cost']:.2f}", f"{profit_pct:.2f}%")
        
        if profit_pct > 20:
            st.warning("💡 Agent 4: 涨幅已超 20%，建议分批止盈。")
        elif profit_pct < -10:
            st.error("💡 Agent 4: 跌幅触为止损线，请检查基本面。")

        if st.button("🚨 确认卖出"):
            sell_val = s_amount * curr_price
            st.session_state.cash += sell_val
            if s_amount == h_info['shares']:
                del st.session_state.holdings[selected_s]
            else:
                st.session_state.holdings[selected_s]['shares'] -= s_amount
            save_account()
            bark_push("卖出成功", f"已清算 {s_amount} 股 {selected_s}")
            st.rerun()

# --- TAB 4: 持仓分布 ---
with tab_portfolio:
    st.subheader("账户资产分布")
    total_stock_val = sum(info['shares'] * market_data.get(t, {'price':0})['price'] for t, info in st.session_state.holdings.items())
    total_assets = total_stock_val + st.session_state.cash
    
    c1, c2 = st.columns(2)
    c1.metric("总资产", f"${total_assets:,.2f}")
    c2.metric("可用现金", f"${st.session_state.cash:,.2f}")
    
    if st.session_state.holdings:
        labels = list(st.session_state.holdings.keys()) + ["现金"]
        values = [info['shares']*market_data.get(t, {'price':0})['price'] for t, info in st.session_state.holdings.items()] + [st.session_state.cash]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # 盈亏明细表
        p_list = []
        for t, info in st.session_state.holdings.items():
            cp = market_data.get(t, {'price':0})['price']
            p_list.append({
                "代码": t, "持股": info['shares'], "盈亏": f"{(cp-info['cost'])*info['shares']:+.2f}",
                "涨跌": f"{(cp/info['cost']-1)*100:+.2f}%"
            })
        st.table(pd.DataFrame(p_list))

st.markdown("---")
st.caption(f"系统最后更新: {datetime.now().strftime('%H:%M:%S')} | 🟢 存档同步正常")
