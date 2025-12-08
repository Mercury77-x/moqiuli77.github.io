import streamlit as st
import pandas as pd
import requests
import json
import os
import re
from PIL import Image, ImageDraw, ImageFont
import io

# --- 1. 页面基础配置 (赛博朋克风) ---
st.set_page_config(page_title="币圈韭菜急诊室", page_icon="🚑", layout="centered")

# 注入自定义 CSS (隐藏顶部栏，黑绿配色)
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background-color: #0e1117;
        color: #00ff41;
        font-family: 'Courier New', monospace;
    }
    /* 标题样式 */
    h1, h2, h3 {
        color: #00ff41 !important;
        text-shadow: 0 0 5px #00ff41;
    }
    /* 卡片背景 */
    .css-1r6slb0, .stMarkdown, .stButton {
        border-radius: 10px;
    }
    /* 按钮样式 */
    .stButton>button {
        background-color: #003300;
        color: #00ff41;
        border: 1px solid #00ff41;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #00ff41;
        color: #000000;
    }
    /* 去除 Streamlit 默认页眉页脚 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏配置 (Key 和 模型) ---
with st.sidebar:
    st.header("⚙️ 后台设置")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ 密钥已注入")
    else:
        api_key = st.text_input("输入 Gemini Key", type="password")
    
    # 模型选择 (保留之前的修正)
    model_name = st.selectbox(
        "🔮 AI 模型",
        ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"],
        index=0
    )

# --- 3. 核心功能函数 ---

def process_data(file):
    """数据清洗逻辑"""
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
        
        # 模糊匹配 PnL
        if 'PnL' not in df.columns:
            for col in df.columns:
                if 'pnl' in col or 'profit' in col or '盈亏' in col:
                    df = df.rename(columns={col: 'PnL'})
                    break
        
        if 'PnL' not in df.columns: return None

        df['PnL'] = pd.to_numeric(df['PnL'], errors='coerce').fillna(0)
        
        if 'Fee' not in df.columns:
            df['Fee'] = 0.0 
        else:
            df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').abs().fillna(0)
            
        return df
    except:
        return None

def get_ai_diagnosis(stats, key, model):
    """调用 LLM 生成诊断报告"""
    if not key: return "请配置 Key"
    
    clean_key = key.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    
    # --- 你的终极 Prompt ---
    system_role = """
    你是一位拥有20年经验的华尔街顶级风险控制专家，也是一位“币圈韭菜急诊室”的毒舌主治医生。
    你的风格混合了《大空头》的Mark Baum和《华尔街之狼》的Jordan Belfort。
    你也是一位“从死人堆里爬出来的币圈老炮”，你要做的是“先扇他两巴掌让他清醒，然后递给他一把真正能杀敌的枪”。
    """

    prompt_text = f"""
    {system_role}

    【用户数据】
    - 交易总数: {stats['count']} 笔
    - 胜率: {stats['win_rate']:.2f}%
    - 总手续费: {stats['fee']:.2f} U
    - 净利润: {stats['net']:.2f} U
    
    # 🧠 深度解剖框架
    请严格按以下 4 个板块输出内容，每个板块之间用 "|||" 分隔：

    1. [板块一：核心诊断]
       - 给用户一个极具侮辱性或赞赏性的标签（如：币安打工仔、野生索罗斯）。
       - 一句话总结死因。

    2. [板块二：残酷真相 (平行宇宙算账)]
       - 计算如果在一个省下40%-60%手续费的渠道，他的账户余额应该是多少？
       - 告诉他“你不是菜，是给交易所交了智商税”。

    3. [板块三：废墟中的黄金 (寻找希望)]
       - 找到他哪怕一点点的优势（如：如果不看土狗币其实是赚的 / 盈亏比很高 / 长线单很稳）。
       - 告诉他这是翻身的希望。

    4. [板块四：处方建议]
       - 给出3条物理级建议（如：每天限3单、删自选）。
       - 如果手续费高且亏损，隐晦强烈暗示换返佣渠道。

    【输出格式要求】
    不要输出 Markdown 标题（如 ###），直接输出纯文本内容。
    确保用 ||| 将这四部分内容严格切分开。
    不要说客套话。
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"Net Error: {e}"

def create_share_image(label, net_pnl, fee_loss, advice):
    """生成分享图片 (Pillow)"""
    # 创建黑色背景
    width, height = 600, 800
    img = Image.new('RGB', (width, height), color=(14, 17, 23)) # 深色背景
    d = ImageDraw.Draw(img)
    
    # 注意：Zeabur 容器可能没有中文字体，这里为了防报错，仅做简单的文字绘制
    # 如果想完美支持中文，需要上传一个 .ttf 文件到仓库
    try:
        # 尝试加载默认字体 (通常不支持中文)
        # 实际部署建议上传一个 font.ttf 文件并在代码里引用
        font_large = ImageFont.load_default() 
        font_small = ImageFont.load_default()
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 画框框
    d.rectangle([(20, 20), (580, 780)], outline="#00ff41", width=3)
    
    # 写入文字 (由于没有中文字体，这里暂写英文 Demo，避免方块乱码)
    # *建议用户后续上传字体文件来支持中文分享图*
    d.text((50, 100), "CRYPTO ER REPORT", fill="#00ff41")
    d.text((50, 200), f"NET PNL: {net_pnl} U", fill="white")
    d.text((50, 250), f"FEES PAID: {fee_loss} U", fill="#ff4b4b")
    d.text((50, 350), "DIAGNOSIS:", fill="#00ff41")
    # 简单的截取标签
    short_label = label[:20] + "..." if len(label)>20 else label
    d.text((50, 380), short_label, fill="white")
    
    d.text((50, 700), "mo-clinic.zeabur.app", fill="gray")
    
    return img

# --- 4. 界面逻辑 ---

# 标题区
st.title("🚑 币圈韭菜急诊室")
st.caption("“甚至死人也能医活。”")
st.markdown("---")

# 初始化 session_state，防止刷新丢数据
if 'report' not in st.session_state:
    st.session_state['report'] = None
if 'stats' not in st.session_state:
    st.session_state['stats'] = None

uploaded_file = st.file_uploader("📂 挂号处 (上传 CSV)", type=['csv'])

if uploaded_file:
    df = process_data(uploaded_file)
    
    if df is not None:
        # 计算基础数据
        net = df['PnL'].sum()
        fee = df['Fee'].sum()
        count = len(df)
        wins = len(df[df['PnL'] > 0])
        win_rate = (wins / count * 100) if count > 0 else 0
        stats = {"count": count, "net": net, "fee": fee, "win_rate": win_rate}
        st.session_state['stats'] = stats

        # 开始诊断按钮
        if st.button("💉 开始全身扫描"):
            with st.spinner("正在进行开颅检查...提取智商税数据..."):
                raw_text = get_ai_diagnosis(stats, api_key, model_name)
                # 切割数据
                parts = raw_text.split("|||")
                # 容错处理
                if len(parts) < 4:
                    parts = [raw_text, "数据解析失败", "无", "无"]
                st.session_state['report'] = parts

# --- 5. 结果展示区 (模拟 H5 流式布局) ---

if st.session_state['report']:
    parts = st.session_state['report']
    stats = st.session_state['stats']
    
    # 板块 1: 核心确诊 (大字报)
    st.markdown("### 🩻 确诊单")
    st.info(parts[0].strip()) # 标签 + 死因
    
    # 板块 2: 残酷真相 (红黑榜)
    st.markdown("### 🩸 残酷真相")
    c1, c2 = st.columns(2)
    c1.metric("你的账面亏损", f"${stats['net']:.0f}")
    c2.metric("给交易所打的工", f"${stats['fee']:.0f}", delta_color="inverse")
    st.warning(parts[1].strip()) # 平行宇宙算账
    
    # 板块 3: 废墟中的光 (希望)
    st.markdown("### ✨ 废墟里的光")
    st.success(parts[2].strip()) # 寻找优势
    
    # 板块 4: 处方 (行动)
    st.markdown("### 💊 救命处方")
    st.markdown(parts[3].strip()) # 建议
    
    st.markdown("---")
    
    # 分享区
    st.markdown("#### 📸 生成病历单")
    # 生成图片
    # 注意：因为这里没有中文字体文件，生成的图片暂时不支持中文显示
    # 如果需要，请在 GitHub 上传一个 font.ttf 并修改代码加载它
    img = create_share_image(parts[0][:15], stats['net'], stats['fee'], parts[3])
    
    # 转为字节流供下载
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    
    c_share1, c_share2 = st.columns(2)
    with c_share1:
        st.download_button(
            label="📥 下载病历单 (发推特)",
            data=byte_im,
            file_name="crypto_er_report.png",
            mime="image/png"
        )
    with c_share2:
        st.link_button("🐦 一键发推吐槽", f"https://twitter.com/intent/tweet?text=我在币圈急诊室确诊了...我的手续费竟然高达 {stats['fee']} U！&url=https://mo-clinic.zeabur.app")
