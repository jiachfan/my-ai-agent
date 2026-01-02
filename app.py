import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 基础配置与安全推送 ---
st.set_page_config(page_title="AI 交易助理", layout="centered")

def bark_push(title, content):
    # 安全：从 Streamlit Secrets 读取，不暴露在 GitHub
    my_key = st.secrets.get("BARK_KEY")
    if my_key:
        url = f"https://api.day.app/{my_key}/{title}/{content}"
        try: requests.get(url)
        except: pass

# --- 2. 初始化模拟账户 (Session State) ---
# 仅在第一次运行时初始化数据
if 'cash' not in st.session_state:
    st.session_state.cash = 100000.0  # 初始资金 10w 美金
if 'my_holdings' not in st.session_state:
    st.session_state.my_holdings = {} # 格式: {"AAPL": {"shares": 10, "cost": 150.0}}

# --- 3. 辅助功能：获取实时股价 ---
@st.cache_data(ttl=300)
def get_current_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        return data['Close'].iloc[-1]
    except:
        return None

# --- 4. 页面布局 ---
st.title("🤖 AI 智能交易系统")

# 定义标签页
tab_trade, tab_portfolio = st.tabs(["🚀 决策与执行", "💰 我的持仓"])

# --- Tab 1: 交易执行 ---
with tab_trade:
    st.subheader("Agent 4 模拟下单")
    
    col1, col2 = st.columns(2)
    with col1:
        target_ticker = st.text_input("股票代码", value="NVDA").upper()
    with col2:
        target_shares = st.number_input("买入股数", min_value=1, value=10)
    
    current_p = get_current_price(target_ticker)
    
    if current_p:
        total_cost = current_p * target_shares
        st.info(f"当前市价: ${current_p:.2f} | 预计总额: ${total_cost:.2f}")
        
        if st.button("确认执行买入"):
            if total_cost > st.session_state.cash:
                st.error("余额不足，下单失败！")
            else:
                # 1. 扣除现金
                st.session_state.cash -= total_cost
                
                # 2. 更新持仓 (计算摊薄成本)
                if target_ticker in st.session_state.my_holdings:
                    old_info = st.session_state.my_holdings[target_ticker]
                    new_shares = old_info['shares'] + target_shares
                    # 摊薄成本公式: (旧总额 + 新总额) / 总股数
                    new_cost = (old_info['shares'] * old_info['cost'] + total_cost) / new_shares
                    st.session_state.my_holdings[target_ticker] = {"shares": new_shares, "cost": new_cost}
                else:
                    st.session_state.my_holdings[target_ticker] = {"shares": target_shares, "cost": current_p}
                
                # 3. 推送通知到 iPhone
                bark_push("交易执行成功", f"已买入 {target_shares} 股 {target_ticker}，成交价 ${current_p:.2f}")
                st.success(f"买入成功！已自动更新持仓。")

# --- Tab 2: 持仓分布与涨跌 ---
with tab_portfolio:
    st.subheader("账户概览")
    
    if not st.session_state.my_holdings:
        st.write("当前暂无持仓，快去下单吧！")
        st.metric("剩余现金", f"${st.session_state.cash:,.2f}")
    else:
        portfolio_list = []
        total_stock_value = 0
        
        for t, info in st.session_state.my_holdings.items():
            curr_p = get_current_price(t)
            value = curr_p * info['shares']
            profit = (curr_p - info['cost']) * info['shares']
            profit_pct = (curr_p / info['cost'] - 1) * 100
            total_stock_value += value
            
            portfolio_list.append({
                "代码": t,
                "股数": info['shares'],
                "现价": f"${curr_p:.2f}",
                "成本": f"${info['cost']:.2f}",
                "盈亏": f"${profit:+.2f}",
                "涨跌幅": f"{profit_pct:+.2f}%",
                "价值": value
            })
        
        # 饼图展示
        labels = [d['代码'] for d in portfolio_list] + ["现金"]
        values = [d['价值'] for d in portfolio_list] + [st.session_state.cash]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(height=350, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        # 盈亏细节表格
        df_p = pd.DataFrame(portfolio_list).drop(columns=['价值'])
        st.table(df_p)
        
        # 总资产 Metrics
        total_assets = total_stock_value + st.session_state.cash
        st.metric("总资产", f"${total_assets:,.2f}", f"现金: ${st.session_state.cash:,.2f}")
