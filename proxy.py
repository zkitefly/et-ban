#!/usr/bin/env python3
"""
TCP 代理服务器，检查客户端 IP 是否为中国大陆
如果是中国大陆 IP，拒绝连接；否则转发到目标服务器
"""
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
    def __init__(self, listen_port, target_host, target_port, geoip_db_path=GEOIP_DB_PATH):
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.geoip_db_path = geoip_db_path
        self.geoip_reader = None
        
        # 加载 GeoIP 数据库
        try:
            if Path(geoip_db_path).exists():
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
                logger.info(f"GeoIP 数据库已加载: {geoip_db_path}")
            else:
                logger.warning(f"GeoIP 数据库不存在: {geoip_db_path}，将允许所有连接")
        except Exception as e:
            logger.error(f"加载 GeoIP 数据库失败: {e}，将允许所有连接")
    
    def is_china_ip(self, ip_address):
        """检查 IP 是否为中国大陆"""
        if not self.geoip_reader:
            return False
        
        try:
            response = self.geoip_reader.country(ip_address)
            country_code = response.country.iso_code
            # CN 表示中国
            return country_code == 'CN'
        except geoip2.errors.AddressNotFoundError:
            logger.warning(f"IP 地址未找到: {ip_address}")
            return False
        except Exception as e:
            logger.error(f"检查 IP 地理位置时出错: {e}")
            return False
    
    def handle_client(self, client_socket, client_address):
        """处理客户端连接"""
        client_ip = client_address[0]
        logger.info(f"收到来自 {client_ip}:{client_address[1]} 的连接")
        
        # 检查是否为中国大陆 IP
        if self.is_china_ip(client_ip):
            logger.warning(f"拒绝来自中国大陆的连接: {client_ip}")
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
    
    proxy = TCPProxy(listen_port, target_host, target_port, geoip_db_path)
    proxy.start()

if __name__ == '__main__':
    main()
