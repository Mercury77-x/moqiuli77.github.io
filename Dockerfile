# 使用轻量级 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制文件
COPY . .

# 安装依赖 (不使用缓存，保证安装最新版)
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 Streamlit 默认端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
