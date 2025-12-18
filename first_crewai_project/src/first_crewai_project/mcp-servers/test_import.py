#!/usr/bin/env python3
"""
测试 Tool 对象的调用方式
"""

import os
import sys

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(project_root)

from tools.mock_tools import get_nginx_servers

print(f"📦 Tool 对象类型: {type(get_nginx_servers)}")
print(f"🔍 Tool 对象属性: {[attr for attr in dir(get_nginx_servers) if not attr.startswith('_')]}")

# 尝试不同调用方式
print("\n🔧 尝试调用方式1: 直接调用")
try:
    result = get_nginx_servers()
    print(f"✅ 方式1成功！结果类型: {type(result)}")
except Exception as e:
    print(f"❌ 方式1失败: {e}")

print("\n🔧 尝试调用方式2: 使用 .function 属性")
try:
    result = get_nginx_servers.function()
    print(f"✅ 方式2成功！结果类型: {type(result)}")
except Exception as e:
    print(f"❌ 方式2失败: {e}")

print("\n🔧 尝试调用方式3: 使用 .run 方法")
try:
    result = get_nginx_servers.run()
    print(f"✅ 方式3成功！结果类型: {type(result)}")
except Exception as e:
    print(f"❌ 方式3失败: {e}")

print("\n🔧 尝试调用方式4: 检查是否可调用")
try:
    if callable(get_nginx_servers):
        result = get_nginx_servers()
        print(f"✅ 方式4成功！结果类型: {type(result)}")
    else:
        print("❌ Tool 对象不可直接调用")
except Exception as e:
    print(f"❌ 方式4失败: {e}")