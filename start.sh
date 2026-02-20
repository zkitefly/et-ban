#!/bin/bash
# 启动脚本

set -e

echo "正在启动 TCP 代理和 easytier 服务..."

# 构建并启动容器
docker-compose up -d --build

echo ""
echo "服务已启动！"
echo ""
echo "查看代理日志: docker logs -f tcp-proxy"
echo "查看 easytier 日志: docker logs -f easytier"
echo "停止服务: docker-compose down"
