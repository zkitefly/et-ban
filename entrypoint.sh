#!/bin/sh
set -e

echo "[entrypoint] 启动 easytier-core，参数来自环境变量 EASYTIER_ARGS: ${EASYTIER_ARGS}"

# 后台启动 easytier-core（参数通过环境变量 EASYTIER_ARGS 提供）
sh -c "easytier-core ${EASYTIER_ARGS}" &

LISTEN_PORT="${LISTEN_PORT:-11221}"
TARGET_HOST="${TARGET_HOST:-0.0.0.0}"
TARGET_PORT="${TARGET_PORT:-11010}"

echo "[entrypoint] 启动 IP 过滤代理，监听 ${LISTEN_PORT}，转发到 ${TARGET_HOST}:${TARGET_PORT}"
exec python3 /app/proxy.py

