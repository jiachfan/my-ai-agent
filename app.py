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

# --- [2. Agent 数据抓取与技术分析] ---
@st.cache_data(ttl=600)
def get_market_intelligence():
    tickers = ["MSFT", "AAPL", "NVDA", "TSLA", "LLY", "UNH", "NEE", "COST", "AMD", "GOOGL"]
    intelligence = {}
    for t in tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period="14d") # 获取14天数据用于简单RSI计算
            info = s.info
            # 简单 RSI 模拟逻辑
            delta = h['Close'].diff()
            gain = (delta.where(delta > 0, 0)).mean()
            loss = (-delta.where(delta < 0, 0)).mean()
            rs = gain / (loss + 0.00001)
            rsi = 100 - (100 / (1+rs))
            
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

# --- [3. UI 布局] ---
st.title("🤖 2026 AI 专家协作系统")
market_data = get_market_intelligence()

tab_scan, tab_trade, tab_portfolio = st.tabs(["🌟 猎手发现", "🛡️ 风险决策", "💰 账户持仓"])

# --- TAB 1: Agent 7 发现潜力 ---
with tab_scan:
    st.subheader("Agent 7: 潜力股扫描")
    potentials = [t for t, v in market_data.items() if 0 < v['pe'] < 40 and v['growth'] > 0.1]
    for t in potentials:
        v = market_data[t]
        st.markdown(f"""
        <div style="background:#161b22; padding:12px; border-radius:10px; border-left:5px solid #ffd700; margin-bottom:10px;">
            <b>{t}</b> | {v['name']} | PE: {v['pe']:.1f}<br>
            <small>RSI: {v['rsi']:.1f} | 增长率: {v['growth']*100:.1f}%</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"📥 提交 {t} 给风险官审查", key=f"scan_{t}"):
            st.session_state.pending_ticker = t
            st.success(f"{t} 已进入决策队列")

# --- TAB 2: Agent 4 风险评估建议 (核心增强) ---
with tab_trade:
    st.subheader("Agent 4: 风险官准入评估")
    
    selected_t = st.selectbox("当前审查标的", list(market_data.keys()), 
                              index=list(market_data.keys()).index(st.session_state.get('pending_ticker', "NVDA")))
    
    amount = st.number_input("拟买入股数", min_value=1, value=10)
    v = market_data[selected_t]
    total_cost = v['price'] * amount
    
    # --- Agent 4 评估逻辑引擎 ---
    total_assets = st.session_state.cash + sum(info['shares'] * market_data.get(t, {'price':0})['price'] for t, info in st.session_state.holdings.items())
    new_ratio = (total_cost / (total_assets + 0.1)) * 100
    
    st.markdown("### 📋 风险评估报告")
    
    # 评分逻辑
    risk_score = 0
    reasons = []
    
    # 1. 集中度评估
    if new_ratio > 20:
        risk_score += 40
        reasons.append("⚠️ **仓位过重**：该笔交易占总资产比重过大，建议降至10%以下。")
    # 2. 技术面评估 (RSI)
    if v['rsi'] > 70:
        risk_score += 30
        reasons.append("🚫 **严重超买**：RSI 指标显示当前股价过热，存在回调风险，建议等待。")
    elif v['rsi'] < 30:
        reasons.append("✅ **低位机会**：RSI 显示超卖，技术面具备反弹动力。")
    # 3. 估值评估
    if v['pe'] > 50:
        risk_score += 20
        reasons.append("📉 **估值过高**：当前市盈率远超保守区间。")

    # 显示评估建议
    if risk_score >= 60:
        st.error(f"**评估结论：不建议交易 (风险分: {risk_score})**")
    elif risk_score >= 30:
        st.warning(f"**评估结论：谨慎观察 (风险分: {risk_score})**")
    else:
        st.success(f"**评估结论：安全，准许交易 (风险分: {risk_score})**")
    
    for r in reasons:
        st.write(r)

    st.markdown("---")
    if st.button("🚀 Agent 1 确认执行 (忽略风险请慎重)"):
        if total_cost > st.session_state.cash:
            st.error("执行失败：可用现金不足。")
        else:
            st.session_state.cash -= total_cost
            if selected_t in st.session_state.holdings:
                h = st.session_state.holdings[selected_t]
                st.session_state.holdings[selected_t] = {
                    "shares": h['shares'] + amount,
                    "cost": (h['shares']*h['cost'] + total_cost)/(h['shares']+amount)
                }
            else:
                st.session_state.holdings[selected_t] = {"shares": amount, "cost": v['price']}
            save_account()
            bark_push("交易成功", f"Agent 4 准许，Agent 1 已买入 {amount} 股 {selected_t}")
            st.balloons()
            st.success("交易记录已保存。")

# --- TAB 3: 持仓分布 ---
with tab_portfolio:
    st.subheader("我的资金分布")
    if not st.session_state.holdings:
        st.info("目前为空仓状态。")
        st.metric("剩余现金", f"${st.session_state.cash:,.2f}")
    else:
        # 饼图
        labels = list(st.session_state.holdings.keys()) + ["现金"]
        values = [info['shares']*market_data.get(t, {'price':0})['price'] for t, info in st.session_state.holdings.items()] + [st.session_state.cash]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # 盈亏表
        p_data = []
        for t, info in st.session_state.holdings.items():
            curr_p = market_data.get(t, {'price':0})['price']
            p_data.append({
                "代码": t, "持股": info['shares'], "现价": f"${curr_p:.2f}",
                "盈亏": f"{(curr_p - info['cost'])*info['shares']:+.2f}",
                "涨跌幅": f"{(curr_p/info['cost']-1)*100:+.2f}%"
            })
        st.table(pd.DataFrame(p_data))
        if st.button("🔄 手动同步云端数据"):
            save_account()
            st.toast("存档同步成功")

st.markdown("---")
st.caption(f"系统时间: {datetime.now().strftime('%H:%M:%S')} | 🟢 Agent 4 已介入监控")
