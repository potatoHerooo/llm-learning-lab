#!/usr/bin/env python3
#!/usr/bin/env python3
import os
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from dotenv import load_dotenv

# 🆕 修改导入方式：从tools包导入工具函数
from tools.mock_tools import get_nginx_servers, get_server_logs, get_server_metrics

load_dotenv()

class FaultDiagnosisCrew:
    """故障诊断智能体团队 (树状并行结构)"""

    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
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
            # ✅ 现在可以正确传递被@tool装饰后的函数
            tools=[get_nginx_servers, get_server_logs],
            verbose=True,
            allow_delegation=False
        )

    def create_metrics_inspector(self) -> Agent:
        return Agent(
            role="服务器指标分析专家",
            goal=f"分析{self.api_endpoint}对应服务的CPU、内存、错误率、请求延迟等关键性能指标，找出指标异常和时间关联性。",
            backstory="你是一个数据驱动的 SRE，精通各种监控系统。你对服务的健康指标非常敏感，能一眼看出成功率下降与 CPU 飙升、内存泄漏或下游依赖故障之间的关联。",
            llm=self.llm,
            # ✅ 现在可以正确传递被@tool装饰后的函数
            tools=[get_nginx_servers, get_server_metrics],
            verbose=True,
            allow_delegation=False
        )

    # ... 其他方法保持不变 ...
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
        """创建三个任务，并建立树状依赖关系"""

        # 任务一：日志分析 (独立并行任务)
        self.log_research_task = Task(
            description=(
                f"使用你拥有的工具，执行以下步骤来分析 {self.api_endpoint} 的日志：\n"
                f"1. 首先调用 get_nginx_servers() 获取所有服务器列表\n"
                f"2. 对每台服务器，调用 get_server_logs(server_ip, time_range_minutes=60) 获取日志\n"
                f"3. 从日志中筛选出与 {self.api_endpoint} 相关的记录，特别是错误日志（状态码4xx、5xx）\n"
                f"4. 分析错误模式、时间分布和可能的根本原因"
            ),
            expected_output=(
                "一份详细的日志分析报告，包含：\n"
                "1. 检查的服务器数量\n"
                "2. 找到的相关日志总数\n"
                "3. 错误日志的统计（按状态码分类）\n"
                "4. 关键发现：错误模式、时间规律、可疑客户端等\n"
                "5. 原始日志片段示例"
            ),
            agent=self.log_analyst,
            verbose=True,
        )

        # 任务二：指标分析 (独立并行任务)
        self.metrics_research_task = Task(
            description=(
                f"使用你拥有的工具，执行以下步骤来分析 {self.api_endpoint} 的指标：\n"
                f"1. 首先调用 get_nginx_servers() 获取所有服务器列表\n"
                f"2. 对每台服务器，调用 get_server_metrics(server_ip, time_range_minutes=60) 获取性能指标\n"
                f"3. 重点关注：成功率、响应延迟、CPU/内存使用率等关键指标\n"
                f"4. 识别异常指标和时间关联性"
            ),
            expected_output=(
                "一份详细的指标分析报告，包含：\n"
                "1. 检查的服务器数量\n"
                "2. 各服务器的关键指标概览（表格形式）\n"
                "3. 发现的异常指标及其严重程度\n"
                "4. 指标异常与时间的关系\n"
                "5. 对问题服务器的初步判断"
            ),
            agent=self.metrics_inspector,
            verbose=True,
        )

        # 任务三：根因诊断 (依赖前两个任务)
        self.root_case_task = Task(
            description=(
                f"你是一名资深架构师，请基于以下两份专家报告进行综合分析：\n\n"
                f"请根据日志分析专家和指标分析专家的调查结果，分析 {self.api_endpoint} 成功率下降的原因。\n"
                f"你需要综合两方面的证据，提出最可能的根本原因，并给出具体的排查建议。"
            ),
            expected_output=(
                "一份完整的故障诊断报告，使用Markdown格式，包含以下部分：\n"
                "1. 问题概述\n"
                "2. 证据链分析（日志+指标）\n"
                "3. 根因假设与可能性评估\n"
                "4. 立即行动建议\n"
                "5. 长期预防措施"
            ),
            agent=self.root_cause_diagnostician,
            # 使用 context 参数建立依赖关系
            context=[self.log_research_task, self.metrics_research_task],
            # 🆕 关键：不再在description中硬编码变量引用
            markdown=True,
            output_file="diagnosis_report.md",
            verbose=True,
        )
    def assemble_and_run(self):
        """组装Crew并运行"""

        print(f"🔍 开始故障诊断分析...")
        print(f"目标接口: {self.api_endpoint}")
        print("-" * 50)

        # 创建Crew，指定智能体、任务和流程
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
            # 使用顺序流程，但依赖关系已通过context建立
            # CrewAI会自动并行执行没有依赖的任务
            process=Process.sequential,
            verbose=True,
        )

        # 运行Crew，传入API端点参数
        print("🚀 启动智能体团队，开始并行分析...")
        result = crew.kickoff(inputs={"api_endpoint": self.api_endpoint})

        print("\n" + "=" * 60)
        print("✅ 诊断完成！")
        print(f"详细报告已保存至: diagnosis_report.md")
        print("=" * 60)

        return result

# 主程序入口
if __name__ == "__main__":
    # 使用示例：诊断特定API端点
    api_to_diagnose = "/api/v2/data.json"

    # 创建并运行故障诊断团队
    diagnosis_crew = FaultDiagnosisCrew(api_endpoint=api_to_diagnose)

    try:
        final_result = diagnosis_crew.assemble_and_run()

        # 打印最终结果的摘要
        print("\n📋 诊断结果摘要:")
        print("-" * 40)
        print(final_result)

    except Exception as e:
        print(f"❌ 运行过程中出现错误: {e}")
        print("请检查：")
        print("1. .env文件中DEEPSEEK_API_KEY是否正确设置")
        print("2. DeepSeek API密钥是否有足够额度")
        print("3. 网络连接是否正常")