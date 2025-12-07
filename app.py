import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import os

# 1. 页面配置
st.set_page_config(page_title="交易员诊所 (Zeabur版)", page_icon="⚡", layout="wide")

# 2. 获取 API Key (优先从环境变量获取)
api_key = os.environ.get("OPENAI_API_KEY")

with st.sidebar:
    st.header("⚡ Zeabur 高速版")
    if api_key:
        st.success("✅ API Key 已自动注入")
    else:
        api_key = st.text_input("请输入 OpenAI Key", type="password")
        if not api_key:
            st.warning("⚠️ 未检测到 Key")

st.title("🚑 币圈交易诊所")
st.markdown("专治各种**频繁交易**、**手续费过高**疑难杂症。")

# 3. 核心逻辑
def load_data(file):
    try:
        df = pd.read_csv(file)
        df.columns = [c.strip() for c in df.columns]
        col_map = {
            'Date(UTC)': 'Time', 'Time': 'Time', '时间': 'Time',
            'Pair': 'Symbol', 'Symbol': 'Symbol', '交易对': 'Symbol',
            'Realized Profit': 'PnL', 'Realized PnL': 'PnL', '已实现盈亏': 'PnL',
            'Fee': 'Fee', 'Commission': 'Fee', '手续费': 'Fee'
        }
        df = df.rename(columns=col_map)
        return df
    except:
        return None

def get_ai_comment(stats, key):
    if not key: return "请配置 Key。"
    client = OpenAI(api_key=key)
    prompt = f"交易{stats['count']}笔，净利{stats['net']}U，手续费{stats['fee']}U。请毒舌点评。"
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except Exception as e:
        return f"AI 报错: {e}"

# 4. 界面交互
uploaded_file = st.file_uploader("📂 上传币安合约 CSV", type=['csv'])

if uploaded_file:
    df = load_data(uploaded_file)
    if df is not None and 'PnL' in df.columns:
        # 数据转换
        df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
        if 'Fee' not in df.columns: df['Fee'] = 0
        df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').abs()

        stats = {
            "count": len(df),
            "net": df['PnL'].sum() - df['Fee'].sum(),
            "fee": df['Fee'].sum()
        }

        c1, c2, c3 = st.columns(3)
        c1.metric("净利润", f"${stats['net']:.2f}")
        c2.metric("手续费", f"${stats['fee']:.2f}")
        c3.metric("交易次数", stats['count'])

        st.divider()

        if st.button("AI 诊断"):
            with st.spinner("AI 正在思考..."):
                st.info(get_ai_comment(stats, api_key))
    else:
        st.error("数据格式无法识别，请检查列名。")
