#!/usr/bin/env python3
import os
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from dotenv import load_dotenv

# 导入工具函数
from tools.mock_tools import (
    get_nginx_servers,
    get_server_logs_simple as get_server_logs,
    get_server_metrics_simple as get_server_metrics
)

load_dotenv()


class FaultDiagnosisCrew:
    """故障诊断智能体团队 (树状并行结构)"""

    def __init__(self, api_endpoint: str, metrics_to_analyze: list[str]):
        self.api_endpoint = api_endpoint
        self.metrics_to_analyze = metrics_to_analyze
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

    def create_log_analyst(self) -> Agent:
        return Agent(
            role="服务器日志分析专家",
            goal=f"从Nginx日志中提取与{self.api_endpoint}相关的错误请求、响应码、延迟异常和客户端模式",
            backstory="你是一个严谨的运维工程师，对 Nginx 日志格式了如指掌，能快速从海量日志中过滤出异常模式，并擅长发现可疑的IP、异常 User-Agent 和错误激增的时间点。",
            llm=self.llm,
            tools=[get_nginx_servers, get_server_logs],
            verbose=True,
            allow_delegation=False
        )

    def create_metrics_inspector(self) -> Agent:
        if not self.metrics_to_analyze:
            self.metrics_to_analyze = ["cpu", "memory", "成功率", "延迟"]
        metrics_desc = "、".join(self.metrics_to_analyze)
        return Agent(
            role="服务器指标分析专家",
            goal=f"分析{self.api_endpoint}对应服务的{metrics_desc}等关键性能指标，找出指标异常和时间关联性。",
            backstory="你是一个数据驱动的 SRE，精通各种监控系统。你对服务的健康指标非常敏感，能一眼看出成功率下降与 CPU 飙升、内存泄漏或下游依赖故障之间的关联。",
            llm=self.llm,
            tools=[get_nginx_servers, get_server_metrics],
            verbose=True,
            allow_delegation=False
        )

    def create_root_cause_diagnostician(self) -> Agent:
        return Agent(
            role="根因诊断官",
            goal=f"综合日志和指标证据，推导出导致 {self.api_endpoint} 成功率下降最可能的根本原因，并提供下一步排查建议。",
            backstory="你是一个逻辑缜密的系统架构师，拥有多年故障排查经验。你善于将零散的线索拼凑成完整的逻辑链，提出合理的假设，并给出清晰、可操作的行动建议。",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def _create_tasks(self):
        """创建三个任务，使用简化的工具调用方式"""

        # 任务一：简化的日志分析任务
        self.log_research_task = Task(
            description=(
                f"请分析 {self.api_endpoint} 接口的Nginx日志。\n"
                f"步骤：\n"
                f"1. 首先使用 get_nginx_servers() 工具获取所有服务器列表\n"
                f"2. 对每个服务器，使用 get_server_logs() 工具获取日志，传入 api_endpoint='{self.api_endpoint}' 参数\n"  # 修改这里
                f"3. 分析日志中是否包含错误（如500、502、503、504状态码）\n"
                f"4. 分析日志中是否包含超时、异常等关键词\n"
                f"5. 总结发现的问题"
            ),
            expected_output=(
                "一份简明的日志分析报告，包含：\n"
                "1. 检查了多少台服务器\n"
                "2. 发现了多少条相关日志\n"
                "3. 主要的错误类型和数量\n"
                "4. 简要的分析结论"
            ),
            agent=self.log_analyst,
            verbose=True,
        )

        # 任务二：简化的指标分析任务
        self.metrics_research_task = Task(
            description=(
                f"请分析 {self.api_endpoint} 接口的服务指标。\n"
                f"步骤：\n"
                f"1. 首先使用 get_nginx_servers() 工具获取所有服务器列表\n"
                f"2. 对每个服务器，使用 get_server_metrics() 工具获取性能指标\n"
                f"3. 关注以下指标：{', '.join(self.metrics_to_analyze)}\n"
                f"4. 分析哪些服务器指标异常"
            ),
            expected_output=(
                "一份简明的指标分析报告，包含：\n"
                "1. 检查了多少台服务器\n"
                "2. 各服务器的关键指标概览\n"
                "3. 发现的问题服务器和异常指标\n"
                "4. 简要的分析结论"
            ),
            agent=self.metrics_inspector,
            verbose=True,
        )

        # 任务三：根因诊断
        self.root_case_task = Task(
            description=(
                f"请基于前两个专家的分析结果，综合分析 {self.api_endpoint} 成功率下降的原因。\n"
                f"结合日志分析和指标分析的结果，提出最可能的根本原因。"
            ),
            expected_output=(
                "一份完整的故障诊断报告，使用Markdown格式，包含以下部分：\n"
                "1. 问题概述\n"
                "2. 证据分析\n"
                "3. 根因假设\n"
                "4. 建议措施"
            ),
            agent=self.root_cause_diagnostician,
            context=[self.log_research_task, self.metrics_research_task],
            markdown=True,
            output_file="diagnosis_report.md",
            verbose=True,
        )

    def assemble_and_run(self):
        """组装Crew并运行"""
        print(f"🔍 开始故障诊断分析...")
        print(f"目标接口: {self.api_endpoint}")
        if self.metrics_to_analyze is not None:
            print(f"指定参数: {self.metrics_to_analyze}")
        print("-" * 50)

        # 创建Crew
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

        # 运行Crew
        print("🚀 启动智能体团队...")
        result = crew.kickoff(inputs={"api_endpoint": self.api_endpoint})

        print("\n" + "=" * 60)
        print("✅ 诊断完成！")
        print(f"详细报告已保存至: diagnosis_report.md")
        print("=" * 60)

        return result


# 主程序入口
if __name__ == "__main__":
    # 使用示例
    api_to_diagnose = "/api/v2/data.json"
    critical_metrics = ["cpu", "成功率"]  # 使用简化的指标名称

    diagnosis_crew = FaultDiagnosisCrew(
        api_endpoint=api_to_diagnose,
        metrics_to_analyze=critical_metrics
    )

    try:
        final_result = diagnosis_crew.assemble_and_run()
        print("\n📋 诊断结果摘要:")
        print("-" * 40)
        print(final_result)

    except Exception as e:
        print(f"❌ 运行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
