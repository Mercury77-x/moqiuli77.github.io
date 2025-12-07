# 使用轻量级 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制文件
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 🌟 关键修改：告诉 Zeabur 我们用 8080
EXPOSE 8080

# 🌟 关键修改：强制 Streamlit 运行在 8080 端口
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
