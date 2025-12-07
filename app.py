import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import os

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="币圈交易诊所",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 侧边栏：API Key 配置 ---
with st.sidebar:
    st.header("🔑 启动钥匙")
    try:
        env_key = st.secrets["OPENAI_API_KEY"]
        api_key = env_key
        st.success("✅ 云端 API Key 已激活")
    except:
        api_key = st.text_input("请输入 OpenAI API Key", type="password")
        if not api_key:
            st.warning("⚠️ 请输入 Key 以解锁 AI 毒舌点评")
    
    st.markdown("---")
    st.markdown("### 🛠 支持格式")
    st.markdown("- **币安/OKX/Bitget** 合约交割单")
    st.markdown("- 支持 **中文** 或 **英文** 表头")

# --- 3. 核心功能函数 ---

def load_and_clean_data(file):
    """清洗数据的逻辑，中英文自动兼容"""
    try:
        # 尝试读取
        df = pd.read_csv(file)
        
        # 去除列名空格 (防止 ' Time ' 这种情况)
        df.columns = [c.strip() for c in df.columns]
        
        # 🌟 关键修改：超级映射表 (中英文通吃) 🌟
        col_map = {
            # 时间列
            'Date(UTC)': 'Time', 'Time': 'Time', 'Date': 'Time', 
            '时间': 'Time', '日期': 'Time', '创建时间': 'Time',
            
            # 交易对
            'Pair': 'Symbol', 'Symbol': 'Symbol', 
            '交易对': 'Symbol', '币种': 'Symbol', '合约': 'Symbol',
            
            # 盈亏列 (这是报错的根源)
            'Realized Profit': 'PnL', 'Realized PnL': 'PnL', 'Profit': 'PnL', 
            '已实现盈亏': 'PnL', '盈亏': 'PnL', '收益': 'PnL', '平仓盈亏': 'PnL',
            
            # 手续费列
            'Fee': 'Fee', 'Commission': 'Fee', 
            '手续费': 'Fee', '佣金': 'Fee'
        }
        
        # 执行重命名
        df = df.rename(columns=col_map)
        
        # 再次检查关键列
        required = ['Time', 'PnL']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            # 如果还是报错，把用户原本的列名打印出来，方便调试
            st.error(f"❌ 格式不匹配！")
            st.write("你的 CSV 列名是：", list(df.columns))
            st.write(f"代码没找到这些列：{missing}")
            st.info("💡 建议：打开 CSV 看看，把‘时间’和‘盈亏’这两列的标题改名为 Time 和 PnL 再上传。")
            return None
            
        # 数据类型转换 (处理可能的逗号，比如 "1,000.00")
        df['Time'] = pd.to_datetime(df['Time'])
        
        # 强制把 PnL 转为数字 (去掉 'USDT' 等单位)
        df['PnL'] = df['PnL'].astype(str).str.replace(' USDT', '').str.replace(',', '')
        df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
        
        # 手续费处理
        if 'Fee' not in df.columns:
            df['Fee'] = 0
        else:
            df['Fee'] = df['Fee'].astype(str).str.replace(' USDT', '').str.replace(',', '')
            df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').abs().fillna(0)
            
        return df
    except Exception as e:
        st.error(f"❌ 文件解析崩溃: {str(e)}")
        return None

def get_ai_diagnosis(stats, key):
    if not key: return "请先配置 API Key。"
    client = OpenAI(api_key=key)
    
    prompt = f"""
    你是一位毒舌交易员教练。根据数据写一份简短诊断：
    交易 {stats['count']} 笔，胜率 {stats['win_rate']:.1f}%，盈亏比 {stats['pl_ratio']:.2f}，
    手续费 ${stats['total_fee']:.0f}，净利 ${stats['net_pnl']:.0f}。
    
    要求：
    1. 给个侮辱性标签。
    2. 狠狠吐槽操作。
    3. 给建议。
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 报错: {e}"

# --- 4. 界面主体 ---

st.title("🚑 币圈交易诊所 (中文特供版)")

uploaded_file = st.file_uploader("📂 拖入 CSV 文件 (支持中文表头)", type=['csv'])

if uploaded_file:
    df = load_and_clean_data(uploaded_file)
    
    if df is not None:
        total_trades = len(df)
        total_fee = df['Fee'].sum()
        net_pnl = df['PnL'].sum() - total_fee
        wins = df[df['PnL'] > 0]
        losses = df[df['PnL'] <= 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        avg_win = wins['PnL'].mean() if not wins.empty else 0
        avg_loss = abs(losses['PnL'].mean()) if not losses.empty else 0
        pl_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0
        
        stats = {"count": total_trades, "win_rate": win_rate, "pl_ratio": pl_ratio, "total_fee": total_fee, "net_pnl": net_pnl}

        # 展示
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("净利润", f"${net_pnl:.0f}")
        c2.metric("手续费", f"${total_fee:.0f}")
        c3.metric("胜率", f"{win_rate:.1f}%")
        c4.metric("盈亏比", f"{pl_ratio:.2f}")

        st.divider()
        
        if st.button("开始 AI 诊断"):
            with st.spinner("AI 正在看你的交割单..."):
                st.info(get_ai_diagnosis(stats, api_key))
        
        st.line_chart(df.set_index('Time')['PnL'].cumsum())
