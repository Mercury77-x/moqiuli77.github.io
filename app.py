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
    # 优先尝试从云端环境变量获取 Key
    try:
        env_key = st.secrets["OPENAI_API_KEY"]
        api_key = env_key
        st.success("✅ 云端 API Key 已激活")
    except:
        # 如果没配置，允许手动输入
        api_key = st.text_input("请输入 OpenAI API Key", type="password")
        if not api_key:
            st.warning("⚠️ 请输入 Key 以解锁 AI 毒舌点评")
    
    st.markdown("---")
    st.markdown("### 🛠 支持格式")
    st.markdown("- 币安 (Binance) USDT 合约交割单 CSV")
    st.markdown("- 必须包含：时间、交易对、已实现盈亏、手续费")

# --- 3. 核心功能函数 ---

def load_and_clean_data(file):
    """清洗数据的逻辑，兼容性处理"""
    try:
        df = pd.read_csv(file)
        # 去除列名空格
        df.columns = [c.strip() for c in df.columns]
        
        # 智能列名映射 (兼容币安不同版本的导出)
        # 你的 CSV 列名可能是 'Realized Profit' 也可能是 'Realized PnL'
        col_map = {
            'Date(UTC)': 'Time', 'Time': 'Time', 'Date': 'Time',
            'Pair': 'Symbol', 'Symbol': 'Symbol',
            'Realized Profit': 'PnL', 'Realized PnL': 'PnL', 'Profit': 'PnL',
            'Fee': 'Fee', 'Commission': 'Fee'
        }
        df = df.rename(columns=col_map)
        
        # 检查关键列是否存在
        required = ['Time', 'PnL']
        if not all(c in df.columns for c in required):
            st.error(f"❌ 数据格式错误！未找到关键列。请检查 CSV 是否包含: {required}")
            return None
            
        # 数据类型转换
        df['Time'] = pd.to_datetime(df['Time'])
        df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
        
        # 手续费处理 (如果没有 Fee 列，默认为 0)
        if 'Fee' not in df.columns:
            df['Fee'] = 0
        else:
            df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').abs().fillna(0)
            
        return df
    except Exception as e:
        st.error(f"❌ 文件解析崩溃: {str(e)}")
        return None

def get_ai_diagnosis(stats, key):
    """调用 AI 进行分析"""
    if not key:
        return "请先配置 API Key 才能看 AI 骂人。"
    
    client = OpenAI(api_key=key)
    
    prompt = f"""
    你是一位华尔街顶级的交易员教练，性格毒舌、犀利、幽默（类似《大空头》风格）。
    请根据以下数据给这位交易员写一份“年度确诊报告”：

    【病历数据】
    - 交易频率: {stats['count']} 笔
    - 胜率: {stats['win_rate']:.2f}%
    - 盈亏比: {stats['pl_ratio']:.2f}
    - 贡献手续费: ${stats['total_fee']:.2f}
    - 最终净利润: ${stats['net_pnl']:.2f}

    【要求】
    1. 给一个侮辱性极强但又好笑的“标签”（如：慈善赌王、交易所打工仔）。
    2. 第一段：狠狠吐槽他的操作习惯（特别是如果手续费高，或者胜率低）。
    3. 第二段：给出 2 个能救命的建议。
    4. 字数控制在 200 字以内，排版精美。
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 大脑短路了: {e}"

# --- 4. 界面主体 ---

st.title("🚑 币圈交易诊所 (AI 版)")
st.markdown("### 把你的 **币安合约交割单 (CSV)** 扔进来，看看你是巴菲特还是韭菜。")

uploaded_file = st.file_uploader("📂 拖入 CSV 文件", type=['csv'])

# --- 5. 数据处理与展示逻辑 ---

if uploaded_file:
    df = load_and_clean_data(uploaded_file)
    
    if df is not None:
        # 计算核心指标
        total_trades = len(df)
        total_fee = df['Fee'].sum()
        gross_pnl = df['PnL'].sum()
        net_pnl = gross_pnl - total_fee
        
        wins = df[df['PnL'] > 0]
        losses = df[df['PnL'] <= 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = wins['PnL'].mean() if not wins.empty else 0
        avg_loss = abs(losses['PnL'].mean()) if not losses.empty else 0
        pl_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0
        
        # 数据打包
        stats = {
            "count": total_trades,
            "win_rate": win_rate,
            "pl_ratio": pl_ratio,
            "total_fee": total_fee,
            "net_pnl": net_pnl
        }

        # --- 展示区域 ---
        st.divider()
        
        # 第一排：KPI 卡片
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💸 真实净利润", f"${net_pnl:,.2f}", delta_color="normal")
        c2.metric("🏦 贡献手续费", f"${total_fee:,.2f}", delta_color="inverse")
        c3.metric("🎯 胜率", f"{win_rate:.1f}%")
        c4.metric("⚖️ 盈亏比", f"{pl_ratio:.2f}")

        # 第二排：AI 诊断
        st.subheader("👨‍⚕️ AI 主任医师诊断")
        if st.button("生成毒舌报告 (消耗 Token)"):
            with st.spinner("AI 正在看你的烂操作..."):
                diagnosis = get_ai_diagnosis(stats, api_key)
                st.info(diagnosis)
        
        # 第三排：图表
        st.subheader("📉 资产缩水曲线")
        df = df.sort_values('Time')
        df['Cumulative PnL'] = (df['PnL'] - df['Fee']).cumsum()
        fig = px.line(df, x='Time', y='Cumulative PnL', title='你的账户余额走势')
        st.plotly_chart(fig, use_container_width=True)
        
        # 第四排：引流逻辑 (你的小心机)
        if total_fee > 500:
            st.warning(f"🚨 警报：你已经给交易所交了 ${total_fee:,.0f} 的手续费！")
            st.markdown(f"""
            #### 🩸 别再流血了！
            如果使用高返佣账户，你本可以省下 **${total_fee * 0.4:,.0f}**。
            👉 **[点此注册 Bitget (享 60% 返佣)](https://你的链接)** """)

else:
    # 没传文件时的默认画面
    st.info("👈 请在左侧上传 CSV 文件。如果没有文件，可以去币安导出近 3 个月的‘合约交易历史’。")
