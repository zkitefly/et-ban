FROM python:3.11-slim

# 在 easytier 基础镜像中安装 Python 与依赖
RUN apk add --no-cache \
    python3 py3-pip wget ca-certificates

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

# 复制依赖文件并安装 Python 依赖
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# 复制代理程序
COPY proxy.py .

# 暴露代理对外端口（11221），内部 easytier 仍监听 11010
EXPOSE 11221

# 运行代理（监听端口、目标地址等均由环境变量控制）
CMD ["python3", "proxy.py"]
