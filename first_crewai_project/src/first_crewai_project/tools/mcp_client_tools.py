"""
MCP客户端 - 完全修复版，修正405错误
"""

import asyncio
import aiohttp
import json
import sys
import os
import traceback

class MCPClient:
    """MCP客户端，通过HTTP连接到远程MCP服务器"""

    def __init__(self, server_type="ops"):
        self.server_type = server_type
        self.base_url = None
        self.tools = {}

        self.servers = {
            "ops": {
                "name": "运维服务器",
                "port": 3000
            },
            "monitor": {
                "name": "监控服务器",
                "port": 3001
            }
        }

    async def connect(self):
        """连接到MCP服务器"""
        try:
            server_config = self.servers[self.server_type]
            self.base_url = f"http://localhost:{server_config['port']}"

            print(f"🔗 正在连接到{server_config['name']} ({self.base_url})...", file=sys.stderr)

            # 测试连接 - 只使用 GET 请求
            async with aiohttp.ClientSession() as session:
                # 1. 首先测试根路径
                try:
                    print("   1. 测试 GET / ...", file=sys.stderr)
                    async with session.get(self.base_url) as response:
                        print(f"     状态码: {response.status}", file=sys.stderr)
                        if response.status == 200:
                            data = await response.json()
                            print(f"     响应: {data}", file=sys.stderr)

                            # 从根路径获取工具名称列表
                            if "tools" in data:
                                for tool_name in data["tools"]:
                                    self.tools[tool_name] = {"name": tool_name}
                                print(f"✅ 从根路径获取到 {len(self.tools)} 个工具", file=sys.stderr)
                                return True
                except Exception as e:
                    print(f"     GET / 失败: {e}", file=sys.stderr)

                # 2. 如果没有获取到工具，尝试 /tools/list
                if not self.tools:
                    try:
                        print("   2. 尝试 GET /tools/list ...", file=sys.stderr)
                        async with session.get(f"{self.base_url}/tools/list") as response:
                            print(f"     状态码: {response.status}", file=sys.stderr)
                            if response.status == 200:
                                data = await response.json()
                                print(f"     响应: {data}", file=sys.stderr)

                                if "tools" in data:
                                    for tool in data["tools"]:
                                        self.tools[tool["name"]] = tool
                                    print(f"✅ 从/tools/list获取到 {len(self.tools)} 个工具", file=sys.stderr)
                                    return True
                    except Exception as e:
                        print(f"     GET /tools/list 失败: {e}", file=sys.stderr)

                # 3. 如果以上都失败，使用预设的工具列表
                print("   3. 使用预设工具列表...", file=sys.stderr)
                if self.server_type == "ops":
                    self.tools = {
                        "get_nginx_servers": {},
                        "get_server_logs_simple": {},
                        "get_mysql_logs_simple": {},
                        "mysql_runtime_diagnosis": {},
                        "get_redis_logs_simple": {}
                    }
                else:
                    self.tools = {
                        "get_nginx_servers": {},
                        "get_server_metrics_simple": {}
                    }

                print(f"✅ 使用预设工具列表: {list(self.tools.keys())}", file=sys.stderr)
                return True

        except Exception as e:
            print(f"❌ 连接失败: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

            # 如果连接失败，使用预设的工具列表
            if self.server_type == "ops":
                self.tools = {
                    "get_nginx_servers": {},
                    "get_server_logs_simple": {},
                    "get_mysql_logs_simple": {},
                    "mysql_runtime_diagnosis": {},
                    "get_redis_logs_simple": {}
                }
            else:
                self.tools = {
                    "get_nginx_servers": {},
                    "get_server_metrics_simple": {}
                }
            print(f"⚠️  使用离线工具列表: {list(self.tools.keys())}", file=sys.stderr)
            return True

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """调用远程工具"""
        if not self.tools:
            await self.connect()

        if tool_name not in self.tools:
            print(f"❌ 工具 '{tool_name}' 不存在", file=sys.stderr)
            return {"error": f"工具 '{tool_name}' 不存在"}

        try:
            print(f"🛠️  调用工具: {tool_name}", file=sys.stderr)
            print(f"   参数: {arguments}", file=sys.stderr)

            async with aiohttp.ClientSession() as session:
                # 根据服务器代码，我们需要发送 POST 请求到 /tools/call
                url = f"{self.base_url}/tools/call"
                payload = {
                    "tool_name": tool_name,
                    "arguments": arguments or {}
                }

                print(f"   请求URL: {url}", file=sys.stderr)
                print(f"   请求数据: {json.dumps(payload, indent=2)}", file=sys.stderr)

                async with session.post(url, json=payload) as response:
                    print(f"   响应状态码: {response.status}", file=sys.stderr)

                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ 工具调用成功", file=sys.stderr)
                        print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...", file=sys.stderr)

                        if "result" in result:
                            return json.dumps(result["result"], ensure_ascii=False, indent=2)
                        else:
                            return json.dumps(result, ensure_ascii=False, indent=2)
                    else:
                        error_text = await response.text()
                        print(f"❌ HTTP错误: {response.status}", file=sys.stderr)
                        print(f"   错误详情: {error_text[:200]}", file=sys.stderr)
                        return {
                            "error": f"HTTP错误: {response.status}",
                            "details": error_text[:500]
                        }

        except Exception as e:
            print(f"❌ 工具调用失败: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"error": str(e)}

# 创建全局客户端实例
ops_client = None
monitor_client = None

async def init_clients():
    """初始化客户端连接"""
    global ops_client, monitor_client

    print("🔄 初始化MCP客户端连接...", file=sys.stderr)

    # 连接到运维服务器
    ops_client = MCPClient("ops")
    ops_success = await ops_client.connect()

    # 连接到监控服务器
    monitor_client = MCPClient("monitor")
    monitor_success = await monitor_client.connect()

    if ops_success and monitor_success:
        print("✅ MCP客户端初始化完成", file=sys.stderr)
    else:
        print("⚠️  MCP客户端部分初始化失败", file=sys.stderr)

# 同步包装函数（供CrewAI使用）
from crewai.tools import tool

@tool("获取Nginx服务器列表")
def get_nginx_servers():
    """获取所有Nginx服务器的IP地址和基本信息。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(ops_client.call_tool("get_nginx_servers", {}))
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()

@tool("获取服务器日志")
def get_server_logs(server_ip: str, api_endpoint: str = None, keywords=None):
    """获取指定服务器的Nginx日志。"""
    arguments = {"server_ip": server_ip}
    if api_endpoint:
        arguments["api_endpoint"] = api_endpoint
    if keywords:
        arguments["keywords"] = keywords

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(ops_client.call_tool("get_server_logs_simple", arguments))
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()

@tool("获取MySQL日志")
def get_mysql_logs_simple(server_ip: str, keywords: str = "", min_duration_s: float = 0.0):
    """获取MySQL日志。"""
    arguments = {
        "server_ip": server_ip,
        "keywords": keywords,
        "min_duration_s": min_duration_s
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(ops_client.call_tool("get_mysql_logs_simple", arguments))
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()

@tool("获取服务器指标")
def get_server_metrics(server_ip: str, metric_name: str = None):
    """获取服务器性能指标。"""
    arguments = {"server_ip": server_ip}
    if metric_name:
        arguments["metric_name"] = metric_name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(monitor_client.call_tool("get_server_metrics_simple", arguments))
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()


# 添加缺失的工具函数

@tool("获取Redis日志")
def get_redis_logs_simple(server_ip: str, keywords=None, min_duration=None):
    """获取Redis日志。"""
    arguments = {"server_ip": server_ip}
    if keywords:
        arguments["keywords"] = keywords
    if min_duration is not None:
        arguments["min_duration"] = min_duration

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(ops_client.call_tool("get_redis_logs_simple", arguments))
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()


@tool("MySQL运行时诊断")
def mysql_runtime_diagnosis(server_ip: str, action: str):
    """MySQL运行时诊断。"""
    arguments = {
        "server_ip": server_ip,
        "action": action
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(ops_client.call_tool("mysql_runtime_diagnosis", arguments))
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()
# 初始化客户端连接
print("🚀 正在启动MCP客户端...", file=sys.stderr)
try:
    # 安装必要的依赖
    try:
        import aiohttp
    except ImportError:
        print("📦 安装aiohttp...", file=sys.stderr)
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        import aiohttp

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_clients())
    print("✅ MCP客户端启动成功", file=sys.stderr)
except Exception as e:
    print(f"❌ MCP客户端启动失败: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)