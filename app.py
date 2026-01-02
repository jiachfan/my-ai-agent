import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# --- [配置层] iOS 移动端界面优化 ---
st.set_page_config(page_title="2026 AI 交易助手", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        height: 45px; background-color: #1e1e1e; border-radius: 8px; color: #888; flex: 1;
    }
    .stTabs [aria-selected="true"] { color: #ffd700 !important; border-bottom: 2px solid #ffd700 !important; }
    .agent-box { background: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- [安全层] Bark 推送函数 ---
def bark_push(title, content):
    # 安全：从 Streamlit Secrets 读取
    my_key = st.secrets.get("BARK_KEY")
    if my_key:
        url = f"https://api.day.app/{my_key}/{title}/{content}"
        try: requests.get(url)
        except: pass

# --- [数据层] 模拟账户初始化 ---
if 'cash' not in st.session_state:
    st.session_state.cash = 100000.0  # 初始 10w 美金
if 'holdings' not in st.session_state:
    st.session_state.holdings = {} # {"TICKER": {"shares": 0, "cost": 0.0}}

# --- [Agent 核心逻辑库] ---
SECTORS = {
    "科技": ["MSFT", "AAPL", "NVDA", "TSLA"],
    "医疗": ["LLY", "UNH"],
    "能源": ["NEE", "VST"],
    "防御": ["COST", "PG"]
}

@st.cache_data(ttl=300)
def fetch_all_data():
    all_tickers = [t for sub in SECTORS.values() for t in sub]
    data = {}
    for t in all_tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="2d")
            info = stock.info
            data[t] = {
                "price": hist['Close'].iloc[-1],
                "change": (hist['Close'].iloc[-1] / hist['Close'].iloc[-2] - 1) * 100,
                "pe": info.get('trailingPE', 0),
                "eps_growth": info.get('earningsQuarterlyGrowth', 0),
                "name": info.get('shortName', t)
            }
        except: continue
    return data

# --- [页面渲染] ---
st.title("🤖 2026 AI 多 Agent 交易系统")
all_market_data = fetch_all_data()

# iOS 底部切换标签
tab_scan, tab_trade, tab_portfolio = st.tabs(["🌟 机会扫描", "🛡️ 风险审查", "💰 我的持仓"])

# --- TAB 1: Agent 7 机会扫描 (全球猎手) ---
with tab_scan:
    st.subheader("Agent 7: 每日潜力筛选")
    # 筛选逻辑：低 PE + 高增长
    potentials = []
    for t, info in all_market_data.items():
        if 0 < info['pe'] < 35 and info['eps_growth'] > 0.05:
            potentials.append({**info, "ticker": t})
    
    if potentials:
        for stock in potentials[:3]:
            st.markdown(f"""
            <div class="agent-box">
                <b style="color:#ffd700;">{stock['ticker']}</b> | {stock['name']}<br>
                <small>PE: {stock['pe']:.1f} | 盈余增长: {stock['eps_growth']*100:.1f}%</small><br>
                <p style="font-size:12px; margin-top:5px; color:#888;">Agent 7: 估值具备安全边际，建议关注。</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("Agent 6: 全板块监控")
    for sector, tickers in SECTORS.items():
        with st.expander(sector):
            for t in tickers:
                if t in all_market_data:
                    c1, c2 = st.columns(2)
                    c1.metric(t, f"${all_market_data[t]['price']:.2f}")
                    c2.metric("日涨跌", f"{all_market_data[t]['change']:.2f}%")

# --- TAB 2: Agent 3 & 4 风险决策 ---
with tab_trade:
    st.subheader("Agent 1-4 协作决策")
    target = st.selectbox("选择操作目标", list(all_market_data.keys()))
    shares = st.number_input("拟买入股数", min_value=1, value=10)
    
    price = all_market_data[target]['price']
    total_val = price * shares
    
    st.markdown(f"""
    <div class="agent-box">
        <b>Agent 3 (短线):</b> 根据指标建议介入。<br>
        <b>Agent 4 (风险官):</b> 当前该股在账户占比拟为 {(total_val/(st.session_state.cash+1)):.1f}%。<br>
        <b>状态:</b> {'✅ 准许交易' if all_market_data[target]['change'] < 4 else '⚠️ 建议分批(涨幅过大)'}
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 执行 Agent 1 模拟买入"):
        if total_val > st.session_state.cash:
            st.error("Agent 4 拒绝：现金余额不足。")
        else:
            # 执行下单逻辑
            st.session_state.cash -= total_val
            if target in st.session_state.holdings:
                old = st.session_state.holdings[target]
                new_shares = old['shares'] + shares
                new_cost = (old['shares']*old['cost'] + total_val) / new_shares
                st.session_state.holdings[target] = {"shares": new_shares, "cost": new_cost}
            else:
                st.session_state.holdings[target] = {"shares": shares, "cost": price}
            
            bark_push("交易成功", f"Agent 1 已买入 {shares} 股 {target}")
            st.balloons()
            st.success("买入成功，请在持仓页查看。")

# --- TAB 3: Agent 5 账户监控 (持仓分布) ---
with tab_portfolio:
    st.subheader("我的资金分布")
    
    if not st.session_state.holdings:
        st.info("Agent 5: 账户目前为空仓状态。")
        st.metric("剩余现金", f"${st.session_state.cash:,.2f}")
    else:
        portfolio_details = []
        stock_val = 0
        for t, info in st.session_state.holdings.items():
            curr_p = all_market_data[t]['price']
            val = curr_p * info['shares']
            stock_val += val
            profit_pct = (curr_p / info['cost'] - 1) * 100
            portfolio_details.append({
                "代码": t, "成本": f"${info['cost']:.2f}", 
                "涨跌": f"{profit_pct:+.2f}%", "价值": val
            })
        
        # 饼图
        fig = go.Figure(data=[go.Pie(labels=[d['代码'] for d in portfolio_details]+["现金"], 
                                   values=[d['价值'] for d in portfolio_details]+[st.session_state.cash], hole=.4)])
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        # 详细表格
        st.table(pd.DataFrame(portfolio_details).drop(columns=['价值']))
        
        total_assets = stock_val + st.session_state.cash
        st.metric("账户总资产", f"${total_assets:,.2f}", f"现金占比: {(st.session_state.cash/total_assets)*100:.1f}%")

st.markdown("---")
st.caption(f"最后刷新: {datetime.now().strftime('%H:%M:%S')} | 🟢 2026 模拟实战环境")
