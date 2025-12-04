#!/usr/bin/env python3
"""
故障诊断系统测试脚本
测试完整的诊断流程
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.mock_tools import (
    get_nginx_servers,
    get_server_logs,
    get_server_metrics
)


def test_tools_individually():
    """单独测试每个工具"""
    print("=" * 60)
    print("🧪 开始测试模拟工具")
    print("=" * 60)

    # 测试1: 获取服务器列表
    print("\n1. 测试获取服务器列表:")
    servers = get_nginx_servers()
    print(f"   返回了 {len(servers)} 台服务器")

    # 测试2: 获取问题服务器的日志
    print("\n2. 测试获取服务器日志:")
    problem_server = next((s for s in servers if s['status'] == 'degraded'), servers[0])
    logs = get_server_logs(problem_server['ip'], 30)
    print(f"   从 {problem_server['ip']} 获取了 {len(logs)} 条日志")

    # 检查错误日志
    error_logs = [log for log in logs if '" 5' in log or '" 4' in log]
    print(f"   其中包含 {len(error_logs)} 条错误日志 (4xx/5xx)")

    # 显示一些错误日志示例
    if error_logs:
        print("\n   错误日志示例:")
        for i, log in enumerate(error_logs[:3]):
            print(f"   {i + 1}. {log}")

    # 测试3: 获取服务器指标
    print("\n3. 测试获取服务器指标:")
    metrics = get_server_metrics(problem_server['ip'], 30)
    print(f"   服务器 {problem_server['ip']} 的成功率: {metrics['success_rate']:.1%}")

    # 总结
    print("\n" + "=" * 60)
    print("✅ 工具测试完成!")
    print("=" * 60)
    return servers, logs, metrics


def test_full_diagnosis_scenario():
    """测试完整的诊断场景"""
    print("\n" + "=" * 60)
    print("🔍 模拟完整故障诊断场景")
    print("=" * 60)

    # 模拟问题参数
    problematic_api = "/api/v2/data.json"

    print(f"\n📋 问题描述: 监控发现 {problematic_api} 的成功率降低")

    # 1. 获取所有服务器
    print("\n📡 步骤1: 获取所有Nginx服务器...")
    servers = get_nginx_servers()

    # 2. 分析每台服务器的日志
    print("\n📊 步骤2: 分析服务器日志...")
    all_error_logs = []

    for server in servers:
        print(f"\n  分析服务器 {server['ip']} ({server['hostname']})...")
        logs = get_server_logs(server['ip'], 60)

        # 过滤出问题API的日志
        api_logs = [log for log in logs if problematic_api in log]
        error_api_logs = [log for log in api_logs if any(f'"{code} ' in log for code in ['5', '4'])]

        print(f"    找到 {len(api_logs)} 条 {problematic_api} 相关日志")
        print(f"    其中 {len(error_api_logs)} 条是错误日志")

        all_error_logs.extend(error_api_logs)

    # 3. 分析问题服务器的指标
    print("\n📈 步骤3: 分析服务器指标...")
    problem_server = next((s for s in servers if s['status'] == 'degraded'), None)
    metrics = None

    if problem_server:
        print(f"\n  重点分析问题服务器 {problem_server['ip']}:")
        metrics = get_server_metrics(problem_server['ip'], 60)

        print(f"\n  📉 发现异常指标:")
        if metrics['success_rate'] < 0.9:
            print(f"    ✗ 成功率过低: {metrics['success_rate']:.1%}")
        if metrics['avg_latency_ms'] > 500:
            print(f"    ✗ 延迟过高: {metrics['avg_latency_ms']:.1f}ms")
        if metrics['cpu_percent'] > 80:
            print(f"    ✗ CPU使用率过高: {metrics['cpu_percent']:.1f}%")

    # 4. 生成诊断报告
    print("\n📋 步骤4: 生成诊断报告...")

    # 模拟日志分析结果
    log_analysis = f"""
## 日志分析发现
- 总共发现 {len(all_error_logs)} 条关于 {problematic_api} 的错误日志
- 主要错误类型: 502 Bad Gateway (占{len([l for l in all_error_logs if ' 502 ' in l])}条)
- 错误时间集中在最近30分钟内
- 主要来自服务器: {problem_server['ip'] if problem_server else '未知'}
"""

    # 修复：使用条件判断代替复杂的f-string内嵌条件表达式
    if problem_server and metrics:
        metrics_analysis = f"""
## 指标分析发现
- 服务器 {problem_server['ip']} 成功率下降至 {metrics['success_rate']:.1%}
- 平均延迟增至 {metrics['avg_latency_ms']:.1f}ms
- CPU使用率达到 {metrics['cpu_percent']:.1f}%
- 内存使用率: {metrics['memory_percent']:.1f}%
"""
    else:
        metrics_analysis = """
## 指标分析发现
- 未发现明显指标异常，或问题服务器未确定。
"""

    print("\n" + "=" * 60)
    print("📄 诊断报告摘要")
    print("=" * 60)
    print(log_analysis)
    print(metrics_analysis)
    print("\n🔍 可能的原因:")
    print("1. 后端服务过载或崩溃")
    print("2. 数据库连接池耗尽")
    print("3. 网络分区或下游服务故障")
    print("4. 最近部署的代码有bug")

    return {
        "api_endpoint": problematic_api,
        "total_servers": len(servers),
        "error_logs_count": len(all_error_logs),
        "problem_server": problem_server['ip'] if problem_server else None,
        "success_rate": metrics['success_rate'] if metrics else None
    }

if __name__ == "__main__":
    print("🚀 故障诊断系统测试套件")
    print("=" * 60)

    # 测试1: 单独测试工具
    test_tools_individually()

    # 测试2: 完整诊断场景
    print("\n\n")
    results = test_full_diagnosis_scenario()

    print("\n" + "=" * 60)
    print("🎯 测试总结")
    print("=" * 60)
    print(f"目标API: {results['api_endpoint']}")
    print(f"扫描服务器: {results['total_servers']}台")
    print(f"发现错误日志: {results['error_logs_count']}条")
    print(f"问题服务器: {results['problem_server'] or '未确定'}")
    if results['success_rate']:
        print(f"问题服务器成功率: {results['success_rate']:.1%}")

    print("\n✅ 所有测试完成！")
    print("现在可以将这些工具集成到你的CrewAI智能体中。")