#!/usr/bin/env python3
"""
我的第一个CrewAI项目 - 主入口
"""
import sys
from pathlib import Path

# 将src目录添加到Python路径
sys.path.append(str(Path(__file__).parent))

from crew import MyCrew


def main():
    print("🚀 启动我的第一个CrewAI项目")

    # 创建Crew实例
    my_crew = MyCrew(topic="人工智能在教育领域的应用")

    # 运行并获取结果
    result = my_crew.run()

    # 输出结果
    print("\n" + "=" * 60)
    print("📋 研究成果摘要:")
    print("=" * 60)
    print(result)

    return result


if __name__ == "__main__":
    main()