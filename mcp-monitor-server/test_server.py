import subprocess
import json
import time
import sys


def test_server_connection():
    """测试 MCP 服务器连接"""
    print("启动服务器进程...")

    # 启动服务器进程
    server_process = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # 等待服务器启动
    time.sleep(2)

    # 发送 MCP 初始化请求
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "TestClient",
                "version": "1.0.0"
            }
        }
    }

    print("发送初始化请求...")
    server_process.stdin.write(json.dumps(init_request) + "\n")
    server_process.stdin.flush()

    # 读取响应
    time.sleep(1)
    try:
        while True:
            line = server_process.stdout.readline()
            if line:
                print(f"收到响应: {line}")
            else:
                break
    except:
        pass

    # 清理
    server_process.terminate()
    server_process.wait()
    print("测试完成")


if __name__ == "__main__":
    test_server_connection()