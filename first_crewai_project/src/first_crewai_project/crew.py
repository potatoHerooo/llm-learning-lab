#!/usr/bin/env python3
import os
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from dotenv import load_dotenv

# 导入工具函数（保持原来）
from tools.mcp_client_tools import (
    get_nginx_servers,
    get_server_logs,
    get_server_metrics,
    get_mysql_logs_simple,
    get_redis_logs_simple,
)

load_dotenv()


class FaultDiagnosisCrew:
    """故障诊断智能体团队 (树状并行结构)"""

    def __init__(self, api_endpoint: str, metrics_to_analyze: list[str], log_keywords: list[str] = None):
        self.api_endpoint = api_endpoint
        self.metrics_to_analyze = metrics_to_analyze
        self.log_keywords = log_keywords  # ★ 新增：把关键词传入整个系统

        self.llm = LLM(
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0.7
        )

        # 创建智能体
        self.log_analyst = self.create_log_analyst()    #nginx日志专家
        self.mysql_analyst = self.create_mysql_analyst()    #SQL日志专家
        self.redis_analyst = self.create_redis_analyst()    #Redis日志分析专家
        self.metrics_inspector = self.create_metrics_inspector()
        self.root_cause_diagnostician = self.create_root_cause_diagnostician()

        # 创建任务
        self.log_research_task = None
        self.metrics_research_task = None
        self.root_case_task = None

        self._create_tasks()

    # -------------------- Agent：Nginx日志分析 --------------------
    def create_log_analyst(self) -> Agent:
        return Agent(
            role="服务器日志分析专家",
            goal=f"从Nginx日志中提取与 {self.api_endpoint} 相关的错误请求、响应码、异常关键词和延迟模式",
            backstory="你是一个日志分析大师，擅长从复杂日志中发现隐藏异常，包括状态码错误、慢请求、超时以及关键词报警。",
            llm=self.llm,
            # 使用新的 MCP 客户端工具
            tools=[get_nginx_servers, get_server_logs],
            verbose=True,
            allow_delegation=False
        )

    # -------------------- Agent：SQL日志分析 --------------------
    def create_mysql_analyst(self) -> Agent:
        return Agent(
            role="MySQL数据库日志分析专家",
            goal="分析 MySQL 日志（Slow Query / Deadlock / Error），识别数据库层面的性能瓶颈与异常行为。",
            backstory="你是数据库性能专家，熟悉 MySQL 慢查询、死锁、错误日志，能够定位数据库作为系统瓶颈的证据。",
            llm=self.llm,
            tools=[get_mysql_logs_simple],
            verbose=True,
            allow_delegation=False
        )

    # -------------------- Agent：Redis日志分析 --------------------
    def create_redis_analyst(self) -> Agent:
        return Agent(
            role="Redis缓存日志分析专家",
            goal="分析 Redis 慢查询、错误、超时，判断缓存层是否导致系统性能下降。",
            backstory="你擅长分析 Redis slowlog、错误日志和命令异常，帮助定位缓存层瓶颈。",
            llm=self.llm,
            tools=[get_redis_logs_simple],
            verbose=True,
            allow_delegation=False
        )

    # -------------------- Agent：指标分析 --------------------
    def create_metrics_inspector(self) -> Agent:
        if not self.metrics_to_analyze:
            self.metrics_to_analyze = ["cpu", "memory", "成功率", "延迟"]
        metrics_desc = "、".join(self.metrics_to_analyze)
        return Agent(
            role="服务器指标分析专家",
            goal=f"分析 {self.api_endpoint} 接口的 {metrics_desc} 关键性能指标，找出异常规律。",
            backstory="你擅长监控分析，能观察成功率、延迟、资源使用之间的关联性。",
            llm=self.llm,
            tools=[get_nginx_servers, get_server_metrics],
            verbose=True,
            allow_delegation=False
        )

    # -------------------- Agent：根因诊断 --------------------
    def create_root_cause_diagnostician(self) -> Agent:
        return Agent(
            role="根因诊断官",
            goal=f"综合日志与指标分析结果，推断导致 {self.api_endpoint} 异常的根本原因。",
            backstory="你擅长将零散线索组合成完整链路，得出合理推断。",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    # -------------------- 任务定义 --------------------
    def _create_tasks(self):
        """创建五个任务"""

        keyword_hint = ""
        if self.log_keywords:
            keyword_hint = f"\n6. 并且使用关键词过滤日志：{self.log_keywords}\n"

        # 任务 1：日志分析
        self.log_research_task = Task(
            description=(
                f"{self.api_endpoint} 接口出现异常访问现象。\n"
                f"你可以使用你拥有的工具来获取相关信息。\n\n"
                f"请你自行判断是否需要：\n"
                f"- 查看服务器层面的访问日志\n"
                f"- 关注异常响应、错误状态码或异常请求模式\n"
                f"- 基于日志线索进行进一步推断\n\n"
                f"请基于你获取的信息，总结你认为重要的异常现象和线索。\n"
                "如果你发现已有信息不足以支持你的判断，你可以再次调用你认为有帮助的工具进行验证"

            ),
            expected_output=(
                "一份日志分析总结，包含：异常现象描述、关键证据、"
                "以及这些证据可能说明的问题。"
            ),
            agent=self.log_analyst,
            verbose=True,
        )

        # 任务 2：指标分析
        self.metrics_research_task = Task(
            description=(
                f"{self.api_endpoint}接口出现异常访问现象。\n"
                f"你可以使用你拥有的工具来获取相关信息\n"
                f"请你自行判断：\n"
                f"- 是否使用相关工具获取所有服务器然后去拉取相关服务器指标\n"
                f"- 是否需要关注相关指标来分析问题\n"
                f"请基于你获取的信息，总结你认为重要的异常现象和线索。\n"
                "如果你发现已有信息不足以支持你的判断，你可以再次调用你认为有帮助的工具进行验证"
            ),
            expected_output=(
                "一份日志分析总结，包含：你关注的异常现象、"
                "你认为重要的证据，以及这些证据可能说明的问题。"
            ),
            agent=self.metrics_inspector,
            verbose=True,
        )

        # 任务 3：MySQL 日志分析任务
        self.mysql_log_task = Task(
            description=(
                f"{self.api_endpoint}接口出现异常访问现象。\n"
                f"你可以使用你拥有的工具来获取相关信息\n"
                f"请你自行判断：\n"
                f"- 是否需要从数据库层面获取日志辅助分析\n"
                f"- 是否存在可能影响接口性能的慢查询、错误或死锁等异常行为\n"
                f"- 当前已获取的信息是否足以支持你的分析结论\n"
                f"请基于你获取的信息，总结你认为重要的异常现象和线索。\n"
                "如果你发现已有信息不足以支持你的判断，你可以自行采取进一步行动来补充证据"
            ),
            expected_output=(
                "输出 MySQL 日志分析报告，包括：\n"
                "1. 异常 SQL 类型\n"
                "2. 慢查询情况\n"
                "3. 错误与死锁分析\n"
                "4. 与接口异常相关的时间段关联性"
            ),
            agent=self.mysql_analyst,
            verbose=True,
        )

        # 任务 4：Redis日志分析任务
        self.redis_log_task = Task(
            description=(
                "请分析 Redis 日志，找出异常命令、慢查询、错误、超时等。\n"
                "使用 get_redis_logs_simple(server_ip, keywords=可选, min_duration=可选)。\n"
                "输出缓存层瓶颈、热点 key、超时命令等信息。\n"
                "如果你发现已有信息不足以支持你的判断，你可以再次调用你认为有帮助的工具进行验证"
            ),
            expected_output=(
                "Redis 缓存层分析报告，包括：慢查询统计、异常命令、错误类型、"
                "潜在缓存击穿或热点 key 问题。"
            ),
            agent=self.redis_analyst,
            verbose=True,
        )

        # 任务 5：根因诊断
        self.root_case_task = Task(
            description=(
                "你将收到来自多个分析 agent 的信息（日志、指标、数据库、缓存）。\n\n"
                "你的任务是：\n"
                "- 综合这些信息\n"
                "- 判断哪些证据是最关键的\n"
                "- 给出你认为最可能的 1~2 个根因解释\n\n"
                "当你认为现有信息已经足以支持你的判断时，"
                "请直接给出最终分析结论，不需要继续调用任何工具。\n"
                "如果你发现已有信息不足以支持你的判断，你可以再次调用你认为有帮助的工具进行验证"
            ),
            expected_output=(
                "一份根因分析报告，包含：\n"
                "- 最可能的根因（1-2个，不要超过）\n"
                "- 支持该判断的关键证据（明确指出来自哪些分析agent）\n"
                "- 如有不确定性，请明确指出"
            ),
            agent=self.root_cause_diagnostician,
            verbose=True
        )


    # -------------------- Execute --------------------
    def assemble_and_run(self):
        print(f"🔍 开始故障诊断分析...")
        print(f"目标接口: {self.api_endpoint}")
        print(f"指定指标: {self.metrics_to_analyze}")
        print(f"日志关键词: {self.log_keywords}")
        print("-" * 50)

        crew = Crew(
            agents=[
                #self.log_analyst,
                #self.metrics_inspector,
                self.mysql_analyst
                #self.redis_analyst,
                #self.root_cause_diagnostician
            ],
            tasks=[
                #self.log_research_task,
                #self.metrics_research_task,
                self.mysql_log_task,
                #self.redis_log_task,
                #self.root_case_task
            ],
            process=Process.sequential,
            verbose=True,
        )

        print("🚀 启动智能体团队...")
        result = crew.kickoff(inputs={"api_endpoint": self.api_endpoint})

        print("\n" + "=" * 60)
        print("✅ 诊断完成！报告已保存至 diagnosis_report.md")
        print("=" * 60)

        return result


# -------------------- 主程序入口 --------------------
if __name__ == "__main__":
    api_to_diagnose = "/api/v2/data.json"
    #指定指标
    critical_metrics = ["cpu", "成功率"]
    #日志关键词
    keywords_to_search = ["timeout", "502", "error"]

    diagnosis_crew = FaultDiagnosisCrew(
        api_endpoint=api_to_diagnose,
        metrics_to_analyze=critical_metrics,
        log_keywords=keywords_to_search
    )

    try:
        final_result = diagnosis_crew.assemble_and_run()
        print("\n📋 诊断结果摘要:")
        print("-" * 40)
        print(final_result)

    except Exception as e:
        print(f"❌ 运行时出现错误: {e}")
        import traceback

        traceback.print_exc()
