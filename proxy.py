import socket
import threading
import sys
import geoip2.database
import geoip2.errors
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# GeoIP2 数据库路径
GEOIP_DB_PATH = '/usr/share/GeoIP/GeoLite2-Country.mmdb'

class TCPProxy:
    def __init__(
        self,
        listen_port,
        target_host,
        target_port,
        geoip_db_path=GEOIP_DB_PATH,
        block_if_in_countries=None,
        block_if_not_in_countries=None,
    ):
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.geoip_db_path = geoip_db_path
        self.geoip_reader = None
        # 需要拦截/放行的国家代码集合（大写，ISO-3166 两位）
        self.block_if_in_countries = set(block_if_in_countries or [])
        self.block_if_not_in_countries = set(block_if_not_in_countries or [])
        
        # 加载 GeoIP 数据库
        try:
            if Path(geoip_db_path).exists():
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
                logger.info(f"GeoIP 数据库已加载: {geoip_db_path}")
            else:
                logger.warning(f"GeoIP 数据库不存在: {geoip_db_path}，将允许所有连接")
        except Exception as e:
            logger.error(f"加载 GeoIP 数据库失败: {e}，将允许所有连接")
    
    def _get_country_code(self, ip_address):
        """获取 IP 所属国家代码，失败返回 None"""
        if not self.geoip_reader:
            return None
        
        try:
            response = self.geoip_reader.country(ip_address)
            country_code = response.country.iso_code
            return country_code
        except geoip2.errors.AddressNotFoundError:
            logger.warning(f"IP 地址未找到: {ip_address}")
            return None
        except Exception as e:
            logger.error(f"检查 IP 地理位置时出错: {e}")
            return None

    def is_blocked_ip(self, ip_address):
        """
        根据环境变量规则判断 IP 是否应被拦截。
        规则（按优先级）：
        1. 如果设置了 BLOCK_IF_IN_COUNTRIES：在列表中则拦截
        2. 否则，如果设置了 BLOCK_IF_NOT_IN_COUNTRIES：不在列表中则拦截
        3. 如果都没设置：不拦截任何国家
        """
        country_code = self._get_country_code(ip_address)
        if not country_code:
            # 查不到国家信息时，默认不拦截（更宽松）
            return False

        # 统一大写
        country_code = country_code.upper()

        # 1. 在这些国家就禁止
        if self.block_if_in_countries:
            return country_code in self.block_if_in_countries

        # 2. 不是这些国家就禁止
        if self.block_if_not_in_countries:
            return country_code not in self.block_if_not_in_countries

        # 3. 默认行为：不拦截任何国家
        return False
    
    def handle_client(self, client_socket, client_address):
        """处理客户端连接"""
        client_ip = client_address[0]
        logger.info(f"收到来自 {client_ip}:{client_address[1]} 的连接")
        
        # 根据国家代码规则判断是否拦截
        if self.is_blocked_ip(client_ip):
            logger.warning(f"根据国家代码规则拒绝连接: {client_ip}")
            client_socket.close()
            return
        
        logger.info(f"允许连接: {client_ip}，转发到 {self.target_host}:{self.target_port}")
        
        # 连接到目标服务器
        try:
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(30)
            target_socket.connect((self.target_host, self.target_port))
            
            # 启动双向转发
            def forward(source, destination, direction):
                try:
                    while True:
                        data = source.recv(4096)
                        if not data:
                            break
                        destination.sendall(data)
                except Exception as e:
                    logger.debug(f"{direction} 转发错误: {e}")
                finally:
                    try:
                        source.close()
                        destination.close()
                    except:
                        pass
            
            # 创建两个转发线程
            thread1 = threading.Thread(
                target=forward,
                args=(client_socket, target_socket, "客户端->目标"),
                daemon=True
            )
            thread2 = threading.Thread(
                target=forward,
                args=(target_socket, client_socket, "目标->客户端"),
                daemon=True
            )
            
            thread1.start()
            thread2.start()
            
            # 等待线程完成
            thread1.join()
            thread2.join()
            
        except Exception as e:
            logger.error(f"连接目标服务器失败: {e}")
            client_socket.close()
    
    def start(self):
        """启动代理服务器"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(('0.0.0.0', self.listen_port))
            server_socket.listen(100)
            logger.info(f"代理服务器启动，监听端口 {self.listen_port}，转发到 {self.target_host}:{self.target_port}")
            
            while True:
                client_socket, client_address = server_socket.accept()
                # 为每个客户端创建新线程
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭服务器...")
        except Exception as e:
            logger.error(f"服务器错误: {e}")
        finally:
            server_socket.close()
            if self.geoip_reader:
                self.geoip_reader.close()

def main():
    # 从环境变量读取配置
    import os

    listen_port = int(os.getenv('LISTEN_PORT', '11221'))
    target_host = os.getenv('TARGET_HOST', '0.0.0.0')
    target_port = int(os.getenv('TARGET_PORT', '11010'))
    geoip_db_path = os.getenv('GEOIP_DB_PATH', GEOIP_DB_PATH)

    # 拦截规则环境变量（逗号分隔的国家代码，如: "CN,US,JP"）
    # 1. BLOCK_IF_IN_COUNTRIES: 在这些国家就禁止
    # 2. BLOCK_IF_NOT_IN_COUNTRIES: 不是这些国家就禁止
    def parse_countries(env_name):
        raw = os.getenv(env_name, '')
        if not raw.strip():
            return []
        return [c.strip().upper() for c in raw.split(',') if c.strip()]

    block_if_in = parse_countries('BLOCK_IF_IN_COUNTRIES')
    block_if_not_in = parse_countries('BLOCK_IF_NOT_IN_COUNTRIES')

    proxy = TCPProxy(
        listen_port,
        target_host,
        target_port,
        geoip_db_path,
        block_if_in_countries=block_if_in,
        block_if_not_in_countries=block_if_not_in,
    )
    proxy.start()

if __name__ == '__main__':
    main()
