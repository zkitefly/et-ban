FROM easytier/easytier:latest

# 在 easytier 基础镜像中安装 Python 与依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip wget ca-certificates \
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

# 复制依赖文件并安装 Python 依赖
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制代理程序与入口脚本
COPY proxy.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露代理对外端口（11221），内部 easytier 仍监听 11010
EXPOSE 11221

# 覆盖 entrypoint：同时启动 easytier-core 和代理
# 传给容器的所有参数都会转交给 easytier-core
ENTRYPOINT ["/entrypoint.sh"]

