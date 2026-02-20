# TCP 代理 - GeoIP 地区过滤 + EasyTier 一体镜像

这是一个 Docker 化的 TCP 代理 + EasyTier 一体镜像。  
它会根据 GeoIP 判断客户端 IP 所属国家，然后决定是否拦截；允许的连接会被转发到本机的 EasyTier 节点。

## 功能特性

- ✅ 基于 GeoIP2 数据库进行 IP 地理位置检查
- ✅ 拦截规则完全由环境变量控制（支持多国家代码）
- ✅ 默认不拦截任何国家，按需开启
- ✅ 单镜像同时运行 `easytier-core` 和 IP 过滤代理
- ✅ Docker 部署简单，适合云平台运行

## 架构说明

- **代理**：监听 `LISTEN_PORT`（默认 **11221**），根据 GeoIP 规则决定拦截或放行
- **后端目标**：允许的连接被转发到 `TARGET_HOST:TARGET_PORT`（默认 **0.0.0.0:11010**，即容器内的 EasyTier 节点）
- **EasyTier**：镜像基于 `easytier/easytier:latest`，通过环境变量 `EASYTIER_ARGS` 启动 `easytier-core`

## 使用方法

### 1. 构建镜像

```bash
docker build -t zkitefly/et-ban:latest .
```

### 2. 运行容器（示例）

```bash
docker run -d \
  --name et-ban \
  --network host \
  --privileged \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  --device /dev/net/tun:/dev/net/tun \
  -e EASYTIER_ARGS='-d --network-name yourname --network-secret yourpassword' \
  -e BLOCK_IF_IN_COUNTRIES='CN' \
  zkitefly/et-ban:latest
```

说明：

- 对外提供端口：宿主机的 **11221**（可改 `LISTEN_PORT`）
- 默认转发到：`0.0.0.0:11010`（可改 `TARGET_HOST` / `TARGET_PORT`）
- 示例中拦截所有来自 **CN** 地区的连接，其它国家放行

### 3. 查看日志

```bash
docker logs -f et-ban
```

### 4. 停止容器

```bash
docker stop et-ban && docker rm et-ban
```

## 配置说明

### 代理相关环境变量

- `LISTEN_PORT`：代理监听端口（默认 `11221`）
- `TARGET_HOST`：转发目标地址（默认 `0.0.0.0`）
- `TARGET_PORT`：转发目标端口（默认 `11010`）
- `GEOIP_DB_PATH`：GeoIP 数据库路径（默认 `/usr/share/GeoIP/GeoLite2-Country.mmdb`）
- `BLOCK_IF_IN_COUNTRIES`：**在这些国家就禁止**。  
  例如：`CN` 或 `CN,US,JP`
- `BLOCK_IF_NOT_IN_COUNTRIES`：**不是这些国家就禁止**。  
  例如：`US,CA`（只允许美国和加拿大）

拦截规则优先级：

1. 如果设置了 `BLOCK_IF_IN_COUNTRIES`：在列表中 → 拒绝
2. 否则如果设置了 `BLOCK_IF_NOT_IN_COUNTRIES`：不在列表中 → 拒绝
3. 两个都没设置：**默认不拦截任何国家**

### EasyTier 相关环境变量

- `EASYTIER_ARGS`：传给 `easytier-core` 的完整参数字符串，例如：

```bash
-e EASYTIER_ARGS='-d --network-name yourname --network-secret yourpassword'
```

## 工作原理

1. 外部程序连接到宿主机的 `LISTEN_PORT`（默认 **11221**）
2. 代理获取客户端 IP 地址，并查询 GeoIP 国家代码
3. 按环境变量规则判断是否拦截：
   - 命中拦截规则 → 直接关闭连接
   - 未命中 → 连接到 `TARGET_HOST:TARGET_PORT`（默认 **0.0.0.0:11010**，EasyTier）
4. 在客户端与 EasyTier 节点之间做双向转发

## 注意事项

- GeoIP 数据库会在构建镜像时自动尝试下载
- 如果 GeoIP 数据库加载失败，代理将无法判断国家代码，此时按“全部放行”处理（请查看日志）
- 使用 `--network host` 部署时，请在云平台安全组 / 防火墙中放行 `LISTEN_PORT`

## 故障排查

- **连接总是被拒绝**
  - 检查 `BLOCK_IF_IN_COUNTRIES` / `BLOCK_IF_NOT_IN_COUNTRIES` 是否配置过严
  - 查看日志中打印的国家代码与规则是否匹配
- **连接超时或失败**
  - 确认 EasyTier 节点实际监听的端口是否为 `TARGET_PORT`
  - 确认防火墙 / 安全组已放行 `LISTEN_PORT`
- **GeoIP 数据库问题**
  - 查看容器日志中是否有“无法下载 GeoIP 数据库”
  - 如有需要，可手动挂载自备的 `.mmdb` 文件到 `/usr/share/GeoIP/GeoLite2-Country.mmdb`
