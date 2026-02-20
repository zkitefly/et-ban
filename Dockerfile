FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 下载 GeoLite2 国家数据库
RUN mkdir -p /usr/share/GeoIP && \
    (wget -q -O /usr/share/GeoIP/GeoLite2-Country.mmdb \
    "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb" || \
    wget -q -O /usr/share/GeoIP/GeoLite2-Country.mmdb \
    "https://github.com/Loyalsoldier/geoip/raw/release/GeoLite2-Country.mmdb" || \
    echo "警告: 无法下载 GeoIP 数据库") && \
    if [ ! -f /usr/share/GeoIP/GeoLite2-Country.mmdb ]; then \
        echo "错误: GeoIP 数据库文件不存在，代理将允许所有连接"; \
    fi

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制代理程序
COPY proxy.py .

# 暴露端口
EXPOSE 11221

# 运行代理服务器
CMD ["python", "proxy.py"]
