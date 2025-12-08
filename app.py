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

# 注入自定义 CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #00ff41;
        font-family: 'Courier New', monospace;
    }
    h1, h2, h3 {
        color: #00ff41 !important;
        text-shadow: 0 0 5px #003300;
    }
    .stButton>button {
        background-color: #003300;
        color: #00ff41;
        border: 1px solid #00ff41;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #00ff41;
        color: #000000;
    }
    /* 卡片背景微调 */
    div[data-testid="stMetricValue"] {
        color: #00ff41 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 诊所后台")
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        api_key = env_key
        st.success("✅ 密钥已注入")
    else:
        api_key = st.text_input("输入 Gemini Key", type="password")
    
    model_name = st.selectbox(
        "🔮 AI 模型",
        ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite"],
        index=0
    )

# --- 3. 核心功能函数 ---

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
    if not key: return "请配置 Key|||无|||无|||无"
    
    clean_key = key.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"
    headers = {'Content-Type': 'application/json'}
    
    # --- 你的“灵魂救赎” Prompt ---
    prompt_text = f"""
    你是一位拥有20年经验的“币圈韭菜急诊室”主治医生，风格混合了《大空头》的Mark Baum和老炮交易员。
    
    【用户数据】
    - 交易总数: {stats['count']}
    - 胜率: {stats['win_rate']:.2f}%
    - 总手续费: {stats['fee']:.2f} U
    - 净利润: {stats['net']:.2f} U
    
    请严格按以下 4 个板块输出内容，板块之间必须用 "|||" 分隔：

    1. [板块一：核心诊断]
       - 给用户一个极具侮辱性或赞赏性的标签（如：币安荣誉员工、被费率吸干的干尸）。
       - 一句话总结死因。

    2. [板块二：残酷真相]
       - 必须计算：如果他省下50%手续费，他的账户余额应该是多少？
       - 告诉他“你以为你亏了 X，其实是手续费杀了你”。

    3. [板块三：废墟中的光]
       - 找到他哪怕一点点的优势（如：如果不看土狗币其实是赚的 / 盈亏比很高）。
       - 告诉他这是翻身的希望。

    4. [板块四：处方建议]
       - 给出3条物理级建议（如：每天限3单、删自选）。
       - 如果手续费高且亏损，隐晦强烈暗示换返佣渠道（用数学逻辑）。

    【输出格式】
    不要输出 Markdown 标题，只输出纯文本。确保用 ||| 分隔这四段。
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error: {response.text}|||API Error|||无|||无"
    except Exception as e:
        return f"Net Error: {e}|||Net Error|||无|||无"

# --- 图片生成核心逻辑 (完美中文版) ---

def draw_text_with_wrap(draw, text, position, font, max_width, fill):
    """辅助函数：处理中文自动换行"""
    x, y = position
    lines = []
    current_line = ""
    
    for char in text:
        # 简单估算字符宽度
        test_line = current_line + char
        # 获取这一行的宽度
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    lines.append(current_line)
    
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1]
        y += line_height + 10 # 行间距
    
    return y # 返回最后的Y坐标

def create_share_image(label, net_pnl, fee_loss, advice):
    """生成中文分享海报"""
    width, height = 600, 950
    bg_color = (14, 17, 23)
    green = (0, 255, 65)
    white = (255, 255, 255)
    red = (255, 75, 75)
    
    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    # 1. 加载字体 (font.ttf)
    try:
        font_title = ImageFont.truetype("font.ttf", 48) # 标题大字
        font_data = ImageFont.truetype("font.ttf", 60)  # 数据超大字
        font_text = ImageFont.truetype("font.ttf", 28)  # 正文
        font_small = ImageFont.truetype("font.ttf", 20) # 脚注
    except:
        # 兜底
        font_title = ImageFont.load_default()
        font_data = ImageFont.load_default()
        font_text = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 2. 绘制外框
    d.rectangle([(20, 20), (580, 930)], outline=green, width=4)
    
    # 3. 头部
    d.text((50, 60), "币圈韭菜急诊室", font=font_title, fill=green)
    d.text((50, 120), "CRYPTO ER REPORT", font=font_small, fill="gray")
    d.line([(40, 150), (560, 150)], fill="gray", width=1)
    
    # 4. 核心数据 (左右布局)
    d.text((50, 180), "净利润 (Net PnL)", font=font_small, fill="gray")
    color_pnl = green if net_pnl >= 0 else red
    d.text((50, 210), f"{int(net_pnl)} U", font=font_data, fill=color_pnl)
    
    d.text((320, 180), "智商税 (Fees)", font=font_small, fill="gray")
    d.text((320, 210), f"{int(fee_loss)} U", font=font_data, fill=red)
    
    # 5. 确诊标签
    y = 320
    d.text((50, y), "确诊标签 (Diagnosis):", font=font_small, fill=green)
    y += 35
    # 清理标签里的无关字符
    clean_label = label.replace("【核心诊断】", "").replace(":", "").strip()
    y = draw_text_with_wrap(d, clean_label, (50, y), font_title, 500, white)
    
    # 6. 医生处方
    y += 40
    d.text((50, y), "医生处方 (Prescription):", font=font_small, fill=green)
    y += 35
    # 清理处方文本
    clean_advice = advice.replace("*", "").strip()[:150] # 截取前150字防止溢出
    y = draw_text_with_wrap(d, clean_advice, (50, y), font_text, 500, (220, 220, 220))
    
    # 7. 底部引流
    d.line([(40, 880), (560, 880)], fill="gray", width=1)
    d.text((180, 900), "mo-clinic.zeabur.app", font=font_small, fill="gray")
    
    return img

# --- 4. 界面逻辑 ---

st.title("🚑 币圈韭菜急诊室")
st.caption("“甚至死人也能医活。”")

if 'report' not in st.session_state:
    st.session_state['report'] = None

uploaded_file = st.file_uploader("📂 挂号处 (上传 CSV)", type=['csv'])

if uploaded_file:
    df = process_data(uploaded_file)
    if df is not None:
        # 统计数据
        net = df['PnL'].sum()
        fee = df['Fee'].sum()
        count = len(df)
        wins = len(df[df['PnL'] > 0])
        win_rate = (wins / count * 100) if count > 0 else 0
        stats = {"count": count, "net": net, "fee": fee, "win_rate": win_rate}
        
        if st.button("💉 开始全身扫描"):
            with st.spinner("正在进行开颅检查..."):
                raw = get_ai_diagnosis(stats, api_key, model_name)
                parts = raw.split("|||")
                if len(parts) < 4: parts = [raw, "数据解析中...", "无", "无"]
                st.session_state['report'] = parts
                st.session_state['stats'] = stats

# --- 5. 结果展示 (H5 流式卡片) ---

if st.session_state['report']:
    parts = st.session_state['report']
    stats = st.session_state['stats']
    
    # 卡片 1: 确诊
    st.markdown("### 🩻 确诊单")
    st.error(parts[0]) # 标签
    
    # 卡片 2: 真相
    st.markdown("### 🩸 残酷真相")
    c1, c2 = st.columns(2)
    c1.metric("账面盈亏", f"${stats['net']:.0f}")
    c2.metric("手续费磨损", f"${stats['fee']:.0f}", delta_color="inverse")
    st.info(parts[1]) # 平行宇宙
    
    # 卡片 3: 希望
    st.markdown("### ✨ 废墟里的光")
    st.success(parts[2])
    
    # 卡片 4: 处方
    st.markdown("### 💊 救命处方")
    st.markdown(parts[3])
    
    st.markdown("---")
    
    # 生成图片
    st.markdown("#### 📸 生成分享海报")
    img = create_share_image(parts[0], stats['net'], stats['fee'], parts[3])
    
    # 转字节流
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    
    col_dl, col_tw = st.columns(2)
    with col_dl:
        st.download_button(
            label="📥 下载病历单 (含中文)",
            data=byte_im,
            file_name="crypto_er_report.png",
            mime="image/png"
        )
    with col_tw:
        st.link_button("🐦 发推特吐槽", "https://twitter.com/intent/tweet?text=我在币圈急诊室确诊了...&url=https://mo-clinic.zeabur.app")
