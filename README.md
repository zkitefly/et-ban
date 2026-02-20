# TCP 代理 - GeoIP 地区过滤

这是一个 Docker 化的 TCP 代理程序。  
它会根据 GeoIP 判断客户端 IP 所属国家，然后决定是否拦截；允许的连接会被转发到你指定的后端服务（例如运行在宿主机/其它容器里的 EasyTier 节点）。

## 功能特性

- ✅ 基于 GeoIP2 数据库进行 IP 地理位置检查
- ✅ 拦截规则完全由环境变量控制（支持多国家代码）
- ✅ 默认不拦截任何国家，按需开启
- ✅ 可与 EasyTier/任意 TCP 服务搭配使用
- ✅ 纯 Python 镜像，适合云平台部署

## 架构说明

- **代理**：监听 `LISTEN_PORT`（默认 **11221**），根据 GeoIP 规则决定拦截或放行
- **后端目标**：允许的连接被转发到 `TARGET_HOST`（格式：`host:port`，例如 **192.168.87.10:11010**，指向 EasyTier）
- **EasyTier（可选）**：建议使用官方 `easytier/easytier:latest` 镜像或直接在宿主机运行，与本代理独立部署

## 使用方法

### 1. 构建代理镜像

```bash
docker build -t zkitefly/et-ban:latest .
```

### 2. 启动后端服务（示例：EasyTier）

示例：在宿主机或单独容器中启动 EasyTier，监听 `0.0.0.0:11010`。  
（具体命令按 EasyTier 官方文档配置）

### 3. 运行代理容器（示例）

假设：
- 宿主机或某容器的 IP 为 `192.168.87.10`
- 后端服务监听 `192.168.87.10:11010`

```bash
docker run -d \
  --name et-ban \
  --network host \
  -e LISTEN_PORT=11221 \
  -e TARGET_HOST=192.168.87.10:11010 \
  -e BLOCK_IF_IN_COUNTRIES='CN' \
  zkitefly/et-ban:latest
```

说明：

- 对外提供端口：宿主机的 **11221**（可改 `LISTEN_PORT`）
- 默认转发到：`TARGET_HOST`（格式：`host:port`，上例为 `192.168.87.10:11010`）
- 示例中拦截所有来自 **CN** 地区的连接，其它国家放行

### 4. 查看日志

```bash
docker logs -f et-ban
```

### 5. 停止容器

```bash
docker stop et-ban && docker rm et-ban
```

## 配置说明

### 代理相关环境变量

- `LISTEN_PORT`：代理监听端口（默认 `11221`）
- `TARGET_HOST`：转发目标地址（格式：`host:port`，默认 `127.0.0.1:10110`）  
  例如：`192.168.87.10:11010`
- `GEOIP_DB_PATH`：GeoIP 数据库路径（默认 `/usr/share/GeoIP/GeoLite2-Country.mmdb`）
- `BLOCK_IF_IN_COUNTRIES`：**是些国家就禁止**。  
  例如：`CN` 或 `CN,US,JP`
- `BLOCK_IF_NOT_IN_COUNTRIES`：**不是这些国家就禁止**。  
  例如：`US,CA`（只允许美国和加拿大）

拦截规则优先级：

1. 如果设置了 `BLOCK_IF_IN_COUNTRIES`：在列表中 → 拒绝
2. 否则如果设置了 `BLOCK_IF_NOT_IN_COUNTRIES`：不在列表中 → 拒绝
3. 两个都没设置：**默认不拦截任何国家**

## 工作原理

1. 外部程序连接到宿主机的 `LISTEN_PORT`（默认 **11221**）
2. 代理获取客户端 IP 地址，并查询 GeoIP 国家代码
3. 按环境变量规则判断是否拦截：
   - 命中拦截规则 → 直接关闭连接
   - 未命中 → 连接到 `TARGET_HOST`（例如 **192.168.87.10:11010**）
4. 在客户端与后端服务之间做双向转发

## 注意事项

- GeoIP 数据库会在构建镜像时自动尝试下载
- 如果 GeoIP 数据库加载失败，代理将无法判断国家代码，此时按“全部放行”处理（请查看日志）
- 使用 `--network host` 部署时，请在云平台安全组 / 防火墙中放行 `LISTEN_PORT`
- 如果后端是 EasyTier，请确保它监听的地址不是 loopback（127.0.0.1）以避免隧道限制

## 故障排查

- **连接总是被拒绝**
  - 检查 `BLOCK_IF_IN_COUNTRIES` / `BLOCK_IF_NOT_IN_COUNTRIES` 是否配置过严
  - 查看日志中打印的国家代码与规则是否匹配
- **连接超时或失败**
  - 确认后端服务实际监听的地址和端口是否与 `TARGET_HOST`（格式：`host:port`）一致
  - 确认防火墙 / 安全组已放行 `LISTEN_PORT`
- **GeoIP 数据库问题**
  - 查看容器日志中是否有“无法下载 GeoIP 数据库”
  - 如有需要，可手动挂载自备的 `.mmdb` 文件到 `/usr/share/GeoIP/GeoLite2-Country.mmdb`
