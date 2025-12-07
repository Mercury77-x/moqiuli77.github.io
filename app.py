import streamlit as st
import pandas as pd
import plotly.express as px  # <--- 补上了这行关键代码
from openai import OpenAI
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="交易员诊所 (修复版)", page_icon="🚑", layout="wide")

# --- 2. 侧边栏 ---
with st.sidebar:
    st.header("⚡ 交易员诊所")
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ API Key 已注入")
    else:
        api_key = st.text_input("OpenAI Key", type="password")

st.title("🚑 币圈交易诊所")
st.markdown("已完美适配：**Closing PNL**、**无手续费列** 的情况。")

# --- 3. 核心逻辑 ---

def process_data(file):
    try:
        # 读取文件
        df = pd.read_csv(file)
        
        # 1. 统一列名：转成字符串，去除空格，全部转为【小写】
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 2. 建立你的文件 -> 标准列名的映射
        col_map = {
            'opened': 'Time',         # 开仓时间
            'closed': 'Time_Close',   # 平仓时间
            'closing pnl': 'PnL',     # 核心修复: Closing PNL -> PnL
            'symbol': 'Symbol',
            'commission': 'Fee',      
            'fee': 'Fee'
        }
        
        df = df.rename(columns=col_map)
        
        # 3. 检查关键列
        if 'PnL' not in df.columns:
            # 最后的模糊搜索
            found_pnl = False
            for col in df.columns:
                if 'pnl' in col or 'profit' in col or '盈亏' in col:
                    df = df.rename(columns={col: 'PnL'})
                    found_pnl = True
                    break
            
            if not found_pnl:
                st.error("❌ 找不到盈亏列。")
                st.write("系统看到的列名:", list(df.columns))
                return None

        # 4. 数据清洗
        df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
        
        # 时间处理
        if 'Time' in df.columns:
            df['Time'] = pd.to_datetime(df['Time'])
        elif 'Time_Close' in df.columns:
            df['Time'] = pd.to_datetime(df['Time_Close'])
            
        # 手续费处理
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
    client = OpenAI(api_key=key)
    prompt = f"""
    分析数据：交易{stats['count']}笔，胜率{stats['win_rate']:.1f}%，净利{stats['net']}U。
    注意：该用户数据中没有包含手续费。
    请用毒舌风格点评。
    """
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except Exception as e:
        return f"AI 报错: {e}"

# --- 4. 界面 ---
uploaded_file = st.file_uploader("📂 拖入 CSV 文件", type=['csv'])

if uploaded_file:
    df = process_data(uploaded_file)
    
    if df is not None:
        # 统计
        net = df['PnL'].sum()
        fee = df['Fee'].sum()
        count = len(df)
        wins = len(df[df['PnL'] > 0])
        win_rate = (wins / count * 100) if count > 0 else 0
        
        stats = {"count": count, "net": net, "fee": fee, "win_rate": win_rate}
        
        # 展示 KPI
        c1, c2, c3 = st.columns(3)
        c1.metric("📊 净利润", f"${stats['net']:.2f}")
        c2.metric("💸 手续费", f"${stats['fee']:.2f}")
        c3.metric("🎯 胜率", f"{stats['win_rate']:.1f}%")
        
        st.divider()
        
        if st.button("开始 AI 诊断"):
            with st.spinner("AI 正在思考..."):
                st.info(get_ai_comment(stats, api_key))
        
        # 画图 (这就是报错的地方，现在修好了)
        if 'Time' in df.columns:
            df = df.sort_values('Time')
            df['Cumulative PnL'] = df['PnL'].cumsum()
            try:
                fig = px.line(df, x='Time', y='Cumulative PnL', title='资金曲线')
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"画图出错: {e}")
