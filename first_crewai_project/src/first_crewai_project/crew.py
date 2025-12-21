#!/usr/bin/env python3
import os
import sys
import time
from functools import wraps

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from dotenv import load_dotenv

from tools.mcp_client_tools import (
    get_nginx_servers,
    get_server_logs,
    get_server_metrics,
    get_mysql_logs_simple,
    get_redis_logs_simple,
    mysql_runtime_diagnosis,
    search_code_in_repository,
    get_code_context,
    analyze_code_pattern
)

load_dotenv()


def timeit(func):
    """执行时间装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"\n⏱️  总执行时间: {time.time() - start:.2f}秒")
        return result

    return wrapper


class FaultDiagnosisCrew:
    """故障诊断智能体团队"""

    def __init__(self, api_endpoint: str, metrics_to_analyze: list[str], log_keywords: list[str] = None):
        self.api_endpoint = api_endpoint
        self.metrics_to_analyze = metrics_to_analyze
        self.log_keywords = log_keywords

        # 修复：简化LLM配置，移除不支持的参数
        self.llm = LLM(
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0.7,
        )

        # 创建智能体
        self.log_analyst = self.create_log_analyst()
        self.mysql_analyst = self.create_mysql_analyst()
        self.redis_analyst = self.create_redis_analyst()
        self.metrics_inspector = self.create_metrics_inspector()
        self.code_analyst = self.create_code_analyst()
        self.root_cause_diagnostician = self.create_root_cause_diagnostician()

        # 创建任务
        self._create_tasks()

    def create_log_analyst(self) -> Agent:
        return Agent(
            role="服务器日志分析专家",
            goal=f"从Nginx日志中提取与 {self.api_endpoint} 相关的错误请求、响应码、异常关键词和延迟模式",
            backstory="你是一个日志分析大师，擅长从复杂日志中发现隐藏异常。",
            llm=self.llm,
            tools=[get_nginx_servers, get_server_logs],
            verbose=True,
            allow_delegation=False
        )

    def create_mysql_analyst(self) -> Agent:
        return Agent(
            role="MySQL数据库日志分析专家",
            goal="分析MySQL日志，识别数据库层面的性能瓶颈与异常行为。",
            backstory="你是数据库性能专家，熟悉MySQL慢查询、死锁、错误日志。",
            llm=self.llm,
            tools=[get_mysql_logs_simple, mysql_runtime_diagnosis],
            verbose=True,
            allow_delegation=False
        )

    def create_redis_analyst(self) -> Agent:
        return Agent(
            role="Redis缓存日志分析专家",
            goal="分析Redis日志，找出异常命令、慢查询、错误、超时等。",
            backstory="你是Redis性能专家，熟悉Redis日志分析。",
            llm=self.llm,
            tools=[get_redis_logs_simple],
            verbose=True,
            allow_delegation=False
        )

    def create_metrics_inspector(self) -> Agent:
        if not self.metrics_to_analyze:
            self.metrics_to_analyze = ["cpu", "memory", "成功率", "延迟"]
        return Agent(
            role="服务器指标分析专家",
            goal=f"分析 {self.api_endpoint} 接口的性能指标，找出异常规律。",
            backstory="你擅长监控分析，能观察成功率、延迟、资源使用之间的关联性。",
            llm=self.llm,
            tools=[get_nginx_servers, get_server_metrics],
            verbose=True,
            allow_delegation=False
        )

    def create_code_analyst(self) -> Agent:
        return Agent(
            role="源代码分析专家",
            goal="根据线索定位源代码文件，分析代码层面的根本原因",
            backstory="你是资深代码审查专家，擅长通过代码静态分析找到性能问题。",
            llm=self.llm,
            tools=[search_code_in_repository, get_code_context, analyze_code_pattern],
            verbose=True,
            allow_delegation=False
        )

    def create_root_cause_diagnostician(self) -> Agent:
        return Agent(
            role="根因诊断官",
            goal=f"综合所有分析结果，推断导致 {self.api_endpoint} 异常的根本原因。",
            backstory="你擅长将零散线索组合成完整链路，得出合理推断。",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def _create_tasks(self):
        """创建六个任务"""

        # 任务 1：日志分析
        self.log_research_task = Task(
            description=(
                f"{self.api_endpoint} 接口出现异常访问现象。\n"
                f"你可以使用你拥有的工具来获取相关信息。\n"
                f"请分析服务器日志，关注异常响应码、超时和错误。"
            ),
            expected_output=(
                "日志分析总结：异常现象、关键证据、可能的问题。"
            ),
            agent=self.log_analyst,
            verbose=True,
        )

        # 任务 2：指标分析
        self.metrics_research_task = Task(
            description=(
                f"{self.api_endpoint}接口出现异常访问现象。\n"
                f"你可以使用你拥有的工具来获取相关信息\n"
                f"请分析服务器指标，关注CPU、成功率等关键指标。"
            ),
            expected_output=(
                "指标分析总结：异常现象、关键证据、可能的问题。"
            ),
            agent=self.metrics_inspector,
            verbose=True,
        )

        # 任务 3：MySQL分析
        self.mysql_log_task = Task(
            description=(
                f"{self.api_endpoint}接口出现异常访问现象。\n"
                f"你可以使用你拥有的工具来获取相关信息\n"
                f"请分析MySQL日志，关注慢查询、死锁和错误。"
            ),
            expected_output=(
                "MySQL分析报告：异常SQL类型、慢查询、死锁分析。"
            ),
            agent=self.mysql_analyst,
            verbose=True,
        )

        # 任务 4：Redis分析
        self.redis_log_task = Task(
            description=(
                "请分析Redis日志，找出异常命令、慢查询、错误、超时等。\n"
                "使用 get_redis_logs_simple 工具。"
            ),
            expected_output=(
                "Redis缓存层分析报告：慢查询、异常命令、错误类型。"
            ),
            agent=self.redis_analyst,
            verbose=True,
        )

        # 任务 5：代码分析
        self.code_analysis_task = Task(
            description=(
                f"基于前面的发现，从代码层面深入分析 {self.api_endpoint} 接口的问题。\n"
                f"搜索相关代码文件，分析潜在问题。"
            ),
            expected_output=(
                "代码分析报告：关键代码文件、发现的代码问题、具体位置和原因。"
            ),
            agent=self.code_analyst,
            verbose=True,
        )

        # 任务 6：根因诊断
        self.root_case_task = Task(
            description=(
                "综合所有分析结果，给出最可能的根因解释。\n"
                "不需要调用任何工具，基于已有的分析结果进行综合判断。"
            ),
            expected_output=(
                "根因分析报告：最可能的根因、关键证据、修复建议。"
            ),
            agent=self.root_cause_diagnostician,
            verbose=True
        )

    @timeit
    def assemble_and_run(self):
        """完整版本 - 顺序执行"""
        print(f"🔍 开始故障诊断分析...")
        print(f"目标接口: {self.api_endpoint}")
        print(f"指定指标: {self.metrics_to_analyze}")
        print(f"日志关键词: {self.log_keywords}")

        # 使用单个Crew顺序执行所有任务
        agents = [
            self.log_analyst,
            self.metrics_inspector,
            self.mysql_analyst,
            self.redis_analyst,
            self.code_analyst,
            self.root_cause_diagnostician
        ]

        tasks = [
            self.log_research_task,
            self.metrics_research_task,
            self.mysql_log_task,
            self.redis_log_task,
            self.code_analysis_task,
            self.root_case_task
        ]

        print("\n🤖 智能体团队配置完成:")
        for agent in agents:
            print(f"  • {agent.role}")

        print("-" * 50)

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        print("🚀 启动智能体团队...")
        result = crew.kickoff()

        print("\n" + "=" * 60)
        print("✅ 诊断完成！")
        print("=" * 60)

        return result

    def quick_demo(self):
        """快速演示模式（汇报时用）- 只运行前2个任务"""
        print("🚀 快速演示模式启动...")

        demo_crew = Crew(
            agents=[self.log_analyst, self.metrics_inspector],
            tasks=[self.log_research_task, self.metrics_research_task],
            process=Process.sequential,
            verbose=True,
        )

        return demo_crew.kickoff()


# -------------------- 主程序入口 --------------------
if __name__ == "__main__":
    api_to_diagnose = "/api/v2/data.json"
    critical_metrics = ["cpu", "成功率"]
    keywords_to_search = ["timeout", "502", "error"]

    diagnosis_crew = FaultDiagnosisCrew(
        api_endpoint=api_to_diagnose,
        metrics_to_analyze=critical_metrics,
        log_keywords=keywords_to_search
    )

    try:
        # 先运行快速演示，确保基础功能正常
        # print("🎯 运行快速演示模式（测试基础功能）...")
        # demo_result = diagnosis_crew.quick_demo()
        #
        # print("\n📋 演示结果:")
        # print("-" * 40)
        # print(demo_result)
        #
        # # 询问是否继续完整版
        # print("\n" + "=" * 60)
        # choice = input("✅ 演示完成！是否继续运行完整版诊断？(y/n): ")

        # if choice.lower() == 'y':
            print("🎯 运行完整版诊断...")
            final_result = diagnosis_crew.assemble_and_run()

            print("\n📋 完整诊断结果:")
            print("-" * 40)
            print(final_result)
        # else:
            print("👋 结束运行。")

    except Exception as e:
        print(f"❌ 运行时出现错误: {e}")
        import traceback

        traceback.print_exc()

    finally:
        time.sleep(1)
        print("\n✅ 程序执行完成")
        sys.exit(0)