from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import requests
import json
import os

app = FastAPI()

# 允许跨域（让前端能连上）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... 这里放入 process_data 函数 (和你之前的一样) ...
# ... 这里放入 get_ai_diagnosis 函数 (和你之前的一样) ...

@app.post("/analyze")
async def analyze_portfolio(
    file: UploadFile = File(...), 
    api_key: str = Form(...)
):
    # 1. 读取文件
    contents = await file.read()
    df = process_data(io.BytesIO(contents))
    
    if df is None:
        return {"error": "数据解析失败，请上传币安标准CSV"}

    # 2. 计算统计数据
    net = df['PnL'].sum()
    fee = df['Fee'].sum()
    count = len(df)
    wins = len(df[df['PnL'] > 0])
    win_rate = (wins / count * 100) if count > 0 else 0
    
    # 3. 增加你想要的“时间毒性检测” (简单的 pandas 逻辑)
    df['hour'] = df['Time'].dt.hour
    # 比如：计算凌晨 2-5 点的胜率
    late_night_trades = df[(df['hour'] >= 2) & (df['hour'] <= 5)]
    night_win_rate = 0
    if len(late_night_trades) > 0:
        night_wins = len(late_night_trades[late_night_trades['PnL'] > 0])
        night_win_rate = (night_wins / len(late_night_trades)) * 100

    stats = {
        "count": count, 
        "net": net, 
        "fee": fee, 
        "win_rate": win_rate,
        "night_win_rate": night_win_rate
    }

    # 4. 调用 LLM
    # 注意：这里需要修改 get_ai_diagnosis 让它返回 JSON 结构，而不是纯文本
    # 或者你在 prompt 里强制要求输出 JSON
    raw_result = get_ai_diagnosis(stats, api_key, "gemini-1.5-pro")
    
    # 假设你已经把 Prompt 改成了返回 JSON 格式
    # 实际项目中这里需要做 JSON 解析处理
    
    return {
        "stats": stats,
        "analysis": raw_result 
    }
