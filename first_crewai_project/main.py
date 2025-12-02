#!/usr/bin/env python3
import os
from crewai import Crew, Agent, Task, Process
from crewai.llm import LLM  # 新增：导入LLM类
from dotenv import load_dotenv

# 1. 加载环境变量（从.env文件）
load_dotenv()


# 2. 创建 DeepSeek 专用的 LLM 配置
def create_deepseek_llm():
    """创建并返回一个配置好的DeepSeek LLM实例"""
    return LLM(
        model="deepseek-chat",  # DeepSeek模型名称
        base_url="https://api.deepseek.com",  # ⚠️ 必须是这个地址
        api_key=os.getenv("DEEPSEEK_API_KEY"),  # 从环境变量读取密钥
        temperature=0.7,
    )


# 3. 从YAML文件创建智能体（现在传入llm参数）
def create_agent_from_config():
    """创建研究员智能体"""
    return Agent(
        role='互联网研究员',
        goal='根据用户给定的主题，从互联网上查找最新、最相关的信息',
        backstory='你是一位资深的互联网研究员，擅长从海量信息中快速筛选出有价值的内容，并以清晰的方式呈现。',
        llm=create_deepseek_llm(),  # ⚠️ 关键：这里显式传入LLM配置
        verbose=True,
        allow_delegation=False  # 只有一个Agent，不需要委托
    )


# 4. 创建任务
def create_task(agent):
    return Task(
        description='请研究一下关于 {topic} 的最新发展和趋势，并整理成一份摘要。',
        expected_output='一份关于 {topic} 的简洁、有条理的摘要报告，包含关键要点。',
        agent=agent,
        verbose=True
    )


# 5. 主函数
def run():
    print("正在初始化DeepSeek LLM配置...")

    # 创建智能体
    researcher = create_agent_from_config()
    print("智能体创建成功！")

    # 创建任务
    research_task = create_task(researcher)

    # 创建Crew并运行
    crew = Crew(
        agents=[researcher],
        tasks=[research_task],
        verbose=True,  # 设置为2可以看到详细执行过程
        process=Process.sequential
    )

    # 运行Crew
    print("开始执行研究任务...")
    result = crew.kickoff(inputs={'topic': '人工智能在教育领域的应用'})

    # 打印结果
    print("\n" + "=" * 60)
    print("✅ 任务完成！结果如下：")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    run()