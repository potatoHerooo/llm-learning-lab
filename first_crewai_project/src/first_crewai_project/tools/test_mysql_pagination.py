#!/usr/bin/env python3
"""
简化版 MySQL 日志工具测试脚本
直接使用 .func 属性调用工具函数
"""

import sys
import os
from datetime import datetime, timedelta

# 添加路径以便导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mock_tools import get_mysql_logs_simple


def test_simple_call():
    """最简单的测试调用"""
    print("🧪 测试简单调用")
    print("=" * 60)

    try:
        # 使用 .func 属性调用原始函数
        logs, next_start = get_mysql_logs_simple.func(
            server_ip="10.0.3.101",
            limit=5
        )

        print(f"✅ 成功获取 {len(logs)} 条日志")
        for i, log in enumerate(logs):
            print(f"  {i + 1}. [{log['severity']}] {log['timestamp']} - {log['operation'][:50]}...")

        print(f"下一页起始时间: {next_start}")
        return True
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pagination():
    """测试分页功能"""
    print("\n📄 测试分页功能")
    print("=" * 60)

    try:
        # 第一次拉取
        logs1, next_start = get_mysql_logs_simple.func(
            server_ip="10.0.3.101",
            limit=3
        )

        print(f"第一次拉取 {len(logs1)} 条日志")
        print(f"下一页起始时间: {next_start}")

        if next_start:
            # 第二次拉取
            logs2, next_start2 = get_mysql_logs_simple.func(
                server_ip="10.0.3.101",
                start_time=next_start,
                limit=3
            )

            print(f"第二次拉取 {len(logs2)} 条日志")
            print(f"新的下一页起始时间: {next_start2}")

            # 检查是否有重复
            timestamps1 = {log['timestamp'] for log in logs1}
            timestamps2 = {log['timestamp'] for log in logs2}
            duplicates = timestamps1 & timestamps2

            if duplicates:
                print(f"⚠️ 警告: 发现 {len(duplicates)} 个重复时间戳")
            else:
                print("✅ 分页正常，无重复日志")
        else:
            print("第一页就已经没有下一页了")

        return True
    except Exception as e:
        print(f"❌ 分页测试失败: {e}")
        return False


def test_time_filter():
    """测试时间过滤"""
    print("\n⏰ 测试时间过滤")
    print("=" * 60)

    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)

        logs, _ = get_mysql_logs_simple.func(
            server_ip="10.0.3.101",
            start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            limit=5
        )

        print(f"在10分钟时间窗内获取到 {len(logs)} 条日志")

        if logs:
            for log in logs[:3]:
                print(f"  • {log['timestamp']} [{log['severity']}]")

        return True
    except Exception as e:
        print(f"❌ 时间过滤测试失败: {e}")
        return False


def test_keyword_filter():
    """测试关键词过滤"""
    print("\n🔍 测试关键词过滤")
    print("=" * 60)

    try:
        logs, _ = get_mysql_logs_simple.func(
            server_ip="10.0.3.101",
            keywords="SELECT",
            limit=5
        )

        print(f"关键词'SELECT'过滤后获取到 {len(logs)} 条日志")

        if logs:
            for log in logs[:3]:
                print(f"  • {log['operation'][:60]}...")

        return True
    except Exception as e:
        print(f"❌ 关键词过滤测试失败: {e}")
        return False


def test_slow_query_filter():
    """测试慢查询过滤"""
    print("\n🐌 测试慢查询过滤")
    print("=" * 60)

    try:
        logs, _ = get_mysql_logs_simple.func(
            server_ip="10.0.3.101",
            min_duration_s=2.0,
            limit=5
        )

        print(f"耗时>2秒的慢查询: {len(logs)} 条")

        if logs:
            for log in logs:
                duration_s = log['latency_ms'] / 1000
                print(f"  • {duration_s:.2f}s - {log['operation'][:40]}...")

        return True
    except Exception as e:
        print(f"❌ 慢查询过滤测试失败: {e}")
        return False


def test_invalid_server():
    """测试无效服务器"""
    print("\n❌ 测试无效服务器")
    print("=" * 60)

    try:
        logs, next_start = get_mysql_logs_simple.func(
            server_ip="999.999.999.999",  # 无效IP
            limit=3
        )

        print(f"无效服务器获取到 {len(logs)} 条日志")
        print(f"注意: 即使服务器IP无效，模拟数据生成器可能仍然会生成数据")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def simulate_agent_scenario():
    """模拟智能体使用场景"""
    print("\n🤖 模拟智能体使用场景")
    print("=" * 60)

    print("场景: 智能体调查数据库性能问题")

    # 步骤1: 查找慢查询
    print("\n步骤1: 查找慢查询...")
    slow_logs, next_start = get_mysql_logs_simple.func(
        server_ip="10.0.3.101",
        min_duration_s=1.0,
        limit=5
    )

    if not slow_logs:
        print("✅ 没有发现慢查询，问题可能不在数据库")
        return

    print(f"发现 {len(slow_logs)} 条慢查询")

    # 步骤2: 检查是否有错误
    error_logs = [log for log in slow_logs if log['severity'] == 'ERROR']
    if error_logs:
        print(f"⚠️ 发现 {len(error_logs)} 条错误日志，需要重点关注")

    # 步骤3: 如果需要更多数据，继续拉取
    if next_start and len(slow_logs) == 5:
        print("\n步骤2: 继续拉取更多慢查询数据...")
        more_logs, _ = get_mysql_logs_simple.func(
            server_ip="10.0.3.101",
            start_time=next_start,
            min_duration_s=1.0,
            limit=5
        )

        if more_logs:
            print(f"再获取 {len(more_logs)} 条慢查询")
            slow_logs.extend(more_logs)

    print(f"\n📊 分析完成: 总共分析 {len(slow_logs)} 条慢查询日志")

    # 按严重级别统计
    from collections import Counter
    severity_counts = Counter(log['severity'] for log in slow_logs)

    print("严重级别分布:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count} 条")


def main():
    """主测试函数"""
    print("🚀 MySQL 日志工具功能测试")
    print("=" * 60)

    tests = [
        ("简单调用", test_simple_call),
        ("分页功能", test_pagination),
        ("时间过滤", test_time_filter),
        ("关键词过滤", test_keyword_filter),
        ("慢查询过滤", test_slow_query_filter),
        ("智能体场景", simulate_agent_scenario),
    ]

    passed_tests = 0
    total_tests = len(tests) - 1  # 智能体场景不算在通过/失败中

    for test_name, test_func in tests:
        if test_name == "智能体场景":
            test_func()  # 智能体场景不参与通过/失败计数
        else:
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✅ {test_name} 测试通过\n")
                else:
                    print(f"❌ {test_name} 测试失败\n")
            except Exception as e:
                print(f"❌ {test_name} 测试异常: {e}\n")

    print("=" * 60)
    print(f"📊 测试总结: {passed_tests}/{total_tests} 个测试通过")

    if passed_tests == total_tests:
        print("✅ 所有测试通过！你的MySQL日志工具功能正常")
    else:
        print("⚠️ 部分测试失败，请检查工具实现")


if __name__ == "__main__":
    main()