# 选择轻量级 Python 3.11 镜像

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装依赖（利用 Docker 缓存优化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY src /app/src
COPY entrypoint.sh /app/

# 赋予执行权限
RUN chmod +x /app/entrypoint.sh

# 设定环境变量
#ENV CONFIG_PATH=/app/config.yaml
#ENV DATA_DIR=/app/data

ENTRYPOINT ["/app/entrypoint.sh"]
