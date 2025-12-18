#!/usr/bin/env python3
"""
测试修复后的 MCP 服务器
"""

import subprocess
import time
import sys
import os


def test_server(script_name, server_name):
    """测试单个服务器"""
    print(f"\n🔍 测试 {server_name} ({script_name})...")

    try:
        # 启动服务器
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # 等待启动
        time.sleep(2)

        # 检查是否还在运行
        if process.poll() is None:
            print(f"  ✅ {server_name} 正常运行")

            # 读取一些输出
            print(f"  📋 {server_name} 输出:")
            for _ in range(3):
                line = process.stderr.readline()
                if line:
                    print(f"    {line.strip()}")

            # 停止进程
            process.terminate()
            process.wait(timeout=2)
            print(f"  🛑 {server_name} 已停止")
            return True
        else:
            # 读取错误信息
            stdout, stderr = process.communicate()
            print(f"  ❌ {server_name} 启动失败")
            print(f"  错误输出:\n{stderr}")
            return False

    except Exception as e:
        print(f"  ❌ 测试 {server_name} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🧪 测试修复后的 MCP 服务器")
    print("=" * 50)

    # 测试运维服务器
    ops_ok = test_server("ops_server.py", "运维服务器")

    # 测试监控服务器
    monitor_ok = test_server("monitor_server.py", "监控服务器")

    # 总结
    print("\n" + "=" * 50)
    if ops_ok and monitor_ok:
        print("🎉 两个服务器都正常运行！")
        print("\n📋 下一步：")
        print("1. 在PyCharm中打开两个终端，分别运行这两个服务器")
        print("2. 配置Claude Desktop连接这两个MCP服务器")
        print("3. 测试Agent是否能同时使用两个服务的工具")
    else:
        print("❌ 测试失败，请检查修复")
        print(f"  运维服务器: {'✅' if ops_ok else '❌'}")
        print(f"  监控服务器: {'✅' if monitor_ok else '❌'}")


if __name__ == "__main__":
    main()