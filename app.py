import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os

st.set_page_config(page_title="交易员诊所 (Flash版)", page_icon="⚡", layout="wide")

with st.sidebar:
    st.header("⚡ 交易员诊所")
    st.caption("🚀 Powered by Gemini 1.5 Flash")
    
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ Gemini Key 已注入")
    else:
        api_key = st.text_input("请输入 Gemini Key", type="password")

st.title("🚑 币圈交易诊所")
st.markdown("支持 **币安/OKX/Bitget** (已启用 Gemini 1.5 Flash)")

# --- 核心逻辑 ---
def process_data(file):
    try:
        df = pd.read_csv(file)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        col_map = {
            'opened': 'Time', 'date(utc)': 'Time', 'time': 'Time',
            'closed': 'Time_Close',
            'closing pnl': 'PnL', 'realized pnl': 'PnL', 'pnl': 'PnL', 'profit': 'PnL',
            'symbol': 'Symbol', 'pair': 'Symbol',
            'commission': 'Fee', 'fee': 'Fee'
        }
        df = df.rename(columns=col_map)
        
        if 'PnL' not in df.columns:
            for col in df.columns:
                if 'pnl' in col or 'profit' in col or '盈亏' in col:
                    df = df.rename(columns={col: 'PnL'})
                    break
        
        if 'PnL' not in df.columns:
            st.error("❌ 找不到盈亏列。")
            return None

        df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
        
        if 'Time' in df.columns:
            df['Time'] = pd.to_datetime(df['Time'])
        elif 'Time_Close' in df.columns:
            df['Time'] = pd.to_datetime(df['Time_Close'])
            
        if 'Fee' not in df.columns:
            df['Fee'] = 0.0 
        else:
            df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').abs().fillna(0)
            
        return df
    except Exception as e:
        st.error(f"❌ 解析出错: {e}")
        return None

def get_ai_comment(stats, key):
    if not key: return "请配置 Key。"
    
    try:
        # 🌟 关键修改1：去除 Key 的首尾空格，防止复制错误
        clean_key = key.strip()
        
        genai.configure(api_key=clean_key)
        
        # 🌟 关键修改2：使用最新的 1.5 Flash 模型
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        你是一位毒舌交易员教练。分析数据：
        交易{stats['count']}笔，胜率{stats['win_rate']:.1f}%，净利{stats['net']}U，手续费{stats['fee']}U。
        请毒舌点评，200字以内。
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini 报错: {e}"

# --- 界面 ---
uploaded_file = st.file_uploader("📂 拖入 CSV 文件", type=['csv'])

if uploaded_file:
    df = process_data(uploaded_file)
    
    if df is not None:
        net = df['PnL'].sum()
        fee = df['Fee'].sum()
        count = len(df)
        wins = len(df[df['PnL'] > 0])
        win_rate = (wins / count * 100) if count > 0 else 0
        stats = {"count": count, "net": net, "fee": fee, "win_rate": win_rate}
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📊 净利润", f"${stats['net']:.2f}")
        c2.metric("💸 手续费", f"${stats['fee']:.2f}")
        c3.metric("🎯 胜率", f"{stats['win_rate']:.1f}%")
        
        st.divider()
        if st.button("开始 Gemini 诊断"):
            with st.spinner("AI 正在思考..."):
                st.info(get_ai_comment(stats, api_key))
        
        if 'Time' in df.columns:
            df = df.sort_values('Time')
            df['Cumulative PnL'] = df['PnL'].cumsum()
            try:
                fig = px.line(df, x='Time', y='Cumulative PnL', title='资金曲线')
                st.plotly_chart(fig, use_container_width=True)
            except: pass
