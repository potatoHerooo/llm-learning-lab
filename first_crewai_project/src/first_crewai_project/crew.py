#!/usr/bin/env python3
import os
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from dotenv import load_dotenv

# 导入工具函数（保持原来）
from tools.mock_tools import (
    get_nginx_servers,
    get_server_logs_simple as get_server_logs,
    get_server_metrics_simple as get_server_metrics
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
        self.log_analyst = self.create_log_analyst()
        self.metrics_inspector = self.create_metrics_inspector()
        self.root_cause_diagnostician = self.create_root_cause_diagnostician()

        # 创建任务
        self.log_research_task = None
        self.metrics_research_task = None
        self.root_case_task = None

        self._create_tasks()

    # -------------------- Agent：日志分析 --------------------
    def create_log_analyst(self) -> Agent:
        return Agent(
            role="服务器日志分析专家",
            goal=f"从Nginx日志中提取与 {self.api_endpoint} 相关的错误请求、响应码、异常关键词和延迟模式",
            backstory="你是一个日志分析大师，擅长从复杂日志中发现隐藏异常，包括状态码错误、慢请求、超时以及关键词报警。",
            llm=self.llm,
            tools=[get_nginx_servers, get_server_logs],
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
        """创建三个任务"""

        keyword_hint = ""
        if self.log_keywords:
            keyword_hint = f"\n6. 并且使用关键词过滤日志：{self.log_keywords}\n"

        # 任务 1：日志分析
        self.log_research_task = Task(
            description=(
                f"请分析 {self.api_endpoint} 接口的Nginx日志。\n"
                f"步骤：\n"
                f"1. 使用 get_nginx_servers() 工具获取所有服务器\n"
                f"2. 对每台服务器使用 get_server_logs() 工具，参数应包括：\n"
                f"    - server_ip=服务器IP\n"
                f"    - api_endpoint='{self.api_endpoint}'\n"
                f"    - keywords={self.log_keywords}\n"
                f"3. 寻找错误状态码（如 500/502/503/504）\n"
                f"4. 检查是否有慢请求、超时或异常的响应时间\n"
                f"5. 提取可疑 IP、接口路径、User-Agent\n"
                f"{keyword_hint}"
            ),
            expected_output=(
                "输出简要日志分析，包括：服务器数量、相关日志数量、错误类型、异常模式、关键词命中的日志总结。"
            ),
            agent=self.log_analyst,
            verbose=True,
        )

        # 任务 2：指标分析
        self.metrics_research_task = Task(
            description=(
                f"请分析接口 {self.api_endpoint} 的服务指标。\n"
                f"步骤：\n"
                f"1. 使用 get_nginx_servers() 获取服务器列表\n"
                f"2. 使用 get_server_metrics() 获取各服务器关键指标\n"
                f"3. 关注指标：{', '.join(self.metrics_to_analyze)}\n"
                f"4. 找出异常服务器及其异常指标"
            ),
            expected_output=(
                "输出各服务器的指标总览、异常服务器说明，以及总体观察结论。"
            ),
            agent=self.metrics_inspector,
            verbose=True,
        )

        # 任务 3：根因诊断
        self.root_case_task = Task(
            description=(
                f"基于前两项分析，推断 {self.api_endpoint} 接口异常的最可能根因。"
            ),
            expected_output=(
                "输出Markdown格式的故障诊断报告，包括问题概述、证据链、根因推测及建议措施。"
            ),
            agent=self.root_cause_diagnostician,
            context=[self.log_research_task, self.metrics_research_task],
            markdown=True,
            output_file="diagnosis_report.md",
            verbose=True,
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
                self.log_analyst,
                self.metrics_inspector,
                self.root_cause_diagnostician
            ],
            tasks=[
                self.log_research_task,
                self.metrics_research_task,
                self.root_case_task
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
