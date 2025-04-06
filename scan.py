import eventlet
from port_scan import port_scan
from concurrent.futures import ThreadPoolExecutor
import ipaddress
from queue import Queue, Empty
import threading
import json
import os
import tempfile
import uuid

eventlet.monkey_patch(socket=True, time=True)

class Portscan:
    def __init__(self, ip_str, port_str, timeout=1, threads=100):
        self.ip_list = self.parse_ip_list(ip_str)
        self.port_list =self.parse_port_list(port_str)
        self.timeout = timeout
        self.threads = threads
        self.results = []
        self.lock = threading.Lock()
        self.stop_flag = False  # 新增停止标志位
        self.temp_dir = 'tmp'  # 创建临时目录
        self.batch_size = 100  # 每批次写入的结果数量
        self.result_file = os.path.join(self.temp_dir, f"results_{uuid.uuid4().hex}.txt")  # 修改文件格式为 .txt
        with open(self.result_file, 'w') as f:
            pass  # 初始化为空文件

    def parse_ip_list(self, ip_str):
        ip_list = []
        for part in ip_str.split(','):
            part = part.strip()
            if '/' in part:  # CIDR notation
                network = ipaddress.ip_network(part, strict=False)
                ip_list.extend([str(ip) for ip in network.hosts()])
            elif '-' in part:  # Range notation
                start_ip, end_ip = part.split('-')
                start_ip = ipaddress.IPv4Address(start_ip.strip())
                end_ip = ipaddress.IPv4Address(end_ip.strip())
                ip_list.extend([str(ip) for ip in range(int(start_ip), int(end_ip) + 1)])
            else:
                ip_list.append(part)
        return ip_list

    def parse_port_list(self, port_str):
        port_list = []
        for part in port_str.split(','):
            part = part.strip()
            if '-' in part:
                start_port, end_port = part.split('-')
                start_port = int(start_port.strip())
                end_port = int(end_port.strip())
                port_list.extend(range(start_port, end_port + 1))
            else:
                port_list.append(int(part.strip()))
        return port_list

    def run_scan(self):
        """生成者消费者模式"""
        queue = Queue()

        def producer():
            for ip in self.ip_list:
                for port in self.port_list:
                    if self.stop_flag:  # 检查停止标志位
                        return
                    queue.put((ip, port))
            # 放入若干个 None, None 作为哨兵
            for _ in range(self.threads):
                queue.put((None, None))

        def consumer():
            batch = []
            while True:
                if self.stop_flag:  # 检查停止标志位
                    print(f"线程 {threading.current_thread().name} 停止")
                    break
                ip_port = queue.get(timeout=1)  # 增加超时以避免死锁
                if ip_port == (None, None):
                    queue.task_done()
                    break
                ip, port = ip_port
                result = port_scan(ip, port, self.timeout)
                if result['status'] == 'Opened':
                    batch.append(result)
                    print(f"当前任务: {ip_port}, 扫描结果: {result}")
                if len(batch) >= self.batch_size:  # 达到批次大小时写入文件
                    print(f"写入批次: {len(batch)} 条结果")
                    self._write_batch_to_file(batch)
                    batch = []
                queue.task_done()
            if batch:  # 写入剩余的批次
                self._write_batch_to_file(batch)

        with ThreadPoolExecutor(max_workers=self.threads + 1) as executor:
            executor.submit(producer)
            for _ in range(self.threads):
                executor.submit(consumer)
        print(f"所有线程已完成, 扫描结果保存在 {self.result_file}")
        queue.join()  # 确保所有任务完成
        return self.get_results()

    def _write_batch_to_file(self, batch):
        print(batch)
        """将结果批次逐行追加写入结果文件"""
        if not batch:  # 确保批次不为空
            return
        with self.lock:  # 确保线程安全
            with open(self.result_file, 'a') as f:  # 确保以追加模式打开文件
                for result in batch:
                    f.write(json.dumps(result) + '\n')  # 每行写入一条 JSON 数据

    def get_results(self):
        """返回结果文件路径"""
        return self.result_file

    def stop(self):
        """设置停止标志位"""
        self.stop_flag = True

    def get_status(self):
        """获取当前扫描状态"""
        return self.stop_flag
    
    