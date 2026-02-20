# TCP 代理 - 中国大陆 IP 过滤

这是一个 Docker 化的 TCP 代理服务器，能够检查客户端 IP 是否为中国大陆，如果是则拒绝连接，否则转发到目标服务器。

## 功能特性

- ✅ 基于 GeoIP2 数据库进行 IP 地理位置检查
- ✅ 自动拒绝来自中国大陆的连接
- ✅ 非中国大陆 IP 自动转发到目标服务器
- ✅ Docker 化部署，易于使用
- ✅ 集成 easytier 容器

## 架构说明

- **代理容器**: 监听 11221 端口，检查客户端 IP，如果是中国大陆 IP 则拒绝，否则转发到 11010 端口
- **easytier 容器**: 运行 easytier/easytier:latest 镜像，监听 11010 端口

## 使用方法

### 1. 构建并启动服务

```bash
docker-compose up -d --build
```

### 2. 查看日志

```bash
# 查看代理日志
docker logs -f tcp-proxy

# 查看 easytier 日志
docker logs -f easytier
```

### 3. 停止服务

```bash
docker-compose down
```

## 配置说明

### 环境变量

代理容器支持以下环境变量（在 `docker-compose.yml` 中配置）：

- `LISTEN_PORT`: 监听端口（默认: 11221）
- `TARGET_HOST`: 目标服务器地址（默认: 0.0.0.0）
- `TARGET_PORT`: 目标服务器端口（默认: 11010）
- `GEOIP_DB_PATH`: GeoIP 数据库路径（默认: /usr/share/GeoIP/GeoLite2-Country.mmdb）

### 修改目标端口

如果需要修改转发目标端口，编辑 `docker-compose.yml` 中的 `TARGET_PORT` 环境变量。

## 工作原理

1. 外部程序连接到代理服务器的 **11221** 端口
2. 代理服务器获取客户端 IP 地址
3. 使用 GeoIP2 数据库查询 IP 所属国家
4. 如果国家代码为 CN（中国），**拒绝连接**
5. 否则，建立到目标服务器（**11010** 端口，easytier 服务）的连接
6. 双向转发数据

## 注意事项

- GeoIP 数据库会在构建时自动下载
- 如果 GeoIP 数据库加载失败，代理将允许所有连接（安全起见，建议检查日志）
- 代理使用 `network_mode: host` 以便访问本地服务
- easytier 容器也使用 `network_mode: host` 模式

## 故障排查

### GeoIP 数据库下载失败

如果构建时 GeoIP 数据库下载失败，可以手动下载并挂载：

```bash
# 下载数据库
wget -O GeoLite2-Country.mmdb "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb"

# 在 docker-compose.yml 中添加卷挂载
volumes:
  - ./GeoLite2-Country.mmdb:/usr/share/GeoIP/GeoLite2-Country.mmdb
```

### 连接被拒绝

- 检查防火墙设置
- 确认 easytier 服务（11010 端口）正在运行
- 查看代理日志了解详细错误信息
- 如果来自中国大陆 IP，连接会被拒绝（这是预期行为）