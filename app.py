import streamlit as st
import pandas as pd
from openai import OpenAI
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="交易员诊所 (终极版)", page_icon="⚡", layout="wide")

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
st.markdown("已升级：支持 **跳过无关表头**、**自动识别GBK/UTF8**、**模糊匹配列名**。")

# --- 3. 核心逻辑 (抗造版) ---

def smart_load_csv(file):
    """
    三重保险读取逻辑：
    1. 尝试不同编码 (utf-8 vs gbk)
    2. 自动寻找表头所在的行 (防止前几行是废话)
    3. 模糊匹配列名 (只要包含'盈亏'就算对)
    """
    
    # 1. 解决编码问题 (中文 CSV 噩梦)
    try:
        df_raw = pd.read_csv(file, encoding='utf-8')
    except:
        file.seek(0)
        df_raw = pd.read_csv(file, encoding='gbk') # 尝试 GBK

    # 2. 解决表头偏移问题 (自动寻找真正的表头行)
    # 策略：我们认为包含 "时间" 或 "Time" 或 "Date" 的那一行才是真正的表头
    header_row_index = -1
    
    # 先看前10行
    for i in range(min(10, len(df_raw))):
        # 把这一行转为字符串，看看有没有关键词
        row_str = str(df_raw.iloc[i].values).lower()
        if 'time' in row_str or 'date' in row_str or '时间' in row_str or '日期' in row_str:
            # 找到了！但这行在 dataframe 里是第 i 行，
            # 实际上如果重新 read_csv，它应该是 header=i+1 (因为第一行变成了列名)
            # 这里简单处理：我们把这一行设为列名，取下面的数据
            df_cleaned = df_raw.iloc[i+1:].copy()
            df_cleaned.columns = df_raw.iloc[i]
            header_row_index = i
            break
    
    # 如果没找到偏移，就默认第一行就是表头
    if header_row_index == -1:
        df_cleaned = df_raw

    # 清洗列名：转字符串、去空格
    df_cleaned.columns = [str(c).strip() for c in df_cleaned.columns]
    
    return df_cleaned

def find_column_by_keyword(df, keywords):
    """模糊搜索列名"""
    for col in df.columns:
        for k in keywords:
            if k in col: # 只要列名包含关键词 (例如 "已实现盈亏(USDT)" 包含 "盈亏")
                return col
    return None

def process_data(df):
    # 3. 模糊匹配关键列
    time_col = find_column_by_keyword(df, ['Time', 'Date', '时间', '日期', 'Created'])
    pnl_col = find_column_by_keyword(df, ['PnL', 'Profit', '盈亏', '收益', 'PL'])
    fee_col = find_column_by_keyword(df, ['Fee', 'Commission', '手续费', '佣金'])
    
    if not pnl_col:
        st.error(f"❌ 还是找不到【盈亏】列。你的列名是：{list(df.columns)}")
        return None

    # 标准化列名
    rename_map = {pnl_col: 'PnL'}
    if time_col: rename_map[time_col] = 'Time'
    if fee_col: rename_map[fee_col] = 'Fee'
    
    df = df.rename(columns=rename_map)
    
    # 数据清洗 (去单位、转数字)
    # 即使是 "1,200.50 USDT"，这行代码也能处理
    df['PnL'] = df['PnL'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True) # 只保留数字、点、负号
    df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
    
    if 'Fee' in df.columns:
        df['Fee'] = df['Fee'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
        df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').abs().fillna(0)
    else:
        df['Fee'] = 0
        
    return df

def get_ai_comment(stats, key):
    if not key: return "请配置 Key。"
    client = OpenAI(api_key=key)
    prompt = f"交易{stats['count']}笔，净利{stats['net']}U，手续费{stats['fee']}U，胜率{stats['win_rate']:.1f}%。请毒舌点评。"
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except Exception as e:
        return f"AI 报错: {e}"

# --- 4. 界面 ---
uploaded_file = st.file_uploader("📂 拖入 CSV 文件 (支持所有乱七八糟的格式)", type=['csv'])

if uploaded_file:
    # 第一步：智能读取
    df_raw = smart_load_csv(uploaded_file)
    
    # 第二步：智能识别列
    df = process_data(df_raw)
    
    if df is not None:
        stats = {
            "count": len(df),
            "net": df['PnL'].sum() - df['Fee'].sum(),
            "fee": df['Fee'].sum(),
            "win_rate": (len(df[df['PnL']>0])/len(df)*100) if len(df)>0 else 0
        }
        
        c1, c2, c3 = st.columns(3)
        c1.metric("净利润", f"${stats['net']:.2f}")
        c2.metric("手续费", f"${stats['fee']:.2f}")
        c3.metric("胜率", f"{stats['win_rate']:.1f}%")
        
        st.divider()
        if st.button("AI 诊断"):
            with st.spinner("AI 正在思考..."):
                st.info(get_ai_comment(stats, api_key))
