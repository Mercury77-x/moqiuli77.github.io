import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="交易员诊所 (Zeabur版)", page_icon="⚡", layout="wide")

# --- 2. 侧边栏 ---
with st.sidebar:
    st.header("⚡ 币圈韭菜急诊室 (AI版)")
    # 尝试自动获取 Key
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ API Key 已自动注入")
    else:
        api_key = st.text_input("请输入 OpenAI Key", type="password")

st.title("🚑 币圈交易诊所")
st.markdown("支持 **币安/OKX/Bitget** 导出的 CSV 文件 (支持中文表头)")

# --- 3. 核心逻辑 (万能清洗版) ---
def load_data(file):
    try:
        df = pd.read_csv(file)
        # 去除列名空格，防止 ' 时间 ' 这种情况
        df.columns = [c.strip() for c in df.columns]
        
        # 🌟 关键修改：超级映射表 (中英文通吃) 🌟
        col_map = {
            # 时间
            'Date(UTC)': 'Time', 'Time': 'Time', 'Date': 'Time', 'Opened': 'Time',
            '时间': 'Time', '日期': 'Time', '成交时间': 'Time',
            
            # 交易对
            'Pair': 'Symbol', 'Symbol': 'Symbol', 
            '交易对': 'Symbol', '币种': 'Symbol', '合约': 'Symbol',
            
            # 盈亏 (核心!)
            'Realized Profit': 'PnL', 'Realized PnL': 'PnL', 'Profit': 'PnL', 'Closing PNL': 'PnL',
            '已实现盈亏': 'PnL', '盈亏': 'PnL', '收益': 'PnL', '平仓盈亏': 'PnL',
            
            # 手续费
            'Fee': 'Fee', 'Commission': 'Fee', 'Est_Fee': 'Fee',
            '手续费': 'Fee', '佣金': 'Fee'
        }
        df = df.rename(columns=col_map)
        
        # 调试信息：如果还没找到，打印下列名给用户看
        if 'PnL' not in df.columns:
            st.error("❌ 找不到【盈亏】列！")
            st.write("你的 CSV 列名是：", list(df.columns))
            st.info("请确保你的 CSV 里包含：'已实现盈亏' 或 'Realized PnL' 或 'Closing PNL'")
            return None
            
        return df
    except Exception as e:
        st.error(f"❌ 文件读取失败: {e}")
        return None

def get_ai_comment(stats, key):
    if not key: return "请配置 Key 才能看 AI 骂人。"
    client = OpenAI(api_key=key)
    prompt = f"""
    分析交易数据：交易{stats['count']}笔，胜率{stats['win_rate']:.1f}%，净利{stats['net']}U，手续费{stats['fee']}U。
    请用毒舌风格点评，并给个侮辱性标签。
    """
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except Exception as e:
        return f"AI 报错: {e}"

# --- 4. 界面交互 ---
uploaded_file = st.file_uploader("📂 拖入 CSV 文件", type=['csv'])

if uploaded_file:
    df = load_data(uploaded_file)
    
    if df is not None:
        # 数据类型清洗 (去掉 'USDT' 单位，转为数字)
        try:
            # 盈亏转数字
            df['PnL'] = df['PnL'].astype(str).str.replace(' USDT', '').str.replace(',', '')
            df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
            
            # 手续费转数字
            if 'Fee' not in df.columns:
                df['Fee'] = 0
            else:
                df['Fee'] = df['Fee'].astype(str).str.replace(' USDT', '').str.replace(',', '')
                df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').abs().fillna(0)
                
            # 时间处理
            if 'Time' in df.columns:
                df['Time'] = pd.to_datetime(df['Time'])

            # 计算统计
            net = df['PnL'].sum() - df['Fee'].sum()
            wins = len(df[df['PnL'] > 0])
            count = len(df)
            win_rate = (wins / count * 100) if count > 0 else 0
            
            stats = {"count": count, "net": net, "fee": df['Fee'].sum(), "win_rate": win_rate}
            
            # 展示
            c1, c2, c3 = st.columns(3)
            c1.metric("净利润", f"${stats['net']:.2f}")
            c2.metric("手续费", f"${stats['fee']:.2f}")
            c3.metric("胜率", f"{stats['win_rate']:.1f}%")
            
            st.divider()
            
            if st.button("开始 AI 诊断"):
                with st.spinner("AI 正在思考..."):
                    st.info(get_ai_comment(stats, api_key))
                    
        except Exception as e:
            st.error(f"数据计算出错: {e}")
