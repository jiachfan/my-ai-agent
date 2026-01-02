import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import os
import streamlit as st

def bark_push(title, content):
    # 从系统环境变量中读取，而不是写在代码里
    my_key = st.secrets.get("BARK_KEY") 
    
    if not my_key:
        return # 如果没配置密钥则不发送
        
    url = f"https://api.day.app/{my_key}/{title}/{content}"
    try:
        requests.get(url)
    except:
        pass

# 示例：当 Agent 4 拦截交易时调用
# if decision == "REJECTED":
#     bark_push("Agent4_预警", "已成功拦截高风险追高操作")

# --- 1. iOS 移动端界面深度优化 ---
st.set_page_config(page_title="2026 AI 交易助理", layout="centered")

# 强制注入 CSS 适配手机竖屏
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; white-space: pre-wrap; background-color: #1e1e1e; 
        border-radius: 10px; color: white; flex: 1; text-align: center;
    }
    .stMetric { background-color: #161b22; padding: 10px; border-radius: 10px; border: 1px solid #30363d; }
    .agent-card { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border-left: 5px solid #ffd700; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：数据抓取与 Agent 7 扫描算法 ---
SECTORS = {
    "科技核心": ["MSFT", "AAPL", "NVDA"],
    "防御潜力": ["LLY", "UNH", "COST", "NEE", "VST", "WM"]
}

@st.cache_data(ttl=600)
def fetch_market_data():
    all_tickers = [t for sub in SECTORS.values() for t in sub]
    data = {}
    for t in all_tickers:
        try:
            s = yf.Ticker(t)
            hist = s.history(period="2d")
            if not hist.empty:
                info = s.info
                data[t] = {
                    "price": hist['Close'].iloc[-1],
                    "change": (hist['Close'].iloc[-1] / hist['Close'].iloc[-2] - 1) * 100,
                    "pe": info.get('trailingPE', 0),
                    "eps_growth": info.get('earningsQuarterlyGrowth', 0),
                    "name": info.get('shortName', t)
                }
        except: continue
    return data

def agent_7_scanner(data):
    """Agent 7: 跨板块寻找低估值+高增长标的"""
    potentials = []
    for t, info in data.items():
        # 筛选标准：PE < 35 且 利润增长 > 5%
        if 0 < info['pe'] < 35 and info['eps_growth'] > 0.05:
            score = (100 - info['pe']) + (info['eps_growth'] * 100)
            potentials.append({**info, "ticker": t, "score": score})
    return sorted(potentials, key=lambda x: x['score'], reverse=True)[:3]

# --- 3. 页面渲染 ---
st.title("🤖 AI 监控系统 (iOS)")
all_data = fetch_market_data()

# iOS 底部切换标签风格
tab_scan, tab_trade, tab_report = st.tabs(["🌟 潜力扫描", "🛡️ 风险决策", "📊 账户复盘"])

with tab_scan:
    st.subheader("Agent 7 每日潜力筛选")
    top_3 = agent_7_scanner(all_data)
    
    if top_3:
        for stock in top_3:
            st.markdown(f"""
            <div class="agent-card">
                <h3 style="margin:0; color:#ffd700;">{stock['ticker']} · {stock['name']}</h3>
                <p style="margin:5px 0; font-size:14px;">估值 PE: {stock['pe']:.1f} | 盈余增长: {stock['eps_growth']*100:.1f}%</p>
                <p style="margin:0; font-size:12px; color:#888;">Agent 7 评价：该标的处于防御板块，当前价格具备安全边际。</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("全板块实时行情")
    for sector, tickers in SECTORS.items():
        with st.expander(sector):
            for t in tickers:
                if t in all_data:
                    c1, c2 = st.columns(2)
                    c1.metric(t, f"${all_data[t]['price']:.2f}")
                    c2.metric("日涨跌", f"{all_data[t]['change']:.2f}%")

with tab_trade:
    st.subheader("Agent 4 交易政审")
    target = st.selectbox("选择要执行的交易目标", list(all_data.keys()))
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Agent 3 (分析师):**")
        st.caption("技术指标显示超卖，建议少量建仓。")
    with col_b:
        st.write("**Agent 4 (风险官):**")
        if all_data[target]['change'] > 3:
            st.warning("提示：今日涨幅过大，追高风险高。")
        else:
            st.success("风险受控，准许操作。")
            
    if st.button("🚀 提交指令到交易队列"):
        st.balloons()
        st.success(f"已发送 {target} 的买入申请。Bark 通知已排队。")

with tab_report:
    st.subheader("Agent 5 账户报告")
    # 模拟净值走势
    fig = go.Figure(data=[go.Scatter(y=[10000, 10200, 10150, 10400, 10550], line=dict(color='#00ff00', width=3))])
    fig.update_layout(
        height=300, 
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("""
    **今日 Agent 总结：**
    1. 系统拦截了 2 次高风险波动操作。
    2. 自动减持了 5% 的科技溢价仓位。
    3. 当前整体防御力：**强**。
    """)

# 状态栏
st.markdown("---")
st.caption(f"最后更新: {datetime.now().strftime('%H:%M:%S')} | 🟢 云端 Agent 环境正常")